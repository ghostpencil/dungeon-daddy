# Dungeon Daddy — Project Index

## Phase

Phase: 23 — Graph Mode Phase 4: Presentation, Detail Panel, and Dungeon Personality
Status: **Complete** (2026-06-01) — Spec: `spec/MAP_LAYOUT_PHASE_4.md`

---

## Next Steps

_No active phase. Phase 24 not yet defined._

### Phase 23 Completed Steps (archived)

| Step | Task |
|---|---|
| ~~1~~ | ~~`GraphPresentationConfig` dataclass — all toggles, defaults enabled~~ — **Done** |
| ~~2~~ | ~~Visible detail panel in Graph Mode (right-side/bottom-right card)~~ — **Done** |
| ~~3~~ | ~~Strengthen hover and selected-room styling; improve style resolver~~ — **Done** |
| ~~4~~ | ~~Role markers: `IN`, `OBJ`, `BOSS`, `!`, `KEY`, `↓`, `HUB` drawn in room boxes~~ — **Done** |
| ~~5~~ | ~~Connection markers: `critical_path`, `locked`, `secret`/`shortcut` (dashed), `vertical`~~ — **Done** |
| ~~6~~ | ~~Restrained atmosphere layer: vignette, subtle background, thin frame~~ — **Done** |
| ~~7~~ | ~~Artifact generation script + screenshots and JSON reports under `artifacts/layout/phase4/`~~ — **Done** |
| ~~8~~ | ~~Integration tests: geometry, semantic, metadata, interaction score regressions; Grid Mode untouched~~ — **Done** |

### Phase 22 Completed Steps (archived)

| Step | Task |
|---|---|
| ~~1~~ | ~~Phase 2.5 cleanup: refine objective warning naming in `validation.py`~~ — **Done** (1188 passing) |
| ~~2~~ | ~~Connection metadata backfill for `crucible.json`, `tomb.json`, and local dungeon files~~ — **Done** (1199 passing) |
| ~~2a~~ | ~~Renderer visual parity: role-based border color, fill color, marker position~~ — **Done** (1194 passing) |
| ~~3~~ | ~~`GraphViewState` model~~ — **Done** (1211 passing) |
| ~~4~~ | ~~Room + connection hit testing~~ — **Done** (1220 passing) |
| ~~5~~ | ~~Style resolution pipeline~~ — **Done** (1228 passing) |
| ~~6~~ | ~~Room hover visual state~~ — **Done** (1232 passing) |
| ~~7~~ | ~~Room selection + focus mode~~ — **Done** (1235 passing) |
| ~~8~~ | ~~Connection hover~~ — **Done** (1238 passing) |
| ~~9~~ | ~~Room detail panel (`room_detail_panel.py`)~~ — **Done** (1262 passing) |
| ~~10~~ | ~~Critical path emphasis when selected room is on path~~ — **Done** (1265 passing) |
| ~~11~~ | ~~Keyboard controls: R = recenter, Escape = clear selection~~ — **Done** (1271 passing) |
| ~~12~~ | ~~Artifact generation script + screenshots under `artifacts/layout/phase3/`~~ — **Done** (1276 passing) |
| ~~13~~ | ~~Integration tests: geometry/semantic/metadata scores do not regress~~ — **Done** (1279 passing) |
| ~~14~~ | ~~Output artifacts: feedback JSON, summary MDs, migration report~~ — **Done** (1280 passing) |

---

## Known Failures

_None._

---

## Previous Phases

| Phase | Status | Tests |
|---|---|---|
| Phase 23 — Graph Mode Phase 4: Presentation, Detail Panel, Dungeon Personality | **Complete** (2026-06-01) | 1368 passing |
| Phase 22 — Graph Mode Phase 3: Interaction Polish | **Complete** (2026-05-31) | 1280 passing |
| Phase 21 — Graph Mode Phase 2.5: Semantic Metadata Backfill | **Complete** (2026-05-30) | 1184 passing |
| Phase 20 — Map Layout Visual Hierarchy (Phase 2) | **Complete** (2026-05-30) | 1097 passing |
| Phase 19 — Map Layout Phase 1 | **Complete** (2026-05-30) | 337 map tests |
| Post-Phase 18 — IP-1 through IP-9, MC-1 | **Complete** (2026-05-27) | 849 passing |
| Phase 18 — Python Code Quality Stabilisation | **Complete** | 664 passing |
| Phases 1–17 | **Complete** | — |

_Full session history in `spec/HISTORY.md`._

---

## Notes

- Provider is OpenAI (`gpt-4o`); `OPENAI_API_KEY` must be set in environment.
- `AnthropicProvider` still exists and is tested — not removed, just not the active provider.
- Spec loading rules and skills are in `CLAUDE.md` (canonical source).
- Published: https://github.com/ghostpencil/dungeon-daddy (2026-05-24).
