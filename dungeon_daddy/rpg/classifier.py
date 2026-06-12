from __future__ import annotations

import re

_KEYWORD_MAP: dict[str, list[str]] = {
    "fight": ["attack", "strike", "block", "duel", "kill", "smash"],
    "move": ["sneak", "run", "climb", "dodge", "leap", "escape"],
    "tinker": ["open", "repair", "disable", "mechanism", "lock", "device"],
    "study": ["study", "studies", "examine", "read", "inspect", "analyze",
              "research", "mural", "book", "symbol", "rune", "runes", "inscription"],
    "focus": ["resist", "concentrate", "calm"],
    "sway": ["persuade", "lie", "comfort", "command", "bargain"],
    "sense": ["listen", "notice", "feel", "search", "detect"],
    "channel": ["ritual", "magic", "ghost", "spirit", "voice", "dream"],
    "endure": ["withstand", "survive", "hold", "bear"],
}

_COMPILED: dict[str, list[re.Pattern[str]]] = {
    action: [re.compile(r"\b" + re.escape(kw) + r"\b") for kw in keywords]
    for action, keywords in _KEYWORD_MAP.items()
}


def classify_intent(text: str) -> list[str]:
    lowered = text.lower()
    scores: dict[str, int] = {}
    for action, patterns in _COMPILED.items():
        count = sum(1 for p in patterns if p.search(lowered))
        if count:
            scores[action] = count
    return sorted(scores, key=lambda a: scores[a], reverse=True)
