# 🕹️ 顶部工具栏 (ToolBar) 开发说明文档

此文档用于记录 UR5 Fiber Printer Studio 顶部工具栏的布局、交互逻辑及状态反馈机制。

## 📍 核心驱动信息
- **UI 驱动文件**: `ui/main_window.py`
- **初始化函数**: `def _init_toolbar(self)`
- **状态更新函数**: `def _update_status_indicator(self, status)`
- **样式定义**: 直接在 `_init_toolbar` 中通过内联 CSS 设置。

---

## 🧩 布局模块拆解 (从左至右)

### 1. 连接控制模块 (Connection)
- **IP 输入框 (`self.ip_combo`)**: 下拉组合框，支持历史记录和手动输入。
- **连接按钮 (`self.btn_connect`)**:
  - 核心逻辑: `toggle_monitor()`。
  - 交互: 点击后变为“断开”状态，背景色切换。

### 2. 状态指示反馈 (Feedback)
- **LED 指示灯 (`self.status_indicator`)**:
  - 实现方式: 圆形 `QLabel` (16x16px)。
  - **核心逻辑**: 由 `_update_status_indicator` 驱动，改变背景色和 `ToolTip`。
  - **颜色含义**:
    - ⚫ 灰色: 断开连接
    - 🔵 蓝色: 握手中/重连中
    - 🟢 绿色: **正常控制 (读写)**
    - 🔴 红色: **只读模式 (被示教器占用)**

### 3. 生产控制模块 (Control) - 视觉中心
这部分按钮的状态（启用/禁用）会随 LED 状态灯同步切换。
- **保存入口**: 不再常驻工具栏，改为通过菜单“文件 -> 保存”或 `Ctrl+S` 触发，避免打断运行控制区的视觉分组。
- **运行按钮 (`self.btn_global_run`)**: 绿色。只在“连接正常”时可用。
- **暂停按钮 (`self.btn_global_pause`)**: 橙色。支持“暂停/继续”状态切换，逻辑由 `_on_pause_clicked` 驱动。
- **停止按钮 (`self.btn_global_stop`)**: 红色。紧急终止机器人运动。

### 4. 辅助区 (Auxiliary)
- **修复连接按钮 (`self.btn_repair_connection`)**:
  - **图标**: 使用 `assets/icons/reconnect.svg`。
  - **逻辑**: 调用 `trigger_connection_repair()`，执行一次完整修复（重新建立监控、Dashboard、控制通道）。
  - **启用时机**: 当连接处于降级或故障状态时启用。

---

## ⚙️ 逻辑维护
- **状态联动**: 工具栏状态现在统一由 `_apply_connection_snapshot()` 驱动。
- **视觉微调**: 工具栏的边距和间距在 `_init_toolbar` 的 `toolbar.setStyleSheet` 中设置；运行区内部使用独立容器做紧凑分组，避免按钮块被次要动作打断。
- **SVG 图标**: 重连图标位于 `assets/icons/reconnect.svg`，如需更换图标，只需替换文件并保持文件名一致。
