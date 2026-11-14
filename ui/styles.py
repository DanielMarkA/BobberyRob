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

.st-key-start_action { margin-top: 1.5rem; }
"""


def inject_global_styles() -> None:
    """Call once per run, right after st.set_page_config()."""
    st.markdown(f"<style>{_CSS}</style>", unsafe_allow_html=True)