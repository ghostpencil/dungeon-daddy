"""Play-session coordinators (Phase 51.7 — PlayView decomposition).

Modules in this package own the play-session's domain coordination — action
orchestration, navigation, dialogue, narration, memory — extracted incrementally
out of ``views/play_view.py``. Coordinators do not import ``arcade``; the
dependency direction is ``views → play → (rpg | memory | llm | data)``.
"""
