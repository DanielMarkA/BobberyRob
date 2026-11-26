"""Scenario configuration loader and validator for Bobbery Rob."""

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

VALID_PERSONALITIES = ("casual", "strict", "observant", "experienced", "impatient")
VALID_ITEM_TYPES = ("consumable", "reusable")
REQUIRED_SUSPICION_EVENTS = (
    "contradiction",
    "unconvincing_explanation",
    "partially_convincing_explanation",
    "convincing_explanation",
    "repeated_evasion",
    "failed_item_use",
    "successful_item_use",
)


class ScenarioValidationError(ValueError):
    """Raised when a scenario configuration fails structural or referential integrity validation."""


@dataclass
class LocationDef:
    id: str
    name: str
    short_description: str
    security_level: int
    image: str
    thumbnail: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class RouteCondition:
    type: str
    objective_id: str | None = None
    item_id: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class RouteDef:
    from_location: str
    to_location: str
    condition: RouteCondition | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class GuardDef:
    id: str
    name: str
    role: str
    personality: str
    assigned_location: str
    opening_line: str
    style_note: str
    portrait: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ItemEffect:
    outcome: str
    consumed: bool
    suspicion_delta: int
    dialogue: str
    notice: str
    triggers_interrogation: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ItemDef:
    id: str
    name: str
    description: str
    type: str
    starting_quantity: int
    image: str
    usage_conditions: dict[str, Any] = field(default_factory=dict)
    effects: dict[str, ItemEffect] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ObjectiveDef:
    id: str
    name: str
    text: str
    description: str
    completion_type: str
    target: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class SuspicionThreshold:
    range: list[int]
    tier: str
    label: str
    behavior: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class SuspicionSettings:
    starting_value: int
    min_value: int
    max_value: int
    thresholds: list[SuspicionThreshold]
    event_table: dict[str, dict[str, Any]]
    balancing_note: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class EndingDef:
    id: str
    title: str
    outcome_label: str
    tone: str
    heading: str
    conditions: dict[str, Any]
    narration_seed: str
    quote: str
    quote_by: str
    scene_image: str
    scene_caption: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ScenarioConfig:
    scenario_id: str
    title: str
    summary: str
    location_name: str
    location_image: str
    starting_location: str
    mission_briefing: dict[str, Any]
    starting_inventory: list[dict[str, Any]]
    locations: dict[str, LocationDef]
    routes: list[RouteDef]
    guards: dict[str, GuardDef]
    items: dict[str, ItemDef]
    objectives: dict[str, ObjectiveDef]
    suspicion_settings: SuspicionSettings
    endings: dict[str, EndingDef]
    challenges: dict[str, Any]
    raw_data: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "scenario_id": self.scenario_id,
            "title": self.title,
            "summary": self.summary,
            "location_name": self.location_name,
            "location_image": self.location_image,
            "starting_location": self.starting_location,
            "mission_briefing": self.mission_briefing,
            "starting_inventory": self.starting_inventory,
            "locations": {k: v.to_dict() for k, v in self.locations.items()},
            "routes": [r.to_dict() for r in self.routes],
            "guards": {k: v.to_dict() for k, v in self.guards.items()},
            "items": {k: v.to_dict() for k, v in self.items.items()},
            "objectives": {k: v.to_dict() for k, v in self.objectives.items()},
            "suspicion_settings": self.suspicion_settings.to_dict(),
            "endings": {k: v.to_dict() for k, v in self.endings.items()},
            "challenges": self.challenges,
        }


def validate_scenario(data: dict[str, Any]) -> ScenarioConfig:
    """Validate raw scenario dictionary and return a typed ScenarioConfig.

    Raises ScenarioValidationError if any required fields are missing,
    IDs are duplicated, or foreign key references do not resolve.
    """
    required_root_keys = (
        "scenario_id",
        "title",
        "summary",
        "starting_location",
        "mission_briefing",
        "starting_inventory",
        "locations",
        "routes",
        "guards",
        "items",
        "objectives",
        "suspicion_settings",
        "endings",
    )
    for key in required_root_keys:
        if key not in data:
            raise ScenarioValidationError(f"Missing required root key: '{key}'")

    # 1. Locations
    raw_locations = data.get("locations", [])
    if not isinstance(raw_locations, list) or len(raw_locations) == 0:
        raise ScenarioValidationError("'locations' must be a non-empty list.")

    locations: dict[str, LocationDef] = {}
    for loc in raw_locations:
        loc_id = loc.get("id")
        if not loc_id:
            raise ScenarioValidationError("Location missing 'id' field.")
        if loc_id in locations:
            raise ScenarioValidationError(f"Duplicate location ID: '{loc_id}'")
        for field_name in ("name", "short_description", "security_level", "image", "thumbnail"):
            if field_name not in loc:
                raise ScenarioValidationError(f"Location '{loc_id}' missing field '{field_name}'")
        locations[loc_id] = LocationDef(
            id=loc_id,
            name=loc["name"],
            short_description=loc["short_description"],
            security_level=loc["security_level"],
            image=loc["image"],
            thumbnail=loc["thumbnail"],
        )

    # Validate starting_location
    starting_loc = data.get("starting_location")
    if starting_loc not in locations:
        raise ScenarioValidationError(
            f"starting_location '{starting_loc}' is not defined in locations."
        )

    # 2. Objectives
    raw_objectives = data.get("objectives", [])
    if not isinstance(raw_objectives, list) or len(raw_objectives) == 0:
        raise ScenarioValidationError("'objectives' must be a non-empty list.")

    objectives: dict[str, ObjectiveDef] = {}
    for obj in raw_objectives:
        obj_id = obj.get("id")
        if not obj_id:
            raise ScenarioValidationError("Objective missing 'id' field.")
        if obj_id in objectives:
            raise ScenarioValidationError(f"Duplicate objective ID: '{obj_id}'")
        for field_name in ("name", "text", "description", "completion_type", "target"):
            if field_name not in obj:
                raise ScenarioValidationError(f"Objective '{obj_id}' missing field '{field_name}'")
        if obj["completion_type"] == "location_reached" and obj["target"] not in locations:
            raise ScenarioValidationError(
                f"Objective '{obj_id}' targets unknown location '{obj['target']}'"
            )
        objectives[obj_id] = ObjectiveDef(
            id=obj_id,
            name=obj["name"],
            text=obj["text"],
            description=obj["description"],
            completion_type=obj["completion_type"],
            target=obj["target"],
        )

    # 3. Guards
    raw_guards = data.get("guards", [])
    if not isinstance(raw_guards, list) or len(raw_guards) == 0:
        raise ScenarioValidationError("'guards' must be a non-empty list.")

    guards: dict[str, GuardDef] = {}
    for g in raw_guards:
        guard_id = g.get("id")
        if not guard_id:
            raise ScenarioValidationError("Guard missing 'id' field.")
        if guard_id in guards:
            raise ScenarioValidationError(f"Duplicate guard ID: '{guard_id}'")
        for field_name in (
            "name",
            "role",
            "personality",
            "assigned_location",
            "opening_line",
            "style_note",
            "portrait",
        ):
            if field_name not in g:
                raise ScenarioValidationError(f"Guard '{guard_id}' missing field '{field_name}'")
        if g["personality"] not in VALID_PERSONALITIES:
            raise ScenarioValidationError(
                f"Guard '{guard_id}' personality '{g['personality']}' is invalid. "
                f"Must be one of: {', '.join(VALID_PERSONALITIES)}"
            )
        if g["assigned_location"] not in locations:
            raise ScenarioValidationError(
                f"Guard '{guard_id}' assigned to unknown location '{g['assigned_location']}'"
            )
        guards[guard_id] = GuardDef(
            id=guard_id,
            name=g["name"],
            role=g["role"],
            personality=g["personality"],
            assigned_location=g["assigned_location"],
            opening_line=g["opening_line"],
            style_note=g["style_note"],
            portrait=g["portrait"],
        )

    # 4. Items
    raw_items = data.get("items", [])
    if not isinstance(raw_items, list) or len(raw_items) == 0:
        raise ScenarioValidationError("'items' must be a non-empty list.")

    items: dict[str, ItemDef] = {}
    for it in raw_items:
        item_id = it.get("id")
        if not item_id:
            raise ScenarioValidationError("Item missing 'id' field.")
        if item_id in items:
            raise ScenarioValidationError(f"Duplicate item ID: '{item_id}'")
        for field_name in ("name", "description", "type", "starting_quantity"):
            if field_name not in it:
                raise ScenarioValidationError(f"Item '{item_id}' missing field '{field_name}'")
        if it["type"] not in VALID_ITEM_TYPES:
            raise ScenarioValidationError(
                f"Item '{item_id}' type '{it['type']}' is invalid. Must be 'consumable' or 'reusable'."
            )
        # Validate usage condition locations
        usage_conds = it.get("usage_conditions", {})
        for cond_loc in usage_conds.get("locations", []):
            if cond_loc not in locations:
                raise ScenarioValidationError(
                    f"Item '{item_id}' usage condition references unknown location '{cond_loc}'"
                )

        # Validate effects
        effects: dict[str, ItemEffect] = {}
        for target_guard_id, eff in it.get("effects", {}).items():
            if target_guard_id not in guards:
                raise ScenarioValidationError(
                    f"Item '{item_id}' defines effect for unknown guard '{target_guard_id}'"
                )
            for eff_key in ("outcome", "consumed", "suspicion_delta", "dialogue", "notice"):
                if eff_key not in eff:
                    raise ScenarioValidationError(
                        f"Item '{item_id}' effect on '{target_guard_id}' missing field '{eff_key}'"
                    )
            effects[target_guard_id] = ItemEffect(
                outcome=eff["outcome"],
                consumed=eff["consumed"],
                suspicion_delta=eff["suspicion_delta"],
                dialogue=eff["dialogue"],
                notice=eff["notice"],
                triggers_interrogation=bool(eff.get("triggers_interrogation", False)),
            )

        items[item_id] = ItemDef(
            id=item_id,
            name=it["name"],
            description=it["description"],
            type=it["type"],
            starting_quantity=it["starting_quantity"],
            image=it.get("image", ""),
            usage_conditions=usage_conds,
            effects=effects,
        )

    # 5. Routes
    raw_routes = data.get("routes", [])
    if not isinstance(raw_routes, list) or len(raw_routes) == 0:
        raise ScenarioValidationError("'routes' must be a non-empty list.")

    routes: list[RouteDef] = []
    for r in raw_routes:
        from_loc = r.get("from_location")
        to_loc = r.get("to_location")
        if not from_loc or not to_loc:
            raise ScenarioValidationError("Route missing 'from_location' or 'to_location'.")
        if from_loc not in locations:
            raise ScenarioValidationError(f"Route origin '{from_loc}' does not exist in locations.")
        if to_loc not in locations:
            raise ScenarioValidationError(
                f"Route destination '{to_loc}' does not exist in locations."
            )

        cond_obj = None
        raw_cond = r.get("condition")
        if raw_cond:
            c_type = raw_cond.get("type")
            if not c_type:
                raise ScenarioValidationError(
                    f"Route condition from '{from_loc}' to '{to_loc}' missing 'type'."
                )
            c_obj_id = raw_cond.get("objective_id")
            c_item_id = raw_cond.get("item_id")
            if c_obj_id and c_obj_id not in objectives:
                raise ScenarioValidationError(
                    f"Route '{from_loc}' -> '{to_loc}' references unknown objective '{c_obj_id}'"
                )
            if c_item_id and c_item_id not in items:
                raise ScenarioValidationError(
                    f"Route '{from_loc}' -> '{to_loc}' references unknown item '{c_item_id}'"
                )
            cond_obj = RouteCondition(type=c_type, objective_id=c_obj_id, item_id=c_item_id)

        routes.append(RouteDef(from_location=from_loc, to_location=to_loc, condition=cond_obj))

    # 6. Suspicion Settings
    raw_susp = data.get("suspicion_settings", {})
    for s_field in ("starting_value", "min_value", "max_value", "thresholds", "event_table"):
        if s_field not in raw_susp:
            raise ScenarioValidationError(f"suspicion_settings missing field '{s_field}'")

    s_min = raw_susp["min_value"]
    s_max = raw_susp["max_value"]
    s_start = raw_susp["starting_value"]
    if not (s_min <= s_start <= s_max):
        raise ScenarioValidationError(
            f"starting_value {s_start} must be between min_value {s_min} and max_value {s_max}."
        )

    thresholds: list[SuspicionThreshold] = []
    for th in raw_susp.get("thresholds", []):
        for th_key in ("range", "tier", "label", "behavior"):
            if th_key not in th:
                raise ScenarioValidationError(f"Suspicion threshold missing '{th_key}'")
        thresholds.append(
            SuspicionThreshold(
                range=th["range"],
                tier=th["tier"],
                label=th["label"],
                behavior=th["behavior"],
            )
        )

    event_tbl = raw_susp.get("event_table", {})
    for ev in REQUIRED_SUSPICION_EVENTS:
        if ev not in event_tbl:
            raise ScenarioValidationError(
                f"suspicion_settings event_table missing required event '{ev}'"
            )
        if "delta" not in event_tbl[ev]:
            raise ScenarioValidationError(f"Event '{ev}' missing 'delta'")

    suspicion_settings = SuspicionSettings(
        starting_value=s_start,
        min_value=s_min,
        max_value=s_max,
        thresholds=thresholds,
        event_table=event_tbl,
        balancing_note=raw_susp.get("balancing_note", ""),
    )

    # 7. Endings
    raw_endings = data.get("endings", [])
    if not isinstance(raw_endings, list) or len(raw_endings) == 0:
        raise ScenarioValidationError("'endings' must be a non-empty list.")

    endings: dict[str, EndingDef] = {}
    for ed in raw_endings:
        end_id = ed.get("id")
        if not end_id:
            raise ScenarioValidationError("Ending missing 'id' field.")
        if end_id in endings:
            raise ScenarioValidationError(f"Duplicate ending ID: '{end_id}'")
        for f_name in ("title", "outcome_label", "tone", "conditions", "narration_seed"):
            if f_name not in ed:
                raise ScenarioValidationError(f"Ending '{end_id}' missing field '{f_name}'")

        conds = ed["conditions"]
        for req_obj in conds.get("objectives_required", []):
            if req_obj not in objectives:
                raise ScenarioValidationError(
                    f"Ending '{end_id}' references unknown objective '{req_obj}'"
                )
        if "item_used" in conds and conds["item_used"] not in items:
            raise ScenarioValidationError(
                f"Ending '{end_id}' references unknown item '{conds['item_used']}'"
            )
        if "location_reached" in conds and conds["location_reached"] not in locations:
            raise ScenarioValidationError(
                f"Ending '{end_id}' references unknown location '{conds['location_reached']}'"
            )

        endings[end_id] = EndingDef(
            id=end_id,
            title=ed["title"],
            outcome_label=ed["outcome_label"],
            tone=ed["tone"],
            heading=ed.get("heading", "MISSION COMPLETE"),
            conditions=conds,
            narration_seed=ed["narration_seed"],
            quote=ed.get("quote", ""),
            quote_by=ed.get("quote_by", ""),
            scene_image=ed.get("scene_image", ""),
            scene_caption=ed.get("scene_caption", ""),
        )

    return ScenarioConfig(
        scenario_id=data["scenario_id"],
        title=data["title"],
        summary=data["summary"],
        location_name=data.get("location_name", "Grand Museum"),
        location_image=data.get("location_image", ""),
        starting_location=starting_loc,
        mission_briefing=data["mission_briefing"],
        starting_inventory=data["starting_inventory"],
        locations=locations,
        routes=routes,
        guards=guards,
        items=items,
        objectives=objectives,
        suspicion_settings=suspicion_settings,
        endings=endings,
        challenges=data.get("challenges", {}),
        raw_data=data,
    )


def load_scenario(path: str | Path | None = None) -> ScenarioConfig:
    """Load scenario configuration from JSON file and validate it.

    If path is omitted, defaults to 'scenario/museum.json' relative to workspace.
    """
    if path is None:
        path = Path(__file__).resolve().parent / "museum.json"
    else:
        path = Path(path).resolve()

    if not path.is_file():
        raise FileNotFoundError(f"Scenario configuration not found at: {path}")

    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    return validate_scenario(data)
