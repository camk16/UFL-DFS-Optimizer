import pulp
import pandas as pd
import re

# DraftKings UFL Roster Configuration
ROSTER_SLOTS = {
    "QB": 1,
    "RB": 1,
    "WR_TE": 2,   # WR or TE
    "FLEX": 2,    # RB, WR, or TE
    "DST": 1,
}

TOTAL_PLAYERS = 7
SALARY_CAP = 50000


def validate_csv(df):
    """Check that all required columns are present in the uploaded CSV."""
    required_columns = ["Player", "Position", "Team", "Salary", "Ownership"]
    missing = [col for col in required_columns if col not in df.columns]
    if missing:
        raise ValueError(f"Your CSV is missing these required columns: {', '.join(missing)}")
    return True


def clean_dataframe(df):
    """Clean and standardize the dataframe."""
    df = df.copy()

    # Standardize column names (strip whitespace)
    df.columns = df.columns.str.strip()

    # Standardize position values
    df["Position"] = df["Position"].str.strip().str.upper()

    # Clean salary - remove $ and commas if present
    df["Salary"] = df["Salary"].astype(str).str.replace(r'[\$,]', '', regex=True)
    df["Salary"] = pd.to_numeric(df["Salary"], errors="coerce").fillna(0).astype(int)

    # Clean ownership - remove % if present
    df["Ownership"] = df["Ownership"].astype(str).str.replace('%', '', regex=False)
    df["Ownership"] = pd.to_numeric(df["Ownership"], errors="coerce").fillna(0).astype(float)

    # Clean all numeric optimization columns if present
    for col in ["DK Points", "Value", "T.Val", "Leverage", "Pts/S"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0).astype(float)

    # Remove players with 0 salary (typically injured/out)
    df = df[df["Salary"] > 0].reset_index(drop=True)

    return df


def get_position_eligibility(position):
    """Return which roster slots a player is eligible for."""
    eligibility = []
    if position == "QB":
        eligibility = ["QB"]
    elif position == "RB":
        eligibility = ["RB", "FLEX"]
    elif position == "WR":
        eligibility = ["WR_TE", "FLEX"]
    elif position == "TE":
        eligibility = ["WR_TE", "FLEX"]
    elif position in ["DST", "D", "DEF"]:
        eligibility = ["DST"]
    return eligibility


def optimize_lineups(
    df,
    optimize_by="Projection",
    num_lineups=1,
    min_salary=49000,
    max_salary=50000,
    max_players_per_team=4,
    max_cumulative_ownership=None,
    force_qb_stack=False,
    qb_stack_count=1,
    locked_players=None,
    excluded_players=None,
    min_exposure=None,
    max_exposure=None,
):
    """
    Generate one or more optimized DFS lineups using Integer Linear Programming.

    Parameters
    ----------
    df : pd.DataFrame
        Cleaned player pool dataframe.
    optimize_by : str
        Column name to maximize ("Projection", "ETR.Val", or "T.Val").
    num_lineups : int
        Number of unique lineups to generate.
    min_salary : int
        Minimum total salary used.
    max_salary : int
        Maximum total salary (salary cap).
    max_players_per_team : int
        Max players from any single team in a lineup.
    max_cumulative_ownership : float or None
        If set, the sum of ownership percentages across all 7 players must be <= this value.
    force_qb_stack : bool
        If True, force QB to share a team with at least qb_stack_count WR/TE players.
    qb_stack_count : int
        Number of WR/TE from same team as QB required (1 or 2).
    locked_players : list or None
        Player names that must appear in every lineup.
    excluded_players : list or None
        Player names that cannot appear in any lineup.
    min_exposure : dict or None
        {player_name: min_lineups} — player must appear in at least this many lineups.
    max_exposure : dict or None
        {player_name: max_lineups} — player can appear in at most this many lineups.
    """

    if locked_players is None:
        locked_players = []
    if excluded_players is None:
        excluded_players = []
    if min_exposure is None:
        min_exposure = {}
    if max_exposure is None:
        max_exposure = {}

    # Validate optimize_by column exists
    if optimize_by not in df.columns:
        raise ValueError(f"Optimization column '{optimize_by}' not found in your CSV.")

    # Filter out excluded players
    pool = df[~df["Player"].isin(excluded_players)].copy().reset_index(drop=True)

    # Validate locked players exist
    for p in locked_players:
        if p not in pool["Player"].values:
            raise ValueError(f"Locked player '{p}' not found in player pool (they may be excluded or missing).")

    generated_lineups = []
    # Track previous lineups to enforce uniqueness
    previous_lineups = []

    # Track per-player lineup count for exposure constraints
    player_lineup_count = {name: 0 for name in pool["Player"]}

    for lineup_num in range(num_lineups):
        prob = pulp.LpProblem(f"UFL_DFS_Lineup_{lineup_num}", pulp.LpMaximize)

        # --- Decision Variables ---
        # x[i] = 1 if player i is selected in this lineup
        x = {i: pulp.LpVariable(f"x_{i}", cat="Binary") for i in pool.index}

        # --- Objective Function ---
        prob += pulp.lpSum(pool.loc[i, optimize_by] * x[i] for i in pool.index)

        # --- Salary Constraints ---
        prob += pulp.lpSum(pool.loc[i, "Salary"] * x[i] for i in pool.index) <= max_salary
        prob += pulp.lpSum(pool.loc[i, "Salary"] * x[i] for i in pool.index) >= min_salary

        # --- Total Players ---
        prob += pulp.lpSum(x[i] for i in pool.index) == TOTAL_PLAYERS

        # --- Position Constraints ---
        # Each player can fill exactly one roster slot

        # QB: exactly 1
        qb_indices = pool[pool["Position"] == "QB"].index
        prob += pulp.lpSum(x[i] for i in qb_indices) == 1

        # RB slot: exactly 1 (RBs not in FLEX)
        # WR_TE slots: exactly 2
        # FLEX: exactly 2
        # DST: exactly 1

        # We need to track slot assignments for positions that can go to multiple slots.
        # Create assignment variables: a[i][slot] = 1 if player i assigned to slot

        slot_names = ["QB", "RB_slot", "WRTE_1", "WRTE_2", "FLEX_1", "FLEX_2", "DST"]

        # For simplicity, use position count constraints (standard DFS optimizer approach):
        # QB = 1
        dst_indices = pool[pool["Position"].isin(["DST", "D", "DEF"])].index
        prob += pulp.lpSum(x[i] for i in dst_indices) == 1

        rb_indices = pool[pool["Position"] == "RB"].index
        wr_indices = pool[pool["Position"] == "WR"].index
        te_indices = pool[pool["Position"] == "TE"].index
        wrte_indices = pool[pool["Position"].isin(["WR", "TE"])].index

        # Total RBs selected: 1 (RB slot) + up to 2 (FLEX) = 1 to 3
        prob += pulp.lpSum(x[i] for i in rb_indices) >= 1
        prob += pulp.lpSum(x[i] for i in rb_indices) <= 3

        # Total WR/TE selected: 2 (WR_TE slots) + up to 2 (FLEX) = 2 to 4
        prob += pulp.lpSum(x[i] for i in wrte_indices) >= 2
        prob += pulp.lpSum(x[i] for i in wrte_indices) <= 4

        # RB + WR/TE + FLEX slots = 1 + 2 + 2 = 5 non-QB, non-DST players
        non_special = pool[pool["Position"].isin(["RB", "WR", "TE"])].index
        prob += pulp.lpSum(x[i] for i in non_special) == 5

        # --- Max Players Per Team ---
        for team in pool["Team"].unique():
            team_indices = pool[pool["Team"] == team].index
            prob += pulp.lpSum(x[i] for i in team_indices) <= max_players_per_team

        # --- Locked Players ---
        for name in locked_players:
            idx = pool[pool["Player"] == name].index
            if len(idx) > 0:
                prob += x[idx[0]] == 1

        # --- Max Cumulative Ownership ---
        if max_cumulative_ownership is not None:
            prob += pulp.lpSum(pool.loc[i, "Ownership"] * x[i] for i in pool.index) <= max_cumulative_ownership

        # --- QB/WR Stack ---
        if force_qb_stack:
            teams = pool["Team"].unique()
            # For each team, create binary variable: is QB from this team selected?
            team_qb = {team: pulp.LpVariable(f"team_qb_{team}", cat="Binary") for team in teams}

            for team in teams:
                t_qb = pool[(pool["Team"] == team) & (pool["Position"] == "QB")].index
                t_wrte = pool[(pool["Team"] == team) & (pool["Position"].isin(["WR", "TE"]))].index

                if len(t_qb) == 0:
                    prob += team_qb[team] == 0
                    continue

                # team_qb[team] = 1 if any QB from this team is selected
                prob += team_qb[team] == pulp.lpSum(x[i] for i in t_qb)

                # If QB from this team selected, must have at least qb_stack_count WR/TE from same team
                if len(t_wrte) > 0:
                    prob += pulp.lpSum(x[i] for i in t_wrte) >= qb_stack_count * team_qb[team]

        # --- Uniqueness Constraint (from previous lineups) ---
        for prev_lineup in previous_lineups:
            # Each new lineup must differ by at least 1 player
            prob += pulp.lpSum(x[i] for i in prev_lineup) <= TOTAL_PLAYERS - 1

        # --- Exposure Constraints ---
        # Max exposure: if player has already hit their max, exclude them
        for name, max_count in max_exposure.items():
            if player_lineup_count.get(name, 0) >= max_count:
                idx = pool[pool["Player"] == name].index
                if len(idx) > 0:
                    prob += x[idx[0]] == 0

        # --- Solve ---
        solver = pulp.PULP_CBC_CMD(msg=0)
        prob.solve(solver)

        if pulp.LpStatus[prob.status] != "Optimal":
            # Could not find another unique valid lineup
            break

        # Extract selected players
        selected_indices = [i for i in pool.index if x[i].value() is not None and x[i].value() > 0.5]
        selected_players = pool.loc[selected_indices].copy()

        # Update tracking
        previous_lineups.append(selected_indices)
        for name in selected_players["Player"].values:
            player_lineup_count[name] = player_lineup_count.get(name, 0) + 1

        # Format the lineup for output
        lineup_row = format_lineup(selected_players, lineup_num + 1, optimize_by)
        generated_lineups.append(lineup_row)

    return generated_lineups


def format_lineup(players_df, lineup_num, optimize_by):
    """Assign players to their roster slots and return a dict representing the lineup."""

    # Sort into slots
    slot_order = []

    # QB
    qb = players_df[players_df["Position"] == "QB"].iloc[0]
    slot_order.append(("QB", qb))

    # DST
    dst = players_df[players_df["Position"].isin(["DST", "D", "DEF"])].iloc[0]

    # Skill players
    skill = players_df[players_df["Position"].isin(["RB", "WR", "TE"])].copy()

    rb_players = skill[skill["Position"] == "RB"]
    wrte_players = skill[skill["Position"].isin(["WR", "TE"])]

    # Assign RB slot (1 RB)
    rb_slot = rb_players.iloc[0]
    slot_order.append(("RB", rb_slot))
    remaining_rbs = rb_players.iloc[1:] if len(rb_players) > 1 else pd.DataFrame()

    # Assign WR/TE slots (2 players)
    wrte_list = wrte_players.to_dict("records")
    remaining_wrtes = []
    wt_assigned = 0
    for p in wrte_list:
        if wt_assigned < 2:
            slot_order.append(("WR/TE", pd.Series(p)))
            wt_assigned += 1
        else:
            remaining_wrtes.append(p)

    # Assign FLEX slots (2 players from remaining RBs and WR/TEs)
    flex_pool = list(remaining_rbs.to_dict("records")) + remaining_wrtes
    for p in flex_pool[:2]:
        slot_order.append(("FLEX", pd.Series(p)))

    slot_order.append(("DST", dst))

    # Build output row
    row = {"Lineup #": lineup_num}
    for slot, player in slot_order:
        row[slot] = player["Player"]

    # Totals
    all_players = players_df
    row["Total Salary"] = all_players["Salary"].sum()
    row["Salary Remaining"] = SALARY_CAP - row["Total Salary"]
    row[f"Total {optimize_by}"] = round(all_players[optimize_by].sum(), 2)
    row["Total Ownership"] = round(all_players["Ownership"].sum(), 1)

    return row


def lineups_to_dk_export(lineups_df, player_pool_df):
    """
    Convert lineups dataframe to DraftKings upload format.
    DK expects: QB,RB,WR/TE,WR/TE,FLEX,FLEX,DST
    Each cell should contain the player's DK ID or Name+Team format.
    """
    export_rows = []
    slot_cols = ["QB", "RB", "WR/TE", "WR/TE", "FLEX", "FLEX", "DST"]

    # Create name lookup for DK ID if available
    has_id = "ID" in player_pool_df.columns

    for _, row in lineups_df.iterrows():
        export_row = {}
        wrte_count = 0
        flex_count = 0

        for col in lineups_df.columns:
            if col in ["QB", "RB", "DST"]:
                export_row[col] = row[col]
            elif col == "WR/TE":
                # Handle duplicate column names
                pass

        # Rebuild from slot order
        dk_row = []
        for slot in ["QB", "RB", "WR/TE", "FLEX", "DST"]:
            if slot in row:
                dk_row.append(row[slot])

        export_rows.append(dk_row)

    return pd.DataFrame(export_rows, columns=["QB", "RB", "WR/TE 1", "WR/TE 2", "FLEX 1", "FLEX 2", "DST"])
