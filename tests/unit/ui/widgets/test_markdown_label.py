from unittest.mock import MagicMock, patch

from dungeon_daddy.ui.widgets.markdown_label import md_to_html

_BODY = "#ffffff"
_MONO = "JetBrains Mono"
_HEAD = "#3cd2c3"


def _html(text: str) -> str:
    return md_to_html(text, _BODY, _MONO, _HEAD)


def test_bold_inline() -> None:
    assert "<b>word</b>" in _html("**word**")


def test_italic_inline() -> None:
    assert "<i>word</i>" in _html("*word*")


def test_inline_code() -> None:
    result = _html("`fn()`")
    assert "JetBrains Mono" in result
    assert "fn()" in result


def test_h1() -> None:
    result = _html("# Title")
    assert 'size="5"' in result
    assert "<b>Title</b>" in result


def test_h2() -> None:
    result = _html("## Title")
    assert 'size="4"' in result
    assert "<b>Title</b>" in result


def test_h3() -> None:
    result = _html("### Title")
    assert 'size="3"' in result
    assert "<b>Title</b>" in result


def test_bullet_dash() -> None:
    assert "• item" in _html("- item")


def test_bullet_star() -> None:
    assert "• item" in _html("* item")


def test_plain_passthrough() -> None:
    result = _html("hello world")
    assert "hello world" in result


def test_newline_becomes_br() -> None:
    assert "<br>" in _html("line1\nline2")


def test_no_raw_asterisks() -> None:
    assert "**" not in _html("**bold**")


# --- MarkdownLabel ---


def _build_label(markdown: str = "**hello**") -> object:
    from dungeon_daddy.ui.widgets.markdown_label import MarkdownLabel

    return MarkdownLabel(
        markdown,
        x=0.0,
        y=0.0,
        width=200,
        color=(255, 255, 255),
        font_name="Inter",
        font_size=12,
    )


def test_markdown_label_html_forwarded_to_pyglet() -> None:
    with patch("pyglet.text.HTMLLabel") as mock_cls:
        mock_cls.return_value = MagicMock()
        _build_label("**bold**")
        html_arg = mock_cls.call_args[0][0]
        assert "<b>bold</b>" in html_arg


def test_markdown_label_content_height() -> None:
    mock_inner = MagicMock()
    mock_inner.content_height = 42
    with patch("pyglet.text.HTMLLabel", return_value=mock_inner):
        label = _build_label()
        assert label.content_height == 42  # type: ignore[union-attr]


def test_markdown_label_draw_delegates() -> None:
    mock_inner = MagicMock()
    with patch("pyglet.text.HTMLLabel", return_value=mock_inner):
        label = _build_label()
        label.draw()  # type: ignore[union-attr]
        mock_inner.draw.assert_called_once()


def test_markdown_label_update_position() -> None:
    mock_inner = MagicMock()
    with patch("pyglet.text.HTMLLabel", return_value=mock_inner):
        label = _build_label()
        label.update_position(10.0, 20.0)  # type: ignore[union-attr]
        assert mock_inner.x == 10
        assert mock_inner.y == 20
