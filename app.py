import streamlit as st
import pandas as pd
from collections import Counter
from optimizer import (
    clean_dataframe,
    validate_csv,
    optimize_lineups,
    SALARY_CAP,
)

# ── Page Config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="UFL DFS Optimizer",
    page_icon="🏈",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Session State ─────────────────────────────────────────────────────────────
if "saved_lineups" not in st.session_state:
    st.session_state.saved_lineups = []
if "last_results" not in st.session_state:
    st.session_state.last_results = []
if "gen_checked" not in st.session_state:
    st.session_state.gen_checked = {}   # lineup_num -> bool
if "saved_checked" not in st.session_state:
    st.session_state.saved_checked = {} # lineup_num -> bool
if "lineup_tags" not in st.session_state:
    st.session_state.lineup_tags = {}   # lineup_num -> tag string
if "saved_display_metric" not in st.session_state:
    st.session_state.saved_display_metric = None  # chosen metric on saved tab

# ── CSS ───────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Bebas+Neue&family=Inter:wght@300;400;500;600&display=swap');
    html, body, [class*="css"] { font-family: 'Inter', sans-serif; }

    .main-title {
        font-family: 'Bebas Neue', sans-serif;
        font-size: 3.2rem; letter-spacing: 0.08em;
        color: #00C2FF; line-height: 1; margin-bottom: 0;
    }
    .sub-title {
        font-size: 0.9rem; color: #888;
        letter-spacing: 0.15em; text-transform: uppercase;
        margin-top: 0.2rem; margin-bottom: 1.5rem;
    }
    .section-header {
        font-family: 'Bebas Neue', sans-serif;
        font-size: 1.4rem; letter-spacing: 0.06em; color: #00C2FF;
        border-bottom: 1px solid #333;
        padding-bottom: 0.3rem; margin-top: 1.2rem; margin-bottom: 0.8rem;
    }
    .info-box {
        background: #1a1a2e; border-left: 3px solid #00C2FF;
        padding: 0.8rem 1rem; border-radius: 0 6px 6px 0;
        font-size: 0.85rem; color: #ccc; margin-bottom: 1rem;
    }
    .success-banner {
        background: #052e16; border: 1px solid #16a34a;
        border-radius: 6px; padding: 0.8rem 1rem;
        color: #4ade80; font-weight: 500; margin: 1rem 0;
    }
    div[data-testid="stDataFrame"] { border-radius: 8px; overflow: hidden; }

    /* ── Lineup Card Grid ── */
    .cards-grid {
        display: grid;
        grid-template-columns: repeat(4, 1fr);
        gap: 12px;
        margin-bottom: 1.5rem;
    }
    .lineup-card {
        background: #111827;
        border: 1px solid #1f2937;
        border-radius: 8px;
        overflow: hidden;
        font-size: 0.78rem;
    }
    .card-header {
        background: #0f172a;
        border-bottom: 1px solid #1f2937;
        padding: 7px 10px;
        display: flex;
        justify-content: space-between;
        align-items: center;
    }
    .card-header-num {
        font-family: 'Bebas Neue', sans-serif;
        font-size: 1rem; letter-spacing: 0.05em; color: #00C2FF;
    }
    .card-header-score {
        font-family: 'Bebas Neue', sans-serif;
        font-size: 1.15rem; color: #f0f0f0; letter-spacing: 0.03em;
    }
    .card-header-meta {
        font-size: 0.7rem; color: #6b7280; text-align: right; line-height: 1.4;
    }
    .card-header-meta span { color: #9ca3af; }
    .card-body { padding: 0; }
    .player-row {
        display: flex;
        align-items: center;
        padding: 4px 10px;
        border-bottom: 1px solid #1a2235;
        gap: 7px;
    }
    .player-row:last-child { border-bottom: none; }
    .player-row:hover { background: #1a2535; }
    .pos-badge {
        font-size: 0.62rem; font-weight: 700;
        padding: 1px 5px; border-radius: 3px;
        min-width: 36px; text-align: center;
        letter-spacing: 0.04em; flex-shrink: 0;
    }
    .pos-QB  { background: #7c3aed22; color: #a78bfa; border: 1px solid #7c3aed44; }
    .pos-RB  { background: #06522422; color: #34d399; border: 1px solid #06522444; }
    .pos-WRTE { background: #0c4a6e22; color: #38bdf8; border: 1px solid #0c4a6e44; }
    .pos-FLEX { background: #78350f22; color: #fbbf24; border: 1px solid #78350f44; }
    .pos-DST { background: #7f1d1d22; color: #f87171; border: 1px solid #7f1d1d44; }
    .player-team {
        font-size: 0.65rem; color: #6b7280;
        min-width: 28px; flex-shrink: 0;
        font-weight: 600; letter-spacing: 0.04em;
    }
    .player-name {
        flex: 1; color: #e5e7eb;
        font-weight: 500; white-space: nowrap;
        overflow: hidden; text-overflow: ellipsis;
    }
    .player-sal  { color: #6b7280; min-width: 38px; text-align: right; flex-shrink: 0; }
    .player-proj { color: #9ca3af; min-width: 32px; text-align: right; flex-shrink: 0; }
    .player-own  { color: #4b5563; min-width: 34px; text-align: right; flex-shrink: 0; font-size: 0.68rem; }
    .card-saved-badge {
        background: #052e16; color: #4ade80;
        font-size: 0.65rem; padding: 1px 6px;
        border-radius: 3px; border: 1px solid #16a34a;
    }
</style>
""", unsafe_allow_html=True)


# ── Helpers ───────────────────────────────────────────────────────────────────

SLOT_COLS = ["QB", "RB", "WR/TE 1", "WR/TE 2", "FLEX 1", "FLEX 2", "DST"]

SLOT_DISPLAY = {
    "QB":      ("QB",   "pos-QB"),
    "RB":      ("RB",   "pos-RB"),
    "WR/TE 1": ("WR/TE","pos-WRTE"),
    "WR/TE 2": ("WR/TE","pos-WRTE"),
    "FLEX 1":  ("FLEX", "pos-FLEX"),
    "FLEX 2":  ("FLEX", "pos-FLEX"),
    "DST":     ("DST",  "pos-DST"),
}


def build_player_lookup(df):
    """Return dict: player_name -> {Team, DK Points/etc, Ownership, Salary}"""
    lookup = {}
    if df is None:
        return lookup
    for _, r in df.iterrows():
        lookup[r["Player"]] = r.to_dict()
    return lookup


def format_salary(val):
    try:
        return f"${int(val):,}"
    except Exception:
        return str(val)


def calc_total_score(lineup, metric, plookup):
    """Sum metric values from player_lookup for all 7 slots — works for any metric."""
    total = 0.0
    for slot in SLOT_COLS:
        name = lineup.get(slot, "")
        if name and name in plookup:
            val = plookup[name].get(metric, 0)
            if isinstance(val, (int, float)):
                total += val
    return total


def render_lineup_cards(lineups, player_lookup, optimize_by, saved_set,
                        mode="gen", id_prefix="gen"):
    """
    Render lineups as a 4-column card grid inside iframes.
    mode="gen"   -> show checkboxes, cards marked if already saved
    mode="saved" -> show checkboxes for deletion
    Checkboxes stored in st.session_state.gen_checked / saved_checked.
    """
    import streamlit.components.v1 as components

    cards_per_row = 4
    rows = [lineups[i:i+cards_per_row] for i in range(0, len(lineups), cards_per_row)]

    checked_state = st.session_state.gen_checked if mode == "gen" else st.session_state.saved_checked


    card_css = """
    <style>
      @import url('https://fonts.googleapis.com/css2?family=Bebas+Neue&family=Inter:wght@400;500;600&display=swap');
      * { box-sizing: border-box; margin: 0; padding: 0; }
      body { background: transparent; font-family: 'Inter', sans-serif; }
      .cards-grid {
        display: grid;
        grid-template-columns: repeat(4, 1fr);
        gap: 10px; padding: 4px 2px;
      }
      .lineup-card {
        background: #111827; border: 1px solid #1f2937;
        border-radius: 8px; overflow: hidden; font-size: 0.76rem;
      }
      .card-header {
        background: #0f172a; border-bottom: 1px solid #1f2937;
        padding: 7px 10px; display: flex;
        justify-content: space-between; align-items: flex-start;
      }
      .card-num {
        font-family: 'Bebas Neue', sans-serif;
        font-size: 0.85rem; letter-spacing: 0.05em; color: #00C2FF;
      }
      .card-score {
        font-family: 'Bebas Neue', sans-serif;
        font-size: 1.2rem; color: #f0f0f0; letter-spacing: 0.02em; margin-top: 1px;
      }
      .card-meta { font-size: 0.67rem; color: #6b7280; text-align: right; line-height: 1.55; }
      .card-meta span { color: #9ca3af; }
      .saved-badge {
        display: inline-block; background: #052e16; color: #4ade80;
        font-size: 0.6rem; padding: 1px 5px; border-radius: 3px;
        border: 1px solid #16a34a; vertical-align: middle; margin-left: 4px;
      }
      .player-row {
        display: flex; align-items: center;
        padding: 4px 10px; border-bottom: 1px solid #1a2235; gap: 6px;
      }
      .player-row:last-child { border-bottom: none; }
      .pos-badge {
        font-size: 0.6rem; font-weight: 700; padding: 1px 4px; border-radius: 3px;
        min-width: 38px; text-align: center; letter-spacing: 0.03em; flex-shrink: 0;
      }
      .pos-QB   { background: #3b1f6e; color: #c4b5fd; border: 1px solid #7c3aed55; }
      .pos-RB   { background: #052e16; color: #6ee7b7; border: 1px solid #05522455; }
      .pos-WRTE { background: #082f49; color: #7dd3fc; border: 1px solid #0c4a6e55; }
      .pos-FLEX { background: #3d1f05; color: #fcd34d; border: 1px solid #78350f55; }
      .pos-DST  { background: #3d0707; color: #fca5a5; border: 1px solid #7f1d1d55; }
      .p-team { font-size: 0.63rem; color: #6b7280; font-weight: 600; min-width: 28px; flex-shrink: 0; letter-spacing: 0.04em; }
      .p-name { flex: 1; color: #e5e7eb; font-weight: 500; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
      .p-sal  { color: #6b7280; min-width: 40px; text-align: right; flex-shrink: 0; }
      .p-proj { color: #9ca3af; min-width: 30px; text-align: right; flex-shrink: 0; }
      .p-own  { color: #4b5563; min-width: 34px; text-align: right; flex-shrink: 0; font-size: 0.65rem; }
      .p-opp  { font-size: 0.6rem; color: #374151; min-width: 26px; flex-shrink: 0; font-style: italic; }
      .tag-badge {
        display: inline-block; background: #1e3a5f; color: #60a5fa;
        font-size: 0.58rem; padding: 1px 5px; border-radius: 3px;
        border: 1px solid #2563eb55; vertical-align: middle; margin-left: 4px;
        font-family: 'Inter', sans-serif; font-weight: 600; letter-spacing: 0.03em;
      }
    </style>
    """

    for row_lineups in rows:
        # ── iframe card row ───────────────────────────────────────────────────
        cards_html = ""
        for lineup in row_lineups:
            lineup_num    = lineup.get("Lineup #", "?")
            already_saved = lineup_num in saved_set

            # Always calculate score live from player data so metric switcher works
            total_score = calc_total_score(lineup, optimize_by, player_lookup)
            total_sal   = lineup.get("Total Salary", 0)
            sal_rem     = lineup.get("Salary Remaining", SALARY_CAP - total_sal)

            # Calculate total ownership live and fix decimal format
            raw_owns = [player_lookup.get(lineup.get(s,""),{}).get("Ownership",0) for s in SLOT_COLS if lineup.get(s,"")]
            raw_owns = [v for v in raw_owns if isinstance(v,(int,float))]
            # Detect if ownership is in decimal format (all values <=1)
            if raw_owns and max(raw_owns) <= 1.0:
                total_own = sum(raw_owns) * 100
            else:
                total_own = sum(raw_owns)

            saved_badge_html = '<span class="saved-badge">✓ Saved</span>' if already_saved else ""
            tag_val  = st.session_state.lineup_tags.get(lineup_num, "")
            tag_html = f'<span class="tag-badge">{tag_val}</span>' if tag_val else ""

            player_rows = ""
            for slot in SLOT_COLS:
                player_name = lineup.get(slot, "")
                if not player_name:
                    continue
                label, badge_cls = SLOT_DISPLAY.get(slot, (slot, "pos-QB"))
                pdata = player_lookup.get(player_name, {})
                team  = pdata.get("Team", "—")
                opp   = pdata.get("Opponent", "")
                sal   = format_salary(pdata.get("Salary", ""))
                proj  = pdata.get(optimize_by, "")
                proj  = f"{proj:.1f}" if isinstance(proj, (int, float)) else str(proj)
                own_raw = pdata.get("Ownership", "")
                if isinstance(own_raw, (int, float)):
                    own_val = own_raw * 100 if 0 <= own_raw <= 1.0 else own_raw
                    own = f"{own_val:.1f}%"
                else:
                    own = str(own_raw)

                opp_span = f'<span class="p-opp">vs {opp}</span>' if opp else ""

                player_rows += f"""
                <div class="player-row">
                  <span class="pos-badge {badge_cls}">{label}</span>
                  <span class="p-team">{team}</span>
                  {opp_span}
                  <span class="p-name">{player_name}</span>
                  <span class="p-sal">{sal}</span>
                  <span class="p-proj">{proj}</span>
                  <span class="p-own">{own}</span>
                </div>"""

            cards_html += f"""
            <div class="lineup-card">
              <div class="card-header">
                <div>
                  <div class="card-num">Lineup #{lineup_num}{saved_badge_html}{tag_html}</div>
                  <div class="card-score">{total_score:.2f} {optimize_by}</div>
                </div>
                <div class="card-meta">
                  <div>Salary <span>{format_salary(total_sal)}</span></div>
                  <div>Rem <span>{format_salary(sal_rem)}</span></div>
                  <div>Own <span>{total_own:.1f}%</span></div>
                </div>
              </div>
              <div>{player_rows}</div>
            </div>"""

        for _ in range(cards_per_row - len(row_lineups)):
            cards_html += "<div></div>"

        full_html = f"""<!DOCTYPE html><html><head>{card_css}</head>
        <body><div class="cards-grid">{cards_html}</div></body></html>"""

        iframe_height = 60 + (7 * 28) + 20
        components.html(full_html, height=iframe_height, scrolling=False)

        # ── Checkboxes + tag inputs below each card in this row ────────────
        cb_cols = st.columns(cards_per_row)
        for col_idx, lineup in enumerate(row_lineups):
            lineup_num = lineup.get("Lineup #", "?")
            with cb_cols[col_idx]:
                # Checkbox
                key = f"{id_prefix}_cb_{lineup_num}"
                current = checked_state.get(lineup_num, False)
                checked = st.checkbox("Select", value=current, key=key)
                checked_state[lineup_num] = checked

                # Tag input (only on saved tab)
                if mode == "saved":
                    current_tag = st.session_state.lineup_tags.get(lineup_num, "")
                    new_tag = st.text_input(
                        "🏷️ Tag",
                        value=current_tag,
                        placeholder="e.g. Cash, GPP...",
                        key=f"tag_{lineup_num}",
                        label_visibility="collapsed",
                    )
                    st.session_state.lineup_tags[lineup_num] = new_tag


# ── Header ────────────────────────────────────────────────────────────────────
st.markdown('<div class="main-title">🏈 UFL DFS OPTIMIZER</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-title">DraftKings · Lineup Generator · Powered by Linear Programming</div>', unsafe_allow_html=True)

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown('<div class="section-header">📁 Upload Projections</div>', unsafe_allow_html=True)
    st.markdown("""
    <div class="info-box">
    Upload your weekly CSV file. Required columns:<br>
    <b>Player, Position, Team, Salary, Ownership</b><br><br>
    Optional: <b>DK Points, Value, T.Val, Leverage, Pts/$, ID</b>
    </div>
    """, unsafe_allow_html=True)

    uploaded_file = st.file_uploader(
        "Choose your CSV file", type=["csv"],
        help="Download from your projections source and upload here each week."
    )

    st.markdown('<div class="section-header">⚙️ Settings</div>', unsafe_allow_html=True)

    ALL_OPTIMIZE_OPTIONS = ["DK Points", "Value", "T.Val", "Leverage", "Pts/$"]
    optimize_by = st.selectbox(
        "Optimize By", options=ALL_OPTIMIZE_OPTIONS, index=0,
        help="Which metric to maximise. DK Points = raw projected fantasy points."
    )

    num_lineups = st.number_input(
        "Number of Lineups to Generate",
        min_value=1, max_value=150, value=1, step=1,
    )

    st.markdown('<div class="section-header">💰 Salary</div>', unsafe_allow_html=True)
    min_salary = st.number_input(
        "Minimum Salary Used ($)",
        min_value=40000, max_value=SALARY_CAP, value=49000, step=100,
    )

    st.markdown('<div class="section-header">👥 Ownership</div>', unsafe_allow_html=True)
    use_max_ownership = st.checkbox("Cap Cumulative Ownership", value=False)
    max_ownership = None
    if use_max_ownership:
        max_ownership = st.slider(
            "Max Total Ownership %", min_value=100, max_value=500, value=250, step=10,
        )

    st.markdown('<div class="section-header">🏟️ Team Limits</div>', unsafe_allow_html=True)
    max_per_team = st.slider("Max Players From One Team", min_value=1, max_value=5, value=4, step=1)

    st.markdown('<div class="section-header">🔗 QB Stack</div>', unsafe_allow_html=True)
    force_stack = st.checkbox("Force QB + WR/TE Stack", value=False)
    stack_count = 1
    if force_stack:
        stack_count = st.radio("WR/TE Stackmates Required", options=[1, 2], index=0)

    st.markdown('<div class="section-header">↩️ Bring-Back</div>', unsafe_allow_html=True)
    force_bring_back = st.checkbox(
        "Force Bring-Back",
        value=False,
        help="Requires at least 1 skill player (RB/WR/TE) from the opposing team of whichever QB is selected. Requires an Opponent column in your CSV."
    )

    st.markdown("---")
    saved_count = len(st.session_state.saved_lineups)
    st.markdown(f"**💾 Saved Lineups:** {saved_count}")
    if saved_count > 0:
        if st.button("🗑️ Clear All Saved Lineups"):
            st.session_state.saved_lineups = []
            st.rerun()


# ── Tabs ──────────────────────────────────────────────────────────────────────
tab_optimizer, tab_saved = st.tabs(["🚀 Optimizer", "💾 Saved Lineups"])


# ═════════════════════════════════════════════════════════════════════════════
# TAB 1 — OPTIMIZER
# ═════════════════════════════════════════════════════════════════════════════
with tab_optimizer:

    if uploaded_file is None:
        st.markdown("""
        <div class="info-box" style="font-size:1rem; padding:1.5rem;">
        👈 <b>Get started by uploading your CSV file in the sidebar.</b><br><br>
        Once uploaded your player pool will appear here and you can configure
        constraints and generate optimised lineups.
        </div>
        """, unsafe_allow_html=True)

        st.markdown("### 📋 Expected CSV Format")
        sample_data = pd.DataFrame({
            "Player":   ["Patrick Mahomes", "Tyreek Hill", "Travis Kelce",
                         "Isiah Pacheco", "Rashee Rice", "Mecole Hardman", "Chiefs DST"],
            "Position": ["QB", "WR", "TE", "RB", "WR", "WR", "DST"],
            "Team":     ["KC"] * 7,
            "Salary":   [8400, 7600, 6800, 6200, 5800, 4200, 3200],
            "DK Points":[28.4, 22.1, 14.3, 16.8, 12.4, 8.2, 9.1],
            "Value":    [3.38, 2.91, 2.10, 2.71, 2.14, 1.95, 2.84],
            "Ownership":[28.5, 18.2, 14.1, 22.3, 15.6, 8.4, 12.0],
            "ID":       [11191729, 11192543, 11192100, 11193021, 11192876, 11193154, 11190044],
            "Leverage": [1.2, 0.9, 0.6, 1.1, 0.7, 0.5, 0.4],
            "Pts/$":    [3.38, 2.91, 2.10, 2.71, 2.14, 1.95, 2.84],
            "T.Val":    [3.4, 2.8, 1.9, 2.6, 1.8, 1.2, 1.0],
        })
        st.dataframe(sample_data, use_container_width=True, hide_index=True)

    else:
        # ── Load & Validate ───────────────────────────────────────────────────
        try:
            raw_df = pd.read_csv(uploaded_file)
            validate_csv(raw_df)
            df = clean_dataframe(raw_df)
            player_lookup = build_player_lookup(df)

            available_opts = [c for c in ALL_OPTIMIZE_OPTIONS if c in df.columns]
            if optimize_by not in available_opts:
                st.warning(
                    f"⚠️ '{optimize_by}' not found in your CSV. "
                    f"Available: {available_opts}. Select a different metric in the sidebar."
                )
                st.stop()

        except ValueError as e:
            st.error(f"❌ CSV Error: {e}")
            st.stop()
        except Exception as e:
            st.error(f"❌ Could not read your file: {e}")
            st.stop()

        # ── Player Pool ───────────────────────────────────────────────────────
        st.markdown('<div class="section-header">📊 Player Pool</div>', unsafe_allow_html=True)

        pos_filter = st.multiselect(
            "Filter by Position", options=sorted(df["Position"].unique()), default=[],
        )
        display_df = df if not pos_filter else df[df["Position"].isin(pos_filter)]

        show_cols = ["Player", "Position", "Team", "Opponent", "Salary", "Ownership"]
        show_cols = [c for c in show_cols if c in df.columns]
        for c in ["DK Points", "Value", "T.Val", "Leverage", "Pts/$"]:
            if c in df.columns:
                show_cols.append(c)
        if "ID" in df.columns:
            show_cols.append("ID")

        pool_display = display_df[show_cols].sort_values("Salary", ascending=False).copy()

        def color_scale(val, col_min, col_max, reverse=False):
            """Return a background-color CSS string on a green-red gradient."""
            try:
                v = float(val)
            except (TypeError, ValueError):
                return ""
            if col_max == col_min:
                ratio = 0.5
            else:
                ratio = (v - col_min) / (col_max - col_min)
            if reverse:
                ratio = 1 - ratio
            ratio = max(0.0, min(1.0, ratio))
            # Green (0,180,80) -> Yellow (220,180,0) -> Red (220,40,40)
            if ratio >= 0.5:
                r2 = ratio * 2 - 1
                r = int(0   + r2 * 220)
                g = int(180 - r2 * 140)
                b = int(80  - r2 * 80)
            else:
                r2 = ratio * 2
                r = int(220 - r2 * 220)
                g = int(40  + r2 * 140)
                b = int(40  + r2 * 40)
            return f"background-color: rgba({r},{g},{b},0.30); color: #e5e7eb;"

        def style_pool(df_s):
            styles = pd.DataFrame("", index=df_s.index, columns=df_s.columns)
            col_cfg = {
                # col_name: (reverse_scale)
                # reverse=True  -> high value = red, low = green
                # reverse=False -> high value = green, low = red
                "Salary":    (True,  df_s["Salary"].min()    if "Salary"    in df_s else 0,
                                     df_s["Salary"].max()    if "Salary"    in df_s else 1),
                "Ownership": (True,  df_s["Ownership"].min() if "Ownership" in df_s else 0,
                                     df_s["Ownership"].max() if "Ownership" in df_s else 1),
                "DK Points": (False, df_s["DK Points"].min() if "DK Points" in df_s else 0,
                                     df_s["DK Points"].max() if "DK Points" in df_s else 1),
                "Value":     (False, -8.0, 8.0),
                "T.Val":     (False, df_s["T.Val"].min()     if "T.Val"     in df_s else 0,
                                     df_s["T.Val"].max()     if "T.Val"     in df_s else 1),
                "Leverage":  (False, df_s["Leverage"].min()  if "Leverage"  in df_s else 0,
                                     df_s["Leverage"].max()  if "Leverage"  in df_s else 1),
            }
            for col, (rev, cmin, cmax) in col_cfg.items():
                if col in df_s.columns:
                    styles[col] = df_s[col].apply(
                        lambda v, r=rev, mn=cmin, mx=cmax: color_scale(v, mn, mx, reverse=r)
                    )
            return styles

        styled = pool_display.style.apply(style_pool, axis=None)

        # Build column_config for formatting (applied on top of the styling)
        col_config = {}
        if "Salary" in pool_display.columns:
            col_config["Salary"] = st.column_config.NumberColumn("Salary", format="$%d")
        if "Ownership" in pool_display.columns:
            col_config["Ownership"] = st.column_config.NumberColumn("Ownership", format="%.1f%%")
        if "ID" in pool_display.columns:
            col_config["ID"] = st.column_config.NumberColumn("ID", format="%d")
        for c in ["DK Points", "Value", "T.Val", "Leverage", "Pts/$"]:
            if c in pool_display.columns:
                col_config[c] = st.column_config.NumberColumn(c, format="%.1f")

        st.dataframe(styled, use_container_width=True, hide_index=True, column_config=col_config)

        # ── Lock / Exclude ────────────────────────────────────────────────────
        st.markdown('<div class="section-header">🔒 Lock & Exclude Players</div>', unsafe_allow_html=True)
        col_lock, col_excl = st.columns(2)
        with col_lock:
            st.markdown("**Lock Players** — Force into every lineup")
            locked = st.multiselect("Select players to lock", options=sorted(df["Player"].tolist()), default=[])
        with col_excl:
            st.markdown("**Exclude Players** — Remove from all lineups")
            excluded = st.multiselect("Select players to exclude", options=sorted(df["Player"].tolist()), default=[])

        # ── Exposure Limits ───────────────────────────────────────────────────
        max_exposure_dict = {}
        min_exposure_dict = {}
        if num_lineups > 1:
            st.markdown('<div class="section-header">📈 Exposure Limits (Optional)</div>', unsafe_allow_html=True)

            # ── Position-level exposure ───────────────────────────────────────
            st.markdown("**By Position** — max % any single player at that position can appear")
            st.markdown("""
            <div class="info-box" style="margin-bottom:0.5rem">
            Leave a position blank to apply no limit. Enter a number 0–100 to cap
            every player at that position to at most that % of lineups.
            </div>
            """, unsafe_allow_html=True)

            pos_exp_cols = st.columns(5)
            pos_labels = ["QB", "RB", "WR", "TE", "DST"]
            pos_max_pct = {}
            for i, pos in enumerate(pos_labels):
                with pos_exp_cols[i]:
                    val = st.number_input(
                        pos, min_value=0, max_value=100, value=0, step=5,
                        key=f"pos_exp_{pos}",
                        help=f"Max % of lineups any single {pos} can appear in. 0 = no limit.",
                    )
                    if val > 0:
                        pos_max_pct[pos] = val

            # Convert position % caps into per-player max lineup counts
            if pos_max_pct:
                for _, row in df.iterrows():
                    pos = row["Position"]
                    # Match WR/TE/DST variations
                    pos_key = None
                    if pos == "QB" and "QB" in pos_max_pct:
                        pos_key = "QB"
                    elif pos == "RB" and "RB" in pos_max_pct:
                        pos_key = "RB"
                    elif pos == "WR" and "WR" in pos_max_pct:
                        pos_key = "WR"
                    elif pos == "TE" and "TE" in pos_max_pct:
                        pos_key = "TE"
                    elif pos in ["DST", "D", "DEF"] and "DST" in pos_max_pct:
                        pos_key = "DST"
                    if pos_key:
                        cap = max(1, int((pos_max_pct[pos_key] / 100) * num_lineups))
                        player = row["Player"]
                        # Only apply if stricter than any existing player-level cap
                        if player not in max_exposure_dict or cap < max_exposure_dict[player]:
                            max_exposure_dict[player] = cap

            st.markdown("---")

            # ── Player-level exposure ─────────────────────────────────────────
            st.markdown("**By Player** — fine-tune min/max for specific players")
            st.markdown("""
            <div class="info-box">
            <b>Min</b> = player must appear in at least this % of lineups.<br>
            <b>Max</b> = player can appear in at most this % of lineups.<br>
            Player-level caps override position-level caps when stricter.
            </div>
            """, unsafe_allow_html=True)
            exp_players = st.multiselect(
                "Set exposure limits for specific players",
                options=sorted(df["Player"].tolist()), default=[],
            )
            for p in exp_players:
                min_pct, max_pct = st.select_slider(
                    f"{p} — Exposure Range %",
                    options=list(range(0, 101, 5)),
                    value=(0, 50),
                    key=f"exp_{p}",
                )
                if max_pct > 0:
                    player_cap = max(1, int((max_pct / 100) * num_lineups))
                    # Player-level is always applied (overrides position cap)
                    max_exposure_dict[p] = player_cap
                if min_pct > 0:
                    min_exposure_dict[p] = max(1, int((min_pct / 100) * num_lineups))

        # ── Generate ──────────────────────────────────────────────────────────
        st.markdown("---")
        gen_col, _ = st.columns([1, 2])
        with gen_col:
            run_optimizer = st.button("🚀 Generate Lineups")

        if run_optimizer:
            with st.spinner(f"Generating {num_lineups} lineup(s)…"):
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
                        force_bring_back=force_bring_back,
                        locked_players=locked,
                        excluded_players=excluded,
                        min_exposure=min_exposure_dict,
                        max_exposure=max_exposure_dict,
                    )
                except ValueError as e:
                    st.error(f"❌ Optimizer Error: {e}")
                    st.stop()
                except Exception as e:
                    st.error(f"❌ Unexpected error: {e}")
                    st.stop()
            st.session_state.last_results = results

        # ── Results ───────────────────────────────────────────────────────────
        results = st.session_state.last_results
        if results:
            results_df = pd.DataFrame(results)
            actual = len(results_df)

            st.markdown('<div class="section-header">📋 Generated Lineups</div>', unsafe_allow_html=True)
            st.markdown("""
            <div class="info-box">
            Each card shows <b>Position · Team · Player · Salary · Projection · Ownership</b>.
            Click <b>💾 Save Lineup</b> under any card to add it to your Saved Lineups tab.
            </div>
            """, unsafe_allow_html=True)

            saved_set = {r.get("Lineup #") for r in st.session_state.saved_lineups}

            # Select All / Deselect All controls
            sel_col1, sel_col2, sel_col3, _ = st.columns([1, 1, 1, 4])
            with sel_col1:
                if st.button("☑️ Select All", key="gen_select_all"):
                    for r in results:
                        st.session_state.gen_checked[r.get("Lineup #")] = True
                    st.rerun()
            with sel_col2:
                if st.button("⬜ Deselect All", key="gen_deselect_all"):
                    st.session_state.gen_checked = {}
                    st.rerun()
            with sel_col3:
                n_checked = sum(1 for v in st.session_state.gen_checked.values() if v)
                already_saved_nums = {r.get("Lineup #") for r in st.session_state.saved_lineups}
                to_save = [
                    r for r in results
                    if st.session_state.gen_checked.get(r.get("Lineup #"), False)
                    and r.get("Lineup #") not in already_saved_nums
                ]
                if st.button(f"💾 Save Selected ({n_checked})", key="gen_save_selected",
                             disabled=(n_checked == 0), type="primary"):
                    st.session_state.saved_lineups.extend(to_save)
                    st.session_state.gen_checked = {}
                    st.rerun()

            render_lineup_cards(
                results, player_lookup, optimize_by,
                saved_set=saved_set,
                mode="gen",
                id_prefix="gen",
            )

            # ── Summary ───────────────────────────────────────────────────────
            st.markdown('<div class="section-header">📊 Summary</div>', unsafe_allow_html=True)
            score_col = f"Total {optimize_by}"
            s1, s2, s3, s4 = st.columns(4)
            s1.metric("Lineups Generated", actual)
            s2.metric(f"Avg {optimize_by}", round(results_df[score_col].mean(), 2))
            s3.metric("Avg Ownership %", round(results_df["Total Ownership"].mean(), 1))
            s4.metric("Avg Salary Used", f"${int(results_df['Total Salary'].mean()):,}")

            # ── Downloads ─────────────────────────────────────────────────────
            st.markdown('<div class="section-header">⬇️ Download</div>', unsafe_allow_html=True)
            dl1, dl2 = st.columns(2)
            with dl1:
                st.download_button(
                    "📥 Download Full Results (CSV)",
                    data=results_df.to_csv(index=False),
                    file_name="ufl_lineups_full.csv", mime="text/csv",
                )
            dk_slot_cols = ["QB", "RB", "WR/TE 1", "WR/TE 2", "FLEX 1", "FLEX 2", "DST"]
            avail_dk = [c for c in dk_slot_cols if c in results_df.columns]
            if avail_dk:
                with dl2:
                    st.download_button(
                        "📥 Download DraftKings Upload Format",
                        data=results_df[avail_dk].to_csv(index=False),
                        file_name="ufl_lineups_dk.csv", mime="text/csv",
                    )


# ═════════════════════════════════════════════════════════════════════════════
# TAB 2 — SAVED LINEUPS
# ═════════════════════════════════════════════════════════════════════════════
with tab_saved:

    saved = st.session_state.saved_lineups

    if not saved:
        st.markdown("""
        <div class="info-box" style="font-size:1rem; padding:1.5rem;">
        💾 <b>No lineups saved yet.</b><br><br>
        Generate lineups in the <b>Optimizer</b> tab, then click <b>💾 Save Lineup</b>
        under any card to add it here for comparison.
        </div>
        """, unsafe_allow_html=True)

    else:
        saved_df = pd.DataFrame(saved)
        total_saved = len(saved_df)

        st.markdown(
            f'<div class="success-banner">💾 {total_saved} lineup(s) saved</div>',
            unsafe_allow_html=True,
        )

        # Player lookup — use uploaded CSV if available, else empty
        card_player_lookup = player_lookup if uploaded_file is not None else {}

        # ── Controls bar: display metric + bulk actions ───────────────────────
        st.markdown('<div class="section-header">📋 Saved Lineups</div>', unsafe_allow_html=True)

        ctrl_a, ctrl_b, ctrl_c, ctrl_d, ctrl_e = st.columns([2, 1, 1, 1, 2])

        with ctrl_a:
            # Find all metric columns available across saved lineups
            available_metrics = [
                c.replace("Total ", "")
                for c in saved_df.columns
                if c.startswith("Total ") and c not in ("Total Salary", "Total Ownership")
            ]
            # Also allow switching to any metric present in the uploaded CSV
            if uploaded_file is not None:
                for m in ALL_OPTIMIZE_OPTIONS:
                    if m in df.columns and m not in available_metrics:
                        available_metrics.append(m)
            if not available_metrics:
                available_metrics = ["DK Points"]

            # Default to previously chosen metric if still valid
            default_idx = 0
            if st.session_state.saved_display_metric in available_metrics:
                default_idx = available_metrics.index(st.session_state.saved_display_metric)

            card_optimize_by = st.selectbox(
                "Display Metric",
                options=available_metrics,
                index=default_idx,
                key="saved_metric_select",
                help="Change which metric is shown on the lineup cards. Does not affect how lineups were optimized.",
            )
            st.session_state.saved_display_metric = card_optimize_by

        with ctrl_b:
            st.markdown("<div style='margin-top:28px'></div>", unsafe_allow_html=True)
            if st.button("☑️ Select All", key="saved_select_all"):
                for r in saved:
                    st.session_state.saved_checked[r.get("Lineup #")] = True
                st.rerun()
        with ctrl_c:
            st.markdown("<div style='margin-top:28px'></div>", unsafe_allow_html=True)
            if st.button("⬜ Deselect All", key="saved_deselect_all"):
                st.session_state.saved_checked = {}
                st.rerun()
        with ctrl_d:
            st.markdown("<div style='margin-top:28px'></div>", unsafe_allow_html=True)
            n_del_checked = sum(1 for v in st.session_state.saved_checked.values() if v)
            if st.button(f"🗑️ Delete ({n_del_checked})", key="saved_delete_selected",
                         disabled=(n_del_checked == 0)):
                keep = [
                    r for r in saved
                    if not st.session_state.saved_checked.get(r.get("Lineup #"), False)
                ]
                # Clean up tags for deleted lineups
                deleted_nums = {
                    r.get("Lineup #") for r in saved
                    if st.session_state.saved_checked.get(r.get("Lineup #"), False)
                }
                for dn in deleted_nums:
                    st.session_state.lineup_tags.pop(dn, None)
                st.session_state.saved_lineups = keep
                st.session_state.saved_checked = {}
                st.rerun()

        # ── Sort controls ─────────────────────────────────────────────────────
        sort_col1, sort_col2, _ = st.columns([1, 1, 5])
        with sort_col1:
            sort_dir = st.selectbox(
                "Sort", options=["↓ Highest First", "↑ Lowest First"],
                index=0, key="saved_sort_dir", label_visibility="collapsed",
            )
        with sort_col2:
            st.markdown("<div style='padding-top:6px; font-size:0.8rem; color:#6b7280'>by display metric</div>",
                        unsafe_allow_html=True)

        # Sort lineups by calculated metric score
        reverse_sort = sort_dir.startswith("↓")
        sorted_saved = sorted(
            saved,
            key=lambda lu: calc_total_score(lu, card_optimize_by, card_player_lookup),
            reverse=reverse_sort,
        )

        saved_set_all = {r.get("Lineup #") for r in saved}
        render_lineup_cards(
            sorted_saved, card_player_lookup, card_optimize_by,
            saved_set=saved_set_all,
            mode="saved",
            id_prefix="saved",
        )



        # ── Player Exposure ───────────────────────────────────────────────────
        st.markdown('<div class="section-header">📈 Player Exposure</div>', unsafe_allow_html=True)
        st.markdown("""
        <div class="info-box">
        How often each player appears across all your saved lineups.<br>
        <b># Lineups</b> = raw count &nbsp;|&nbsp;
        <b>Exposure %</b> = share of your saved lineup pool.
        </div>
        """, unsafe_allow_html=True)

        present_slots = [c for c in SLOT_COLS if c in saved_df.columns]
        all_appearances = []
        for col in present_slots:
            all_appearances.extend(saved_df[col].dropna().tolist())

        counts = Counter(all_appearances)
        exposure_df = pd.DataFrame([
            {"Player": p, "Lineups": c, "Exposure %": round(c / total_saved * 100, 1)}
            for p, c in sorted(counts.items(), key=lambda x: -x[1])
        ])

        st.dataframe(
            exposure_df,
            use_container_width=True, hide_index=True,
            column_config={
                "Lineups": st.column_config.NumberColumn("# Lineups"),
                "Exposure %": st.column_config.ProgressColumn(
                    "Exposure %", format="%.1f%%", min_value=0, max_value=100,
                ),
            },
        )

        # ── Downloads ─────────────────────────────────────────────────────────
        st.markdown('<div class="section-header">⬇️ Download Saved Lineups</div>', unsafe_allow_html=True)
        dl_a, dl_b = st.columns(2)

        # Attach tags column to export
        export_df = saved_df.copy()
        export_df.insert(1, "Tag", export_df.get("Lineup #", pd.Series(dtype=str)).map(
            lambda n: st.session_state.lineup_tags.get(n, "")
        ))

        with dl_a:
            st.download_button(
                "📥 Download Saved Lineups (CSV)",
                data=export_df.to_csv(index=False),
                file_name="ufl_saved_lineups.csv", mime="text/csv",
            )

        avail_dk = [c for c in ["QB", "RB", "WR/TE 1", "WR/TE 2", "FLEX 1", "FLEX 2", "DST"] if c in saved_df.columns]
        if avail_dk:
            with dl_b:
                st.download_button(
                    "📥 Download DraftKings Upload Format",
                    data=saved_df[avail_dk].to_csv(index=False),
                    file_name="ufl_saved_lineups_dk.csv", mime="text/csv",
                )
