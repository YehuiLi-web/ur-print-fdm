from __future__ import annotations

import html
import re
from dataclasses import dataclass


@dataclass(frozen=True)
class Heading:
    level: int
    text: str
    anchor: str


@dataclass(frozen=True)
class RenderedMarkdown:
    html: str
    headings: list[Heading]
    title: str


def _rewrite_link(url: str) -> str:
    target = (url or "").strip()
    if not target:
        return "#"
    if ".md#" in target:
        return target.replace(".md#", ".html#")
    if target.endswith(".md"):
        return target[:-3] + ".html"
    return target


def _render_inline(text: str) -> str:
    code_tokens: list[str] = []

    def _code_repl(match: re.Match[str]) -> str:
        code_tokens.append(f"<code>{html.escape(match.group(1))}</code>")
        return f"@@CODE{len(code_tokens) - 1}@@"

    escaped = re.sub(r"`([^`]+)`", _code_repl, text)
    escaped = html.escape(escaped)
    escaped = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", escaped)
    escaped = re.sub(
        r"\[([^\]]+)\]\(([^)]+)\)",
        lambda match: (
            f'<a href="{html.escape(_rewrite_link(match.group(2)))}">'
            f"{match.group(1)}</a>"
        ),
        escaped,
    )

    for idx, token in enumerate(code_tokens):
        escaped = escaped.replace(f"@@CODE{idx}@@", token)
    return escaped


def _split_table_row(line: str) -> list[str]:
    return [cell.strip() for cell in line.strip().strip("|").split("|")]


def _is_table_separator(line: str) -> bool:
    stripped = line.strip()
    if not stripped.startswith("|"):
        return False
    return all(set(part.strip()) <= {"-", ":"} for part in stripped.strip("|").split("|"))


def render_markdown_document(markdown_text: str) -> RenderedMarkdown:
    lines = markdown_text.splitlines()
    blocks: list[str] = []
    headings: list[Heading] = []
    heading_counter = 0
    title = "文档"
    index = 0

    while index < len(lines):
        line = lines[index].rstrip()
        stripped = line.strip()

        if not stripped:
            index += 1
            continue

        if stripped.startswith("<div") or stripped == "</div>":
            index += 1
            continue

        if stripped.startswith("```"):
            language = stripped[3:].strip()
            code_lines: list[str] = []
            index += 1
            while index < len(lines) and not lines[index].strip().startswith("```"):
                code_lines.append(lines[index])
                index += 1
            if index < len(lines):
                index += 1
            lang_attr = f' class="language-{html.escape(language)}"' if language else ""
            code_html = html.escape("\n".join(code_lines))
            label = html.escape(language or "code")
            blocks.append(
                '<div class="code-block">'
                f'<div class="code-block__header"><span>{label}</span></div>'
                f"<pre><code{lang_attr}>{code_html}</code></pre>"
                "</div>"
            )
            continue

        heading_match = re.match(r"^(#{1,6})\s+(.*)$", stripped)
        if heading_match:
            level = len(heading_match.group(1))
            text = heading_match.group(2).strip()
            heading_counter += 1
            anchor = f"section-{heading_counter}"
            headings.append(Heading(level=level, text=text, anchor=anchor))
            if level == 1:
                title = text
            blocks.append(f'<h{level} id="{anchor}">{_render_inline(text)}</h{level}>')
            index += 1
            continue

        if stripped.startswith("|") and index + 1 < len(lines) and _is_table_separator(lines[index + 1]):
            header = _split_table_row(stripped)
            rows: list[list[str]] = []
            index += 2
            while index < len(lines) and lines[index].strip().startswith("|"):
                rows.append(_split_table_row(lines[index]))
                index += 1
            head_html = "".join(f"<th>{_render_inline(cell)}</th>" for cell in header)
            body_html = "".join(
                "<tr>" + "".join(f"<td>{_render_inline(cell)}</td>" for cell in row) + "</tr>"
                for row in rows
            )
            blocks.append(
                "<div class=\"table-wrap\"><table><thead><tr>"
                + head_html
                + "</tr></thead><tbody>"
                + body_html
                + "</tbody></table></div>"
            )
            continue

        if re.match(r"^\d+\.\s+", stripped):
            items: list[str] = []
            while index < len(lines) and re.match(r"^\d+\.\s+", lines[index].strip()):
                items.append(re.sub(r"^\d+\.\s+", "", lines[index].strip(), count=1))
                index += 1
            blocks.append(
                "<ol>" + "".join(f"<li>{_render_inline(item)}</li>" for item in items) + "</ol>"
            )
            continue

        if stripped.startswith("- "):
            items = []
            while index < len(lines) and lines[index].strip().startswith("- "):
                items.append(lines[index].strip()[2:].strip())
                index += 1
            blocks.append(
                "<ul>" + "".join(f"<li>{_render_inline(item)}</li>" for item in items) + "</ul>"
            )
            continue

        paragraph_lines = [stripped]
        index += 1
        while index < len(lines):
            candidate = lines[index].strip()
            if not candidate:
                break
            if (
                candidate.startswith("```")
                or candidate.startswith("|")
                or candidate.startswith("- ")
                or re.match(r"^\d+\.\s+", candidate)
                or re.match(r"^(#{1,6})\s+", candidate)
                or candidate.startswith("<div")
                or candidate == "</div>"
            ):
                break
            paragraph_lines.append(candidate)
            index += 1
        blocks.append(f"<p>{_render_inline(' '.join(paragraph_lines))}</p>")

    return RenderedMarkdown(html="\n".join(blocks), headings=headings, title=title)
