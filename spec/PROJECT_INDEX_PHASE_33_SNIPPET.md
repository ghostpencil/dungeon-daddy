# PROJECT_INDEX.md Update Snippet

Replace the current Phase 33 placeholder with:

```md
## Phase

Phase: 33 — Player-Controlled Action Loop
Status: **Ready to implement** — Phase 32 closed out 2026-06-03. See `docs/PHASE_32_CLOSEOUT.md`.

---

## Next Steps

Phase 33 establishes the first playable RPG loop in Play Mode.

| Priority | Item | Notes |
|---|---|---|
| 1 | Seed both existing campaigns with RPG-ready player-controlled actors | Must support one or more player-controlled actors; do not hardcode party-only assumptions |
| 2 | Add Player Action UI | Select actor, enter intent, choose action, resolve through `RpgService` |
| 3 | Wire `ContextBundleBuilder` into `PlayView._spawn_dm_thread` | Build/snapshot bundle before thread; pass to `DungeonMasterAgent.respond(context_bundle=...)` |
| 4 | Add Debug provenance display | Show bundle id, memory counts, focus actors, clocks/fallout counts, and whether bundle was passed to DM |
| 5 | Smoke test both existing campaigns | Screenshots after each visible UI action |

## Known Failures

_None._
```

Add/update Notes:

```md
- Player controls the player side: one or more player-controlled actors.
- Dungeon Daddy controls the dungeon, monsters, NPCs, factions, clocks, secrets, and consequences.
- The LLM is advisory. It may narrate or propose, but deterministic services apply authoritative state.
- World reactions are deferred to Phase 35 via `WorldReactionService`.
```
