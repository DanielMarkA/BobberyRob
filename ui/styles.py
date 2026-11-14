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

/* ---------- Panels ---------- */
.st-key-leaderboard_panel,
.st-key-entry_panel {
  background: var(--panel);
  border: 1px solid var(--line);
  border-radius: 12px;
  padding: 2rem 2rem 1.5rem;
  min-height: 640px;
}

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
"""


def inject_global_styles() -> None:
    """Call once per run, right after st.set_page_config()."""
    st.markdown(f"<style>{_CSS}</style>", unsafe_allow_html=True)