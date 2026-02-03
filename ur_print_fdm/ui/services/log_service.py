from __future__ import annotations

import datetime

from ur_print_fdm.ui import theme


class LogService:
    def __init__(self, console, *, max_lines: int | None = None, auto_scroll: bool = True):
        self._console = console
        self._auto_scroll = bool(auto_scroll)
        if max_lines is not None and int(max_lines) > 0:
            # QTextDocument will automatically drop old blocks when the limit is exceeded.
            self._console.document().setMaximumBlockCount(int(max_lines))

    def set_auto_scroll(self, auto_scroll: bool) -> None:
        self._auto_scroll = bool(auto_scroll)

    def set_max_lines(self, max_lines: int | None) -> None:
        # Qt uses 0 for "no limit".
        if max_lines is None or int(max_lines) <= 0:
            self._console.document().setMaximumBlockCount(0)
            return
        self._console.document().setMaximumBlockCount(int(max_lines))

    def log(self, msg: str, level: str = "INFO") -> None:
        ts = datetime.datetime.now().strftime("[%H:%M:%S]")
        level_norm = str(level).upper()

        t = theme.current_tokens()
        use_dark = t is theme.DARK

        # Text colors
        color_map = {
            "INFO": t["text"],
            "DEBUG": t["text_muted"],
            "SUCCESS": t["success"],
            "WARN": t["warning"],
            "ERROR": t["danger"],
        }
        color = color_map.get(level_norm, t["text"])

        # Optional subtle background for high-signal levels
        bg_color_map = {
            "INFO": "transparent",
            "DEBUG": "transparent",
            "SUCCESS": "#1a3d1a" if use_dark else "#dafbe1",
            "WARN": "#3d3520" if use_dark else "#fff8c5",
            "ERROR": "#3d2020" if use_dark else "#ffebe9",
        }
        bg_color = bg_color_map.get(level_norm, "transparent")
        ts_color = t["text_dim"]
        
        # 级别标签（更紧凑的格式）
        level_tag = ""
        if level_norm not in ("INFO",):
            level_tag = f'<span style="color: {color}; font-weight: bold;">[{level_norm}]</span> '
        
        html_msg = (
            f'<div style="background-color: {bg_color}; padding: 2px 4px; margin: 1px 0; border-radius: 2px;">'
            f'<span style="color: {ts_color};">{ts}</span> {level_tag}'
            f'<span style="color: {color};">{msg}</span>'
            f'</div>'
        )
        self._console.append(html_msg)

        if self._auto_scroll:
            sb = self._console.verticalScrollBar()
            sb.setValue(sb.maximum())

    def clear(self) -> None:
        self._console.clear()
