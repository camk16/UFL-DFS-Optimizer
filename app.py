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
if "global_lineup_counter" not in st.session_state:
    st.session_state.global_lineup_counter = 0  # ever-increasing, unique across runs
if "saved_display_metric" not in st.session_state:
    st.session_state.saved_display_metric = None  # chosen metric on saved tab
if "cb_gen_gen" not in st.session_state:
    st.session_state.cb_gen_gen = 0   # incremented to force checkbox re-init
if "cb_saved_gen" not in st.session_state:
    st.session_state.cb_saved_gen = 0
if "lineup_sets" not in st.session_state:
    st.session_state.lineup_sets = {}        # name -> list of lineup dicts
if "active_set_name" not in st.session_state:
    st.session_state.active_set_name = None  # None = show live results
if "gen_display_metric" not in st.session_state:
    st.session_state.gen_display_metric = None  # chosen display metric on gen tab
if "edited_pool" not in st.session_state:
    st.session_state.edited_pool = None   # user-edited version of df
if "pool_csv_hash" not in st.session_state:
    st.session_state.pool_csv_hash = None # detect when a new CSV is uploaded
if "csv_store" not in st.session_state:
    st.session_state.csv_store = {}       # name -> raw CSV bytes
if "active_csv_name" not in st.session_state:
    st.session_state.active_csv_name = None
if "global_lineup_counter" not in st.session_state:
    st.session_state.global_lineup_counter = 0  # ever-increasing lineup ID

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

    /* Prevent sidebar buttons from wrapping */
    section[data-testid="stSidebar"] button {
        white-space: nowrap !important;
        overflow: hidden;
        text-overflow: ellipsis;
    }

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
            raw_tags = st.session_state.lineup_tags.get(lineup_num, [])
            if isinstance(raw_tags, str):
                raw_tags = [raw_tags] if raw_tags else []
            tag_html = " ".join(
                f'<span class="tag-badge">{t}</span>'
                for t in raw_tags if t
            )

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
                gen_counter = st.session_state.get(f"cb_{id_prefix}_gen", 0)
                key = f"{id_prefix}_cb_{lineup_num}_g{gen_counter}"
                current = checked_state.get(lineup_num, False)
                checked = st.checkbox("Select", value=current, key=key)
                checked_state[lineup_num] = checked

                # Multi-tag input
                # Rule: NEVER write to a widget key after the widget has rendered —
                # Streamlit raises StreamlitAPIException. Instead, lineup_tags is the
                # single source of truth. Widget keys seed from it on first render
                # only. After render, we read from the widget key to update lineup_tags.
                widget_key = f"{id_prefix}_tag_{lineup_num}"
                newtag_key = f"{id_prefix}_newtag_{lineup_num}"

                # Read current tags from lineup_tags (authoritative store)
                stored = st.session_state.lineup_tags.get(lineup_num, [])
                if not isinstance(stored, list):
                    stored = [stored] if stored else []

                # Build options from all known tags + this lineup's current tags
                all_known_tags = sorted({
                    t for tags in st.session_state.lineup_tags.values()
                    for t in (tags if isinstance(tags, list) else ([tags] if tags else []))
                    if t
                } | set(stored))

                # Multiselect — pass default only when key not yet in session state
                if widget_key not in st.session_state:
                    selected = st.multiselect(
                        "Tags", options=all_known_tags,
                        default=stored,
                        key=widget_key,
                        placeholder="Select tags...",
                        label_visibility="collapsed",
                    )
                else:
                    selected = st.multiselect(
                        "Tags", options=all_known_tags,
                        key=widget_key,
                        placeholder="Select tags...",
                        label_visibility="collapsed",
                    )

                # Text input for a new tag not yet in the list
                new_tag_typed = st.text_input(
                    "New tag",
                    placeholder="Type new tag + Enter to add",
                    key=newtag_key,
                    label_visibility="collapsed",
                )

                # Merge typed tag: update lineup_tags and clear the text box next run
                # Do NOT write to widget_key — write only to lineup_tags
                typed = st.session_state.get(newtag_key, "").strip()
                if typed and typed not in selected:
                    final_tags = list(dict.fromkeys(selected + [typed]))
                    # Clear the text input next render by resetting its key
                    del st.session_state[newtag_key]
                else:
                    final_tags = list(selected)

                st.session_state.lineup_tags[lineup_num] = final_tags


# ── Header ────────────────────────────────────────────────────────────────────
st.markdown('<div class="main-title">🏈 UFL DFS OPTIMIZER</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-title">DraftKings · Lineup Generator · Powered by Linear Programming</div>', unsafe_allow_html=True)

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown('<div class="section-header">📁 Player Pools</div>', unsafe_allow_html=True)
    st.markdown("""
    <div class="info-box">
    Upload one or more CSV files and name each one (e.g. GPP, Cash).
    Switch between them instantly using the dropdown.<br><br>
    Required: <b>Player, Position, Team, Salary, Ownership</b><br>
    Optional: <b>DK Points, Value, T.Val, Leverage, Pts/$, ID</b>
    </div>
    """, unsafe_allow_html=True)

    # ── Upload + name a new CSV ───────────────────────────────────────────────
    new_file = st.file_uploader(
        "Upload a CSV", type=["csv"],
        help="Upload a new player pool CSV then give it a name below.",
        key="csv_uploader",
    )
    csv_name_input = st.text_input(
        "Pool name", placeholder="e.g. GPP, Cash, Week 5...",
        key="csv_name_input",
        label_visibility="collapsed",
    )
    if st.button("➕ Add Pool", disabled=(new_file is None or not csv_name_input.strip())):
        name = csv_name_input.strip()
        st.session_state.csv_store[name] = new_file.getvalue()
        st.session_state.active_csv_name = name
        # Reset edited pool when a new CSV is added
        st.session_state.edited_pool = None
        st.session_state.pool_csv_hash = None
        st.rerun()

    # ── Switch between stored CSVs ────────────────────────────────────────────
    if st.session_state.csv_store:
        pool_names = list(st.session_state.csv_store.keys())

        # Keep active selection valid
        if st.session_state.active_csv_name not in pool_names:
            st.session_state.active_csv_name = pool_names[0]

        selected_pool = st.selectbox(
            "Active Pool",
            options=pool_names,
            index=pool_names.index(st.session_state.active_csv_name),
            key="active_pool_select",
        )
        if selected_pool != st.session_state.active_csv_name:
            st.session_state.active_csv_name = selected_pool
            st.session_state.edited_pool = None
            st.session_state.pool_csv_hash = None
            st.rerun()

        # Delete pool button
        if st.button("🗑️ Remove Pool", key="del_pool", use_container_width=False):
            del st.session_state.csv_store[selected_pool]
            if selected_pool == st.session_state.active_csv_name:
                remaining = list(st.session_state.csv_store.keys())
                st.session_state.active_csv_name = remaining[0] if remaining else None
            st.session_state.edited_pool = None
            st.session_state.pool_csv_hash = None
            st.rerun()

    # Expose active CSV as uploaded_file-compatible object for the rest of the app
    import io
    if st.session_state.active_csv_name and st.session_state.active_csv_name in st.session_state.csv_store:
        uploaded_file = io.BytesIO(st.session_state.csv_store[st.session_state.active_csv_name])
    else:
        uploaded_file = None

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

    st.markdown('<div class="section-header">🎲 Variance</div>', unsafe_allow_html=True)
    variance_pct = st.slider(
        "Projection Noise %",
        min_value=0, max_value=50, value=0, step=5,
        help="Adds random noise to each player's projection before building each lineup. "
             "0% = pure optimization. 20% means each player's value is randomly adjusted "
             "by up to ±20%, producing more lineup diversity across a multi-lineup run."
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

        # Detect new CSV upload — reset edited pool
        csv_hash = str(len(df)) + str(df["Player"].iloc[0] if len(df) > 0 else "")
        if st.session_state.pool_csv_hash != csv_hash:
            st.session_state.pool_csv_hash = csv_hash
            st.session_state.edited_pool = None

        # Initialise edited pool from raw df
        if st.session_state.edited_pool is None:
            st.session_state.edited_pool = df.copy()

        working_df = st.session_state.edited_pool.copy()

        # ── Position filter toggles (multi-select) ────────────────────────────
        # FLEX = WR + RB + TE combined
        POS_FILTER_OPTS = ["QB", "RB", "WR", "TE", "FLEX", "DST"]
        active_pos = st.multiselect(
            "Filter positions",
            options=POS_FILTER_OPTS,
            default=[],
            label_visibility="collapsed",
            placeholder="ALL positions — click to filter by position",
            key="pool_pos_filter",
        )

        if not active_pos:
            filtered_df = working_df.copy()
        else:
            pos_set = set()
            for p in active_pos:
                if p == "FLEX":
                    pos_set.update(["WR", "RB", "TE"])
                elif p == "DST":
                    pos_set.update(["DST", "D", "DEF"])
                else:
                    pos_set.add(p)
            filtered_df = working_df[working_df["Position"].isin(pos_set)].copy()

        # ── Build display columns ─────────────────────────────────────────────
        show_cols = ["Player", "Position", "Team", "Opponent", "Salary", "Ownership"]
        show_cols = [c for c in show_cols if c in filtered_df.columns]
        for c in ["DK Points", "Value", "T.Val", "Leverage", "Pts/$"]:
            if c in filtered_df.columns:
                show_cols.append(c)
        if "ID" in filtered_df.columns:
            show_cols.append("ID")

        pool_display = filtered_df[show_cols].sort_values("Salary", ascending=False).copy()

        # ── Conditional formatting ────────────────────────────────────────────
        def color_scale(val, col_min, col_max, reverse=False):
            try:
                v = float(val)
            except (TypeError, ValueError):
                return ""
            ratio = (v - col_min) / (col_max - col_min) if col_max != col_min else 0.5
            if reverse:
                ratio = 1 - ratio
            ratio = max(0.0, min(1.0, ratio))
            if ratio >= 0.5:
                r2 = ratio * 2 - 1
                r = int(r2 * 220); g = int(180 - r2 * 140); b = int(80 - r2 * 80)
            else:
                r2 = ratio * 2
                r = int(220 - r2 * 220); g = int(40 + r2 * 140); b = int(40 + r2 * 40)
            return f"background-color: rgba({r},{g},{b},0.30); color: #e5e7eb;"

        def style_pool(df_s):
            styles = pd.DataFrame("", index=df_s.index, columns=df_s.columns)
            # Use full pool for min/max so scale is consistent across position filters
            full = st.session_state.edited_pool
            col_cfg = {
                "Salary":    (True,  full["Salary"].min()    if "Salary"    in full.columns else 0, full["Salary"].max()    if "Salary"    in full.columns else 1),
                "Ownership": (True,  full["Ownership"].min() if "Ownership" in full.columns else 0, full["Ownership"].max() if "Ownership" in full.columns else 1),
                "DK Points": (False, full["DK Points"].min() if "DK Points" in full.columns else 0, full["DK Points"].max() if "DK Points" in full.columns else 1),
                "Value":     (False, -8.0, 8.0),
                "T.Val":     (False, full["T.Val"].min()     if "T.Val"     in full.columns else 0, full["T.Val"].max()     if "T.Val"     in full.columns else 1),
                "Leverage":  (False, full["Leverage"].min()  if "Leverage"  in full.columns else 0, full["Leverage"].max()  if "Leverage"  in full.columns else 1),
                "Pts/$":     (False, full["Pts/$"].min()     if "Pts/$"     in full.columns else 0, full["Pts/$"].max()     if "Pts/$"     in full.columns else 1),
            }
            for col, (rev, cmin, cmax) in col_cfg.items():
                if col in df_s.columns:
                    styles[col] = df_s[col].apply(
                        lambda v, r=rev, mn=cmin, mx=cmax: color_scale(v, mn, mx, reverse=r)
                    )
            return styles

        styled = pool_display.style.apply(style_pool, axis=None)

        col_config = {}
        if "Salary"    in pool_display.columns: col_config["Salary"]    = st.column_config.NumberColumn("Salary",    format="$%d")
        if "Ownership" in pool_display.columns: col_config["Ownership"] = st.column_config.NumberColumn("Ownership", format="%.1f%%")
        if "ID"        in pool_display.columns: col_config["ID"]        = st.column_config.NumberColumn("ID",        format="%d")
        for c in ["DK Points", "Value", "T.Val", "Leverage", "Pts/$"]:
            if c in pool_display.columns:
                col_config[c] = st.column_config.NumberColumn(c, format="%.1f")

        st.dataframe(styled, use_container_width=True, hide_index=True, column_config=col_config)

        # ── Lock / Exclude ────────────────────────────────────────────────────
        st.markdown('<div class="section-header">🔒 Lock & Exclude Players</div>', unsafe_allow_html=True)
        # Use full edited pool player list for multiselects
        all_players = st.session_state.edited_pool["Player"].tolist()
        col_lock, col_excl = st.columns(2)
        with col_lock:
            st.markdown("**Lock Players** — Force into every lineup")
            locked = st.multiselect("Select players to lock",
                options=sorted(all_players), default=[])
        with col_excl:
            st.markdown("**Exclude Players** — Remove from all lineups")
            excluded = st.multiselect("Select players to exclude",
                options=sorted(all_players), default=[])

        # Use edited pool (without Lock/Exclude cols) as df for the optimizer
        df = st.session_state.edited_pool.drop(
            columns=[c for c in ["Lock","Exclude"] if c in st.session_state.edited_pool.columns],
            errors="ignore"
        ).copy()
        player_lookup = build_player_lookup(df)

        # ── Exposure Limits ───────────────────────────────────────────────────
        max_exposure_dict = {}
        min_exposure_dict = {}
        st.markdown('<div class="section-header">📈 Exposure Limits (Optional)</div>', unsafe_allow_html=True)
        st.markdown("""
        <div class="info-box">
        Exposure settings only apply when generating more than 1 lineup.
        </div>
        """, unsafe_allow_html=True)

        # ── Position-level exposure ───────────────────────────────────────────
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
        if pos_max_pct and num_lineups > 1:
            for _, row in df.iterrows():
                pos = row["Position"]
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
                    if player not in max_exposure_dict or cap < max_exposure_dict[player]:
                        max_exposure_dict[player] = cap

        st.markdown("---")

        # ── Player-level exposure ─────────────────────────────────────────────
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
            if num_lineups > 1:
                if max_pct > 0:
                    max_exposure_dict[p] = max(1, int((max_pct / 100) * num_lineups))
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
                        variance_pct=variance_pct / 100.0,
                    )
                except ValueError as e:
                    st.error(f"❌ Optimizer Error: {e}")
                    st.stop()
                except Exception as e:
                    st.error(f"❌ Unexpected error: {e}")
                    st.stop()
            # Remap Lineup # to globally unique numbers so run 2 lineup #1
            # never collides with run 1 lineup #1 in tags/saved state
            base = st.session_state.global_lineup_counter
            remapped = []
            for i, lu in enumerate(results):
                new_lu = dict(lu)
                new_lu["Lineup #"] = base + i + 1
                remapped.append(new_lu)
            st.session_state.global_lineup_counter = base + len(results)
            # Clear old gen tags so previous tags don't bleed into new lineups
            old_nums = {r.get("Lineup #") for r in st.session_state.last_results}
            for k in list(st.session_state.lineup_tags.keys()):
                if k in old_nums:
                    del st.session_state.lineup_tags[k]
            results = remapped
            # Assign globally unique lineup numbers (avoids collisions between runs)
            base = st.session_state.global_lineup_counter
            for i, lu in enumerate(results):
                lu["Lineup #"] = base + i + 1
            st.session_state.global_lineup_counter += len(results)

            # Clear old gen tag widget keys so new lineups start untagged
            keys_to_del = [k for k in st.session_state if k.startswith("gen_tag_")]
            for k in keys_to_del:
                del st.session_state[k]

            st.session_state.last_results = results

        # ── Results ───────────────────────────────────────────────────────────
        live_results = st.session_state.last_results
        has_sets     = bool(st.session_state.lineup_sets)
        has_live     = bool(live_results)

        if has_live or has_sets:
            st.markdown('<div class="section-header">📋 Generated Lineups</div>', unsafe_allow_html=True)

            # ── Set switcher bar ──────────────────────────────────────────────
            set_names   = list(st.session_state.lineup_sets.keys())
            view_options = (["▶ Live Results"] if has_live else []) + set_names
            if not view_options:
                st.info("No lineups generated yet.")
                st.stop()

            # Keep active selection valid
            if st.session_state.active_set_name not in (view_options + [None]):
                st.session_state.active_set_name = view_options[0]

            default_view = st.session_state.active_set_name or view_options[0]
            default_idx  = view_options.index(default_view) if default_view in view_options else 0

            sw_col1, sw_col2, sw_col3 = st.columns([3, 1, 1])
            with sw_col1:
                active_view = st.selectbox(
                    "Viewing",
                    options=view_options,
                    index=default_idx,
                    key="gen_set_view",
                    label_visibility="collapsed",
                )
                st.session_state.active_set_name = active_view

            # Determine which lineups to display
            if active_view == "▶ Live Results":
                results = live_results
            else:
                results = st.session_state.lineup_sets.get(active_view, [])

            with sw_col2:
                # Save current live results as a named set
                if active_view == "▶ Live Results":
                    set_name_input = st.text_input(
                        "Set name", placeholder="Name this set…",
                        key="gen_set_name_input", label_visibility="collapsed",
                    )
                    if st.button("💼 Save Set", key="gen_save_set",
                                 disabled=not set_name_input.strip()):
                        name = set_name_input.strip()
                        st.session_state.lineup_sets[name] = list(live_results)
                        st.session_state.active_set_name = name
                        st.rerun()

            with sw_col3:
                # Delete the currently viewed saved set
                if active_view != "▶ Live Results":
                    if st.button("🗑️ Delete Set", key="gen_delete_set"):
                        del st.session_state.lineup_sets[active_view]
                        st.session_state.active_set_name = view_options[0] if len(view_options) > 1 else None
                        st.rerun()

            results_df = pd.DataFrame(results)
            actual     = len(results_df)

            if not results:
                st.warning("This set has no lineups.")
                st.stop()

            # ── Display Metric (independent of Optimize By) ───────────────────
            gen_metric_col, _ = st.columns([2, 5])
            with gen_metric_col:
                gen_avail_metrics = list(ALL_OPTIMIZE_OPTIONS)
                if uploaded_file is not None:
                    gen_avail_metrics = [m for m in ALL_OPTIMIZE_OPTIONS if m in df.columns]
                if not gen_avail_metrics:
                    gen_avail_metrics = ["DK Points"]
                gen_default_idx = 0
                if st.session_state.gen_display_metric in gen_avail_metrics:
                    gen_default_idx = gen_avail_metrics.index(st.session_state.gen_display_metric)
                gen_display_metric = st.selectbox(
                    "Display Metric",
                    options=gen_avail_metrics,
                    index=gen_default_idx,
                    key="gen_display_metric_select",
                    help="Which metric to show on the cards. Independent of the Optimize By setting.",
                )
                st.session_state.gen_display_metric = gen_display_metric

            saved_set = {r.get("Lineup #") for r in st.session_state.saved_lineups}

            # ── Controls row ──────────────────────────────────────────────────
            sel_col1, sel_col2, _ = st.columns([1, 1, 5])
            with sel_col1:
                if st.button("☑️ Select All", key="gen_select_all"):
                    for r in results:
                        st.session_state.gen_checked[r.get("Lineup #")] = True
                    st.session_state.cb_gen_gen += 1
                    st.rerun()
            with sel_col2:
                if st.button("⬜ Deselect All", key="gen_deselect_all"):
                    st.session_state.gen_checked = {}
                    st.session_state.cb_gen_gen += 1
                    st.rerun()

            # ── Sort ──────────────────────────────────────────────────────────
            gsort_col1, gsort_col2, _ = st.columns([1, 1, 5])
            with gsort_col1:
                gen_sort_dir = st.selectbox(
                    "Sort", options=["↓ Highest First", "↑ Lowest First"],
                    index=0, key="gen_sort_dir", label_visibility="collapsed",
                )
            with gsort_col2:
                st.markdown("<div style='padding-top:6px; font-size:0.8rem; color:#6b7280'>by display metric</div>",
                            unsafe_allow_html=True)

            gen_reverse = gen_sort_dir.startswith("↓")
            sorted_results = sorted(
                results,
                key=lambda lu: calc_total_score(lu, gen_display_metric, player_lookup),
                reverse=gen_reverse,
            )

            # ── Tag filter ────────────────────────────────────────────────────
            def get_gen_tags(num):
                """Return list of tags for a generated lineup."""
                widget_key = f"gen_tag_{num}"
                if widget_key in st.session_state:
                    val = st.session_state[widget_key]
                    return val if isinstance(val, list) else ([val] if val else [])
                stored = st.session_state.lineup_tags.get(num, [])
                return stored if isinstance(stored, list) else ([stored] if stored else [])

            gen_all_tags = sorted({
                tag
                for r in results
                for tag in get_gen_tags(r.get("Lineup #"))
                if tag
            })
            gen_tag_filter = None
            if gen_all_tags:
                gfilt_col, _ = st.columns([2, 5])
                with gfilt_col:
                    gen_tag_opts = ["All Tags"] + gen_all_tags
                    gen_tag_sel = st.selectbox(
                        "🏷️ Filter by Tag", options=gen_tag_opts, index=0,
                        key="gen_tag_filter",
                    )
                    if gen_tag_sel != "All Tags":
                        gen_tag_filter = gen_tag_sel

            if gen_tag_filter:
                sorted_results = [
                    lu for lu in sorted_results
                    if gen_tag_filter in get_gen_tags(lu.get("Lineup #"))
                ]
                st.markdown(
                    f'<div class="info-box" style="margin:0.4rem 0 0.6rem">Showing <b>{len(sorted_results)}</b> of {actual} lineups tagged <b>"{gen_tag_filter}"</b></div>',
                    unsafe_allow_html=True,
                )

            render_lineup_cards(
                sorted_results, player_lookup, gen_display_metric,
                saved_set=saved_set,
                mode="gen",
                id_prefix="gen",
            )

            # ── Save Selected (placed AFTER render so checkbox state is current) ──
            st.markdown("---")
            n_checked_now = sum(
                1 for num, v in st.session_state.gen_checked.items()
                if v and num in {r.get("Lineup #") for r in results}
            )
            # Global unique lineup numbers mean no ID collisions between runs.
            # If identical players already saved, merge tags instead of duplicating.
            def _lineup_players(lu):
                return tuple(lu.get(s, "") for s in SLOT_COLS)

            existing_players = {_lineup_players(r): r.get("Lineup #")
                                for r in st.session_state.saved_lineups}
            to_save_now = []
            for r in results:
                if not st.session_state.gen_checked.get(r.get("Lineup #"), False):
                    continue
                player_key = _lineup_players(r)
                new_tags = get_gen_tags(r.get("Lineup #"))
                if player_key in existing_players:
                    # Merge tags into the already-saved lineup
                    existing_num = existing_players[player_key]
                    existing_tags = st.session_state.lineup_tags.get(existing_num, [])
                    if not isinstance(existing_tags, list):
                        existing_tags = [existing_tags] if existing_tags else []
                    merged = list(dict.fromkeys(existing_tags + [t for t in new_tags if t]))
                    st.session_state.lineup_tags[existing_num] = merged
                else:
                    # Copy current tags to the new saved lineup's number
                    st.session_state.lineup_tags[r.get("Lineup #")] = list(new_tags)
                    to_save_now.append(r)
            save_col, _ = st.columns([1, 3])
            with save_col:
                if st.button(
                    f"💾 Save Selected ({n_checked_now})",
                    key="gen_save_selected",
                    disabled=(n_checked_now == 0),
                    type="primary",
                    use_container_width=True,
                ):
                    st.session_state.saved_lineups.extend(to_save_now)
                    st.session_state.gen_checked = {}
                    st.session_state.cb_gen_gen += 1
                    st.rerun()

            # ── Summary ───────────────────────────────────────────────────────
            st.markdown('<div class="section-header">📊 Summary</div>', unsafe_allow_html=True)
            s1, s2, s3, s4 = st.columns(4)
            s1.metric("Lineups Generated", actual)

            # Score: prefer stored Total column, fall back to live calculation
            score_col = f"Total {gen_display_metric}"
            if score_col in results_df.columns:
                avg_score = round(results_df[score_col].mean(), 2)
            else:
                avg_score = round(
                    sum(calc_total_score(r, gen_display_metric, player_lookup) for r in results) / max(actual, 1), 2
                )
            s2.metric(f"Avg {gen_display_metric}", avg_score)

            # Ownership: live-calculate to handle decimal format correctly
            def lineup_total_own(lu):
                raws = [player_lookup.get(lu.get(s, ""), {}).get("Ownership", 0) for s in SLOT_COLS if lu.get(s, "")]
                raws = [v for v in raws if isinstance(v, (int, float))]
                if raws and max(raws) <= 1.0:
                    return sum(raws) * 100
                return sum(raws)
            avg_own = round(sum(lineup_total_own(r) for r in results) / max(actual, 1), 1)
            s3.metric("Avg Ownership %", avg_own)

            avg_sal = int(results_df["Total Salary"].mean()) if "Total Salary" in results_df.columns else 0
            s4.metric("Avg Salary Used", f"${avg_sal:,}")

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
                # Build ID lookup from player_lookup
                id_lookup = {
                    name: int(data.get("ID", 0))
                    for name, data in player_lookup.items()
                    if data.get("ID") not in (None, "", 0)
                }
                has_ids = bool(id_lookup)

                dk_df = results_df[avail_dk].copy()
                if has_ids:
                    for col in avail_dk:
                        dk_df[col] = dk_df[col].map(lambda n: id_lookup.get(n, n))

                with dl2:
                    st.download_button(
                        "📥 Download DraftKings Upload Format",
                        data=dk_df.to_csv(index=False),
                        file_name="ufl_lineups_dk.csv", mime="text/csv",
                        help="Player IDs used for upload." if has_ids else "No ID column found — using player names.",
                    )

            # ── Clear Lineups ──────────────────────────────────────────────────
            st.markdown("---")
            clear_col, _ = st.columns([1, 4])
            with clear_col:
                if st.button("🗑️ Clear Lineups", key="clear_lineups", use_container_width=True):
                    st.session_state.last_results = []
                    st.session_state.gen_checked = {}
                    st.session_state.cb_gen_gen += 1
                    st.rerun()


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
                st.session_state.cb_saved_gen += 1
                st.rerun()
        with ctrl_c:
            st.markdown("<div style='margin-top:28px'></div>", unsafe_allow_html=True)
            if st.button("⬜ Deselect All", key="saved_deselect_all"):
                st.session_state.saved_checked = {}
                st.session_state.cb_saved_gen += 1
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

        # ── Tag filter ───────────────────────────────────────────────────────
        # Read tags from both session_state.lineup_tags AND from the widget
        # keys directly (f"saved_tag_{num}") so tags entered this render
        # are immediately available without waiting for a rerun.
        def get_tags(num):
            """Return list of tags for a saved lineup."""
            widget_key = f"saved_tag_{num}"
            if widget_key in st.session_state:
                val = st.session_state[widget_key]
                return val if isinstance(val, list) else ([val] if val else [])
            stored = st.session_state.lineup_tags.get(num, [])
            return stored if isinstance(stored, list) else ([stored] if stored else [])

        all_tags = sorted({
            tag
            for r in saved
            for tag in get_tags(r.get("Lineup #"))
            if tag
        })
        tag_filter = None
        if all_tags:
            tag_filter_col, _ = st.columns([2, 5])
            with tag_filter_col:
                tag_options = ["All Tags"] + all_tags
                tag_filter = st.selectbox(
                    "🏷️ Filter by Tag", options=tag_options, index=0,
                    key="saved_tag_filter",
                )
                if tag_filter == "All Tags":
                    tag_filter = None

        # Sort lineups by calculated metric score
        reverse_sort = sort_dir.startswith("↓")
        sorted_saved = sorted(
            saved,
            key=lambda lu: calc_total_score(lu, card_optimize_by, card_player_lookup),
            reverse=reverse_sort,
        )

        # Apply tag filter
        if tag_filter:
            sorted_saved = [
                lu for lu in sorted_saved
                if tag_filter in get_tags(lu.get("Lineup #"))
            ]

        n_showing = len(sorted_saved)
        n_total   = len(saved)
        if tag_filter:
            st.markdown(
                f'<div class="info-box" style="margin:0.4rem 0 0.6rem">Showing <b>{n_showing}</b> of {n_total} saved lineups tagged <b>"{tag_filter}"</b></div>',
                unsafe_allow_html=True,
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
        def _tags_str(n):
            t = st.session_state.lineup_tags.get(n, [])
            if isinstance(t, list):
                return ", ".join(filter(None, t))
            return str(t) if t else ""
        export_df.insert(1, "Tags", export_df.get("Lineup #", pd.Series(dtype=str)).map(_tags_str))

        with dl_a:
            st.download_button(
                "📥 Download Saved Lineups (CSV)",
                data=export_df.to_csv(index=False),
                file_name="ufl_saved_lineups.csv", mime="text/csv",
            )

        avail_dk = [c for c in ["QB", "RB", "WR/TE 1", "WR/TE 2", "FLEX 1", "FLEX 2", "DST"] if c in saved_df.columns]
        if avail_dk:
            # Build ID lookup from uploaded pool if available
            saved_id_lookup = {}
            if uploaded_file is not None:
                try:
                    saved_id_lookup = {
                        name: int(data.get("ID", 0))
                        for name, data in card_player_lookup.items()
                        if data.get("ID") not in (None, "", 0)
                    }
                except Exception:
                    pass
            saved_has_ids = bool(saved_id_lookup)
            saved_dk_df = saved_df[avail_dk].copy()
            if saved_has_ids:
                for col in avail_dk:
                    saved_dk_df[col] = saved_dk_df[col].map(
                        lambda n: saved_id_lookup.get(n, n)
                    )
            with dl_b:
                st.download_button(
                    "📥 Download DraftKings Upload Format",
                    data=saved_dk_df.to_csv(index=False),
                    file_name="ufl_saved_lineups_dk.csv", mime="text/csv",
                    help="Player IDs used." if saved_has_ids else "No ID column — using names.",
                )
