"""Try one LLM call from the command line.

From the repository root:

    python -m llm.try_it "Actually I'm an electrician." --mock
    python -m llm.try_it "Actually I'm an electrician." --guard guard_strict
    python -m llm.try_it "I hold two degrees." --call evaluate
    python -m llm.try_it "Here is my invitation letter." --call dialogue

The sample context has one earlier claim: at turn 1 the player told
Officer Miller they are an art historian.
"""

import argparse
import json
import sys

from llm import get_client
from scenario.loader import load_scenario


def sample_context(guard_id: str) -> dict:
    scenario = load_scenario()
    guard = scenario.guards[guard_id]
    location = scenario.locations[guard.assigned_location]
    first_turn = {
        "turn_id": 1,
        "speaker": "player",
        "text": "Good evening, I'm Dr. Vance, an art historian conducting research.",
        "guard_id": "guard_casual",
        "location_id": "museum_entrance",
    }
    return {
        "guard": guard.to_dict(),
        "location": {"id": location.id, "name": location.name},
        "suspicion_label": "Moderate Attention",
        "interrogation": False,
        "inventory": [
            {"id": i["id"], "name": i["name"], "quantity": i["quantity"]}
            for i in scenario.starting_inventory
            if i["quantity"] > 0
        ],
        "earlier_claims": [
            {
                "id": 1,
                "slot": "occupation",
                "value": "art historian",
                "source_turn": 1,
                "status": "asserted",
                "supersedes": None,
            },
            {
                "id": 2,
                "slot": "name",
                "value": "Dr. Vance",
                "source_turn": 1,
                "status": "asserted",
                "supersedes": None,
            },
        ],
        "evidence": [first_turn],
        "recent_turns": [first_turn],
        "reports": [],
        "current_turn_id": 3,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("message", help="the player's message")
    parser.add_argument("--call", choices=["analyze", "dialogue", "evaluate"], default="analyze")
    parser.add_argument("--guard", default="guard_strict", help="guard id from museum.json")
    parser.add_argument("--mock", action="store_true", help="use the mock client")
    args = parser.parse_args()

    try:
        client = get_client(mock=True if args.mock else None)
    except RuntimeError as exc:
        sys.exit(f"{exc}")

    context = sample_context(args.guard)
    if args.call == "analyze":
        result = client.analyze(args.message, context)
    elif args.call == "evaluate":
        context["interrogation"] = True
        result = client.evaluate_explanation(args.message, context)
    else:
        outcome = {"event": "player_spoke", "facts": ["No game state changed this turn."]}
        result = {"dialogue": client.write_dialogue(args.message, outcome, context)}

    print(f"model: {client.model}")
    print(json.dumps(result, indent=2, ensure_ascii=False))
    if client.last_error:
        print(f"last_error: {client.last_error}", file=sys.stderr)


if __name__ == "__main__":
    main()
