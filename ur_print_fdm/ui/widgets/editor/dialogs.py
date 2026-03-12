from PyQt6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QCheckBox, QWidget
from PyQt6.QtCore import Qt

class FindReplaceDialog(QDialog):
    """查找和替换对话框（支持纯查找模式）"""
    def __init__(self, editor, find_only=False):
        super().__init__(editor)
        self.editor = editor
        self._find_only = find_only
        self.setWindowTitle("查找" if find_only else "查找和替换")
        self.resize(400, 150 if find_only else 200)
        self._match_count = 0
        self.init_ui()

    def set_find_only_mode(self, find_only):
        """切换查找/查找替换模式"""
        if self._find_only == find_only:
            return
        self._find_only = find_only
        self.setWindowTitle("查找" if find_only else "查找和替换")

        # 显示/隐藏替换相关控件
        self.replace_container.setVisible(not find_only)
        self.btn_replace.setVisible(not find_only)
        self.btn_replace_all.setVisible(not find_only)

        # 调整窗口大小
        self.resize(400, 150 if find_only else 200)

    def init_ui(self):
        layout = QVBoxLayout(self)

        # 查找
        flayout = QHBoxLayout()
        flayout.addWidget(QLabel("查找:"))
        self.find_input = QLineEdit()
        self.find_input.textChanged.connect(self._on_find_text_changed)
        flayout.addWidget(self.find_input)
        layout.addLayout(flayout)

        # 替换（可隐藏）
        self.replace_container = QWidget()
        rlayout = QHBoxLayout(self.replace_container)
        rlayout.setContentsMargins(0, 0, 0, 0)
        rlayout.addWidget(QLabel("替换:"))
        self.replace_input = QLineEdit()
        rlayout.addWidget(self.replace_input)
        layout.addWidget(self.replace_container)
        self.replace_container.setVisible(not self._find_only)

        # 选项
        opt_layout = QHBoxLayout()
        self.case_sensitive = QCheckBox("区分大小写")
        self.whole_word = QCheckBox("全词匹配")
        opt_layout.addWidget(self.case_sensitive)
        opt_layout.addWidget(self.whole_word)
        opt_layout.addStretch()
        layout.addLayout(opt_layout)

        # 匹配计数标签
        self.match_label = QLabel("")
        self.match_label.setStyleSheet("color: #888;")
        layout.addWidget(self.match_label)

        # 按钮
        blayout = QHBoxLayout()
        btn_prev = QPushButton("查找上一个")
        btn_prev.clicked.connect(self.find_prev)
        btn_next = QPushButton("查找下一个")
        btn_next.clicked.connect(self.find_next)
        self.btn_replace = QPushButton("替换")
        self.btn_replace.clicked.connect(self.replace_current)
        self.btn_replace_all = QPushButton("替换全部")
        self.btn_replace_all.clicked.connect(self.replace_all)

        blayout.addWidget(btn_prev)
        blayout.addWidget(btn_next)
        blayout.addWidget(self.btn_replace)
        blayout.addWidget(self.btn_replace_all)
        layout.addLayout(blayout)

        # 根据模式隐藏替换按钮
        self.btn_replace.setVisible(not self._find_only)
        self.btn_replace_all.setVisible(not self._find_only)

    def keyPressEvent(self, event):
        """支持快捷键"""
        if event.key() == Qt.Key.Key_Return or event.key() == Qt.Key.Key_Enter:
            if event.modifiers() == Qt.KeyboardModifier.ShiftModifier:
                self.find_prev()
            else:
                self.find_next()
        elif event.key() == Qt.Key.Key_Escape:
            self.close()
        else:
            super().keyPressEvent(event)

    def _on_find_text_changed(self, text):
        """查找文本变化时更新匹配计数"""
        if not text:
            self.match_label.setText("")
            return
        self._update_match_count()

    def _update_match_count(self):
        """更新匹配计数"""
        text = self.find_input.text()
        if not text:
            self.match_label.setText("")
            return

        content = self.editor.text()
        if not self.case_sensitive.isChecked():
            content = content.lower()
            text = text.lower()

        count = content.count(text)
        self._match_count = count
        if count == 0:
            self.match_label.setText("未找到匹配项")
            self.match_label.setStyleSheet("color: #f44;")
        else:
            self.match_label.setText(f"找到 {count} 个匹配项")
            self.match_label.setStyleSheet("color: #4a4;")

    def find_next(self):
        text = self.find_input.text()
        if not text:
            return
        res = self.editor.findFirst(
            text, False, self.case_sensitive.isChecked(),
            self.whole_word.isChecked(), True, True
        )
        if not res:
            # 循环查找：从头开始
            self.editor.findFirst(
                text, False, self.case_sensitive.isChecked(),
                self.whole_word.isChecked(), True, True, 0, 0
            )

    def find_prev(self):
        """向上查找"""
        text = self.find_input.text()
        if not text:
            return
        # QScintilla 的 findFirst 第6个参数 forward=False 表示向上查找
        res = self.editor.findFirst(
            text, False, self.case_sensitive.isChecked(),
            self.whole_word.isChecked(), True, False
        )
        if not res:
            # 循环查找：从末尾开始
            line_count = self.editor.lines()
            last_line_len = len(self.editor.text(line_count - 1)) if line_count > 0 else 0
            self.editor.findFirst(
                text, False, self.case_sensitive.isChecked(),
                self.whole_word.isChecked(), True, False, line_count - 1, last_line_len
            )

    def replace_current(self):
        if self.editor.hasSelectedText():
            self.editor.replace(self.replace_input.text())
            self.find_next()
            self._update_match_count()

    def replace_all(self):
        """替换全部匹配项"""
        find_text = self.find_input.text()
        replace_text = self.replace_input.text()
        if not find_text:
            return

        content = self.editor.text()
        if self.case_sensitive.isChecked():
            new_content = content.replace(find_text, replace_text)
            count = content.count(find_text)
        else:
            # 不区分大小写的替换
            import re
            pattern = re.compile(re.escape(find_text), re.IGNORECASE)
            matches = pattern.findall(content)
            count = len(matches)
            new_content = pattern.sub(replace_text, content)

        if count > 0:
            self.editor.setText(new_content)
            self.match_label.setText(f"已替换 {count} 处")
            self.match_label.setStyleSheet("color: #4a4;")
        else:
            self.match_label.setText("未找到匹配项")
            self.match_label.setStyleSheet("color: #f44;")
