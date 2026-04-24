from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QAbstractSpinBox,
    QApplication,
    QDialog,
    QDoubleSpinBox,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QSpinBox,
    QTextEdit,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from ur_print_fdm.core.print_lib import URPrintLib
from ur_print_fdm.ui.main_window import URPrintIDE
from ur_print_fdm.ui.resources.icon_manager import IconManager
from ur_print_fdm.ui.style_factory import StyleFactory
from ur_print_fdm.ui.theme_manager import get_theme_manager
from ur_print_fdm.ui.widgets.calibration import CalibrationWidget
from ur_print_fdm.ui.widgets.editor.dialogs import FindReplaceDialog
from ur_print_fdm.ui.widgets.editor.manager import DockableEditorWidget
from ur_print_fdm.ui.widgets.file_explorer import DeleteConfirmationDialog, FileExplorerWidget
from ur_print_fdm.ui.widgets.fused_combo_box import FusedComboBox
from ur_print_fdm.ui.widgets.help_dialog import HelpDialog
from ur_print_fdm.ui.widgets.library import LibraryWidget
from ur_print_fdm.ui.widgets.preferences_dialog import _NoWheelDoubleSpinBox, _NoWheelSpinBox, PreferencesDialog
from ur_print_fdm.ui.widgets.printing_notes_dialog import NoteEditDialog, PrintingNotesDialog
from ur_print_fdm.ui.widgets.queue_dialog import QueueDialog
from ur_print_fdm.ui.widgets.styled_message_box import StyledMessageBox
from ur_print_fdm.ui.widgets.sync_calculator import SyncCalculatorWidget
from ur_print_fdm.ui.widgets.extrusion_calculator import ExtrusionCalculatorWidget
from ur_print_fdm.ui.widgets.upload_options_dialog import UploadOptionsDialog, _UploadOptionRow
from ur_print_fdm.ui.widgets.collapsible_status_dock import StatusWidget


ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = ROOT / "manual_checks" / "ui_style_catalog"
MANIFEST_PATH = OUTPUT_DIR / "manifest.json"
INDEX_PATH = OUTPUT_DIR / "INDEX.md"


@dataclass(frozen=True)
class CaptureItem:
    category: str
    name: str
    description: str
    builder: Callable[[], QWidget]


class _FakeDriver:
    def is_connected(self) -> bool:
        return False

    def get_status(self):
        return None, None, None, None

    def get_tcp_pose(self):
        return None

    def get_tcp_force(self):
        return None


class _FakeMainWindow:
    def __init__(self):
        self.driver = _FakeDriver()
        self.print_lib = URPrintLib()
        self.messages: list[str] = []

    def log(self, message: str, level: str = "INFO") -> None:
        self.messages.append(f"[{level}] {message}")


class _GalleryDialog(QDialog):
    def __init__(self, title: str):
        super().__init__()
        self.setWindowTitle(title)
        self.resize(760, 520)
        self._root = QVBoxLayout(self)
        self._root.setContentsMargins(18, 18, 18, 18)
        self._root.setSpacing(14)

        heading = QLabel(title)
        heading.setStyleSheet("font-size: 16px; font-weight: 700;")
        self._root.addWidget(heading)

    def add_block(self, title: str, widget: QWidget) -> None:
        frame = QFrame()
        frame.setFrameShape(QFrame.Shape.StyledPanel)
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(10)

        label = QLabel(title)
        label.setStyleSheet("font-size: 12px; font-weight: 600;")
        layout.addWidget(label)
        layout.addWidget(widget)
        self._root.addWidget(frame)


def _pump(app: QApplication, cycles: int = 4) -> None:
    for _ in range(cycles):
        app.processEvents()


def _capture_widget(app: QApplication, item: CaptureItem) -> dict[str, str]:
    widget = item.builder()
    widget.show()
    widget.raise_()
    _pump(app)

    output_path = OUTPUT_DIR / f"{item.category}_{item.name}.png"
    widget.grab().save(str(output_path))

    try:
        widget.close()
    finally:
        widget.deleteLater()
        _pump(app, 2)

    return {
        "category": item.category,
        "name": item.name,
        "description": item.description,
        "file": output_path.name,
    }


def _make_main_window() -> QWidget:
    window = URPrintIDE()
    window.resize(1440, 920)
    try:
        window.project_widget.load_project(str(ROOT))
    except Exception:
        pass
    try:
        window.open_file_in_tab(str(ROOT / "README.md"))
    except Exception:
        pass
    return window


def _make_file_explorer() -> QWidget:
    widget = FileExplorerWidget()
    widget.resize(420, 720)
    try:
        widget.load_project(str(ROOT))
    except Exception:
        pass
    return widget


def _make_status_widget() -> QWidget:
    widget = StatusWidget()
    widget.resize(300, 860)
    return widget


def _make_editor_workspace() -> QWidget:
    widget = DockableEditorWidget()
    widget.resize(980, 700)
    try:
        widget.open_file_in_tab(str(ROOT / "README.md"))
    except Exception:
        pass
    return widget


def _make_find_replace_dialog() -> QWidget:
    editor_host = DockableEditorWidget()
    try:
        editor_host.open_file_in_tab(str(ROOT / "README.md"))
    except Exception:
        pass
    editor = editor_host.get_current_editor()
    dialog = FindReplaceDialog(editor, find_only=False)
    dialog.find_input.setText("UR")
    dialog.replace_input.setText("Robot")
    dialog.resize(520, 220)
    dialog._preview_owner = editor_host
    return dialog


def _make_preferences_dialog() -> QWidget:
    dialog = PreferencesDialog()
    dialog.resize(1060, 720)
    return dialog


def _make_help_dialog() -> QWidget:
    dialog = HelpDialog()
    dialog.resize(1040, 720)
    return dialog


def _make_notes_dialog() -> QWidget:
    dialog = PrintingNotesDialog()
    dialog.resize(1180, 760)
    return dialog


def _make_note_edit_dialog() -> QWidget:
    dialog = NoteEditDialog(
        note_data={
            "id": "note_preview",
            "category": "Process",
            "title": "Nozzle angle setup",
            "content": "Preview content for the style catalog.\n\nCompare spacing, labels, and actions.",
            "created_at": "2026-03-13 10:00:00",
            "updated_at": "2026-03-13 10:00:00",
        },
        categories=["Process", "Hardware", "Maintenance"],
    )
    dialog.resize(720, 560)
    return dialog


def _make_queue_dialog() -> QWidget:
    dialog = QueueDialog()
    dialog.queue_list.addItems(
        [
            str(ROOT / "URscript" / "fiber.script"),
            str(ROOT / "URscript" / "fiber_test_no_modbus.script"),
            str(ROOT / "URscript" / "cylinder_auto_calc.script"),
        ]
    )
    dialog.prog_batch.setMaximum(3)
    dialog.prog_batch.setValue(1)
    dialog.btn_stop_batch.setEnabled(True)
    dialog.btn_pause_batch.setEnabled(True)
    dialog.resize(860, 720)
    return dialog


def _make_upload_dialog() -> QWidget:
    dialog = UploadOptionsDialog(file_count=1, file_paths=[str(ROOT / "URscript" / "fiber.script")])
    return dialog


def _make_styled_message_box() -> QWidget:
    dialog = StyledMessageBox(
        None,
        "Connection issue",
        "The dashboard channel is offline.\n\nUse the repair action before starting production.",
        StyledMessageBox.Warning,
    )
    dialog.add_button("Repair", StyledMessageBox.Yes, is_default=True, is_accent=True)
    dialog.add_button("Cancel", StyledMessageBox.Cancel)
    return dialog


def _make_delete_dialog() -> QWidget:
    dialog = DeleteConfirmationDialog("demo.script")
    return dialog


def _make_native_message_box() -> QWidget:
    box = QMessageBox()
    box.setWindowTitle("Native warning")
    box.setIcon(QMessageBox.Icon.Warning)
    box.setText("This is the native QMessageBox style used in some legacy flows.")
    box.setStandardButtons(QMessageBox.StandardButton.Ok | QMessageBox.StandardButton.Cancel)
    box.resize(460, 220)
    return box


def _make_native_input_dialog() -> QWidget:
    dialog = QInputDialog()
    dialog.setWindowTitle("Native text input")
    dialog.setLabelText("Folder name:")
    dialog.setTextValue("NewFolder")
    dialog.resize(420, 160)
    return dialog


def _make_calibration_dialog() -> QWidget:
    host = QDialog()
    host.setWindowTitle("Calibration")
    host.resize(1120, 760)
    layout = QVBoxLayout(host)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.addWidget(CalibrationWidget(_FakeMainWindow()))
    return host


def _make_library_dialog() -> QWidget:
    host = QDialog()
    host.setWindowTitle("Sample library")
    host.resize(1040, 760)
    layout = QVBoxLayout(host)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.addWidget(LibraryWidget())
    return host


def _make_flow_calculator() -> QWidget:
    host = QDialog()
    host.setWindowTitle("Flow calculator")
    host.resize(640, 520)
    layout = QVBoxLayout(host)
    layout.addWidget(ExtrusionCalculatorWidget(show_only="flow"))
    return host


def _make_sync_calculator() -> QWidget:
    host = QDialog()
    host.setWindowTitle("Turntable calculator")
    host.resize(640, 520)
    layout = QVBoxLayout(host)
    layout.addWidget(SyncCalculatorWidget(show_only="turntable"))
    return host


def _make_text_input_gallery() -> QWidget:
    dialog = _GalleryDialog("Text Input Styles")

    form = QWidget()
    layout = QFormLayout(form)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(12)

    plain = QLineEdit("Plain line edit")
    plain.setPlaceholderText("Default project text input")

    password = QLineEdit("secret-token")
    password.setEchoMode(QLineEdit.EchoMode.Password)

    combo = FusedComboBox(editable=True, variant="toolbar_combo")
    combo.addItems(["192.168.1.120", "192.168.1.121", "192.168.1.122"])
    combo.setCurrentText("192.168.1.120")

    form_combo = FusedComboBox()
    form_combo.addItems(["Production", "Direct"])
    form_combo.setCurrentIndex(0)

    text_edit = QTextEdit()
    text_edit.setPlainText("QTextEdit\n\nUsed in notes, results, and documentation-heavy panels.")
    text_edit.setFixedHeight(110)

    plain_text = QPlainTextEdit()
    plain_text.setPlainText("{\n  \"ui\": \"advanced json\"\n}")
    plain_text.setFixedHeight(110)

    layout.addRow("QLineEdit", plain)
    layout.addRow("Password", password)
    layout.addRow("Editable combo", combo)
    layout.addRow("Fused combo", form_combo)
    layout.addRow("QTextEdit", text_edit)
    layout.addRow("QPlainTextEdit", plain_text)

    dialog.add_block("Representative text-entry controls", form)
    return dialog


def _make_numeric_gallery() -> QWidget:
    dialog = _GalleryDialog("Numeric Input Styles")

    form = QWidget()
    layout = QFormLayout(form)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(12)

    plain_spin = QSpinBox()
    plain_spin.setRange(0, 9999)
    plain_spin.setValue(4000)
    plain_spin.setSuffix(" mm")

    plain_double = QDoubleSpinBox()
    plain_double.setRange(0.0, 20.0)
    plain_double.setValue(3.5)
    plain_double.setSuffix(" N")

    compact_spin = _NoWheelSpinBox()
    compact_spin.setRange(0, 65535)
    compact_spin.setValue(1200)
    compact_spin.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.NoButtons)

    compact_double = _NoWheelDoubleSpinBox()
    compact_double.setRange(0.0, 100.0)
    compact_double.setValue(8.5)
    compact_double.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.NoButtons)
    compact_double.setSuffix(" mm/s")

    layout.addRow("Plain QSpinBox", plain_spin)
    layout.addRow("Plain QDoubleSpinBox", plain_double)
    layout.addRow("No-wheel compact spin", compact_spin)
    layout.addRow("No-wheel compact double", compact_double)

    dialog.add_block("Representative numeric controls", form)
    return dialog


def _make_button_gallery() -> QWidget:
    dialog = _GalleryDialog("Button Styles")
    icon_mgr = IconManager()

    host = QWidget()
    layout = QVBoxLayout(host)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(16)

    default_row = QWidget()
    default_layout = QHBoxLayout(default_row)
    default_layout.setContentsMargins(0, 0, 0, 0)
    default_layout.setSpacing(10)

    default_btn = QPushButton("Default")

    toolbar_primary = QPushButton("Run")
    toolbar_primary.setObjectName("btn-toolbar-primary")
    toolbar_primary.setIcon(icon_mgr.get_svg_icon("play", (16, 16)))

    toolbar_danger = QPushButton("Stop")
    toolbar_danger.setObjectName("btn-toolbar-danger")
    toolbar_danger.setIcon(icon_mgr.get_svg_icon("stop", (16, 16)))

    toolbar_ghost = QPushButton("Upload")
    toolbar_ghost.setObjectName("btn-toolbar-ghost")
    toolbar_ghost.setIcon(icon_mgr.get_svg_icon("upload", (16, 16)))

    accent_btn = QPushButton("Apply")
    accent_btn.setProperty("ui_variant", "accent")
    accent_btn.style().unpolish(accent_btn)
    accent_btn.style().polish(accent_btn)

    for button in (default_btn, toolbar_primary, toolbar_danger, toolbar_ghost, accent_btn):
        default_layout.addWidget(button)

    style_factory_row = QWidget()
    style_factory_layout = QHBoxLayout(style_factory_row)
    style_factory_layout.setContentsMargins(0, 0, 0, 0)
    style_factory_layout.setSpacing(10)

    accent_factory = QPushButton("Factory Accent")
    accent_factory.setStyleSheet(StyleFactory.get_style("button_accent"))
    neutral_factory = QPushButton("Factory Neutral")
    neutral_factory.setStyleSheet(StyleFactory.get_style("button_neutral"))
    danger_factory = QPushButton("Factory Danger")
    danger_factory.setStyleSheet(StyleFactory.get_style("button_danger"))

    tool_button = QToolButton()
    tool_button.setIcon(icon_mgr.get_svg_icon("settings", (18, 18)))
    tool_button.setAutoRaise(True)

    card_button = _UploadOptionRow(
        role="upload_only",
        title="Card-style action row",
        description="Used by the upload options dialog.",
        state_text="Default",
        recommended=True,
        enabled=True,
    )

    for button in (accent_factory, neutral_factory, danger_factory, tool_button):
        style_factory_layout.addWidget(button)
    style_factory_layout.addStretch(1)

    layout.addWidget(default_row)
    layout.addWidget(style_factory_row)
    layout.addWidget(card_button)

    dialog.add_block("Representative button families", host)
    return dialog


def _catalog_items() -> list[CaptureItem]:
    return [
        CaptureItem("shell", "main_window", "Main application shell with toolbar, docks, and editor", _make_main_window),
        CaptureItem("navigation", "file_explorer", "Tree-based navigation and embedded header actions", _make_file_explorer),
        CaptureItem("panel", "status_widget", "Right-side monitoring panel with collapsible cards", _make_status_widget),
        CaptureItem("workspace", "editor_workspace", "Dockable editor workspace and welcome/tab styling", _make_editor_workspace),
        CaptureItem("dialog", "find_replace", "Legacy editor utility dialog style", _make_find_replace_dialog),
        CaptureItem("form", "preferences_dialog", "Modern settings center with cards and inline fields", _make_preferences_dialog),
        CaptureItem("tool", "calibration_dialog", "Tabbed calibration workbench", _make_calibration_dialog),
        CaptureItem("tool", "library_dialog", "Sample library and dynamic form area", _make_library_dialog),
        CaptureItem("tool", "flow_calculator", "Single-purpose form calculator", _make_flow_calculator),
        CaptureItem("tool", "sync_calculator", "Single-purpose sync calculator", _make_sync_calculator),
        CaptureItem("content", "help_dialog", "Documentation reader layout", _make_help_dialog),
        CaptureItem("content", "printing_notes_dialog", "Knowledge-base list/detail workspace", _make_notes_dialog),
        CaptureItem("dialog", "queue_dialog", "List-based production queue dialog", _make_queue_dialog),
        CaptureItem("dialog", "upload_options_dialog", "Modern choice-card modal dialog", _make_upload_dialog),
        CaptureItem("dialog", "styled_message_box", "Custom app message dialog", _make_styled_message_box),
        CaptureItem("dialog", "delete_confirmation", "Custom destructive confirmation dialog", _make_delete_dialog),
        CaptureItem("dialog", "native_message_box", "Native QMessageBox style still used in legacy flows", _make_native_message_box),
        CaptureItem("dialog", "native_input_dialog", "Native QInputDialog style still used in legacy flows", _make_native_input_dialog),
        CaptureItem("dialog", "note_edit_dialog", "Form-heavy edit dialog", _make_note_edit_dialog),
        CaptureItem("controls", "text_inputs", "Text-entry control gallery", _make_text_input_gallery),
        CaptureItem("controls", "numeric_inputs", "Numeric-entry control gallery", _make_numeric_gallery),
        CaptureItem("controls", "buttons", "Button family gallery", _make_button_gallery),
    ]


def _write_index(entries: list[dict[str, str]]) -> None:
    grouped: dict[str, list[dict[str, str]]] = {}
    for entry in entries:
        grouped.setdefault(entry["category"], []).append(entry)

    lines = [
        "# UI Style Catalog",
        "",
        "Generated by `manual_checks/render_ui_style_catalog.py`.",
        "",
    ]
    for category in sorted(grouped):
        lines.append(f"## {category}")
        lines.append("")
        for entry in grouped[category]:
            lines.append(f"- `{entry['file']}`: {entry['description']}")
        lines.append("")

    INDEX_PATH.write_text("\n".join(lines), encoding="utf-8")
    MANIFEST_PATH.write_text(json.dumps(entries, ensure_ascii=False, indent=2), encoding="utf-8")


def main() -> int:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    for file in OUTPUT_DIR.glob("*.png"):
        file.unlink()

    app = QApplication.instance() or QApplication([])
    app.setQuitOnLastWindowClosed(False)
    get_theme_manager().set_theme("dark")
    _pump(app, 6)

    entries = [_capture_widget(app, item) for item in _catalog_items()]
    _write_index(entries)

    print(INDEX_PATH)
    for entry in entries:
        print(OUTPUT_DIR / entry["file"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
