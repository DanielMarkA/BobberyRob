"""Global styles for Bobbery Rob. All custom CSS lives here."""

import streamlit as st

_CSS = """
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

:root {
  --bg: #0B0B0D;
  --panel: #131316;
  --panel-2: #1A1A1E;
  --line: #2A2A30;
  --gold: #C8A24A;
  --text: #ECE8DF;
  --muted: #8C877D;
}

.stApp {
  font-family: 'Inter', sans-serif;
  background: radial-gradient(ellipse at 50% 0%, #1B1813 0%, var(--bg) 65%);
}

/* Hide Streamlit chrome we don't want */
header[data-testid="stHeader"],
[data-testid="stSidebar"],
[data-testid="collapsedControl"] { display: none; }

.block-container { max-width: 1250px; padding-top: 3rem; }

/* ---------- Primary buttons (all screens): dark text on gold for contrast ---------- */
.stApp [data-testid^="stBaseButton-primary"],
.stApp button[kind^="primary"] {
  height: 3.4rem; font-weight: 700; letter-spacing: 0.04em; color: #0B0B0D;
}
.stApp [data-testid^="stBaseButton-primary"] p { color: #0B0B0D; }

/* ---------- Panels ---------- */
.st-key-leaderboard_panel,
.st-key-entry_panel {
  background: var(--panel);
  border: 1px solid var(--line);
  border-radius: 12px;
  padding: 2rem 2rem 1.5rem;
  min-height: 640px;
}

/* ---------- Game entry ---------- */
.st-key-entry_panel { justify-content: center; padding: 2rem 3.4rem; }
.entry-mark {
  width: 86px; height: 64px; margin: 0 auto 1rem;
  display: flex; align-items: center; justify-content: center;
  border: 1px solid var(--line); border-radius: 8px;
  background: var(--panel-2); font-size: 1.8rem;
}
.entry-title {
  text-align: center; font-weight: 800; font-size: 3rem;
  letter-spacing: 0.06em; line-height: 1.1;
}
.entry-tagline { text-align: center; color: var(--muted); margin: 0.75rem 0 2.5rem; }

.st-key-entry_panel [data-testid="stForm"] { border: none; padding: 0; }
.st-key-entry_panel label p { font-size: 1rem; font-weight: 500; }
.st-key-entry_panel input { height: 3.2rem; font-size: 1.05rem; }

/* ---------- Leaderboard ---------- */
.lb-trophy {
  width: 64px; height: 48px; margin: 0 auto 0.75rem;
  display: flex; align-items: center; justify-content: center;
  border: 1px solid var(--line); border-radius: 8px;
  background: var(--panel-2); font-size: 1.4rem;
}
.lb-title {
  text-align: center; font-weight: 700; font-size: 1.3rem;
  letter-spacing: 0.14em; margin-bottom: 1.25rem;
}
.lb-head, .lb-row {
  display: grid; grid-template-columns: 3rem 1fr 5rem;
  gap: 0.5rem; align-items: center; padding: 0.55rem 1rem;
}
.lb-head {
  background: var(--panel-2); border-radius: 6px; margin-top: 0.75rem;
  color: var(--muted); font-size: 0.75rem; font-weight: 600;
  text-transform: uppercase; letter-spacing: 0.1em;
}
.lb-row { border-bottom: 1px solid rgba(255, 255, 255, 0.05); }
.lb-row.top {
  color: var(--gold); font-weight: 700;
  background: rgba(200, 162, 74, 0.09); border-radius: 6px;
}
.lb-name { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.lb-time { text-align: right; font-variant-numeric: tabular-nums; }
.lb-empty { text-align: center; color: var(--muted); padding: 3rem 0; }

/* ---------- Shared header ---------- */
.app-header {
  position: fixed; top: 0; left: 0; right: 0; z-index: 999; height: 84px;
  display: flex; align-items: center; padding: 0 4rem;
  background: var(--panel); border-bottom: 1px solid var(--line);
  font-weight: 700; font-size: 1.5rem; letter-spacing: 0.06em;
}

/* ---------- Image placeholder ---------- */
.img-slot {
  width: 100%; display: flex; flex-direction: column;
  align-items: center; justify-content: center; text-align: center;
  background: var(--panel-2); border: 1px solid var(--line); border-radius: 10px;
}
.img-slot-label {
  font-weight: 600; font-size: 0.85rem;
  letter-spacing: 0.1em; text-transform: uppercase;
}
.img-slot-caption { color: var(--muted); margin-top: 0.4rem; }

/* ---------- Mission briefing ---------- */
.brief-eyebrow {
  color: var(--muted); font-size: 0.8rem; font-weight: 600;
  letter-spacing: 0.22em; text-transform: uppercase;
}
.brief-title { font-size: 2.7rem; font-weight: 700; line-height: 1.15; margin: 0.5rem 0 1rem; }
.brief-summary {
  font-size: 1.1rem; line-height: 1.6; color: #CFCABF;
  padding-bottom: 1.5rem; margin-bottom: 1.75rem; border-bottom: 1px solid var(--line);
}
.brief-item { display: flex; gap: 1.25rem; margin-bottom: 1.5rem; }
.brief-num {
  flex: 0 0 44px; height: 44px; display: flex; align-items: center; justify-content: center;
  border: 1px solid var(--gold); border-radius: 6px; background: rgba(200, 162, 74, 0.08);
  color: var(--gold); font-weight: 600;
}
.brief-label { font-weight: 700; font-size: 0.95rem; letter-spacing: 0.06em; text-transform: uppercase; margin-bottom: 0.25rem; }
.brief-text { color: #CFCABF; line-height: 1.55; }
.brief-text ul { margin: 0.25rem 0 0; padding-left: 1.1rem; }


/* ---------- Cards (any container whose key starts with "card_") ---------- */
div[class*="st-key-card_"] {
  background: var(--panel); border: 1px solid var(--line);
  border-radius: 10px; padding: 1.25rem 1.4rem;
}
.card-title { font-size: 1.15rem; font-weight: 600; margin-bottom: 0.35rem; }
.card-sub { font-weight: 500; margin-bottom: 0.9rem; }
.card-text { color: #CFCABF; line-height: 1.55; }

/* Mission briefing card: collapsible, no inner border */
div[class*="st-key-card_briefing"] [data-testid="stExpander"] { border: none; }
div[class*="st-key-card_briefing"] [data-testid="stExpander"] summary {
  padding: 0; font-size: 1.15rem; font-weight: 600;
}

/* Objectives */
.obj { display: flex; gap: 0.75rem; align-items: flex-start; padding: 0.3rem 0; }
.obj-box { color: var(--muted); font-size: 1.1rem; line-height: 1.3; }
.obj.done { color: var(--muted); }
.obj.done .obj-box { color: var(--gold); }


/* ---------- Scene and dialogue ---------- */
div[class*="st-key-card_scene"] { padding: 0; overflow: hidden; }
.scene {
  position: relative; width: 100%; aspect-ratio: 914 / 640; background: var(--panel-2);
}
.scene-art {
  position: absolute; inset: 0; padding-bottom: 14%;
  display: flex; flex-direction: column; align-items: center; justify-content: center;
  text-align: center;
}
.dialogue-wrap {
  position: absolute; left: 2.2%; right: 2.2%; bottom: 3.5%;
  padding: 1.7rem 1.6rem 1.2rem;
  background: rgba(11, 11, 13, 0.9); border: 1px solid var(--line); border-radius: 10px;
}
.speaker {
  position: absolute; top: -1.15rem; left: 1.4rem; padding: 0.35rem 1rem;
  background: var(--panel); border: 1px solid var(--gold); border-radius: 6px;
  color: var(--gold); font-weight: 600; font-size: 0.95rem; letter-spacing: 0.04em;
}
.dialogue-text {
  font-size: 1.4rem; line-height: 1.45; min-height: 3.5rem;
  max-height: 8.5rem; overflow-y: auto;
}

/* ---------- Response bar ---------- */
.st-key-response_bar { margin-top: 0.25rem; }
.st-key-response_bar [data-testid="stForm"] { padding: 0; }
.st-key-response_bar textarea { font-size: 1.1rem; }
.stApp .st-key-response_bar [data-testid^="stBaseButton-primary"] { height: 96px; }


/* ---------- Suspicion meter ---------- */
.susp-value { font-size: 2.6rem; font-weight: 700; text-align: center; line-height: 1.1; margin: 0.4rem 0 0.9rem; }
.susp-value span { font-size: 1.2rem; font-weight: 500; color: var(--muted); }
.susp-track {
  height: 14px; background: var(--panel-2); border: 1px solid var(--line);
  border-radius: 999px; overflow: hidden;
}
.susp-fill { height: 100%; border-radius: 999px; background: var(--gold); }
.susp-fill.mid { background: #D98A2B; }
.susp-fill.high { background: #C0392B; }
.susp-label { text-align: center; color: var(--muted); margin-top: 0.7rem; }

/* ---------- Inventory ---------- */
.item-icon {
  width: 100%; aspect-ratio: 1; display: flex; align-items: center; justify-content: center;
  background: var(--panel); border: 1px solid var(--line); border-radius: 6px;
  color: var(--muted); font-size: 0.6rem; font-weight: 600; letter-spacing: 0.06em;
}
div[class*="st-key-item_"] {
  background: var(--panel-2); border: 1px solid var(--line);
  border-radius: 8px; padding: 0.4rem; margin-bottom: 0.5rem;
}
div[class*="st-key-item_sel_"] {
  border-color: var(--gold); background: rgba(200, 162, 74, 0.1);
}
div[class*="st-key-item_"] button {
  background: transparent; border: none; justify-content: flex-start; text-align: left;
}
div[class*="st-key-item_"] button p { text-align: left; }


/* ---------- Results ---------- */
.result-scene {
  position: relative; width: 100%; aspect-ratio: 1; overflow: hidden;
  background: var(--panel-2); border: 1px solid var(--line); border-radius: 10px;
}
.result-quote {
  position: absolute; left: 0; right: 0; bottom: 0; padding: 1.4rem 2rem;
  background: rgba(11, 11, 13, 0.88); text-align: center;
  font-size: 1.3rem; line-height: 1.4;
}
.result-quote small { display: block; margin-top: 0.3rem; color: var(--muted); font-size: 1rem; }

.result-heading { text-align: center; font-size: 2.4rem; font-weight: 800; letter-spacing: 0.06em; margin-bottom: 0.9rem; }
.result-banner {
  text-align: center; font-weight: 700; font-size: 1.5rem; padding: 1.1rem;
  border: 1px solid var(--gold); border-radius: 8px;
  background: rgba(200, 162, 74, 0.1); color: var(--gold);
}
.result-banner.partial { border-color: #D98A2B; background: rgba(217, 138, 43, 0.1); color: #D98A2B; }
.result-banner.failure { border-color: #C0392B; background: rgba(192, 57, 43, 0.12); color: #E5685A; }

.result-label {
  text-align: center; margin-top: 1.4rem; color: var(--muted);
  font-size: 0.85rem; font-weight: 600; letter-spacing: 0.12em; text-transform: uppercase;
}
.result-time { text-align: center; font-size: 4.6rem; font-weight: 700; line-height: 1.15; font-variant-numeric: tabular-nums; }
.result-note { text-align: center; color: var(--muted); margin-bottom: 0.5rem; }

.result-row {
  display: flex; justify-content: space-between; padding: 0.5rem 1.5rem; font-size: 1.15rem;
}
.result-row .v { font-variant-numeric: tabular-nums; }
.result-row.total {
  background: var(--panel-2); border-top: 1px solid var(--line); border-bottom: 1px solid var(--line);
  font-weight: 700; padding: 0.9rem 1.5rem; margin: 0.6rem 0;
}

.pb-panel {
  margin: 1.25rem auto 0; max-width: 90%; padding: 0.9rem 1.2rem; text-align: center;
  background: var(--panel-2); border: 1px solid var(--line); border-radius: 8px;
}
.pb-label { color: var(--muted); font-size: 0.8rem; font-weight: 600; letter-spacing: 0.12em; text-transform: uppercase; }
.pb-row { display: flex; justify-content: center; align-items: baseline; gap: 2.5rem; margin-top: 0.3rem; }
.pb-time { font-size: 1.7rem; font-weight: 700; font-variant-numeric: tabular-nums; }
.pb-badge { color: var(--gold); font-weight: 700; }

.st-key-result_actions { margin-top: 1.5rem; }
.st-key-result_actions button { height: 3.4rem; font-weight: 700; letter-spacing: 0.04em; }

.st-key-start_action { margin-top: 1.5rem; }
"""


def inject_global_styles() -> None:
    """Call once per run, right after st.set_page_config()."""
    st.markdown(f"<style>{_CSS}</style>", unsafe_allow_html=True)