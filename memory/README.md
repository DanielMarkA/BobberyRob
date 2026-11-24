# Memory Layer API Guide

The `memory` package provides deterministic storage and retrieval for dialogue turns, claims, and guard security reports. It contains no LLM calls and performs no heuristic searches.

## Role Responsibilities

| Role | Permitted Access | Methods Called |
| --- | --- | --- |
| **Engine** (`engine/turn.py`, game rules) | Write & update claims, turns, and reports | `add_turn`, `add_claim`, `correct_claim`, `set_status`, `add_report`, `to_dict`, `from_dict` |
| **LLM Layer** (`llm/`, prompt building) | Read candidates and evidence for evaluation | `candidates_for`, `evidence`, `guard_view` |
| **UI** (`screens/`, `ui/`) | **No access** | The UI never touches memory directly. It renders game state supplied by the engine. |

> **Note:** To preserve hidden identity deception mechanics, there is no function that compiles or exposes the player's full identity.

---

## Worked Example: Detecting Conflicting Claims

When a player makes a statement, the engine logs the turn and stores any extracted claim. The LLM layer then queries `candidates_for` to find earlier claims in the same slot to evaluate for contradictions:

```python
from memory import MemoryStore

store = MemoryStore()

# 1. Turn 1: Player claims to be an art historian
t1 = store.add_turn(
    speaker="player",
    text="Good evening officer, I'm Dr. Vance, an art historian.",
    guard_id="guard_checkpoint",
    location_id="museum_entrance",
)
c1 = store.add_claim(slot="occupation", value="art historian", source_turn=t1.turn_id)

# 2. Turn 2: Guard responds
t2 = store.add_turn(
    speaker="guard",
    text="Do you have authorization to enter the restricted wing?",
    guard_id="guard_checkpoint",
    location_id="museum_entrance",
)

# 3. Turn 3: Player slips up and claims to be an electrician
t3 = store.add_turn(
    speaker="player",
    text="I'm here to fix the breaker box; I'm an electrician.",
    guard_id="guard_checkpoint",
    location_id="museum_entrance",
)
c2 = store.add_claim(slot="occupation", value="electrician", source_turn=t3.turn_id)

# 4. LLM query: Retrieve earlier statements in the same slot for contradiction analysis
conflicts = store.candidates_for(c2.id)
# conflicts -> [Claim(id=1, slot='occupation', value='art historian', status='asserted', ...)]

# 5. Retrieve exact verbatim quotes for prompt context
quote_turns = store.evidence([c.id for c in conflicts])
# quote_turns[0].text -> "Good evening officer, I'm Dr. Vance, an art historian."
```

---

## State Persistence

`MemoryStore` can serialize to and deserialize from plain Python dictionaries:

```python
data = store.to_dict()
restored_store = MemoryStore.from_dict(data)
```
