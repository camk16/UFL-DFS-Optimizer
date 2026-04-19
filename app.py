import streamlit as st
import pandas as pd
import io
from optimizer import (
    clean_dataframe,
    validate_csv,
    optimize_lineups,
    SALARY_CAP,
)

# ── Page Config ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="UFL DFS Optimizer",
    page_icon="🏈",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Custom CSS ────────────────────────────────────────────────────────────────
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Bebas+Neue&family=Inter:wght@300;400;500;600&display=swap');

    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
    }

    .main-title {
        font-family: 'Bebas Neue', sans-serif;
        font-size: 3.2rem;
        letter-spacing: 0.08em;
        color: #00C2FF;
        line-height: 1;
        margin-bottom: 0;
    }

    .sub-title {
        font-size: 0.9rem;
        color: #888;
        letter-spacing: 0.15em;
        text-transform: uppercase;
        margin-top: 0.2rem;
        margin-bottom: 1.5rem;
    }

    .section-header {
        font-family: 'Bebas Neue', sans-serif;
        font-size: 1.4rem;
        letter-spacing: 0.06em;
        color: #00C2FF;
        border-bottom: 1px solid #333;
        padding-bottom: 0.3rem;
        margin-top: 1.2rem;
        margin-bottom: 0.8rem;
    }

    .info-box {
        background: #1a1a2e;
        border-left: 3px solid #00C2FF;
        padding: 0.8rem 1rem;
        border-radius: 0 6px 6px 0;
        font-size: 0.85rem;
        color: #ccc;
        margin-bottom: 1rem;
    }

    .metric-card {
        background: #111827;
        border: 1px solid #1f2937;
        border-radius: 8px;
        padding: 0.8rem 1rem;
        text-align: center;
    }

    .stButton > button {
        background: linear-gradient(135deg, #00C2FF, #0077cc);
        color: white;
        font-family: 'Bebas Neue', sans-serif;
        font-size: 1.2rem;
        letter-spacing: 0.08em;
        border: none;
        border-radius: 6px;
        padding: 0.6rem 2rem;
        width: 100%;
        transition: opacity 0.2s;
    }

    .stButton > button:hover {
        opacity: 0.85;
    }

    .success-banner {
        background: #052e16;
        border: 1px solid #16a34a;
        border-radius: 6px;
        padding: 0.8rem 1rem;
        color: #4ade80;
        font-weight: 500;
        margin: 1rem 0;
    }

    div[data-testid="stDataFrame"] {
        border-radius: 8px;
        overflow: hidden;
    }
</style>
""", unsafe_allow_html=True)

# ── Header ────────────────────────────────────────────────────────────────────
st.markdown('<div class="main-title">🏈 UFL DFS OPTIMIZER</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-title">DraftKings · Lineup Generator · Powered by Linear Programming</div>', unsafe_allow_html=True)

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown('<div class="section-header">📁 Upload Projections</div>', unsafe_allow_html=True)

    st.markdown("""
    <div class="info-box">
    Upload your weekly CSV file containing player projections. Required columns:
    <b>Player, Position, Team, Salary, Ownership</b><br><br>
    Optional but recommended: <b>DK Points, Value, T.Val, Leverage, Pts/S, ID</b>
    </div>
    """, unsafe_allow_html=True)

    uploaded_file = st.file_uploader(
        "Choose your CSV file",
        type=["csv"],
        help="Download this from your projections source and upload here each week."
    )

    st.markdown('<div class="section-header">⚙️ Settings</div>', unsafe_allow_html=True)

    # Optimization metric — will be filtered to only show columns present in the uploaded CSV
    ALL_OPTIMIZE_OPTIONS = ["DK Points", "Value", "T.Val", "Leverage", "Pts/S"]
    optimize_by = st.selectbox(
        "Optimize By",
        options=ALL_OPTIMIZE_OPTIONS,
        index=0,
        help="Which metric to maximize when building lineups. DK Points = raw projected fantasy points. Value, T.Val, Leverage, and Pts/S are advanced metrics from your CSV."
    )

    # Number of lineups
    num_lineups = st.number_input(
        "Number of Lineups to Generate",
        min_value=1,
        max_value=150,
        value=1,
        step=1,
        help="How many unique lineups to generate. For tournaments, you might want 20–150. For cash games, 1 is fine."
    )

    st.markdown('<div class="section-header">💰 Salary</div>', unsafe_allow_html=True)

    min_salary = st.number_input(
        "Minimum Salary Used ($)",
        min_value=40000,
        max_value=SALARY_CAP,
        value=49000,
        step=100,
        help="The optimizer must use at least this much salary. Setting this high (like $49,000) prevents cheap, unrealistic lineups."
    )

    st.markdown('<div class="section-header">👥 Ownership & Exposure</div>', unsafe_allow_html=True)

    use_max_ownership = st.checkbox(
        "Cap Cumulative Ownership",
        value=False,
        help="Turn this on to avoid stacking high-ownership players together. Useful for tournament differentiation."
    )

    max_ownership = None
    if use_max_ownership:
        max_ownership = st.slider(
            "Max Total Ownership %",
            min_value=100,
            max_value=500,
            value=250,
            step=10,
            help="The sum of all 7 players' ownership percentages must be under this number. Lower = more contrarian lineup."
        )

    st.markdown('<div class="section-header">🏟️ Team Limits</div>', unsafe_allow_html=True)

    max_per_team = st.slider(
        "Max Players From One Team",
        min_value=1,
        max_value=5,
        value=4,
        step=1,
        help="Prevents loading up too many players from a single team. 4 is a common tournament setting."
    )

    st.markdown('<div class="section-header">🔗 QB Stack</div>', unsafe_allow_html=True)

    force_stack = st.checkbox(
        "Force QB + WR/TE Stack",
        value=False,
        help="When checked, the optimizer will always pair the QB with at least 1 WR or TE from the same team. Recommended for tournaments."
    )

    stack_count = 1
    if force_stack:
        stack_count = st.radio(
            "WR/TE Stackmates Required",
            options=[1, 2],
            index=0,
            help="How many WR/TE from the QB's team to include. 1 = single stack, 2 = double stack."
        )

# ── Main Area ─────────────────────────────────────────────────────────────────
if uploaded_file is None:
    st.markdown("""
    <div class="info-box" style="font-size:1rem; padding: 1.5rem;">
    👈 <b>Get started by uploading your CSV file in the sidebar.</b><br><br>
    Once uploaded, your player pool will appear here and you can configure
    constraints and generate optimized lineups.
    </div>
    """, unsafe_allow_html=True)

    st.markdown("### 📋 Expected CSV Format")
    sample_data = pd.DataFrame({
        "Player": ["Patrick Mahomes", "Tyreek Hill", "Travis Kelce", "Isiah Pacheco", "Rashee Rice", "Mecole Hardman", "Chiefs DST"],
        "Position": ["QB", "WR", "TE", "RB", "WR", "WR", "DST"],
        "Team": ["KC", "KC", "KC", "KC", "KC", "KC", "KC"],
        "Salary": [8400, 7600, 6800, 6200, 5800, 4200, 3200],
        "DK Points": [28.4, 22.1, 14.3, 16.8, 12.4, 8.2, 9.1],
        "Value": [3.38, 2.91, 2.10, 2.71, 2.14, 1.95, 2.84],
        "Ownership": [28.5, 18.2, 14.1, 22.3, 15.6, 8.4, 12.0],
        "ID": [11191729, 11192543, 11192100, 11193021, 11192876, 11193154, 11190044],
        "Leverage": [1.2, 0.9, 0.6, 1.1, 0.7, 0.5, 0.4],
        "Pts/S": [3.38, 2.91, 2.10, 2.71, 2.14, 1.95, 2.84],
        "T.Val": [3.4, 2.8, 1.9, 2.6, 1.8, 1.2, 1.0],
    })
    st.dataframe(sample_data, use_container_width=True, hide_index=True)

else:
    # ── Load & Validate CSV ───────────────────────────────────────────────────
    try:
        raw_df = pd.read_csv(uploaded_file)
        validate_csv(raw_df)
        df = clean_dataframe(raw_df)

        # Detect available optimization columns
        ALL_OPTIMIZE_OPTIONS = ["DK Points", "Value", "T.Val", "Leverage", "Pts/S"]
        available_opts = [c for c in ALL_OPTIMIZE_OPTIONS if c in df.columns]
        if optimize_by not in available_opts:
            st.warning(f"⚠️ '{optimize_by}' column not found in your CSV. Available options: {available_opts}. Please select a different metric in the sidebar.")
            st.stop()

    except ValueError as e:
        st.error(f"❌ CSV Error: {e}")
        st.stop()
    except Exception as e:
        st.error(f"❌ Could not read your file: {e}")
        st.stop()

    # ── Player Pool ───────────────────────────────────────────────────────────
    st.markdown('<div class="section-header">📊 Player Pool</div>', unsafe_allow_html=True)

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Players", len(df))
    with col2:
        st.metric("QBs", len(df[df["Position"] == "QB"]))
    with col3:
        st.metric("RBs", len(df[df["Position"] == "RB"]))
    with col4:
        st.metric("WRs / TEs", len(df[df["Position"].isin(["WR", "TE"])]))

    # Filter by position for easier viewing
    pos_filter = st.multiselect(
        "Filter by Position",
        options=sorted(df["Position"].unique()),
        default=[],
        help="Filter the table below to specific positions. Leave blank to show all."
    )

    display_df = df if not pos_filter else df[df["Position"].isin(pos_filter)]

    # Show columns that exist
    show_cols = ["Player", "Position", "Team", "Salary", "Ownership"]
    for opt_col in ["DK Points", "Value", "T.Val", "Leverage", "Pts/S"]:
        if opt_col in df.columns:
            show_cols.append(opt_col)
    if "ID" in df.columns:
        show_cols.append("ID")

    st.dataframe(
        display_df[show_cols].sort_values("Salary", ascending=False),
        use_container_width=True,
        hide_index=True,
    )

    # ── Player Locks / Excludes ───────────────────────────────────────────────
    st.markdown('<div class="section-header">🔒 Lock & Exclude Players</div>', unsafe_allow_html=True)

    col_lock, col_excl = st.columns(2)

    with col_lock:
        st.markdown("**Lock Players** — Force into every lineup")
        locked = st.multiselect(
            "Select players to lock",
            options=sorted(df["Player"].tolist()),
            default=[],
            help="These players will appear in every lineup generated."
        )

    with col_excl:
        st.markdown("**Exclude Players** — Remove from all lineups")
        excluded = st.multiselect(
            "Select players to exclude",
            options=sorted(df["Player"].tolist()),
            default=[],
            help="These players will never appear in any lineup."
        )

    # ── Exposure Controls (multi-lineup only) ─────────────────────────────────
    if num_lineups > 1:
        st.markdown('<div class="section-header">📈 Exposure Limits (Optional)</div>', unsafe_allow_html=True)
        st.markdown("""
        <div class="info-box">
        Exposure = what % of lineups a player appears in. For example, if you generate 20 lineups and
        cap a player at 50% exposure, they'll appear in at most 10 lineups. Leave blank to apply no limits.
        </div>
        """, unsafe_allow_html=True)

        exp_player = st.multiselect(
            "Set max exposure for specific players",
            options=sorted(df["Player"].tolist()),
            default=[],
        )

        max_exposure_dict = {}
        if exp_player:
            for p in exp_player:
                pct = st.slider(
                    f"{p} — Max Exposure %",
                    min_value=10,
                    max_value=100,
                    value=50,
                    step=10,
                    key=f"exp_{p}",
                )
                max_exposure_dict[p] = max(1, int((pct / 100) * num_lineups))
    else:
        max_exposure_dict = {}

    # ── Generate Button ───────────────────────────────────────────────────────
    st.markdown("---")
    run_col, _ = st.columns([1, 2])
    with run_col:
        run_optimizer = st.button("🚀 Generate Lineups")

    if run_optimizer:
        with st.spinner(f"Generating {num_lineups} lineup(s)... This may take a moment for large batches."):
            try:
                results = optimize_lineups(
                    df=df,
                    optimize_by=optimize_by,
                    num_lineups=num_lineups,
                    min_salary=min_salary,
                    max_salary=SALARY_CAP,
                    max_players_per_team=max_per_team,
                    max_cumulative_ownership=max_ownership,
                    force_qb_stack=force_stack,
                    qb_stack_count=stack_count,
                    locked_players=locked,
                    excluded_players=excluded,
                    max_exposure=max_exposure_dict,
                )
            except ValueError as e:
                st.error(f"❌ Optimizer Error: {e}")
                st.stop()
            except Exception as e:
                st.error(f"❌ Unexpected error: {e}")
                st.stop()

        if not results:
            st.warning("⚠️ No valid lineups could be generated with the current constraints. Try relaxing your settings (e.g. lower the min salary, reduce ownership cap, or unlock players).")
        else:
            actual = len(results)
            requested = num_lineups
            if actual < requested:
                st.warning(f"⚠️ Only {actual} unique lineup(s) could be generated (requested {requested}). Try relaxing your constraints to get more.")
            else:
                st.markdown(f'<div class="success-banner">✅ Successfully generated {actual} lineup(s)!</div>', unsafe_allow_html=True)

            results_df = pd.DataFrame(results)

            # ── Results Table ─────────────────────────────────────────────────
            st.markdown('<div class="section-header">📋 Generated Lineups</div>', unsafe_allow_html=True)
            st.dataframe(results_df, use_container_width=True, hide_index=True)

            # ── Summary Stats ─────────────────────────────────────────────────
            st.markdown('<div class="section-header">📊 Summary</div>', unsafe_allow_html=True)
            stat_col1, stat_col2, stat_col3, stat_col4 = st.columns(4)

            score_col = f"Total {optimize_by}"
            own_col = "Total Ownership"
            sal_col = "Total Salary"

            with stat_col1:
                st.metric("Lineups Generated", actual)
            with stat_col2:
                st.metric(f"Avg {optimize_by}", round(results_df[score_col].mean(), 2))
            with stat_col3:
                st.metric("Avg Ownership %", round(results_df[own_col].mean(), 1))
            with stat_col4:
                st.metric("Avg Salary Used", f"${int(results_df[sal_col].mean()):,}")

            # ── Download ──────────────────────────────────────────────────────
            st.markdown('<div class="section-header">⬇️ Download Lineups</div>', unsafe_allow_html=True)

            dl_col1, dl_col2 = st.columns(2)

            # Full results CSV
            csv_full = results_df.to_csv(index=False)
            with dl_col1:
                st.download_button(
                    label="📥 Download Full Results (CSV)",
                    data=csv_full,
                    file_name="ufl_lineups_full.csv",
                    mime="text/csv",
                    help="Download all lineup details including salary, ownership, and projected scores."
                )

            # DK-formatted export
            dk_cols = ["QB", "RB", "WR/TE 1", "WR/TE 2", "FLEX 1", "FLEX 2", "DST"]
            available_dk_cols = [c for c in dk_cols if c in results_df.columns]
            if available_dk_cols:
                dk_df = results_df[available_dk_cols]
                csv_dk = dk_df.to_csv(index=False)
                with dl_col2:
                    st.download_button(
                        label="📥 Download DraftKings Upload Format",
                        data=csv_dk,
                        file_name="ufl_lineups_dk.csv",
                        mime="text/csv",
                        help="Download lineups formatted for DraftKings bulk upload."
                    )
