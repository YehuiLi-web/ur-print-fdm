import os
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QListWidget,
                            QPushButton, QGroupBox, QProgressBar, QCheckBox,
                            QFileDialog, QAbstractItemView)
from PyQt6.QtCore import Qt, pyqtSignal, QSize
from ur_print_fdm.ui.resources.icon_manager import IconManager
from ur_print_fdm.ui.widgets.styled_message_box import StyledMessageBox


class QueueDialog(QDialog):
    """生产队列对话框 - 独立窗口版本"""

    # 定义与主窗口中相同的关键信号
    queue_added = pyqtSignal(str)  # 添加队列项时发射
    queue_removed = pyqtSignal(int)  # 删除队列项时发射

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("生产队列管理")
        self.setModal(False)  # 设置为非模态，允许与主窗口交互
        self.resize(800, 700)

        # 居中显示
        self.center_on_screen()

        self.init_ui()

    def center_on_screen(self):
        """将对话框居中显示"""
        if self.parent():
            # 如果有父窗口，则相对于父窗口居中
            parent_geo = self.parent().geometry()
            x = parent_geo.x() + (parent_geo.width() - self.width()) // 2
            y = parent_geo.y() + (parent_geo.height() - self.height()) // 2
            self.move(x, y)
        else:
            # 如果没有父窗口，则居中于屏幕
            screen_geometry = self.screen().availableGeometry()
            window_geometry = self.geometry()
            x = (screen_geometry.width() - window_geometry.width()) // 2
            y = (screen_geometry.height() - window_geometry.height()) // 2
            self.move(x, y)

    def init_ui(self):
        """初始化界面"""
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(16, 16, 16, 16)

        # 队列列表
        self.queue_list = QListWidget()
        self.queue_list.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.queue_list.setMinimumHeight(200)
        layout.addWidget(self.queue_list)

        # 按钮行
        button_layout = QHBoxLayout()
        button_layout.setSpacing(8)
        icon_mgr = IconManager()
        btn_add = QPushButton("添加")
        btn_add.setIcon(icon_mgr.get_svg_icon('add', (16, 16)))
        btn_add.clicked.connect(self.queue_add)
        btn_del = QPushButton("删除")
        btn_del.setIcon(icon_mgr.get_svg_icon('trash', (16, 16)))
        btn_del.clicked.connect(self.queue_remove)
        btn_clr = QPushButton("清空")
        btn_clr.clicked.connect(self.queue_list.clear)
        btn_save = QPushButton("保存选中")
        btn_save.setIcon(icon_mgr.get_svg_icon('save', (16, 16)))
        btn_save.clicked.connect(self.save_selected_script)
        button_layout.addWidget(btn_add)
        button_layout.addWidget(btn_del)
        button_layout.addWidget(btn_clr)
        button_layout.addWidget(btn_save)
        layout.addLayout(button_layout)

        # 安全设置
        self.chk_watchdog = QGroupBox("安全设置")
        self.chk_watchdog.setCheckable(True)
        self.chk_watchdog.setTitle("启用挤出看门狗")
        self.chk_watchdog.setChecked(True)
        layout.addWidget(self.chk_watchdog)

        # 控制按钮
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(10)
        self.btn_start_batch = QPushButton("开始队列生产")
        self.btn_start_batch.setIcon(icon_mgr.get_svg_icon('play', (16, 16)))
        self.btn_start_batch.clicked.connect(self.start_production)
        self.btn_pause_batch = QPushButton("暂停")
        self.btn_pause_batch.setIcon(icon_mgr.get_svg_icon('pause', (16, 16)))
        self.btn_pause_batch.setCheckable(True)
        self.btn_pause_batch.clicked.connect(self.pause_production)
        self.btn_pause_batch.setEnabled(False)
        self.btn_stop_batch = QPushButton("停止 / 急停")
        self.btn_stop_batch.setIcon(icon_mgr.get_svg_icon('stop', (16, 16)))
        self.btn_stop_batch.clicked.connect(self.stop_production)
        self.btn_stop_batch.setEnabled(False)
        btn_layout.addWidget(self.btn_start_batch)
        btn_layout.addWidget(self.btn_pause_batch)
        btn_layout.addWidget(self.btn_stop_batch)
        layout.addLayout(btn_layout)

        # 进度条
        self.prog_batch = QProgressBar()
        self.prog_batch.setMinimumHeight(22)
        layout.addWidget(self.prog_batch)

        self.setLayout(layout)

    def queue_add(self):
        """添加队列项目"""
        controller = getattr(self.parent(), "queue_controller", None) if self.parent() else None
        if controller and hasattr(controller, "queue_add"):
            controller.queue_add(self.queue_list)
        elif self.parent() and hasattr(self.parent(), 'queue_add_to_dialog'):
            self.parent().queue_add_to_dialog(self.queue_list)
        else:
            # 否则使用本地实现
            files, _ = QFileDialog.getOpenFileNames(self, "添加脚本", "", "URScript (*.script *.txt);;All (*.*)")
            if files:
                for f in files:
                    self.queue_list.addItem(f)
                if self.parent() and hasattr(self.parent(), 'log'):
                    self.parent().log(f"添加 {len(files)} 个文件到队列。")

    def queue_remove(self):
        """删除选中的队列项目"""
        controller = getattr(self.parent(), "queue_controller", None) if self.parent() else None
        if controller and hasattr(controller, "queue_remove"):
            controller.queue_remove(self.queue_list)
        elif self.parent() and hasattr(self.parent(), 'queue_remove_from_dialog'):
            self.parent().queue_remove_from_dialog(self.queue_list)
        else:
            # 否则使用本地实现
            for item in self.queue_list.selectedItems():
                self.queue_list.takeItem(self.queue_list.row(item))

    def save_selected_script(self):
        """保存当前编辑器内容到选中的队列项"""
        controller = getattr(self.parent(), "queue_controller", None) if self.parent() else None
        if controller and hasattr(controller, "save_selected_script"):
            controller.save_selected_script(self.queue_list)
        elif self.parent() and hasattr(self.parent(), 'save_selected_script_dialog'):
            self.parent().save_selected_script_dialog(self.queue_list)
        else:
            # 这个功能需要与父窗口通信来获取当前编辑器内容
            StyledMessageBox.information(self, "提示", "此功能需要与主编辑器通信。")

    def start_production(self):
        """开始生产（需要与主窗口通信）"""
        controller = getattr(self.parent(), "queue_controller", None) if self.parent() else None
        if controller and hasattr(controller, "start_production"):
            controller.start_production(self.queue_list, self.chk_watchdog.isChecked(), self.prog_batch)
        elif self.parent() and hasattr(self.parent(), 'start_production_dialog'):
            self.parent().start_production_dialog(self.queue_list, self.chk_watchdog.isChecked(), self.prog_batch)
        else:
            StyledMessageBox.information(self, "提示", "开始生产功能需要与主窗口协调。")

    def stop_production(self):
        """停止生产"""
        controller = getattr(self.parent(), "queue_controller", None) if self.parent() else None
        if controller and hasattr(controller, "stop_production"):
            controller.stop_production()
        elif self.parent() and hasattr(self.parent(), 'stop_production_dialog'):
            self.parent().stop_production_dialog()
        else:
            StyledMessageBox.information(self, "提示", "停止生产功能需要与主窗口协调。")

    def pause_production(self):
        """暂停/继续生产（Dashboard pause/play）"""
        controller = getattr(self.parent(), "queue_controller", None) if self.parent() else None
        if controller and hasattr(controller, "pause_production"):
            is_paused = bool(self.btn_pause_batch.isChecked())
            controller.pause_production(is_paused)
            self.btn_pause_batch.setText("继续" if is_paused else "暂停")
        elif self.parent() and hasattr(self.parent(), "pause_production_dialog"):
            is_paused = bool(self.btn_pause_batch.isChecked())
            self.parent().pause_production_dialog(is_paused)
            self.btn_pause_batch.setText("继续" if is_paused else "暂停")
        else:
            StyledMessageBox.information(self, "提示", "暂停/继续需要与主窗口协调。")

    def load_scripts_to_list(self, scripts):
        """从主窗口加载脚本列表到对话框"""
        self.queue_list.clear()
        for script in scripts:
            self.queue_list.addItem(script)

    def get_scripts_from_list(self):
        """从对话框获取脚本列表到主窗口"""
        scripts = []
        for i in range(self.queue_list.count()):
            scripts.append(self.queue_list.item(i).text())
        return scripts


if __name__ == "__main__":
    import sys
    from PyQt6.QtWidgets import QApplication

    app = QApplication(sys.argv)
    dialog = QueueDialog()
    dialog.show()
    sys.exit(app.exec())
