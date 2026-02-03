# 右侧状态监控栏优化说明

## 概述
对原有的状态监控栏进行了全面优化，实现了以下改进：
1. 垂直侧边栏结构，采用纵向堆叠方式组织信息
2. 可折叠面板设计（Accordion/Collapsible Panels）
3. 更好的用户体验和视觉效果

## 主要特性

### 1. 垂直侧边栏结构
- 监控栏作为一个独立的垂直面板（Dock Widget）固定在主界面右侧
- 采用纵向堆叠的方式组织信息，便于阅读和操作
- 支持滚动，可以显示更多信息而不会占用过多空间

### 2. 可折叠面板设计
- 整体由多个可折叠的逻辑块组成
- 每个区块都有一个带有箭头的标题栏，允许用户根据需要展开或隐藏特定信息
- 在处理高密度工业数据时能有效减少视觉干扰
- 包含以下面板：
  - 🦾 关节角度 (Joints)
  - 📍 TCP 位姿 (Base)
  - 🛠️ TCP 偏移 (Offset)
- **状态记忆功能**：记住用户折叠/展开面板的状态，下次启动时恢复上次的状态

### 3. 数据更新机制
- 提供 `update_status()` 方法统一更新所有状态信息
- 支持实时显示机器人状态、关节角度、TCP位姿、连接状态等
- 进度条颜色根据关节角度的安全范围动态变化

## 技术实现

### CollapsibleBox 类
- 自定义可折叠面板组件
- 包含带箭头的标题栏和可展开/折叠的内容区域
- 支持自定义样式和状态监听

### StatusWidget 类
- 继承自 QWidget，作为状态监控栏的主组件
- 包含多个 CollapsibleBox 实例
- 提供统一的数据更新接口

### 样式设计
- 深色主题，符合工业软件界面风格
- 颜色编码：绿色（安全范围）、黄色（中等范围）、红色（接近极限）
- 清晰的视觉层次和间距

## 使用方法

在主窗口中，状态监控栏的集成方式如下：
```python
# 在 ui/main_window.py 中
from ui.widgets.collapsible_status_dock import StatusWidget

# 创建状态监控栏
self.status_widget = StatusWidget()
self.dock_status = QDockWidget("🤖 状态监视", self)
self.dock_status.setWidget(self.status_widget)
self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self.dock_status)
```

更新状态信息：
```python
# 在主窗口的 on_robot_status_update 方法中
connection_info = {
    'connected': self.driver.is_connected(),
    'ip': self.ip_combo.currentText(),
    'mode': '只读模式' if self.driver.is_read_only() else '控制模式'
}
self.status_widget.update_status(tcp, joints, offset, connection_info)
```

## 优势

1. **更好的用户体验**：可折叠面板让用户可以根据需要查看特定信息
2. **更清晰的信息组织**：逻辑分组使信息更容易理解和查找
3. **更高的可定制性**：用户可以选择显示哪些信息块
4. **更强的扩展性**：易于添加新的监控信息类型
5. **更佳的视觉效果**：现代化的设计和直观的状态指示