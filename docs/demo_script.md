# Bobbery Rob Live Demo Script (3–5 Minutes)

This script provides a turn-by-turn presentation walkthrough for the CS365 demo. It showcases the core social-deception mechanics:
1. **A lie that works** (plausible cover story asserting claims without automatic suspicion).
2. **Item use** (leveraging inventory items to bypass security checks).
3. **A lie that gets caught & defended in interrogation** (cross-guard contradiction detection, evidence citation, and an explanation recovery).

---

## Pre-Demo Setup Checklist
- [ ] Ensure the app is running: `python -m streamlit run app.py`
- [ ] Browser window open at `http://localhost:8501`, sized to full screen.
- [ ] Codename entered on Main Menu: `Spectre`
- [ ] Click **Enter Game**, review Mission Briefing, and click **Start Mission**.

---

## Demo Walkthrough

### Act 1: Establishing the Cover (A Lie That Works) — 1 Minute
* **Location:** Museum Entrance & Reception
* **Guard:** Officer Miller (`guard_casual`)
* **Suspicion:** 10 / 100 ("Low Attention")

#### What to Say to Audience:
> *"Bobbery Rob gives the player complete freedom to invent their identity through natural conversation. The AI extracts structured claims into hidden memory slots, but never exposes a cheat-sheet identity summary. Watch how Officer Miller reacts to a well-crafted cover story."*

#### Exact Message to Type:
```text
Good evening officer. I'm Dr. Alistair Vance, a visiting art historian from the Cambridge Antiquities Trust. I'm here for after-hours inspection of the Queen Cynthia dynasty relics.
```

#### What to Point Out On-Screen:
1. **Dialogue Panel:** Officer Miller responds warmly in his casual persona:
   *"Hey Dr. Vance! Welcome. Let me just log you in—always great having visiting scholars."*
2. **Suspicion Meter:** Remains low (10/100). Emphasize that asserting new claims does **not** penalize the player.
3. **Objectives Panel:** `Enter the museum` marks as completed (`[x]`).

---

### Act 2: Using the Inventory (Item Action) — 1 Minute
* **Location:** Security Checkpoint
* **Guard:** Inspector Lin (`guard_observant`)
* **Suspicion:** 10 / 100

#### What to Say to Audience:
> *"Now we face Inspector Lin at the security scanner. Lin is observant and analytical. Dialogue alone cannot bypass physical checkpoints—the game engine enforces backend rules. Let's use our forged credentials."*

#### Actions to Perform:
1. In the **Inventory** panel on the right, click **Fake Passport**.
2. Point out that the item highlights and shows quantity `x1`.
3. Click the **Use item** button.

#### What to Point Out On-Screen:
1. **Notice Banner:** *"The receptionist validated your research passport."*
2. **Dialogue Panel:** Inspector Lin inspects the credentials:
   *"Passport serials match the academic guest list. You may proceed through checkpoint screening."*
3. **Suspicion Meter:** Decreases by 5 to 5/100 (successful item reward).
4. **Objectives Panel:** `Pass security` updates to completed.

---

### Act 3: The Contradiction & Interrogation Defense — 2 Minutes
* **Location:** Restricted Collection Area
* **Guard:** Chief Sterling (`guard_experienced`)

#### What to Say to Audience:
> *"Now we slip up. Chief Sterling is an experienced veteran who has worked here for thirty years. We are going to contradict our earlier claim to see how the memory store catches us."*

#### Exact Message to Type (The Blatant Contradiction):
```text
Out of the way, guard. I'm Marcus King, the chief high-voltage contractor. Facilities dispatched me for an emergency breaker malfunction in the vault.
```

#### What to Point Out On-Screen:
1. **Contradiction Caught:** Chief Sterling immediately references our Turn 1 claim:
   *"Hold on right there. Officer Miller's checkpoint report says you registered twenty minutes ago as Dr. Vance, an art historian from Cambridge. Now you claim to be an electrician named Marcus King?"*
2. **Suspicion Spike:** Suspicion jumps +25 points from 5 to 30 ("Moderate Attention").
3. **Interrogation Stance:** Sterling blocks the vault door and demands an explanation.

#### What to Say to Audience:
> *"The backend queried `candidates_for('occupation')`, pulled the verbatim Turn 1 transcript as evidence, and flagged the conflict. Now we must provide a convincing explanation to de-escalate."*

#### Exact Message to Type (The Convincing Explanation):
```text
Chief Sterling, forgive the abruptness. The Antiquities Trust employs me specifically for specialized display wiring inside heritage cases—restoring ancient micro-filament lighting requires dual degrees in historical conservation and electrical engineering. Here is my dual-certification registry number: CT-8842.
```

#### What to Point Out On-Screen:
1. **Dialogue Panel:** Chief Sterling nods thoughtfully:
   *"Fair enough. High-voltage work around Cynthia dynasty relics requires special handling. I'll verify the registry number, but keep your hands where I can see them."*
2. **Suspicion Meter:** Drops by 10 points (from 30 down to 20), rewarding the player for a credible, contextual explanation.
3. **Player Recovery:** The route to the vault display remains accessible without triggering detention.

---

### Wrap-Up / Takeaway (30 Seconds)
* Summarize:
  - **Authored World vs Freeform Identity:** The museum rules, guards, items, and routes are rigid, while the player's deception strategy is fluid.
  - **Deterministic Engine Oversight:** The LLM roleplays personality and evaluates plausibility, but the Python backend controls suspicion deltas, items, and victory conditions.
  - Show the **Results Screen** (or trigger developer shortcut ending) to display the mission statistics, penalties breakdown, and narrative outcome.
