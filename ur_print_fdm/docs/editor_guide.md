# UR5 Fiber Printer IDE - 编辑器模块技术规格书

本手册详细说明了编辑器模块的架构设计、核心函数及其与 VSCode 风格对齐的实现逻辑。

## 📁 文件索引

- **内核层**: [ui/widgets/editor/core.py](../ui/widgets/editor/core.py) - 处理语法高亮与 API 注入
- **管理层**: [ui/widgets/editor/manager.py](../ui/widgets/editor/manager.py) - 处理标签页、状态栏与 UI 布局
- **对话框**: [ui/widgets/editor/dialogs.py](../ui/widgets/editor/dialogs.py) - 查找与替换逻辑
- **全局皮肤**: [ui/theme.py](../ui/theme.py) - 全局滚动条与 Dock 样式

---

## 🛠️ 核心组件说明

### 1. CodeEditor (内核类)
基于 `QScintilla` 的高度定制化实现。

#### 🔹 语法高亮 (Syntax Highlighting)
采用 `QsciLexerPython` 并针对 **URScript** 进行配色微调：
- **注释 (`#`)**: `#6A9955` (暗绿色)
- **关键字 (`def`, `end`, `thread`等)**: `#569CD6` (亮蓝色)
- **函数/方法名**: `#DCDCAA` (浅黄色)
- **数字**: `#B5CEA8` (浅绿色)
- **操作符**: `#858585` (灰色)

#### 🔹 自动补全 (IntelliSense)
通过 `QsciAPIs` 注入了机器人核心指令集，支持 **2字符触发** 自动补全。已包含：
- **运动**: `movel`, `movej`, `movec`, `servoj`, `stopl`, `stopj`
- **位姿计算**: `pose_add`, `pose_inv`, `pose_trans`, `get_actual_tcp_pose`
- **IO控制**: `set_standard_digital_out`, `set_tool_digital_out`, `modbus_set_output_register`
- **逻辑控制**: `sleep`, `wait_wait`, `popup`, `textmsg`

#### 🔹 视觉特性
- **VSCode 风格行号区**:
  - `Margin 0`: 留有 `  000  ` 宽度的双侧 Padding。
  - `Margin 1`: 2px 宽的 `#2d2d30` 垂直分隔线。
- **缩进引导**: 启用 `IndentationGuides`，显示虚线引导对齐。
- **光标增强**: 加粗光标宽度 (`setCaretWidth(2)`)，并高亮当前行背景 (`#2a2d32`)。

---

### 2. DockableEditorWidget (管理层)
负责多标签生命周期与交互。

#### 🔹 标签栏顶替逻辑 (`open_file_in_tab`)
实现现代 IDE 的平滑过渡：
- 若当前仅打开 **欢迎页**，则打开新文件时自动执行 `close_tab` 顶替逻辑。
- 若标签页全关，自动回退至 **欢迎页** (`_show_welcome_tab`)。

#### 🔹 非对称名截断 (`_truncate_tab_name`)
采用 `1:2` 截断权重：
- **规则**: 剥离 `.script`，保留前 1/3 和后 2/3。
- **目的**: 优先保留文件名末尾的 `part01`, `part06` 等关键编号。

#### 🔹 中文状态栏 (`EditorStatusBar`)
- **光标追踪**: 实时显示 `行 X, 列 Y`。
- **动态高亮**: 选中文本时，统计信息以 **青色 (`#4EC9B0`)** 突出显示。

---

## ⌨️ 快捷键系统

| 快捷键 | 功能 |
| :--- | :--- |
| **Ctrl + N** | 新建脚本 |
| **Ctrl + S** | 保存当前文件 |
| **Ctrl + F** | 快速查找 |
| **Ctrl + H** | 查找与替换 |
| **滚轮滑动** | 在标签栏区域左右滑动文件标签 |

---

## 🎨 全局视觉规范 (Theme.py)

- **极简滚动条**:
  - 背景完全透明，滑块采用 `rgba(120, 120, 120, 0.4)`。
  - 悬停时加深至 `0.7`，消除传统滚动条的厚重感。
- **Dock 对齐**:
  - `QDockWidget::title` 统一为 **30px**。
  - 编辑器标签统一为 **33px**。
  - 视觉上通过扁平化设计确保三者高度在同一水平线上。

🤖 *由 Claude Code 自动生成 - 2026-01-31*
