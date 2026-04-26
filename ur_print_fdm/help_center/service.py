from __future__ import annotations

import html
import json
import re
import shutil
from pathlib import Path
from typing import Any

from PyQt6.QtGui import QDesktopServices

from ur_print_fdm.config import config_manager
from ur_print_fdm.help_center.markdown import Heading, render_markdown_document
from ur_print_fdm.help_center.note_data import default_printing_notes
from ur_print_fdm.help_center.urscript_catalog import (
    URSCRIPT_DOCS,
    URSCRIPT_FOUNDATION_TRACK,
    URSCRIPT_MOTION_TRACK,
    URSCRIPT_RUNTIME_TRACK,
)
from ur_print_fdm.paths import ensure_app_data_dir


HOME_SEARCH_ENTRIES: list[dict[str, str]] = [
    {
        "title": "总览",
        "href": "#overview",
        "kind": "帮助中心",
        "excerpt": "包含快速开始、打印前检查、工艺与轨迹、故障排查、硬件维护、开发接口和 URScript 语法参考。",
        "keywords": "总览 帮助中心 软件说明 打印前检查 URScript 语法",
    },
    {
        "title": "常用入口",
        "href": "#common-entry",
        "kind": "帮助中心",
        "excerpt": "按任务进入最常用的内容。",
        "keywords": "常用入口 打印前检查 故障排查 URScript 经验记录",
    },
    {
        "title": "快速开始",
        "href": "#quick-start",
        "kind": "帮助中心",
        "excerpt": "第一次连机或现场换设备时，先按这个顺序过一遍。",
        "keywords": "快速开始 环境搭建 连接 IP 上电顺序 G-code URScript",
    },
    {
        "title": "打印前检查清单",
        "href": "#print-checklist",
        "kind": "帮助中心",
        "excerpt": "开始打印前请逐项确认网络、遥控模式、TCP、首层和急停方案。",
        "keywords": "打印前 检查清单 首层 TCP feature 遥控模式 转盘 电源 喷嘴",
    },
    {
        "title": "URScript 语法参考",
        "href": "#urscript",
        "kind": "帮助中心",
        "excerpt": "查阅语法结构、运动指令、位姿、线程、系统接口、示例和常见坑。",
        "keywords": "URScript 语法 运动 指令 线程 位姿 I/O RPC 常见坑",
    },
    {
        "title": "工艺与轨迹",
        "href": "#process",
        "kind": "帮助中心",
        "excerpt": "汇总影响打印质量和运动结果的关键说明。",
        "keywords": "工艺 轨迹 MoveJ MoveL MoveP pose_trans 首层 拖拽 角度",
    },
    {
        "title": "故障排查",
        "href": "#troubleshooting",
        "kind": "帮助中心",
        "excerpt": "按照表象快速缩小问题范围，优先检查最容易影响结果的项目。",
        "keywords": "故障 排查 堵头 出料困难 拖拽 地线 风扇 导管",
    },
    {
        "title": "硬件与维护",
        "href": "#hardware",
        "kind": "帮助中心",
        "excerpt": "常见机械端与外围设备检查项。",
        "keywords": "硬件 维护 Modbus 喷嘴 导管 挤出机 转盘",
    },
    {
        "title": "开发与接口",
        "href": "#development",
        "kind": "帮助中心",
        "excerpt": "项目结构、关键入口和相关文档索引。",
        "keywords": "开发 接口 main_window driver toolbox docs architecture URScript parser runtime",
    },
    {
        "title": "经验记录",
        "href": "#local-notes",
        "kind": "帮助中心",
        "excerpt": "收录本机保存的经验记录，便于检索和回看。",
        "keywords": "经验记录 维护笔记 现场经验",
    },
]


def help_center_source_dir() -> Path:
    return Path(__file__).resolve().parent / "site"


def help_center_content_dir() -> Path:
    return Path(__file__).resolve().parent / "content"


def urscript_content_dir() -> Path:
    return help_center_content_dir() / "urscript"


def help_center_runtime_dir() -> Path:
    path = ensure_app_data_dir() / "help_center"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _normalize_note(raw: Any) -> dict[str, str] | None:
    if not isinstance(raw, dict):
        return None
    title = str(raw.get("title", "") or "").strip()
    content = str(raw.get("content", "") or "").strip()
    if not title or not content:
        return None
    category = str(raw.get("category", "") or "未分类").strip() or "未分类"
    note_id = str(raw.get("id", "") or f"note-{abs(hash((title, category))) % 10_000_000}")
    created_at = str(raw.get("created_at", "") or "")
    updated_at = str(raw.get("updated_at", "") or "")
    return {
        "id": note_id,
        "category": category,
        "title": title,
        "content": content,
        "created_at": created_at,
        "updated_at": updated_at,
    }


def load_printing_notes() -> list[dict[str, str]]:
    raw_notes = config_manager.get("printing_notes.data")
    if isinstance(raw_notes, str) and raw_notes.strip():
        try:
            payload = json.loads(raw_notes)
        except json.JSONDecodeError:
            payload = None
        if isinstance(payload, list):
            normalized = [_normalize_note(item) for item in payload]
            notes = [item for item in normalized if item]
            if notes:
                return notes
    return default_printing_notes()


def _safe_fragment(value: str, *, prefix: str) -> str:
    slug = re.sub(r"[^0-9a-zA-Z_-]+", "-", value.strip()).strip("-").lower()
    return f"{prefix}-{slug or 'item'}"


def _note_anchor(note: dict[str, str]) -> str:
    return _safe_fragment(note.get("id", note.get("title", "note")), prefix="note")


def _render_note_filters(notes: list[dict[str, str]]) -> str:
    categories = sorted({note["category"] for note in notes})
    chips = [
        '<button class="filter-chip is-active" type="button" data-note-filter="all">全部</button>'
    ]
    for category in categories:
        escaped = html.escape(category)
        chips.append(
            f'<button class="filter-chip" type="button" data-note-filter="{escaped}">{escaped}</button>'
        )
    return "\n".join(chips)


def _render_note_cards(notes: list[dict[str, str]]) -> str:
    cards: list[str] = []
    for note in notes:
        anchor = html.escape(_note_anchor(note))
        category = html.escape(note["category"])
        title = html.escape(note["title"])
        content = html.escape(note["content"]).replace("\n", "<br>")
        updated_at = html.escape(note.get("updated_at") or note.get("created_at") or "未记录")
        search_index = html.escape(f"{note['category']} {note['title']} {note['content']}")
        cards.append(
            f"""
            <article id="{anchor}" class="note-card searchable" data-note-category="{category}" data-search="{search_index}">
              <div class="note-card__meta">
                <span class="badge">{category}</span>
                <span class="timestamp">更新于 {updated_at}</span>
              </div>
              <h3>{title}</h3>
              <p>{content}</p>
            </article>
            """.strip()
        )
    return "\n".join(cards)


def _render_urscript_doc_cards(slugs: list[str], *, href_prefix: str) -> str:
    doc_map = {doc["slug"]: doc for doc in URSCRIPT_DOCS}
    cards: list[str] = []
    for slug in slugs:
        doc = doc_map.get(slug)
        if doc is None:
            continue
        cards.append(
            f"""
            <a class="doc-link-card" href="{html.escape(href_prefix)}{html.escape(doc['slug'])}.html">
              <div class="doc-link-card__meta">
                <span class="badge">{html.escape(doc['audience'])}</span>
              </div>
              <h3>{html.escape(doc['title'])}</h3>
              <p>{html.escape(doc['summary'])}</p>
            </a>
            """.strip()
        )
    return "\n".join(cards)


def _urscript_track_label(slug: str) -> str:
    if slug in URSCRIPT_FOUNDATION_TRACK:
        return "语法与结构"
    if slug in URSCRIPT_MOTION_TRACK:
        return "运动与位姿"
    if slug in URSCRIPT_RUNTIME_TRACK:
        return "运行时与示例"
    return "URScript"


def _find_adjacent_urscript_docs(slug: str) -> tuple[dict[str, str] | None, dict[str, str] | None]:
    for index, doc in enumerate(URSCRIPT_DOCS):
        if doc["slug"] != slug:
            continue
        previous_doc = URSCRIPT_DOCS[index - 1] if index > 0 else None
        next_doc = URSCRIPT_DOCS[index + 1] if index + 1 < len(URSCRIPT_DOCS) else None
        return previous_doc, next_doc
    return None, None


def _render_urscript_nav(current_slug: str | None = None) -> str:
    doc_map = {doc["slug"]: doc for doc in URSCRIPT_DOCS}
    groups = [
        ("语法与结构", URSCRIPT_FOUNDATION_TRACK),
        ("运动与位姿", URSCRIPT_MOTION_TRACK),
        ("运行时与示例", URSCRIPT_RUNTIME_TRACK),
    ]
    sections: list[str] = []
    for title, slugs in groups:
        links: list[str] = []
        for slug in slugs:
            doc = doc_map.get(slug)
            if doc is None:
                continue
            active = ' class="is-active"' if doc["slug"] == current_slug else ""
            links.append(
                f'<a{active} href="{html.escape(doc["slug"])}.html">{html.escape(doc["title"])}</a>'
            )
        if not links:
            continue
        sections.append(
            """
            <section class="nav-group">
              <p class="nav-group__title">{title}</p>
              <div class="nav-group__links">
                {links}
              </div>
            </section>
            """.strip().format(title=html.escape(title), links="\n".join(links))
        )
    return "\n".join(sections)


def _render_urscript_toc(headings: list[Heading]) -> str:
    toc_items = [heading for heading in headings if heading.level in {2, 3}]
    if not toc_items:
        return "<p class=\"toc-empty\">本页暂无可折叠目录。</p>"
    return "\n".join(
        (
            f'<a class="toc-level-{heading.level}" href="#{html.escape(heading.anchor)}">'
            f"{html.escape(heading.text)}</a>"
        )
        for heading in toc_items
    )


def _render_urscript_pager(current_slug: str) -> str:
    previous_doc, next_doc = _find_adjacent_urscript_docs(current_slug)
    if previous_doc is None and next_doc is None:
        return ""

    cards: list[str] = []
    for direction, doc in (("上一篇", previous_doc), ("下一篇", next_doc)):
        if doc is None:
            continue
        cards.append(
            f"""
            <a class="pager-card" href="{html.escape(doc['slug'])}.html">
              <span class="pager-card__label">{html.escape(direction)}</span>
              <strong>{html.escape(doc['title'])}</strong>
              <p>{html.escape(doc['summary'])}</p>
            </a>
            """.strip()
        )
    return '<nav class="article-pager">' + "\n".join(cards) + "</nav>"


def _markdown_to_search_text(markdown_text: str) -> str:
    text = re.sub(r"```.*?```", " ", markdown_text, flags=re.S)
    text = re.sub(r"`([^`]+)`", r"\1", text)
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)
    text = re.sub(r"^#{1,6}\s*", "", text, flags=re.M)
    text = re.sub(r"^\s*[-*]\s+", "", text, flags=re.M)
    text = re.sub(r"^\s*\d+\.\s+", "", text, flags=re.M)
    text = re.sub(r"^\s*\|.*\|\s*$", " ", text, flags=re.M)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def _build_search_index(notes: list[dict[str, str]]) -> list[dict[str, str]]:
    entries = [dict(item) for item in HOME_SEARCH_ENTRIES]

    for note in notes:
        entries.append(
            {
                "title": note["title"],
                "href": f"#{_note_anchor(note)}",
                "kind": f"经验记录 · {note['category']}",
                "excerpt": note["content"],
                "keywords": f"{note['category']} {note['title']} {note['content']}",
            }
        )

    content_dir = urscript_content_dir()
    for doc in URSCRIPT_DOCS:
        source_path = content_dir / doc["filename"]
        if not source_path.exists():
            continue

        source_text = source_path.read_text(encoding="utf-8")
        rendered = render_markdown_document(source_text)
        plain_text = _markdown_to_search_text(source_text)
        entries.append(
            {
                "title": doc["title"],
                "href": f"urscript/{doc['slug']}.html",
                "kind": f"URScript · {_urscript_track_label(doc['slug'])}",
                "excerpt": doc["summary"],
                "keywords": f"{doc['title']} {doc['summary']} {plain_text}",
            }
        )

        for heading in rendered.headings:
            if heading.level not in {2, 3}:
                continue
            entries.append(
                {
                    "title": f"{doc['title']} / {heading.text}",
                    "href": f"urscript/{doc['slug']}.html#{heading.anchor}",
                    "kind": f"URScript · {doc['title']}",
                    "excerpt": doc["summary"],
                    "keywords": f"{heading.text} {doc['title']} {plain_text}",
                }
            )

    return entries


def _write_search_index_asset(runtime_dir: Path, notes: list[dict[str, str]]) -> None:
    assets_dir = runtime_dir / "assets"
    assets_dir.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(_build_search_index(notes), ensure_ascii=False, separators=(",", ":"))
    (assets_dir / "help-search-index.js").write_text(
        f"window.__HELP_SEARCH_INDEX__ = {payload};",
        encoding="utf-8",
    )


def _render_urscript_hub_page() -> str:
    return f"""
<!DOCTYPE html>
<html lang="zh-CN">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>URScript 语法参考</title>
    <link rel="stylesheet" href="../assets/help-center.css" />
  </head>
  <body class="article-body">
    <div class="article-shell article-shell--hub">
      <aside class="article-sidebar">
        <a class="back-link" href="../index.html#urscript">返回帮助中心</a>
        <p class="eyebrow">URScript</p>
        <h1>URScript 语法参考</h1>
        <p class="article-intro">语法结构、运动位姿、运行时接口、示例和常见坑。</p>
        <nav class="article-nav">
          {_render_urscript_nav()}
        </nav>
      </aside>

      <main class="article-main">
        <div class="article-main__inner article-main__inner--hub">
          <section class="article-hero">
            <p class="eyebrow">URScript</p>
            <h2>URScript 语法参考</h2>
            <p>按主题分组，便于查阅。</p>
          </section>

          <section class="doc-section">
            <div class="section-heading">
              <h2>语法与结构</h2>
              <p>语法结构、作用域、线程和常见错误。</p>
            </div>
            <div class="doc-link-grid">
              {_render_urscript_doc_cards(URSCRIPT_FOUNDATION_TRACK, href_prefix="")}
            </div>
          </section>

          <section class="doc-section">
            <div class="section-heading">
              <h2>运动、位姿与数学</h2>
              <p>运动指令、位姿表示和常用数学函数。</p>
            </div>
            <div class="doc-link-grid">
              {_render_urscript_doc_cards(URSCRIPT_MOTION_TRACK, href_prefix="")}
            </div>
          </section>

          <section class="doc-section">
            <div class="section-heading">
              <h2>运行时接口与示例</h2>
              <p>系统函数、I/O、RPC 和示例脚本。</p>
            </div>
            <div class="doc-link-grid">
              {_render_urscript_doc_cards(URSCRIPT_RUNTIME_TRACK, href_prefix="")}
            </div>
          </section>
        </div>
      </main>
    </div>
    <script src="../assets/help-center.js"></script>
  </body>
</html>
""".strip()


def _render_urscript_article_page(doc: dict[str, str], source_markdown: str) -> str:
    rendered = render_markdown_document(source_markdown)
    return f"""
<!DOCTYPE html>
<html lang="zh-CN">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>{html.escape(rendered.title)} | URScript 语法参考</title>
    <link rel="stylesheet" href="../assets/help-center.css" />
  </head>
  <body class="article-body">
    <div class="article-shell">
      <aside class="article-sidebar">
        <a class="back-link" href="index.html">返回 URScript 语法参考</a>
        <p class="eyebrow">URScript</p>
        <h1>{html.escape(rendered.title)}</h1>
        <p class="article-intro">{html.escape(doc['summary'])}</p>
        <div class="article-badges">
          <span class="badge">{html.escape(doc['audience'])}</span>
          <span class="badge badge--soft">{html.escape(_urscript_track_label(doc['slug']))}</span>
        </div>
        <nav class="article-nav">
          {_render_urscript_nav(current_slug=doc["slug"])}
        </nav>
      </aside>

      <main class="article-main">
        <div class="article-main__inner">
          <div class="article-breadcrumb">
            <a href="../index.html#urscript">帮助中心</a>
            <span>/</span>
            <a href="index.html">URScript 语法参考</a>
            <span>/</span>
            <strong>{html.escape(rendered.title)}</strong>
          </div>
          <section class="article-hero">
            <p class="eyebrow">URScript</p>
            <h2>{html.escape(rendered.title)}</h2>
            <p>{html.escape(doc['summary'])}</p>
          </section>
          <article class="article-prose">
            {rendered.html}
          </article>
          {_render_urscript_pager(doc["slug"])}
        </div>
      </main>

      <aside class="article-aside">
        <div class="article-aside__inner">
          <div class="article-toc">
            <p class="article-toc__title">本页目录</p>
            {_render_urscript_toc(rendered.headings)}
          </div>
        </div>
      </aside>
    </div>
    <script src="../assets/help-center.js"></script>
  </body>
</html>
""".strip()


def build_urscript_section(runtime_dir: Path) -> None:
    urscript_dir = runtime_dir / "urscript"
    urscript_dir.mkdir(parents=True, exist_ok=True)
    content_dir = urscript_content_dir()

    for existing in urscript_dir.glob("*.html"):
        existing.unlink(missing_ok=True)

    (urscript_dir / "index.html").write_text(_render_urscript_hub_page(), encoding="utf-8")
    for doc in URSCRIPT_DOCS:
        source_path = content_dir / doc["filename"]
        if not source_path.exists():
            continue
        source_text = source_path.read_text(encoding="utf-8")
        (urscript_dir / f"{doc['slug']}.html").write_text(
            _render_urscript_article_page(doc, source_text),
            encoding="utf-8",
        )


def render_help_center_html(notes: list[dict[str, str]] | None = None) -> str:
    effective_notes = notes if notes is not None else load_printing_notes()
    template_path = help_center_source_dir() / "index.template.html"
    template = template_path.read_text(encoding="utf-8")
    return (
        template.replace("__LOCAL_NOTE_FILTERS__", _render_note_filters(effective_notes))
        .replace("__LOCAL_NOTE_CARDS__", _render_note_cards(effective_notes))
        .replace(
            "__URSCRIPT_FOUNDATION_TRACK__",
            _render_urscript_doc_cards(URSCRIPT_FOUNDATION_TRACK, href_prefix="urscript/"),
        )
        .replace(
            "__URSCRIPT_MOTION_TRACK__",
            _render_urscript_doc_cards(URSCRIPT_MOTION_TRACK, href_prefix="urscript/"),
        )
        .replace(
            "__URSCRIPT_RUNTIME_TRACK__",
            _render_urscript_doc_cards(URSCRIPT_RUNTIME_TRACK, href_prefix="urscript/"),
        )
    )


def build_help_center_site(
    *,
    notes: list[dict[str, str]] | None = None,
    output_dir: Path | None = None,
) -> Path:
    source_dir = help_center_source_dir()
    effective_notes = notes if notes is not None else load_printing_notes()
    runtime_dir = Path(output_dir) if output_dir is not None else help_center_runtime_dir()
    runtime_dir.mkdir(parents=True, exist_ok=True)

    assets_src = source_dir / "assets"
    assets_dst = runtime_dir / "assets"
    if assets_src.exists():
        shutil.copytree(assets_src, assets_dst, dirs_exist_ok=True)

    _write_search_index_asset(runtime_dir, effective_notes)

    index_path = runtime_dir / "index.html"
    index_path.write_text(render_help_center_html(notes=effective_notes), encoding="utf-8")
    build_urscript_section(runtime_dir)
    return index_path


def open_help_center(*, anchor: str | None = None) -> bool:
    from PyQt6.QtCore import QUrl

    index_path = build_help_center_site()
    url = QUrl.fromLocalFile(str(index_path))
    if anchor:
        url.setFragment(anchor)
    return QDesktopServices.openUrl(url)
