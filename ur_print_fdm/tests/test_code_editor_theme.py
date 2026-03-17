from PyQt6.QtWidgets import QApplication

from ur_print_fdm.ui import theme


def test_code_editor_uses_light_theme_paper_and_text():
    app = QApplication.instance() or QApplication([])

    theme.apply_app_theme(use_dark=False)
    from ur_print_fdm.ui.widgets.editor.core import CodeEditor

    ed = CodeEditor()
    try:
        if not getattr(ed, "_is_qsci", False):
            return
        t = theme.current_tokens()
        assert ed.lexer.defaultPaper(0).name().lower() == t["bg_secondary"].lower()
        assert ed.lexer.defaultColor(0).name().lower() == t["text"].lower()
    finally:
        ed.deleteLater()
        app.processEvents()


def test_code_editor_line_number_margin_tracks_line_count():
    app = QApplication.instance() or QApplication([])

    from ur_print_fdm.ui.widgets.editor.core import CodeEditor

    ed = CodeEditor()
    try:
        if not getattr(ed, "_is_qsci", False):
            return

        ed.setText("line1\nline2\n")
        app.processEvents()
        compact_width = ed.marginWidth(0)

        ed.setText("\n".join(f"line {i}" for i in range(120)))
        app.processEvents()
        expanded_width = ed.marginWidth(0)

        assert compact_width > 0
        assert expanded_width > compact_width
        assert ed.marginWidth(CodeEditor.FOLD_MARGIN_INDEX) == CodeEditor.FOLD_MARGIN_WIDTH
    finally:
        ed.deleteLater()
        app.processEvents()
