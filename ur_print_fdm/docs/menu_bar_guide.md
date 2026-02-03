# 🛠️ 顶部菜单栏 (MenuBar) 开发说明文档

此文档用于记录 UR5 Fiber Printer Studio 顶部菜单栏的构成及其驱动逻辑，便于后续修改功能项或调整布局。

## 📍 核心驱动信息
- **逻辑驱动文件**: `ui/main_window.py`
- **核心初始化函数**: `def _init_menus(self)`
- **样式定义文件**: `ui/theme.py` (搜索 `QMenuBar` 和 `QMenu` 部分)

---

## 菜单结构详解

### 1. 文件 (File) - 快捷键 `Alt+F`
| 功能项 | 动作名称 (Action) | 快捷键 | 功能描述 |
| :--- | :--- | :--- | :--- |
| **新建脚本** | `act_new` | `Ctrl+N` | 调用 `create_new_tab()` 创建空白编辑器标签 |
| **打开项目** | `act_open_project` | `Ctrl+O` | 调用 `open_project()` 弹出文件夹选择框 |
| **保存** | `act_save` | `Ctrl+S` | 调用 `save_current_script()` 保存当前编辑内容 |
| **退出** | `act_exit` | `Alt+F4` | 调用 `close()` 关闭应用程序 |

### 2. 工具 (Tools) - 快捷键 `Alt+T`
这是系统功能最密集的模块，采用多级子菜单结构。

#### A. 工艺计算器 (子菜单)
驱动函数: `show_specific_calculator(type)`
- **挤出控制**: 流量控制、纤维补偿、压力补偿
- **姿态控制**: 切线跟随、倾角计算、曲率校验
- **同步控制**: 转台同步、外部轴映射、加热功率
- **几何工具**: 位姿偏置、TCP 转换、单位转换

#### B. 独立工具项
- **样件生成库**: `act_library` (`Ctrl+L`) -> `show_library_panel()`
- **平面标定**: `act_calibration` -> `show_calibration_panel()`
- **生产队列**: `act_queue` (`Ctrl+Q`) -> `show_queue_panel()`

#### C. 脚本处理 (子菜单)
驱动逻辑位于 `core/toolbox.py`
- **G-code 转换**: 调用 `tool_gcode_convert()`
- **脚本分割**: 调用 `tool_split_script()`
- **插入标志**: 调用 `tool_insert_flag()`

### 3. 设置 (Settings) - 快捷键 `Alt+S`
- **高级控制**: `act_advanced` -> `show_advanced_panel()`。用于配置机器人底层参数。

### 4. 帮助 (Help) - 快捷键 `Alt+H`
- **关于**: `act_about` -> `_show_about_dialog()`。显示软件版本、内核信息。

---

## 💡 修改建议
- **增加菜单项**: 在 `_init_menus` 中定义新的 `QAction`，设置其 `icon`、`text` 和 `setStatusTip`，最后使用 `menu.addAction()`。
- **调整图标**: 目前使用系统标准图标 `self.style().standardIcon(SP.SP_...)`，如需自定义，请将图标放入 `assets/icons/` 并使用 `QIcon("路径")`。
