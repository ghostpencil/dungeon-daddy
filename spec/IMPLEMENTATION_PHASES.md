# Implementation Phases — Index

This file was split into smaller documents to keep context load manageable.
Load only the file that covers the phase you are working on.

| File | Phases | Status |
|---|---|---|
| [IMPLEMENTATION_PHASES_1_10.md](IMPLEMENTATION_PHASES_1_10.md) | 1–10 | Complete |
| [IMPLEMENTATION_PHASES_11_18.md](IMPLEMENTATION_PHASES_11_18.md) | 11–18 + Post-18 | Complete |
| [IMPLEMENTATION_PHASES_19_25.md](IMPLEMENTATION_PHASES_19_25.md) | 19–25 (Map Layout) | Complete |
| [IMPLEMENTATION_PHASES_26_32.md](IMPLEMENTATION_PHASES_26_32.md) | 26–32 (RPG + Memory Foundation) | Complete |
| [IMPLEMENTATION_PHASES_33_ONWARDS.md](IMPLEMENTATION_PHASES_33_ONWARDS.md) | 33–53 (Active Play Loop + Future Roadmap) | 33–51.8 Complete; 52–53 planned |

## Current phase

**STABILIZATION / cleanup.** All feature phases through **51.8** are complete and **merged to `main`**:
Phase 51 + 51.5 (PR #83, 2026-07-04), 51.6 World Reaction Policy (PR #88), 51.7 PlayView Decomposition
(PR #89), 51.8 A Tag Hygiene (PR #90) + B Narrator Lookup Tool (PR #92, 2026-07-17). The off-roadmap
add-ons **50.5 / 50.6** are also merged. Details + PRs in `spec/PROJECT_INDEX.md` → Phase History.

**Next up (OWNER-DECIDED 2026-07-17): a cleanup slice** for the Phase A + B deferred pile — scope in
`spec/PROJECT_INDEX.md` → START HERE. **Phases 52–53** (Milestone Advancement, Threat Behavior) are
defined on the GitHub roadmap (planned) and deferred behind the cleanup slice — see the "Planned Roadmap"
section in `IMPLEMENTATION_PHASES_33_ONWARDS.md`. The World Reaction Policy is no longer pending — it
shipped as Phase 51.6.

See `IMPLEMENTATION_PHASES_33_ONWARDS.md` for the full spec.
