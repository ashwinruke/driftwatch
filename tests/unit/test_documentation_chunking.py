from driftwatch.analyzers.documentation.indexer import (
    _split_into_paragraphs,
    split_markdown_into_sections,
)


def test_splits_on_headings():
    content = (
        "# Heading One\n\n"
        "Some paragraph text that is definitely longer than fifty characters.\n\n"
        "# Heading Two\n\n"
        "Another paragraph that is also long enough to pass the fifty character filter.\n"
    )
    sections = split_markdown_into_sections(content)
    headings = {s["heading"] for s in sections}
    assert headings == {"Heading One", "Heading Two"}


def test_splits_multiple_paragraphs_under_one_heading():
    content = (
        "# Heading\n\n"
        "First paragraph that is long enough to survive the fifty character minimum length filter here.\n\n"
        "Second, unrelated paragraph that is also long enough to survive the same fifty character filter.\n"
    )
    sections = split_markdown_into_sections(content)
    assert len(sections) == 2
    assert all(s["heading"] == "Heading" for s in sections)


def test_short_paragraphs_are_dropped():
    content = "# Heading\n\ntoo short\n"
    assert split_markdown_into_sections(content) == []


def test_fenced_code_block_kept_as_one_paragraph():
    content = (
        "line before that is long enough to survive the fifty character minimum length filter\n"
        "```\n"
        "code line one\n"
        "code line two\n"
        "```\n"
    )
    paragraphs = _split_into_paragraphs(content)
    code_paragraphs = [p for p in paragraphs if p.startswith("```")]
    assert len(code_paragraphs) == 1
    assert "code line one" in code_paragraphs[0]
    assert "code line two" in code_paragraphs[0]
