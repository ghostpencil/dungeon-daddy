from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator, model_validator

ClockCategory = Literal[
    "objective",
    "relationship",
    "faction_pressure",
    "dungeon_intimacy",
    "danger",
    "pursuit",
    "ritual",
]

_ADVERSE_CATEGORIES = frozenset({"danger", "pursuit", "ritual"})

# The canonical ClockCategory members, as a runtime-iterable tuple (the Literal
# type itself is not iterable). Order matches the Literal above.
CLOCK_CATEGORIES: tuple[ClockCategory, ...] = (
    "objective",
    "relationship",
    "faction_pressure",
    "dungeon_intimacy",
    "danger",
    "pursuit",
    "ritual",
)
_CLOCK_CATEGORY_MEMBERS = frozenset(CLOCK_CATEGORIES)

# Non-enum category strings that appear in seeded/authored data (e.g. the
# campaign manifests) mapped onto their canonical ClockCategory. "threat" and
# "environment" are generic adverse buckets → danger; "escalation" is an
# alert/detection ramp → pursuit.
_CLOCK_CATEGORY_SYNONYMS: dict[str, ClockCategory] = {
    "threat": "danger",
    "environment": "danger",
    "escalation": "pursuit",
}

# Fallback for an unrecognized category. Deliberately a firewall-protected,
# non-adverse member: an unknown clock must never become ambient-eligible
# (that fail-safe asymmetry is the whole point of the firewall). Unknowns are
# reported via is_known_clock_category rather than coerced silently.
_UNKNOWN_CLOCK_CATEGORY_FALLBACK: ClockCategory = "faction_pressure"


def is_adverse(category: ClockCategory | None) -> bool:
    """A clock is adverse iff its category is danger, pursuit, or ritual.

    Takes an already-normalized ``ClockCategory`` (or ``None``). The narrowed
    signature is deliberate: callers must run raw strings through
    ``normalize_clock_category`` first, or a synonym like ``"threat"`` would be
    read as non-adverse and silently drop out of the ambient tier.
    """
    return category in _ADVERSE_CATEGORIES


def is_known_clock_category(category: str | None) -> bool:
    """True if the raw category is None, a canonical member, or a known synonym.

    A False result is the explicit "unknown category" signal — a data pass can
    flag the clock instead of silently coercing it to the fallback.
    """
    if category is None:
        return True
    return category in _CLOCK_CATEGORY_MEMBERS or category in _CLOCK_CATEGORY_SYNONYMS


def normalize_clock_category(category: str | None) -> ClockCategory | None:
    """Map a raw clock category string onto the ClockCategory enum.

    None stays None; canonical members pass through unchanged (idempotent);
    known synonyms map to their canonical member; anything else falls back to
    _UNKNOWN_CLOCK_CATEGORY_FALLBACK. Every non-None result is a valid enum member.
    """
    if category is None:
        return None
    if category in _CLOCK_CATEGORY_MEMBERS:
        return category
    if category in _CLOCK_CATEGORY_SYNONYMS:
        return _CLOCK_CATEGORY_SYNONYMS[category]
    return _UNKNOWN_CLOCK_CATEGORY_FALLBACK


class StressTrack(BaseModel):
    track_key: str
    capacity: int = 4
    filled: int = 0

    @field_validator("filled")
    @classmethod
    def filled_not_negative(cls, v: int) -> int:
        if v < 0:
            raise ValueError("filled cannot be negative")
        return v

    @model_validator(mode="after")
    def filled_within_capacity(self) -> StressTrack:
        if self.filled > self.capacity:
            raise ValueError("filled cannot exceed capacity")
        return self


class ClockState(BaseModel):
    clock_id: str
    campaign_id: str
    label: str
    segments: int
    filled: int = 0
    status: Literal["active", "completed", "abandoned"] = "active"
    scope_room_id: str | None = None
    action_tags: list[str] = Field(default_factory=list)
    clock_level: Literal["room", "level", "dungeon", "quest", "character", "faction"] = "dungeon"
    # Typed with ClockCategory for the firewall (Phase 51.6), but `str` is still
    # accepted so pre-normalization saves/seeds (e.g. "threat") load; Slice 2 maps
    # those onto the enum.
    category: ClockCategory | str | None = None
    level_id: str | None = None
    owner_actor_id: str | None = None
    stakes: str | None = None
    completion_effect: str | None = None
    visible_to_player: bool = True
    monotonic: bool = True
    tags: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def filled_within_segments(self) -> ClockState:
        if self.filled > self.segments:
            raise ValueError("filled cannot exceed segments")
        return self


class ActionRating(BaseModel):
    actor_id: str
    action_key: str
    rating: int = 0

    @field_validator("rating")
    @classmethod
    def rating_in_range(cls, v: int) -> int:
        if not (0 <= v <= 3):
            raise ValueError("rating must be 0–3")
        return v


class ActorState(BaseModel):
    actor_id: str
    campaign_id: str
    actor_type: Literal["pc", "npc", "monster", "dungeon", "faction", "dungeon_presence"]
    slug: str
    display_name: str
    concept: str | None = None
    status: Literal["active", "inactive", "dead", "absorbed", "lost"] = "active"
    markdown_path: str | None = None
    actions: dict[str, int] = Field(default_factory=dict)
    stress: dict[str, StressTrack] = Field(default_factory=dict)
    abilities: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    playbook_slug: str | None = None
    room_id: str | None = None
    # Stance toward the party. Gates dialogue: only a "willing" creature can be
    # spoken to (Phase 50.6 §6); "wary"/"hostile" stay contested. Surfaced as the
    # CREATURES status chip in the "Things Here" overlay (§5.2).
    disposition: Literal["hostile", "wary", "neutral", "willing"] = "neutral"


class Ability(BaseModel):
    actor_id: str
    ability_key: str
    value: str | None = None


class ActionRequest(BaseModel):
    campaign_id: str
    scene_id: str | None = None
    actor_id: str
    action_key: str
    dice_pool: int = 1
    momentum_spend: int = 0
    push_yourself: bool = False
    intent: str | None = None


class ActionResolution(BaseModel):
    resolution_id: str
    campaign_id: str
    actor_id: str
    action_key: str
    dice_rolled: list[int]
    outcome: Literal["critical", "full", "partial", "miss"]
    stress_cost: int = 0
    notes: str | None = None
    intent: str | None = None


class ReactionClockLine(BaseModel):
    clock_id: str
    label: str
    ticks: int
    new_filled: int
    new_status: str
    reason: str


class ReactionStressLine(BaseModel):
    actor_id: str
    display_name: str
    track_key: str
    amount: int
    new_filled: int
    triggered_fallout: bool = False
    reason: str


class WorldReaction(BaseModel):
    reaction_id: str
    campaign_id: str
    source_resolution_id: str
    outcome: Literal["critical", "full", "partial", "miss"]
    clock_lines: list[ReactionClockLine] = Field(default_factory=list)
    stress_lines: list[ReactionStressLine] = Field(default_factory=list)
    summary_lines: list[str] = Field(default_factory=list)


class FactionState(BaseModel):
    faction_id: str
    campaign_id: str
    slug: str
    display_name: str
    concept: str | None = None
    goal: str | None = None
    status: Literal["active", "inactive", "dissolved"] = "active"
    reputation: Literal["hostile", "cold", "neutral", "warm", "allied"] = "neutral"
    tier: int = 0
    tags: list[str] = Field(default_factory=list)


class FalloutRecord(BaseModel):
    fallout_id: str
    campaign_id: str
    actor_id: str
    source_action_id: str | None = None
    track_key: Literal["body", "composure", "bonds", "weird"]
    severity: Literal["minor", "moderate", "severe"]
    title: str
    summary: str
    status: Literal["active", "resolved", "escalated"] = "active"
    mechanical_hooks: dict[str, Any] = Field(default_factory=dict)
    markdown_path: str | None = None


class ItemFeature(BaseModel):
    feature_id: str
    item_id: str
    feature_type: Literal["new_action", "rating_modifier"]
    action_key: str
    modifier: int | None = None

    @model_validator(mode="after")
    def check_modifier_consistency(self) -> ItemFeature:
        if self.feature_type == "rating_modifier" and self.modifier is None:
            raise ValueError("rating_modifier feature requires a non-null modifier")
        if self.feature_type == "new_action" and self.modifier is not None:
            raise ValueError("new_action feature must have modifier=None")
        return self


class Item(BaseModel):
    item_id: str
    campaign_id: str
    slug: str
    display_name: str
    item_type: Literal["class_kit", "dungeon_item", "equipped_gear"]
    description: str
    owner_actor_id: str | None = None
    room_id: str | None = None
    level_id: str | None = None
    status: Literal["active", "consumed", "inert", "lost"] = "active"
    charges_current: int | None = None
    charges_max: int | None = None
    is_equipped: bool = False
    combines_with_slug: str | None = None
    combination_result_slug: str | None = None
    features: list[ItemFeature] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)

    @field_validator("description")
    @classmethod
    def description_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("description must not be empty")
        return v

    @model_validator(mode="after")
    def check_item_invariants(self) -> Item:
        if self.item_type == "class_kit":
            if self.charges_max is None or self.charges_max < 1:
                raise ValueError("class_kit requires charges_max >= 1")
            current = self.charges_current if self.charges_current is not None else 0
            if not (0 <= current <= self.charges_max):
                raise ValueError("class_kit charges_current must be 0..charges_max")
        if self.item_type in ("class_kit", "dungeon_item") and self.features:
            raise ValueError(f"{self.item_type} must not carry features")
        return self


ObjectArchetype = Literal[
    "container",
    "door",
    "mechanism",
    "structure",
    "trap",
    "lore_fixture",
    "resource",
    "resonance_point",
]


class ObjectTransition(BaseModel):
    transition_id: str
    object_id: str
    from_state: str
    to_state: str
    trigger: str
    requires_item_slug: str | None = None
    spawns_item_slug: str | None = None
    advances_clock_slug: str | None = None
    contested: bool = False
    action_verb: str | None = None


class ObjectReactionBinding(BaseModel):
    """A scripted world-reaction consequence for a `scripted` RoomObject (Phase 51.6 §5).

    Authored, engine-owned mapping ``action_verb × outcome → consequence`` for the
    miss/partial tiers only (success/critical flow through transitions and the
    objective service, D5). ``action_verb`` may be ``"*"`` to match any verb.
    A binding may advance a clock, apply stress, or both.
    """

    binding_id: str
    object_id: str
    action_verb: str
    outcome: Literal["miss", "partial"]
    clock_slug: str | None = None
    clock_delta: int = 0
    stress_track: str | None = None
    stress_amount: int = 0

    @model_validator(mode="after")
    def check_effect_consistency(self) -> ObjectReactionBinding:
        """Reject silent-no-op shapes: a target without a magnitude (or vice versa).

        A ``clock_slug`` with a zero ``clock_delta`` (or a nonzero delta with no
        slug) matches a verb/outcome and then advances nothing — the exact silent
        failure this phase exists to prevent. Same for the stress pair. An
        all-empty binding stays legal (flavor-only), but a half-specified effect
        is always an authoring error.
        """
        if (self.clock_slug is not None) != (self.clock_delta != 0):
            raise ValueError(
                "clock_slug and a nonzero clock_delta must be set together"
            )
        if (self.stress_track is not None) != (self.stress_amount != 0):
            raise ValueError(
                "stress_track and a nonzero stress_amount must be set together"
            )
        return self


class RoomObject(BaseModel):
    object_id: str
    campaign_id: str
    room_id: str
    level_id: str
    slug: str
    display_name: str
    archetype: ObjectArchetype
    description: str
    current_state: str
    transitions: list[ObjectTransition] = Field(default_factory=list)
    # Phase 51.6 World Reaction Policy: how a miss/partial on this object reacts.
    # `ambient` = one locally-scoped adverse clock (§4); `scripted` = only the
    # authored `reaction_bindings` (§5); `inert` = no mechanics.
    reaction_policy: Literal["scripted", "ambient", "inert"] = "ambient"
    reaction_bindings: list[ObjectReactionBinding] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)

    @field_validator("description")
    @classmethod
    def description_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("description must not be empty")
        return v


class RoomState(BaseModel):
    """A room as a first-class campaign-DB entity (Phase 51.8 Slice B0, spec §7.1).

    The campaign-runtime projection of a dungeon room: the searchable, taggable,
    lore-bearing fields, seeded from the dungeon + campaign seed. Geometry/layout
    (``x/y/w/h``, loop roles, graph notes) stays in the dungeon JSON
    (:class:`dungeon_daddy.data.models.Room`) — this record does not duplicate it.
    ``summary`` is the inline setting-lore for fast retrieval; ``markdown_path``
    points to the full authored body (mirroring :class:`MemoryEntry`). ``quest_role``
    is the room's authoritative role in the quest; it is a **column only** and is
    NOT mirrored into ``tags`` — there is no ``quest:`` namespace (see
    ``memory/tags.py::TAG_NAMESPACES``), so such a tag would fail ``validate_tag``.
    ``tags`` are authored independently by the populate scripts (``theme:``/
    ``thread:``); nothing keeps the two in step.
    """

    room_id: str
    campaign_id: str
    level_id: str
    slug: str
    display_name: str
    room_type: str
    summary: str = ""
    quest_role: str | None = None
    markdown_path: str | None = None
    checksum: str | None = None
    tags: list[str] = Field(default_factory=list)


class ObjectiveCompletion(BaseModel):
    """Deterministic condition that completes an Objective (Phase 51.5 §4.3.1).

    Keyed to existing world state — the engine evaluates it by querying state, no
    LLM involvement (D4). ``object_state`` is the primary kind (a subsystem
    ``RoomObject`` reaching ``required_state``); item/room kinds are extensible.
    """

    kind: Literal["object_state", "item_obtained", "room_reached"]
    target_slug: str
    required_state: str | None = None

    @model_validator(mode="after")
    def object_state_requires_required_state(self) -> ObjectiveCompletion:
        if self.kind == "object_state" and not self.required_state:
            raise ValueError("object_state completion requires required_state")
        return self


class Objective(BaseModel):
    """A tracked, deterministically-completable goal (Phase 51.5 §4.3.1, D2).

    Completing the tier's objective advances the latching ``dungeon_intimacy``
    clock and unlocks that tier's ``reveals_knowledge``. Designed to also serve
    as the foundation for Phase 52 milestones (§10).
    """

    objective_id: str
    campaign_id: str
    slug: str
    title: str
    description: str
    tier_index: int
    status: Literal["locked", "active", "completed"] = "locked"
    completion: ObjectiveCompletion
    advances_clock_slug: str | None = None
    reveals_knowledge: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)

    @field_validator("tier_index")
    @classmethod
    def tier_index_not_negative(cls, v: int) -> int:
        if v < 0:
            raise ValueError("tier_index cannot be negative")
        return v


class ActorAbility(BaseModel):
    actor_id: str
    ability_slug: str
    display_name: str
    description: str
    source: str  # 'playbook_start' | 'kit' | 'advancement'
    surfaces_as_verb: bool = False
    target_types: list[str] = []
    cost_type: str = "none"
    cost_amount: int = 0


class RoomExit(BaseModel):
    exit_id: str
    campaign_id: str
    from_room_id: str
    to_room_id: str
    level_id: str
    label: str
    exit_type: str = "door"
    connector_type: str | None = None
    to_level_id: str | None = None
    status: str = "open"
    requires_item_slug: str | None = None
    requires_object_id: str | None = None
    requires_object_state: str | None = None
    requires_clock_slug: str | None = None
    requires_clock_min_filled: int | None = None
    requires_memory_slug: str | None = None
