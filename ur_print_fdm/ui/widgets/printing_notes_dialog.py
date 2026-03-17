from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QListWidget,
                              QStackedWidget, QTextBrowser, QDialogButtonBox,
                              QLabel, QPushButton, QLineEdit,
                              QSplitter, QWidget, QFormLayout, QTextEdit, QListWidgetItem, QFrame)
from ur_print_fdm.ui.widgets.styled_message_box import StyledMessageBox
from PyQt6.QtCore import Qt, QDateTime, pyqtSignal
import json
from ur_print_fdm.ui.resources.icon_manager import IconManager
from ur_print_fdm.ui import theme
from ur_print_fdm.ui.style_factory import StyleFactory
from ur_print_fdm.ui.widgets.fused_combo_box import FusedComboBox
from ur_print_fdm.help_center.note_data import default_printing_notes

class NoteEditDialog(QDialog):
    """添加/编辑注意事项的对话框"""
    
    def __init__(self, note_data=None, categories=None, parent=None):
        super().__init__(parent)
        self.note_data = note_data  # None 表示新建，dict 表示编辑
        self.categories = categories or []
        self.init_ui()
        self.load_data()
    
    def init_ui(self):
        self.setWindowTitle("编辑注意事项" if self.note_data else "添加注意事项")
        self.resize(600, 500)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        form_layout = QFormLayout()
        form_layout.setSpacing(12)
        form_layout.setContentsMargins(0, 0, 0, 0)

        self.combo_category = FusedComboBox()
        self.combo_category.addItems(self.categories)
        self.combo_category.setControlHeight(32)
        self.combo_category.setPopupRowHeight(32)
        form_layout.addRow("分类:", self.combo_category)

        self.edit_title = QLineEdit()
        self.edit_title.setPlaceholderText("请输入问题标题（例如：风扇防拖拽）")
        self.edit_title.setMinimumHeight(32)
        form_layout.addRow("标题:", self.edit_title)

        self.edit_content = QTextEdit()
        self.edit_content.setPlaceholderText("请输入详细内容...")
        self.edit_content.setMinimumHeight(280)
        form_layout.addRow("内容:", self.edit_content)

        layout.addLayout(form_layout)

        layout.addSpacing(8)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.validate_and_save)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
    
    def load_data(self):
        if self.note_data:
            self.edit_title.setText(self.note_data.get('title', ''))
            self.edit_content.setPlainText(self.note_data.get('content', ''))
            category = self.note_data.get('category', '打印工艺')
            index = self.combo_category.findText(category)
            if index >= 0:
                self.combo_category.setCurrentIndex(index)
    
    def validate_and_save(self):
        title = self.edit_title.text().strip()
        content = self.edit_content.toPlainText().strip()
        category = self.combo_category.currentText()
        
        if not title:
            StyledMessageBox.warning(self, "警告", "标题不能为空！")
            return
        
        if not content:
            StyledMessageBox.warning(self, "警告", "内容不能为空！")
            return
        
        now = QDateTime.currentDateTime().toString("yyyy-MM-dd hh:mm:ss")
        
        self.result_data = {
            'id': self.note_data.get('id') if self.note_data else f"note_{int(QDateTime.currentMSecsSinceEpoch())}",
            'category': category,
            'title': title,
            'content': content,
            'created_at': self.note_data.get('created_at', now),
            'updated_at': now
        }
        
        self.accept()
    
    def get_result(self):
        return getattr(self, 'result_data', None)


class PrintingNotesDialog(QDialog):
    """打印注意事项主对话框"""
    
    notes_updated = pyqtSignal()  # 信号：数据更新时发出
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("打印注意事项")
        self.setMinimumSize(1000, 700)
        self.notes = []
        self.current_category = "全部"
        self._init_default_notes()
        self._init_ui()
        self.load_notes()
    
    def _init_default_notes(self):
        """初始化默认的14条注意事项"""
        now = QDateTime.currentDateTime().toString("yyyy-MM-dd hh:mm:ss")
        self.default_notes = default_printing_notes(timestamp=now)
    
    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(12)

        # 顶部工具栏
        toolbar = QHBoxLayout()
        toolbar.setSpacing(8)

        icon_mgr = IconManager()
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("搜索问题...")
        self.search_edit.setMaximumWidth(300)
        self.search_edit.setMinimumHeight(32)
        self.search_edit.textChanged.connect(self.on_search_changed)
        search_icon = QLabel()
        search_icon.setPixmap(icon_mgr.get_svg_icon('search', (18, 18)).pixmap(18, 18))
        toolbar.addWidget(search_icon)
        toolbar.addWidget(self.search_edit)

        toolbar.addStretch()

        # 视觉分隔符
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.VLine)
        t = theme.current_tokens()
        separator.setStyleSheet(f"background-color: {t['border_light']};")
        separator.setFixedWidth(1)
        separator.setFixedHeight(24)
        toolbar.addWidget(separator)

        self.btn_add = QPushButton("添加")
        self.btn_add.setIcon(icon_mgr.get_svg_icon('add', (16, 16)))
        self.btn_add.setStyleSheet(StyleFactory.get_style("button_accent"))
        self.btn_add.clicked.connect(self.add_note)
        toolbar.addWidget(self.btn_add)

        self.btn_edit = QPushButton("编辑")
        self.btn_edit.setIcon(icon_mgr.get_svg_icon('edit', (16, 16)))
        self.btn_edit.setStyleSheet(StyleFactory.get_style("button_neutral"))
        self.btn_edit.clicked.connect(self.edit_note)
        toolbar.addWidget(self.btn_edit)

        self.btn_delete = QPushButton("删除")
        self.btn_delete.setIcon(icon_mgr.get_svg_icon('trash', (16, 16)))
        self.btn_delete.setStyleSheet(StyleFactory.get_style("button_danger"))
        self.btn_delete.clicked.connect(self.delete_note)
        toolbar.addWidget(self.btn_delete)

        layout.addLayout(toolbar)

        # 主体内容区（使用单个Splitter，三个面板）
        main_splitter = QSplitter(Qt.Orientation.Horizontal)
        main_splitter.setHandleWidth(1)

        # 左侧：分类导航
        self.category_list = QListWidget()
        self.category_list.setMinimumWidth(180)
        self.category_list.setMaximumWidth(250)
        self.category_list.currentRowChanged.connect(self.on_category_changed)

        # 中间：问题列表
        self.note_list = QListWidget()
        self.note_list.setMinimumWidth(250)
        self.note_list.currentRowChanged.connect(self.on_note_selected)

        # 右侧：问题详情（带容器以添加内边距）
        detail_container = QWidget()
        detail_layout = QVBoxLayout(detail_container)
        detail_layout.setContentsMargins(16, 16, 16, 16)
        detail_layout.setSpacing(0)

        self.detail_browser = QTextBrowser()
        self.detail_browser.setReadOnly(True)
        detail_layout.addWidget(self.detail_browser)

        main_splitter.addWidget(self.category_list)
        main_splitter.addWidget(self.note_list)
        main_splitter.addWidget(detail_container)
        main_splitter.setStretchFactor(0, 2)  # 分类: 20%
        main_splitter.setStretchFactor(1, 3)  # 笔记: 30%
        main_splitter.setStretchFactor(2, 5)  # 详情: 50%

        layout.addWidget(main_splitter)
        
        # 底部按钮
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok)
        buttons.accepted.connect(self.accept)
        layout.addWidget(buttons)
    
    def get_categories(self):
        """获取所有分类"""
        categories = set()
        for note in self.notes:
            categories.add(note['category'])
        return sorted(list(categories))
    
    def load_notes(self):
        """加载注意事项数据"""
        try:
            from ur_print_fdm.config import config_manager

            notes_str = config_manager.get("printing_notes.data")
            if notes_str and isinstance(notes_str, str):
                self.notes = json.loads(notes_str)
            else:
                self.notes = self.default_notes.copy()
                self.save_notes()
        except Exception as e:
            print(f"加载注意事项失败: {e}")
            self.notes = self.default_notes.copy()
        
        self.update_category_list()
        self.update_note_list()
    
    def save_notes(self):
        """保存注意事项数据"""
        try:
            from ur_print_fdm.config import config_manager
            notes_str = json.dumps(self.notes, ensure_ascii=False, indent=2)
            config_manager.set("printing_notes.data", notes_str)
            config_manager.save_config()
            self.notes_updated.emit()
            return True
        except Exception as e:
            StyledMessageBox.critical(self, "错误", f"保存失败：{e}")
            return False
    
    def update_category_list(self):
        """更新分类列表"""
        self.category_list.clear()
        self.category_list.addItem("全部")
        
        for category in self.get_categories():
            self.category_list.addItem(category)
        
        self.category_list.setCurrentRow(0)
    
    def update_note_list(self):
        """更新问题列表"""
        self.note_list.clear()
        
        search_text = self.search_edit.text().lower()
        
        for note in self.notes:
            if self.current_category != "全部" and note['category'] != self.current_category:
                continue
            
            if search_text:
                title_match = search_text in note['title'].lower()
                content_match = search_text in note['content'].lower()
                if not title_match and not content_match:
                    continue
            
            display_text = f"{note['title']}"
            item = QListWidgetItem(display_text)
            item.setData(Qt.ItemDataRole.UserRole, note['id'])
            self.note_list.addItem(item)
    
    def on_category_changed(self, index):
        """分类改变事件"""
        if index >= 0:
            category_item = self.category_list.item(index)
            if category_item:
                self.current_category = category_item.text()
                self.update_note_list()
                self.note_list.setCurrentRow(-1)
                self.show_empty_state()

    def on_note_selected(self, index):
        """问题选中事件"""
        if index >= 0:
            item = self.note_list.item(index)
            if item:
                note_id = item.data(Qt.ItemDataRole.UserRole)
                if note_id:
                    note = self._find_note_by_id(note_id)
                    if note:
                        self.display_note_detail(note)
                        return

        # 显示空状态
        self.show_empty_state()

    def show_empty_state(self):
        """显示空状态提示"""
        t = theme.current_tokens()
        empty_html = f"""
        <style>
            body {{
                display: flex;
                align-items: center;
                justify-content: center;
                height: 100%;
                color: {t["text_muted"]};
                font-size: 14px;
                text-align: center;
                padding: 40px;
            }}
            .empty-icon {{
                font-size: 48px;
                color: {t["text_dim"]};
                margin-bottom: 16px;
            }}
            .empty-text {{
                color: {t["text_muted"]};
                line-height: 1.6;
            }}
        </style>
        <div>
            <div class="empty-icon">📝</div>
            <div class="empty-text">
                请从左侧列表选择一个问题查看详情<br>
                或点击"添加"按钮创建新的注意事项
            </div>
        </div>
        """
        self.detail_browser.setHtml(empty_html)
    
    def _find_note_by_id(self, note_id):
        """根据ID查找问题"""
        for note in self.notes:
            if note['id'] == note_id:
                return note
        return None
    
    def display_note_detail(self, note):
        """显示问题详情"""
        self.detail_browser.setHtml(render_note_detail_html(note))


    def apply_theme(self) -> None:
        """Re-apply themed HTML for the current selection (after theme switch)."""
        # 更新按钮样式
        self.btn_add.setStyleSheet(StyleFactory.get_style("button_accent"))
        self.btn_edit.setStyleSheet(StyleFactory.get_style("button_neutral"))
        self.btn_delete.setStyleSheet(StyleFactory.get_style("button_danger"))

        # 重新渲染当前笔记或空状态
        try:
            current_row = self.note_list.currentRow()
            if current_row < 0:
                self.show_empty_state()
                return
            item = self.note_list.item(current_row)
            if not item:
                self.show_empty_state()
                return
            note_id = item.data(Qt.ItemDataRole.UserRole)
            note = self._find_note_by_id(note_id) if note_id else None
            if note:
                self.display_note_detail(note)
            else:
                self.show_empty_state()
        except Exception:
            pass

    def on_search_changed(self):
        """搜索文本改变事件"""
        self.update_note_list()

    def add_note(self):
        """添加新问题"""
        categories = self.get_categories()
        if not categories:
            categories = ["打印工艺", "机械问题", "挤出问题", "硬件问题", "维护保养"]

        dialog = NoteEditDialog(categories=categories, parent=self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            note_data = dialog.get_result()
            if note_data:
                self.notes.append(note_data)
                self.save_notes()
                self.update_category_list()
                self.update_note_list()
                self.log(f"已添加新问题: {note_data['title']}")

    def edit_note(self):
        """编辑问题"""
        current_row = self.note_list.currentRow()
        if current_row < 0:
            StyledMessageBox.warning(self, "提示", "请先选择要编辑的问题！")
            return

        item = self.note_list.item(current_row)
        if not item:
            StyledMessageBox.warning(self, "错误", "未找到选中的问题！")
            return

        note_id = item.data(Qt.ItemDataRole.UserRole)
        if not note_id:
            StyledMessageBox.warning(self, "错误", "未找到问题ID！")
            return

        note = self._find_note_by_id(note_id)

        if not note:
            StyledMessageBox.warning(self, "错误", "未找到选中的问题！")
            return

        categories = self.get_categories()
        dialog = NoteEditDialog(note_data=note, categories=categories, parent=self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            note_data = dialog.get_result()
            if note_data:
                # 更新原问题
                for i, n in enumerate(self.notes):
                    if n['id'] == note_id:
                        self.notes[i] = note_data
                        break
                self.save_notes()
                self.update_category_list()
                self.update_note_list()
                # 重新选中并显示
                self.note_list.setCurrentRow(current_row)
                self.log(f"已更新问题: {note_data['title']}")

    def delete_note(self):
        """删除问题"""
        current_row = self.note_list.currentRow()
        if current_row < 0:
            StyledMessageBox.warning(self, "提示", "请先选择要删除的问题！")
            return

        item = self.note_list.item(current_row)
        if not item:
            return

        note_id = item.data(Qt.ItemDataRole.UserRole)
        if not note_id:
            return

        note = self._find_note_by_id(note_id)

        if not note:
            return

        reply = StyledMessageBox.question(
            self,
            "确认删除",
            f"确定要删除问题「{note['title']}」吗？"
        )

        if reply == StyledMessageBox.Yes:
            self.notes = [n for n in self.notes if n['id'] != note_id]
            self.save_notes()
            self.update_category_list()
            self.update_note_list()
            self.log(f"已删除问题: {note['title']}")

    def log(self, message):
        """记录日志（调用主窗口的日志方法）"""
        try:
            parent = self.parent()
            if parent and hasattr(parent, 'log'):
                parent.log(f"打印注意事项: {message}")
        except Exception:
            pass


def render_note_detail_html(note: dict) -> str:
    """Build the themed HTML used by the note detail viewer."""
    t = theme.current_tokens()
    title = str(note.get("title", "") or "")
    category = str(note.get("category", "") or "")
    content = str(note.get("content", "") or "").replace("\n", "<br>")
    created_at = str(note.get("created_at", "") or "")
    updated_at = str(note.get("updated_at", "") or "")

    return f"""
    <style>
        body {{
            color: {t["text"]};
            font-family: {t.get("font_main", "sans-serif")};
            font-size: 13px;
            line-height: 1.8;
            padding: 24px;
            margin: 0;
        }}
        h1 {{
            color: {t["accent_link"]};
            font-size: 20px;
            font-weight: 600;
            margin: 0 0 12px 0;
            padding-bottom: 12px;
            border-bottom: 2px solid {t["accent_link"]};
        }}
        .category-badge {{
            display: inline-block;
            background-color: {t["bg_tertiary"]};
            color: {t["text_muted"]};
            font-size: 11px;
            font-weight: 500;
            padding: 4px 12px;
            border-radius: {t["radius"]};
            margin-bottom: 20px;
            border: 1px solid {t["border"]};
        }}
        .content {{
            color: {t["text"]};
            font-size: 14px;
            line-height: 1.8;
            margin: 20px 0;
            padding: 16px;
            background-color: {t["bg_panel"]};
            border-radius: {t.get("radius_lg", "6px")};
            border-left: 3px solid {t["accent_blue"]};
        }}
        .meta {{
            color: {t["text_dim"]};
            font-size: 11px;
            margin-top: 24px;
            padding-top: 16px;
            border-top: 1px solid {t["border_light"]};
            line-height: 1.6;
        }}
        .meta-label {{
            color: {t["text_muted"]};
            font-weight: 500;
        }}
    </style>
    <h1>{title}</h1>
    <div class="category-badge">📁 {category}</div>
    <div class="content">{content}</div>
    <div class="meta">
        <div><span class="meta-label">创建时间:</span> {created_at}</div>
        <div><span class="meta-label">更新时间:</span> {updated_at}</div>
    </div>
    """
