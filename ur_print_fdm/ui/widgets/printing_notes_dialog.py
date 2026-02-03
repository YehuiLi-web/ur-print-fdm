from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QListWidget,
                              QStackedWidget, QTextBrowser, QDialogButtonBox,
                              QLabel, QPushButton, QLineEdit, QComboBox,
                              QSplitter, QWidget, QFormLayout, QTextEdit, QListWidgetItem)
from ur_print_fdm.ui.widgets.styled_message_box import StyledMessageBox
from PyQt6.QtCore import Qt, QDateTime, pyqtSignal
import json
from pathlib import Path
from ur_print_fdm.ui.resources.icon_manager import IconManager
from ur_print_fdm.ui import theme

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
        self.resize(500, 400)
        
        layout = QVBoxLayout(self)
        
        form_layout = QFormLayout()
        
        self.combo_category = QComboBox()
        self.combo_category.addItems(self.categories)
        form_layout.addRow("分类:", self.combo_category)
        
        self.edit_title = QLineEdit()
        self.edit_title.setPlaceholderText("请输入问题标题（例如：风扇防拖拽）")
        form_layout.addRow("标题:", self.edit_title)
        
        self.edit_content = QTextEdit()
        self.edit_content.setPlaceholderText("请输入详细内容...")
        self.edit_content.setMinimumHeight(200)
        form_layout.addRow("内容:", self.edit_content)
        
        layout.addLayout(form_layout)
        
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
        self.default_notes = [
            {
                'id': 'note_1',
                'category': '打印工艺',
                'title': '风扇防拖拽',
                'content': '纯预浸渍碳纤维打印用风扇对着吹可以防拖拽。',
                'created_at': now,
                'updated_at': now
            },
            {
                'id': 'note_2',
                'category': '机械问题',
                'title': '喷头变角度打印',
                'content': '打印喷头变角度，倾斜30度进行打印。变角度的关键是要把TCP标定好，因为是沿着工具坐标原点进行旋转的，绕y轴旋转角度就是将角度放在第二个位姿角度上，函数为pose_trans(原来的，改变角度)。',
                'created_at': now,
                'updated_at': now
            },
            {
                'id': 'note_3',
                'category': '打印工艺',
                'title': '温度和速度设置',
                'content': '温度设置为190度，速度为8mm到16mm/s，纤维线宽为0.8，线宽大概设置为0.6，但是存在覆盖的现象，最大的问题就是两边拖拽。',
                'created_at': now,
                'updated_at': now
            },
            {
                'id': 'note_4',
                'category': '机械问题',
                'title': 'Feature坐标含义',
                'content': 'Feature坐标的含义，是相对base坐标的变换。例如feature(0.2，0.1，0.2，0，0，1.57)含义是相对base坐标，X轴偏移0.2m，y轴偏移0.1m，z轴偏移0.2m，坐标旋转，绕Z轴旋转了1.57弧度（约90度）。',
                'created_at': now,
                'updated_at': now
            },
            {
                'id': 'note_5',
                'category': '机械问题',
                'title': 'Feature坐标Z轴调整',
                'content': '例如在设置好的feature坐标系下本来可以正常打印，现在因为把打印喷头往下拧了，也就是说不更改的话就要产生碰撞。解决方法是将feature坐标的Z轴调高。',
                'created_at': now,
                'updated_at': now
            },
            {
                'id': 'note_6',
                'category': '机械问题',
                'title': '相对运动理解',
                'content': '如何理解：运动是相对运动，是相对feature坐标Z的偏移。例如本来Z=200，机械臂设置相对移动距离为100，则机械臂实际会走到300，这时改变Z为210，则机械臂实际会走到310，也就是相当于抬升了。',
                'created_at': now,
                'updated_at': now
            },
            {
                'id': 'note_7',
                'category': '打印工艺',
                'title': '第一层打印高度',
                'content': '打印第一层时，第一层的打印高度会严重影响打印质量及其重要，如果偏高的话就会导致线材不贴合，就产生类似波浪状的形状，如果偏低就会堆料，但是看起来的效果要好一点。',
                'created_at': now,
                'updated_at': now
            },
            {
                'id': 'note_8',
                'category': '挤出问题',
                'title': '打印头出料困难',
                'content': '打印头出料困难，尝试拧松大喷嘴，手动挤压线材，看是否出料，如果出料，大概率就是小喷嘴太大太长了压迫或者说是堵住出料了，使出料困难。',
                'created_at': now,
                'updated_at': now
            },
            {
                'id': 'note_9',
                'category': '硬件问题',
                'title': '白色导管插入检查',
                'content': '打印头不出料的话强烈建议检查一下白色导管是否完全插入喉管。',
                'created_at': now,
                'updated_at': now
            },
            {
                'id': 'note_10',
                'category': '维护保养',
                'title': '喷嘴安装',
                'content': '喷嘴得加热才能拧进去。',
                'created_at': now,
                'updated_at': now
            },
            {
                'id': 'note_11',
                'category': '维护保养',
                'title': '挤出机齿轮声音',
                'content': '注意挤出机齿轮的声音，有响声的话证明阻力很大，需要注意打印头的问题，查看是哪里堵住了。',
                'created_at': now,
                'updated_at': now
            },
            {
                'id': 'note_12',
                'category': '挤出问题',
                'title': '打印头堵住处理',
                'content': '打印头堵住，需要观察风扇是否在转，温度合适不。',
                'created_at': now,
                'updated_at': now
            },
            {
                'id': 'note_13',
                'category': '硬件问题',
                'title': '转盘打印注意事项',
                'content': '用到转盘打印时要注意必须开电源才能使用，而电源和是加热在一起的转盘打印同步问题不好解决，往往不是按照设定的步长去运行的，需要手动调，或者尝试一下多线程打印。',
                'created_at': now,
                'updated_at': now
            },
            {
                'id': 'note_14',
                'category': '挤出问题',
                'title': '地线接触不良',
                'content': '挤出机出料不均匀一卡一卡的大概率就是地线接触不良拔了重新插，通过调成3000检验齿轮是否转动。',
                'created_at': now,
                'updated_at': now
            }
        ]
    
    def _init_ui(self):
        layout = QVBoxLayout(self)
        
        # 顶部工具栏
        toolbar = QHBoxLayout()
        
        icon_mgr = IconManager()
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("搜索问题...")
        self.search_edit.setMaximumWidth(300)
        self.search_edit.textChanged.connect(self.on_search_changed)
        search_icon = QLabel()
        search_icon.setPixmap(icon_mgr.get_svg_icon('search', (18, 18)).pixmap(18, 18))
        toolbar.addWidget(search_icon)
        toolbar.addWidget(self.search_edit)
        
        toolbar.addStretch()
        
        self.btn_add = QPushButton("添加")
        self.btn_add.setIcon(icon_mgr.get_svg_icon('add', (16, 16)))
        self.btn_add.clicked.connect(self.add_note)
        toolbar.addWidget(self.btn_add)
        
        self.btn_edit = QPushButton("编辑")
        self.btn_edit.setIcon(icon_mgr.get_svg_icon('edit', (16, 16)))
        self.btn_edit.clicked.connect(self.edit_note)
        toolbar.addWidget(self.btn_edit)
        
        self.btn_delete = QPushButton("删除")
        self.btn_delete.setIcon(icon_mgr.get_svg_icon('trash', (16, 16)))
        self.btn_delete.clicked.connect(self.delete_note)
        toolbar.addWidget(self.btn_delete)
        
        layout.addLayout(toolbar)
        
        # 主体内容区（使用Splitter）
        main_splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # 左侧：分类导航 + 问题列表
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 0, 0)
        
        # 分类导航
        category_splitter = QSplitter(Qt.Orientation.Horizontal)
        
        self.category_list = QListWidget()
        self.category_list.setFixedWidth(150)
        self.category_list.currentRowChanged.connect(self.on_category_changed)

        self.note_list = QListWidget()
        self.note_list.currentRowChanged.connect(self.on_note_selected)
        
        category_splitter.addWidget(self.category_list)
        category_splitter.addWidget(self.note_list)
        category_splitter.setStretchFactor(0, 0)
        category_splitter.setStretchFactor(1, 1)
        
        left_layout.addWidget(category_splitter)
        
        # 右侧：问题详情
        self.detail_browser = QTextBrowser()
        self.detail_browser.setReadOnly(True)
        
        main_splitter.addWidget(left_widget)
        main_splitter.addWidget(self.detail_browser)
        main_splitter.setStretchFactor(0, 4)
        main_splitter.setStretchFactor(1, 6)
        
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
                self.detail_browser.clear()

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
        else:
            self.detail_browser.clear()
    
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
        try:
            current_row = self.note_list.currentRow()
            if current_row < 0:
                self.detail_browser.clear()
                return
            item = self.note_list.item(current_row)
            if not item:
                self.detail_browser.clear()
                return
            note_id = item.data(Qt.ItemDataRole.UserRole)
            note = self._find_note_by_id(note_id) if note_id else None
            if note:
                self.display_note_detail(note)
            else:
                self.detail_browser.clear()
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
      body {{ color: {t["text"]}; font-size: 11pt; line-height: 1.6; }}
      h1 {{ color: {t["accent_link"]}; font-size: 14pt; margin-bottom: 10px; }}
      .category {{ color: {t["text_muted"]}; font-size: 10pt; margin-bottom: 15px; }}
      .meta {{ color: {t["text_dim"]}; font-size: 9pt; margin-top: 20px; padding-top: 10px; border-top: 1px solid {t["border_light"]}; }}
      hr {{ border: none; border-top: 1px solid {t["border_light"]}; margin: 10px 0; }}
    </style>
    <h1>{title}</h1>
    <p class="category">分类: {category}</p>
    <hr>
    <p>{content}</p>
    <p class="meta">
      创建时间: {created_at}<br>
      更新时间: {updated_at}
    </p>
    """
    
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
