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

# ── Session State Initialisation ──────────────────────────────────────────────
# st.session_state is Streamlit's built-in memory. It keeps data alive across
# page interactions within the same browser session — no database needed.
if "saved_lineups" not in st.session_state:
    st.session_state.saved_lineups = []   # list of lineup row dicts
if "last_results" not in st.session_state:
    st.session_state.last_results = []    # most recently generated lineups

# ── Custom CSS ────────────────────────────────────────────────────────────────
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Bebas+Neue&family=Inter:wght@300;400;500;600&display=swap');

    html, body, [class*="css"] { font-family: 'Inter', sans-serif; }

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
    .success-banner {
        background: #052e16;
        border: 1px solid #16a34a;
        border-radius: 6px;
        padding: 0.8rem 1rem;
        color: #4ade80;
        font-weight: 500;
        margin: 1rem 0;
    }
    div[data-testid="stDataFrame"] { border-radius: 8px; overflow: hidden; }
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
    Upload your weekly CSV file. Required columns:<br>
    <b>Player, Position, Team, Salary, Ownership</b><br><br>
    Optional: <b>DK Points, Value, T.Val, Leverage, Pts/S, ID</b>
    </div>
    """, unsafe_allow_html=True)

    uploaded_file = st.file_uploader(
        "Choose your CSV file", type=["csv"],
        help="Download from your projections source and upload here each week."
    )

    st.markdown('<div class="section-header">⚙️ Settings</div>', unsafe_allow_html=True)

    ALL_OPTIMIZE_OPTIONS = ["DK Points", "Value", "T.Val", "Leverage", "Pts/S"]
    optimize_by = st.selectbox(
        "Optimize By", options=ALL_OPTIMIZE_OPTIONS, index=0,
        help="Which metric to maximise. DK Points = raw projected fantasy points."
    )

    num_lineups = st.number_input(
        "Number of Lineups to Generate",
        min_value=1, max_value=150, value=1, step=1,
        help="How many unique lineups to generate per run."
    )

    st.markdown('<div class="section-header">💰 Salary</div>', unsafe_allow_html=True)
    min_salary = st.number_input(
        "Minimum Salary Used ($)",
        min_value=40000, max_value=SALARY_CAP, value=49000, step=100,
        help="Optimizer must spend at least this much."
    )

    st.markdown('<div class="section-header">👥 Ownership</div>', unsafe_allow_html=True)
    use_max_ownership = st.checkbox(
        "Cap Cumulative Ownership", value=False,
        help="Avoid stacking high-ownership players. Good for GPP differentiation."
    )
    max_ownership = None
    if use_max_ownership:
        max_ownership = st.slider(
            "Max Total Ownership %", min_value=100, max_value=500, value=250, step=10,
            help="Sum of all 7 players' ownership % must stay under this value."
        )

    st.markdown('<div class="section-header">🏟️ Team Limits</div>', unsafe_allow_html=True)
    max_per_team = st.slider(
        "Max Players From One Team", min_value=1, max_value=5, value=4, step=1,
    )

    st.markdown('<div class="section-header">🔗 QB Stack</div>', unsafe_allow_html=True)
    force_stack = st.checkbox("Force QB + WR/TE Stack", value=False)
    stack_count = 1
    if force_stack:
        stack_count = st.radio(
            "WR/TE Stackmates Required", options=[1, 2], index=0,
            help="1 = single stack, 2 = double stack."
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
                         "Isiah Pacheco",   "Rashee Rice", "Mecole Hardman", "Chiefs DST"],
            "Position": ["QB", "WR", "TE", "RB", "WR", "WR", "DST"],
            "Team":     ["KC"] * 7,
            "Salary":   [8400, 7600, 6800, 6200, 5800, 4200, 3200],
            "DK Points":[28.4, 22.1, 14.3, 16.8, 12.4,  8.2,  9.1],
            "Value":    [3.38, 2.91, 2.10, 2.71, 2.14, 1.95, 2.84],
            "Ownership":[28.5, 18.2, 14.1, 22.3, 15.6,  8.4, 12.0],
            "ID":       [11191729, 11192543, 11192100, 11193021,
                         11192876, 11193154, 11190044],
            "Leverage": [1.2, 0.9, 0.6, 1.1, 0.7, 0.5, 0.4],
            "Pts/S":    [3.38, 2.91, 2.10, 2.71, 2.14, 1.95, 2.84],
            "T.Val":    [3.4,  2.8,  1.9,  2.6,  1.8,  1.2,  1.0],
        })
        st.dataframe(sample_data, use_container_width=True, hide_index=True)

    else:
        # ── Load & Validate ───────────────────────────────────────────────────
        try:
            raw_df = pd.read_csv(uploaded_file)
            validate_csv(raw_df)
            df = clean_dataframe(raw_df)

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

        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Total Players", len(df))
        m2.metric("QBs",  len(df[df["Position"] == "QB"]))
        m3.metric("RBs",  len(df[df["Position"] == "RB"]))
        m4.metric("WRs / TEs", len(df[df["Position"].isin(["WR", "TE"])]))

        pos_filter = st.multiselect(
            "Filter by Position", options=sorted(df["Position"].unique()), default=[],
        )
        display_df = df if not pos_filter else df[df["Position"].isin(pos_filter)]

        show_cols = ["Player", "Position", "Team", "Salary", "Ownership"]
        for c in ["DK Points", "Value", "T.Val", "Leverage", "Pts/S"]:
            if c in df.columns:
                show_cols.append(c)
        if "ID" in df.columns:
            show_cols.append("ID")

        st.dataframe(
            display_df[show_cols].sort_values("Salary", ascending=False),
            use_container_width=True, hide_index=True,
        )

        # ── Lock / Exclude ────────────────────────────────────────────────────
        st.markdown('<div class="section-header">🔒 Lock & Exclude Players</div>', unsafe_allow_html=True)
        col_lock, col_excl = st.columns(2)

        with col_lock:
            st.markdown("**Lock Players** — Force into every lineup")
            locked = st.multiselect(
                "Select players to lock", options=sorted(df["Player"].tolist()), default=[],
            )
        with col_excl:
            st.markdown("**Exclude Players** — Remove from all lineups")
            excluded = st.multiselect(
                "Select players to exclude", options=sorted(df["Player"].tolist()), default=[],
            )

        # ── Exposure Limits ───────────────────────────────────────────────────
        max_exposure_dict = {}
        if num_lineups > 1:
            st.markdown('<div class="section-header">📈 Exposure Limits (Optional)</div>', unsafe_allow_html=True)
            st.markdown("""
            <div class="info-box">
            Exposure = what % of lineups a player appears in. Cap individual players here
            to ensure variety across your lineup set.
            </div>
            """, unsafe_allow_html=True)
            exp_players = st.multiselect(
                "Set max exposure for specific players",
                options=sorted(df["Player"].tolist()), default=[],
            )
            for p in exp_players:
                pct = st.slider(
                    f"{p} — Max Exposure %", min_value=10, max_value=100,
                    value=50, step=10, key=f"exp_{p}",
                )
                max_exposure_dict[p] = max(1, int((pct / 100) * num_lineups))

        # ── Generate Button ───────────────────────────────────────────────────
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

            st.session_state.last_results = results

        # ── Show Results ──────────────────────────────────────────────────────
        results = st.session_state.last_results

        if results:
            results_df = pd.DataFrame(results)
            actual = len(results_df)

            st.markdown('<div class="section-header">📋 Generated Lineups</div>', unsafe_allow_html=True)
            st.markdown("""
            <div class="info-box">
            Click <b>💾 Save</b> next to any lineup to add it to your Saved Lineups tab
            for comparison and exposure tracking.
            </div>
            """, unsafe_allow_html=True)

            # Set of already-saved lineup numbers to avoid duplicate saves
            saved_lineup_nums = {r.get("Lineup #") for r in st.session_state.saved_lineups}

            for _, row in results_df.iterrows():
                lineup_num = row["Lineup #"]
                already_saved = lineup_num in saved_lineup_nums

                row_col, btn_col = st.columns([7, 1])
                with row_col:
                    st.dataframe(
                        pd.DataFrame([row]),
                        use_container_width=True,
                        hide_index=True,
                    )
                with btn_col:
                    st.markdown("<div style='margin-top:28px'></div>", unsafe_allow_html=True)
                    if already_saved:
                        st.success("✅")
                    else:
                        if st.button("💾 Save", key=f"save_{lineup_num}"):
                            st.session_state.saved_lineups.append(row.to_dict())
                            st.rerun()

            # ── Summary ───────────────────────────────────────────────────────
            st.markdown('<div class="section-header">📊 Summary</div>', unsafe_allow_html=True)
            score_col = f"Total {optimize_by}"
            s1, s2, s3, s4 = st.columns(4)
            s1.metric("Lineups Generated", actual)
            s2.metric(f"Avg {optimize_by}", round(results_df[score_col].mean(), 2))
            s3.metric("Avg Ownership %",    round(results_df["Total Ownership"].mean(), 1))
            s4.metric("Avg Salary Used",    f"${int(results_df['Total Salary'].mean()):,}")

            # ── Downloads ─────────────────────────────────────────────────────
            st.markdown('<div class="section-header">⬇️ Download</div>', unsafe_allow_html=True)
            dl1, dl2 = st.columns(2)

            with dl1:
                st.download_button(
                    "📥 Download Full Results (CSV)",
                    data=results_df.to_csv(index=False),
                    file_name="ufl_lineups_full.csv",
                    mime="text/csv",
                )

            dk_slot_cols = ["QB", "RB", "WR/TE 1", "WR/TE 2", "FLEX 1", "FLEX 2", "DST"]
            avail_dk = [c for c in dk_slot_cols if c in results_df.columns]
            if avail_dk:
                with dl2:
                    st.download_button(
                        "📥 Download DraftKings Upload Format",
                        data=results_df[avail_dk].to_csv(index=False),
                        file_name="ufl_lineups_dk.csv",
                        mime="text/csv",
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
        Generate lineups in the <b>Optimizer</b> tab, then click <b>💾 Save</b>
        next to any lineup you want to keep here for comparison.
        </div>
        """, unsafe_allow_html=True)

    else:
        saved_df = pd.DataFrame(saved)
        total_saved = len(saved_df)

        st.markdown(
            f'<div class="success-banner">💾 {total_saved} lineup(s) saved</div>',
            unsafe_allow_html=True,
        )

        # ── Saved Lineups Table ───────────────────────────────────────────────
        st.markdown('<div class="section-header">📋 Saved Lineups</div>', unsafe_allow_html=True)

        display_saved = saved_df.copy()
        display_saved.insert(0, "#", range(1, total_saved + 1))
        st.dataframe(display_saved, use_container_width=True, hide_index=True)

        # ── Remove a Lineup ───────────────────────────────────────────────────
        st.markdown("**Remove a saved lineup:**")
        remove_options = {
            f"#{i+1} — QB: {r.get('QB','?')} | Salary: ${r.get('Total Salary', 0):,}": i
            for i, r in enumerate(saved)
        }
        remove_label = st.selectbox("Select lineup to remove", ["— select —"] + list(remove_options.keys()))
        if remove_label != "— select —":
            if st.button("🗑️ Remove selected lineup"):
                idx = remove_options[remove_label]
                st.session_state.saved_lineups.pop(idx)
                st.rerun()

        # ── Player Exposure ───────────────────────────────────────────────────
        st.markdown('<div class="section-header">📈 Player Exposure</div>', unsafe_allow_html=True)
        st.markdown("""
        <div class="info-box">
        How often each player appears across all your saved lineups.<br>
        <b>Lineups</b> = raw count &nbsp;|&nbsp; <b>Exposure %</b> = share of your saved lineup pool.
        </div>
        """, unsafe_allow_html=True)

        slot_cols = ["QB", "RB", "WR/TE 1", "WR/TE 2", "FLEX 1", "FLEX 2", "DST"]
        present_slots = [c for c in slot_cols if c in saved_df.columns]

        # Flatten every player name from every slot into one list
        all_appearances = []
        for col in present_slots:
            all_appearances.extend(saved_df[col].dropna().tolist())

        counts = Counter(all_appearances)

        exposure_df = pd.DataFrame([
            {
                "Player":     player,
                "Lineups":    count,
                "Exposure %": round(count / total_saved * 100, 1),
            }
            for player, count in sorted(counts.items(), key=lambda x: -x[1])
        ])

        st.dataframe(
            exposure_df,
            use_container_width=True,
            hide_index=True,
            column_config={
                "Lineups": st.column_config.NumberColumn("# Lineups"),
                "Exposure %": st.column_config.ProgressColumn(
                    "Exposure %",
                    help="Percentage of saved lineups this player appears in",
                    format="%.1f%%",
                    min_value=0,
                    max_value=100,
                ),
            },
        )

        # ── Downloads ─────────────────────────────────────────────────────────
        st.markdown('<div class="section-header">⬇️ Download Saved Lineups</div>', unsafe_allow_html=True)
        dl_a, dl_b = st.columns(2)

        with dl_a:
            st.download_button(
                "📥 Download Saved Lineups (CSV)",
                data=saved_df.to_csv(index=False),
                file_name="ufl_saved_lineups.csv",
                mime="text/csv",
            )

        dk_slot_cols = ["QB", "RB", "WR/TE 1", "WR/TE 2", "FLEX 1", "FLEX 2", "DST"]
        avail_dk = [c for c in dk_slot_cols if c in saved_df.columns]
        if avail_dk:
            with dl_b:
                st.download_button(
                    "📥 Download DraftKings Upload Format",
                    data=saved_df[avail_dk].to_csv(index=False),
                    file_name="ufl_saved_lineups_dk.csv",
                    mime="text/csv",
                )
