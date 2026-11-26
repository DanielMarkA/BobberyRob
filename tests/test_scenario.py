"""Unit tests for scenario configuration loading and validation."""

import copy
import json
import unittest
from pathlib import Path

from scenario.loader import (
    ScenarioValidationError,
    load_scenario,
    validate_scenario,
)


class TestScenarioLoader(unittest.TestCase):
    def setUp(self) -> None:
        self.scenario = load_scenario()
        scenario_file = Path(__file__).resolve().parent.parent / "scenario" / "museum.json"
        with open(scenario_file, "r", encoding="utf-8") as f:
            self.raw_data = json.load(f)

    def test_load_valid_scenario(self) -> None:
        self.assertEqual(self.scenario.scenario_id, "the_forgotten_artifact")
        self.assertEqual(len(self.scenario.locations), 6)
        self.assertEqual(len(self.scenario.guards), 6)
        self.assertEqual(len(self.scenario.items), 4)
        self.assertEqual(len(self.scenario.objectives), 7)
        self.assertEqual(len(self.scenario.endings), 5)

    def test_unique_ids(self) -> None:
        location_ids = list(self.scenario.locations.keys())
        self.assertEqual(len(location_ids), len(set(location_ids)))

        guard_ids = list(self.scenario.guards.keys())
        self.assertEqual(len(guard_ids), len(set(guard_ids)))

        item_ids = list(self.scenario.items.keys())
        self.assertEqual(len(item_ids), len(set(item_ids)))

        objective_ids = list(self.scenario.objectives.keys())
        self.assertEqual(len(objective_ids), len(set(objective_ids)))

        ending_ids = list(self.scenario.endings.keys())
        self.assertEqual(len(ending_ids), len(set(ending_ids)))

    def test_duplicate_location_id_raises_error(self) -> None:
        bad_data = copy.deepcopy(self.raw_data)
        bad_data["locations"].append(bad_data["locations"][0])
        with self.assertRaises(ScenarioValidationError):
            validate_scenario(bad_data)

    def test_route_to_unknown_location_raises_error(self) -> None:
        bad_data = copy.deepcopy(self.raw_data)
        bad_data["routes"].append(
            {
                "from_location": "museum_entrance",
                "to_location": "nonexistent_room",
                "condition": None,
            }
        )
        with self.assertRaises(ScenarioValidationError):
            validate_scenario(bad_data)

    def test_guard_assigned_to_unknown_location_raises_error(self) -> None:
        bad_data = copy.deepcopy(self.raw_data)
        bad_data["guards"][0]["assigned_location"] = "secret_underground_bunker"
        with self.assertRaises(ScenarioValidationError):
            validate_scenario(bad_data)

    def test_item_effect_on_unknown_guard_raises_error(self) -> None:
        bad_data = copy.deepcopy(self.raw_data)
        bad_data["items"][0]["effects"]["nonexistent_guard"] = {
            "outcome": "success",
            "consumed": False,
            "suspicion_delta": -5,
            "dialogue": "Hello",
            "notice": "Notice",
        }
        with self.assertRaises(ScenarioValidationError):
            validate_scenario(bad_data)

    def test_ending_with_unknown_objective_raises_error(self) -> None:
        bad_data = copy.deepcopy(self.raw_data)
        bad_data["endings"][0]["conditions"]["objectives_required"] = ["unknown_obj"]
        with self.assertRaises(ScenarioValidationError):
            validate_scenario(bad_data)

    def test_invalid_personality_raises_error(self) -> None:
        bad_data = copy.deepcopy(self.raw_data)
        bad_data["guards"][0]["personality"] = "furious"
        with self.assertRaises(ScenarioValidationError):
            validate_scenario(bad_data)

    def test_export_to_dict_matches(self) -> None:
        exported = self.scenario.to_dict()
        self.assertIn("locations", exported)
        self.assertIn("guards", exported)
        self.assertIn("items", exported)
        self.assertIn("suspicion_settings", exported)


if __name__ == "__main__":
    unittest.main()
