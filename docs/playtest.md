# Bobbery Rob Playtest Logging & Balancing Guide

This document provides a structured protocol and log template for playtesting "The Forgotten Artifact" scenario. Use it to record player behaviors, claim consistency, suspicion trajectory, and balance issues.

---

## 1. Playtest Session Log Template

Copy and fill out this section for each playtest run:

```markdown
### Session ID: BR-PT-YYYYMMDD-01
- **Tester / Codename:** [e.g., PhantomFox]
- **Date & Time:** [e.g., 2026-11-24 15:30]
- **Build / Commit:** [e.g., feat/scenario-content @ HEAD]
- **Total Duration:** [e.g., 8m 42s]

#### Cover Story Claims
| Slot | Claimed Value | Turn Introduced | Guard Present |
|---|---|---|---|
| name | | | |
| occupation | | | |
| employer | | | |
| hometown | | | |
| reason_for_visit | | | |
| relationships | | | |
| other | | | |

#### Suspicion Trajectory
- Starting Suspicion: 10
- Turn-by-Turn Suspicion Timeline:
  - Turn 1 (Entrance / Officer Miller): [ ] -> Delta: [ ] (Reason: [ ])
  - Turn 2 (Main Hall / Officer Graves): [ ] -> Delta: [ ] (Reason: [ ])
  - Turn 3 (Checkpoint / Inspector Lin): [ ] -> Delta: [ ] (Reason: [ ])
  - Turn 4 (Restricted Area / Chief Sterling): [ ] -> Delta: [ ] (Reason: [ ])
  - Turn 5 (Vault Display / Officer Gomez): [ ] -> Delta: [ ] (Reason: [ ])
- Peak Suspicion: [ /100]
- Final Suspicion: [ /100]

#### Contradictions & Interrogations Flagged
- **Contradiction #1:**
  - *Prior Claim:* [e.g., Turn 1: "Art Historian"]
  - *Conflict Statement:* [e.g., Turn 3: "Master Electrician"]
  - *Was the flag accurate?* [Yes / No / Harmless variation]
  - *Explanation provided:* [e.g., "Dual certification"]
  - *Evaluator rating:* [Convincing / Partially Convincing / Unconvincing]
  - *Suspicion delta applied:* [ ]
- **Interrogation Triggered?** [Yes / No] (Turn: [ ])

#### Items Used
| Item ID | Target Guard / Location | Outcome (Success / Partial / Failure) | Consumed? |
|---|---|---|---|
| | | | |

#### Objectives & Ending
- **Objectives Completed:** [ /5]
- **Ending Achieved:** [Perfect Infiltration / Successful Infiltration / Compromised Victory / Capture / Alternate Ending]
- **Optional Challenge (Zero Interrogations):** [Passed / Failed]
- **Hidden Challenge (Zero Unresolved Contradictions):** [Passed / Failed]

#### Qualitative Player Feedback
- **What felt unfair?** (e.g., was a harmless synonym flagged as a contradiction? Did an explanation feel dismissed unfairly?)
- **What felt too easy?** (e.g., did a guard accept an absurd lie without scrutiny?)
- **Narrative & Immersion notes:**
```

---

## 2. Core Balancing Questions for Tuning

Review these questions during balance reviews with the engine and LLM owners:

1. **Initial Contradiction Penalty (+25 Suspicion):**
   - Is a first contradiction too punishing?
   - Moving from 10 to 35 immediately pushes the player into "Moderate Attention", while a second mistake (+25) pushes them to 60 ("High Scrutiny"). Does this leave enough room for player recovery?

2. **Explanation Recovery Deltas:**
   - Convincing explanation (`-10` delta): Does `-10` adequately reward a brilliant, lore-consistent player justification, or should it be `-15`?
   - Partially convincing explanation (`+5` delta): Does gaining 5 suspicion feel fair when an explanation is plausible but imperfect?

3. **Consumable Bribe Economy:**
   - The player starts with 3 `bribe_money`. Since each successful bribe subtracts 10–15 suspicion and allows bypass, does this make avoiding guards too easy if hoarding bribes for strict guards?
   - How does the strict guard's refusal (+30 suspicion penalty) influence player decision-making?

4. **False Claims vs Harmless Differences:**
   - Are conversational jokes or omitted details accidentally parsed by the LLM as contradicted claims?
   - Does the distinction between factual identity claims and rhetorical speech remain robust under creative player prompting?

5. **Route Progression Gating:**
   - Is requiring specific objectives to unlock routes intuitive to the player from the dialogue context alone, or do players get confused about why they cannot advance to the next room?
