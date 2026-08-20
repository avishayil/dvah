import pytest

from dvah.artifacts.frontmatter import split_frontmatter


@pytest.mark.unit
def test_no_frontmatter_returns_empty_meta_and_full_body():
    meta, body = split_frontmatter("just a plain body\nwith lines")
    assert meta == {}
    assert body == "just a plain body\nwith lines"


@pytest.mark.unit
def test_parses_meta_and_strips_body():
    meta, body = split_frontmatter("---\nname: x\nversion: 1.0\n---\n\nhello body\n")
    assert meta == {"name": "x", "version": 1.0}
    assert body == "hello body"


@pytest.mark.unit
def test_empty_body_after_frontmatter():
    meta, body = split_frontmatter("---\nname: x\n---\n")
    assert meta == {"name": "x"}
    assert body == ""


@pytest.mark.unit
def test_crlf_line_endings_are_normalized():
    meta, body = split_frontmatter("---\r\nname: x\r\n---\r\nbody\r\n")
    assert meta == {"name": "x"}
    assert body == "body"


@pytest.mark.unit
def test_missing_closing_fence_raises():
    with pytest.raises(ValueError, match="unterminated frontmatter"):
        split_frontmatter("---\nname: x\nno closing fence\n")


@pytest.mark.unit
def test_non_mapping_frontmatter_raises():
    with pytest.raises(ValueError, match="must be a YAML mapping"):
        split_frontmatter("---\n- just\n- a\n- list\n---\nbody")
