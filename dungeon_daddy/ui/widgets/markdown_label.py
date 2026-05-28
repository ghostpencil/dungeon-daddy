import re

import pyglet.text

from dungeon_daddy.ui.theme import FONT_MONO, TEAL


def _rgb_to_hex(color: tuple[int, int, int]) -> str:
    return "#{:02x}{:02x}{:02x}".format(*color)


def md_to_html(
    text: str,
    body_color_hex: str,
    mono_font: str,
    heading_color_hex: str,
) -> str:
    """Convert a small subset of Markdown to pyglet HTML."""
    out = text
    # Headings — processed before inline rules
    _h = heading_color_hex
    out = re.sub(r"^### (.+)", lambda m: f'<font color="{_h}" size="3"><b>{m.group(1)}</b></font>', out, flags=re.MULTILINE)
    out = re.sub(r"^## (.+)", lambda m: f'<font color="{_h}" size="4"><b>{m.group(1)}</b></font>', out, flags=re.MULTILINE)
    out = re.sub(r"^# (.+)", lambda m: f'<font color="{_h}" size="5"><b>{m.group(1)}</b></font>', out, flags=re.MULTILINE)
    out = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", out)
    out = re.sub(r"\*(.+?)\*", r"<i>\1</i>", out)
    out = re.sub(r"`(.+?)`", lambda m: f'<font face="{mono_font}">{m.group(1)}</font>', out)
    out = re.sub(r"^[ \t]*[-*] (.+)", r"• \1", out, flags=re.MULTILINE)
    out = out.replace("\n", "<br>")
    return f'<font color="{body_color_hex}">{out}</font>'


class MarkdownLabel:
    def __init__(
        self,
        markdown: str,
        x: float,
        y: float,
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
            x=int(x),
            y=int(y),
            width=width,
            multiline=True,
            anchor_x="left",
            anchor_y="top",
        )

    @property
    def content_height(self) -> int:
        return self._label.content_height

    def draw(self) -> None:
        self._label.draw()

    def update_position(self, x: float, y: float) -> None:
        self._label.x = int(x)
        self._label.y = int(y)
