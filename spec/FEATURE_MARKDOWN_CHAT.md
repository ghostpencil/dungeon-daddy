# Feature: Markdown Rendering in Chat Panels

**Status: DONE**

## Goal

Replace plain-text message rendering in `ChatPanel` with formatted markdown display
so LLM responses with `**bold**`, `*italic*`, `` `code` ``, headings, and bullet lists
are shown with visual treatment instead of raw syntax characters.

---

## Problem

### Current Behavior

LLM responses are displayed verbatim via `arcade.draw_text()`. Markdown syntax
appears as literal characters (`**`, `*`, `#`, `` ` ``) in every GM and Dungeon
bubble.

### Desired Behavior

Common markdown constructs are visually rendered:

| Markdown | Display |
|---|---|
| `**text**` | **bold** (pyglet `<b>`) |
| `*text*` | *italic* (pyglet `<i>`) |
| `` `code` `` | monospace (JetBrains Mono face) |
| `# Heading` | 18 pt, teal, bold |
| `## Heading` | 14 pt, teal, bold |
| `### Heading` | 12 pt, teal, bold |
| `- item` / `* item` | `• item` (bullet prefix substitution) |
| plain text | unchanged |

Syntax characters not listed above pass through untouched.

Bubble height estimation uses the rendered label's `content_height` instead of the
current character-count heuristic, so bubbles never clip long formatted responses.

---

## Scope and Constraints

- **In scope:** `ChatPanel` message bubbles in **both** Design Mode and Play Mode.
  Both views use the same `ChatPanel` class (`design_view.py` passes the default
  `mode="design"`; `play_view.py` passes `mode="play"`), so a single implementation
  covers both.
- **Message roles covered:** all three roles used by both views — `"gm"` (player
  input, color `INK_2`), `"dm"` (AI response, color `INK_1`), and `"system"`
  (status/warning lines, color `INK_1`). System messages are typically plain text
  (`⚠`, emoji prefixes) and pass through `md_to_html` unchanged.
- **Out of scope (this feature):** `ChatBubble` (the in-map DM overlay widget) — it
  may be updated in a follow-on pass.
- **No new libraries.** Uses `pyglet.text.HTMLLabel` (already a transitive dependency
  via Arcade) and stdlib `re`.
- Rendering is via direct pyglet label calls (`label.draw()`), bypassing
  `arcade.draw_text` only for message body text. Labels, header kickers, role chips,
  and typing indicators continue to use `arcade.draw_text`.

---

## Technical Approach

### `md_to_html(text, body_color_hex, mono_font, heading_color_hex) → str`

Pure function in `dungeon_daddy/ui/widgets/markdown_label.py`.
Applies regex substitutions in order:

1. Headings — full-line `^#{1,3} ` patterns (processed before inline rules).
2. Bold — `\*\*(.+?)\*\*` → `<b>\1</b>`.
3. Italic — `\*(.+?)\*` → `<i>\1</i>`.
4. Inline code — `` `(.+?)` `` → `<font face="{mono_font}">\1</font>`.
5. Bullets — `^[-*] (.+)` (after stripping any leading spaces) → `• \1`.
6. Line breaks — `\n` → `<br>`.

Output is wrapped in a root `<font>` tag that sets the default face, size, and color
so every bubble inherits the correct theme values.

### `MarkdownLabel`

Class in the same file. Wraps one `pyglet.text.HTMLLabel`.

```python
class MarkdownLabel:
    def __init__(
        self,
        markdown: str,
        x: float, y: float,
        width: int,
        color: tuple[int, int, int],
        font_name: str,
        font_size: int,
    ) -> None: ...

    @property
    def content_height(self) -> int: ...

    def draw(self) -> None: ...

    def update_position(self, x: float, y: float) -> None: ...
```

- `anchor_y="top"` matches the existing `arcade.draw_text(..., anchor_y="top")` call site.
- `multiline=True`, `width=width` for wrapping.
- `content_height` reads `self._label.content_height`.

### Label Cache in `ChatPanel`

```python
_label_cache: dict[int, MarkdownLabel]  # keyed by message index
```

- `add_message()` does **not** pre-build; cache entries are created lazily in
  `_get_or_build_label(index, bubble_w)`.
- `resize()` calls `_label_cache.clear()` so labels are rebuilt at the new width.
- `teardown()` also clears the cache.

`_compute_heights` calls `_get_or_build_label` for each message; returns
`label.content_height + PAD_SM * 2 + _LABEL_H` (replacing the character-count
formula).

`_draw_messages_inner` calls `_get_or_build_label` (cache hit on every frame after
the first) and calls `label.update_position(bx + PAD_SM, draw_y + b_h - _LABEL_H)`
then `label.draw()`.

---

## Execution Plan

### Status: DONE

Build order — tests written before each implementation step.

---

### Step 1 — Unit tests for `md_to_html()` ← TODO

File: `tests/unit/ui/test_markdown_label.py`

No arcade display needed — pure string-in, string-out.

Tests:
- `test_bold_inline` — `**word**` → output contains `<b>word</b>`
- `test_italic_inline` — `*word*` → output contains `<i>word</i>`
- `test_inline_code` — `` `fn()` `` → output contains `JetBrains Mono`
- `test_h1` — `# Title` → output contains `size="5"` and `<b>Title</b>`
- `test_h2` — `## Title` → output contains `size="4"` and `<b>Title</b>`
- `test_h3` — `### Title` → output contains `size="3"` and `<b>Title</b>`
- `test_bullet_dash` — `- item` → output contains `• item`
- `test_bullet_star` — `* item` → output contains `• item`
- `test_plain_passthrough` — `hello world` → text is preserved, no extra tags
- `test_newline_becomes_br` — `"line1\nline2"` → output contains `<br>`
- `test_no_raw_asterisks` — `**bold**` → output does **not** contain `**`

---

### Step 2 — Implement `md_to_html()` ← TODO

File: `dungeon_daddy/ui/widgets/markdown_label.py`

```python
import re

def md_to_html(
    text: str,
    body_color_hex: str,
    mono_font: str,
    heading_color_hex: str,
) -> str:
    """Convert a small subset of Markdown to pyglet HTML."""
    ...
```

Color helpers needed:

```python
def _rgb_to_hex(color: tuple[int, int, int]) -> str:
    return "#{:02x}{:02x}{:02x}".format(*color)
```

Call site will pass:
- `body_color_hex` from `INK_1` or `INK_2` depending on role
- `heading_color_hex` from `TEAL` = `"#3cd2c3"`
- `mono_font` = `FONT_MONO` = `"JetBrains Mono"`

---

### Step 3 — Implement `MarkdownLabel` class ← TODO

File: `dungeon_daddy/ui/widgets/markdown_label.py` (same file)

```python
import pyglet.text

class MarkdownLabel:
    def __init__(
        self,
        markdown: str,
        x: float, y: float,
        width: int,
        color: tuple[int, int, int],
        font_name: str,
        font_size: int,
    ) -> None:
        html = md_to_html(
            markdown,
            _rgb_to_hex(color),
            FONT_MONO,
            _rgb_to_hex(TEAL),
        )
        self._label = pyglet.text.HTMLLabel(
            html,
            x=int(x), y=int(y),
            width=width,
            multiline=True,
            anchor_x="left",
            anchor_y="top",
        )
```

Note: `pyglet.text.HTMLLabel` requires an active OpenGL context at construction
time. `MarkdownLabel` must only be instantiated inside `draw()` or equivalent
(never at module load or `__init__` of `ChatPanel`).

---

### Step 4 — Add label cache to `ChatPanel` ← TODO

File: `dungeon_daddy/ui/panels/chat_panel.py`

In `__init__` add:

```python
self._label_cache: dict[int, MarkdownLabel] = {}
```

Add helper:

```python
def _get_or_build_label(self, index: int, msg: ChatMessage, bubble_w: float) -> MarkdownLabel:
    if index not in self._label_cache:
        text_w = int(bubble_w - PAD_SM * 2)
        color = INK_2 if msg.role == "gm" else INK_1   # "dm" and "system" both use INK_1
        self._label_cache[index] = MarkdownLabel(
            msg.content,
            x=0, y=0,
            width=text_w,
            color=color,
            font_name=FONT_UI,
            font_size=TEXT_BASE,
        )
    return self._label_cache[index]
```

Update `resize()` and `teardown()` to call `self._label_cache.clear()`.

---

### Step 5 — Update `_compute_heights` to use `content_height` ← TODO

File: `dungeon_daddy/ui/panels/chat_panel.py`

Replace `_bubble_height` character-count formula:

```python
def _bubble_height(self, index: int, msg: ChatMessage, bubble_w: float) -> int:
    label = self._get_or_build_label(index, msg, bubble_w)
    return max(40, label.content_height + int(PAD_SM) * 2 + _LABEL_H)
```

Update `_compute_heights` signature to pass the index:

```python
def _compute_heights(self, bubble_w: float) -> list[int]:
    return [
        self._bubble_height(i, msg, bubble_w)
        for i, msg in enumerate(self._messages)
    ]
```

---

### Step 6 — Update `_draw_messages_inner` to call `label.draw()` ← TODO

File: `dungeon_daddy/ui/panels/chat_panel.py`

Replace the `arcade.draw_text(msg.content, ...)` call with:

```python
label = self._get_or_build_label(n - 1 - i, msg, bubble_w)
label.update_position(bx + PAD_SM, draw_y + b_h - _LABEL_H)
label.draw()
```

The role label (`"GM"` / `"◆ Dungeon"`) continues to use `arcade.draw_text`.

---

## Manual UI Tests

Run the app: `python -m dungeon_daddy`
Load the sample dungeon and open the Design chat or Play chat.

---

**MUC-1 — Bold text renders without asterisks**
Send a message that triggers a response containing `**bold**`.
Expected: word appears bold; no `*` characters visible.
Status: TODO

---

**MUC-2 — Italic text renders without asterisks**
Trigger a response containing `*italic*`.
Expected: word appears italic; no `*` visible.
Status: TODO

---

**MUC-3 — Inline code renders in monospace**
Trigger a response containing a backtick-quoted term.
Expected: term renders in JetBrains Mono; no backtick characters visible.
Status: TODO

---

**MUC-4 — Headings render larger and teal**
Trigger a response with `## Section`.
Expected: heading text is teal, visually larger than body text, no `#` visible.
Status: TODO

---

**MUC-5 — Bullet lists render with bullet character**
Trigger a response with a `- item` list.
Expected: each item prefixed with `•`; no `-` dash visible.
Status: TODO

---

**MUC-6 — Plain text unchanged**
Trigger a short plain-text response (no markdown).
Expected: text displays normally; no regressions.
Status: TODO

---

**MUC-7 — Bubble height fits content**
Trigger a long multi-paragraph response.
Expected: bubble height grows to contain all text without clipping.
Status: TODO

---

**MUC-8 — Resize clears cache and reflows**
Resize the window horizontally.
Expected: chat text reflows to the new panel width with no artifacts.
Status: TODO

---

**MUC-9 — Scroll still works after markdown rendering**
Accumulate enough messages to require scrolling.
Expected: scroll wheel moves the message stack as before.
Status: TODO
