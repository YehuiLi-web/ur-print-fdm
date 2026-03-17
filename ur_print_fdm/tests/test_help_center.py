from pathlib import Path
from unittest.mock import patch


def test_build_help_center_site_renders_local_notes(tmp_path):
    from ur_print_fdm.help_center.service import build_help_center_site

    notes = [
        {
            "id": "n1",
            "category": "打印工艺",
            "title": "首层高度",
            "content": "首层偏低会堆料，偏高会不贴合。",
            "created_at": "2026-03-17 10:00:00",
            "updated_at": "2026-03-17 10:00:00",
        }
    ]

    index_path = build_help_center_site(notes=notes, output_dir=tmp_path)

    assert index_path == tmp_path / "index.html"
    assert index_path.exists()
    assert (tmp_path / "assets" / "help-center.css").exists()
    assert (tmp_path / "assets" / "help-search-index.js").exists()
    html = index_path.read_text(encoding="utf-8")
    search_index = (tmp_path / "assets" / "help-search-index.js").read_text(encoding="utf-8")
    assert "帮助中心" in html
    assert "首层高度" in html
    assert "打印工艺" in html
    assert "经验记录" in html
    assert "helpSearchResults" in html
    assert "help-search-index.js" in html
    assert "页面生成时间" not in html
    assert "scope-and-threads.html#section-2" in search_index
    assert "#note-n1" in search_index
    assert (tmp_path / "urscript" / "index.html").exists()
    assert (tmp_path / "urscript" / "motion.html").exists()
    assert not (tmp_path / "urscript" / "software-support.html").exists()
    assert not (tmp_path / "urscript" / "parser-notes.html").exists()


def test_open_help_center_opens_local_index_with_anchor(tmp_path):
    from PyQt6.QtCore import QUrl

    index_path = tmp_path / "index.html"
    index_path.write_text("<html></html>", encoding="utf-8")

    with patch("ur_print_fdm.help_center.service.build_help_center_site", return_value=index_path):
        with patch("ur_print_fdm.help_center.service.QDesktopServices.openUrl", return_value=True) as open_url:
            from ur_print_fdm.help_center.service import open_help_center

            assert open_help_center(anchor="print-checklist") is True
            open_url.assert_called_once()
            url = open_url.call_args.args[0]
            assert isinstance(url, QUrl)
            assert url.isLocalFile()
            assert Path(url.toLocalFile()) == index_path
            assert url.fragment() == "print-checklist"


def test_build_help_center_site_includes_urscript_hub(tmp_path):
    from ur_print_fdm.help_center.service import build_help_center_site

    build_help_center_site(output_dir=tmp_path)

    home = (tmp_path / "index.html").read_text(encoding="utf-8")
    hub = (tmp_path / "urscript" / "index.html").read_text(encoding="utf-8")
    grammar = (tmp_path / "urscript" / "grammar.html").read_text(encoding="utf-8")
    scope = (tmp_path / "urscript" / "scope-and-threads.html").read_text(encoding="utf-8")
    pitfalls = (tmp_path / "urscript" / "pitfalls.html").read_text(encoding="utf-8")

    assert "URScript 语法参考" in home
    assert "常用入口" in home
    assert "打开 URScript 语法参考" in home
    assert "语法与结构" in hub
    assert "article-shell--hub" in hub
    assert "语法基础" in grammar
    assert "作用域与线程" in grammar
    assert "运动指令" in grammar
    assert "示例脚本" in scope
    assert "article-aside" in scope
    assert "article-pager" in scope
    assert "上一篇" in scope
    assert "下一篇" in scope
    assert 'class="code-block"' in scope
    assert "badge badge--soft" in scope
    assert "下一篇" not in pitfalls
    assert "help-search-index.js" in home
    assert "软件支持范围" not in home
    assert "解析实现备注" not in hub
    assert "parser-notes.html" not in grammar
    assert "parser-notes.html" not in scope
    assert "页面生成时间" not in home
    assert "替代原有自定义帮助弹窗" not in home
