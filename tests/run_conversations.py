"""Runner and validator for scripted conversation test suites."""

import json
import sys
import unittest
from pathlib import Path

# Ensure project root is on sys.path for direct script execution
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from memory.store import MemoryStore
from scenario.loader import load_scenario


class ConversationScriptValidator(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.scenario = load_scenario()
        cls.conversations_dir = Path(__file__).resolve().parent / "conversations"
        cls.script_files = sorted(cls.conversations_dir.glob("*.json"))

    def test_all_conversation_scripts_exist(self) -> None:
        self.assertGreaterEqual(
            len(self.script_files),
            13,
            "Expected at least 13 conversation test script files.",
        )

    def test_script_schema_and_scenario_references(self) -> None:
        """Validate that all location, guard, and item IDs in test scripts exist in scenario."""
        for file_path in self.script_files:
            with self.subTest(file=file_path.name):
                with open(file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)

                self.assertIn("test_id", data)
                self.assertIn("title", data)

                # Check top-level location/guard if present
                if "location_id" in data:
                    self.assertIn(
                        data["location_id"],
                        self.scenario.locations,
                        f"{file_path.name} references unknown location '{data['location_id']}'",
                    )
                if "guard_id" in data:
                    self.assertIn(
                        data["guard_id"],
                        self.scenario.guards,
                        f"{file_path.name} references unknown guard '{data['guard_id']}'",
                    )

                # Check turn-level location/guard if present
                for turn in data.get("turns", []):
                    if "location_id" in turn:
                        self.assertIn(
                            turn["location_id"],
                            self.scenario.locations,
                            f"{file_path.name} turn references unknown location '{turn['location_id']}'",
                        )
                    if "guard_id" in turn:
                        self.assertIn(
                            turn["guard_id"],
                            self.scenario.guards,
                            f"{file_path.name} turn references unknown guard '{turn['guard_id']}'",
                        )

                # Check cases if present (e.g., item usages)
                for case in data.get("cases", []):
                    if "item_id" in case:
                        self.assertIn(
                            case["item_id"],
                            self.scenario.items,
                            f"{file_path.name} case references unknown item '{case['item_id']}'",
                        )
                    if "guard_id" in case:
                        self.assertIn(
                            case["guard_id"],
                            self.scenario.guards,
                            f"{file_path.name} case references unknown guard '{case['guard_id']}'",
                        )

    def test_memory_layer_simulation_for_claims_and_contradictions(self) -> None:
        """Simulate MemoryStore execution for cross-guard contradiction test."""
        script_path = self.conversations_dir / "05_contradiction_across_guards.json"
        with open(script_path, "r", encoding="utf-8") as f:
            script = json.load(f)

        store = MemoryStore()

        # Turn 1
        t1 = store.add_turn(
            speaker="player",
            text=script["turns"][0]["text"],
            guard_id=script["turns"][0]["guard_id"],
            location_id=script["turns"][0]["location_id"],
        )
        store.add_claim(slot="occupation", value="art historian", source_turn=t1.turn_id)

        # Turn 2
        t2 = store.add_turn(
            speaker="player",
            text=script["turns"][1]["text"],
            guard_id=script["turns"][1]["guard_id"],
            location_id=script["turns"][1]["location_id"],
        )
        c2 = store.add_claim(slot="occupation", value="master electrician", source_turn=t2.turn_id)

        # Find candidates for contradiction analysis
        candidates = store.candidates_for(c2.id)
        self.assertEqual(len(candidates), 1)
        self.assertEqual(candidates[0].value, "art historian")

        # Evidence retrieval
        evidence_turns = store.evidence([c.id for c in candidates])
        self.assertEqual(len(evidence_turns), 1)
        self.assertEqual(evidence_turns[0].turn_id, t1.turn_id)
        self.assertIn("art historian", evidence_turns[0].text)

    def test_memory_layer_simulation_for_correction(self) -> None:
        """Simulate MemoryStore claim correction without history loss."""
        script_path = self.conversations_dir / "04_immediate_correction.json"
        with open(script_path, "r", encoding="utf-8") as f:
            script = json.load(f)

        store = MemoryStore()
        t1 = store.add_turn(
            speaker="player",
            text=script["turns"][0]["text"],
            guard_id="guard_casual",
            location_id="museum_entrance",
        )
        c1 = store.add_claim(slot="employer", value="Oxford", source_turn=t1.turn_id)

        t2 = store.add_turn(
            speaker="player",
            text=script["turns"][1]["text"],
            guard_id="guard_casual",
            location_id="museum_entrance",
        )
        c2 = store.correct_claim(old_claim_id=c1.id, new_value="Cambridge", source_turn=t2.turn_id)

        self.assertEqual(store.get_claim(c1.id).status, "corrected")
        self.assertEqual(c2.status, "asserted")
        self.assertEqual(c2.supersedes, c1.id)
        self.assertEqual(c2.value, "Cambridge")


def main() -> None:
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(ConversationScriptValidator)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    if not result.wasSuccessful():
        sys.exit(1)


if __name__ == "__main__":
    main()
