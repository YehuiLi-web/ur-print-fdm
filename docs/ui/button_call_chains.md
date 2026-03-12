# 主窗口/队列对话框按钮文案与调用链

> 说明：本表覆盖 `ur_print_fdm/ui/main_window.py` 与 `ur_print_fdm/ui/widgets/queue_dialog.py` 中创建的 **QPushButton**（含文本）。
> 未包含菜单 QAction、仅图标的 QToolButton、以及其它子组件内部按钮（如文件浏览器、设置对话框等）。
> 如需“全项目所有按钮”，请告知范围（例如：仅主窗口 + 所有子对话框）。

## MainWindow（`ur_print_fdm/ui/main_window.py`）

| 按钮文案 | 位置/用途 | 点击处理函数 | 关键调用链（到驱动/线程） |
|---|---|---|---|
| 连接 / 断开 / 修复连接 | 工具栏连接按钮 `btn_connect` | `toggle_monitor()` | **连接**：`toggle_monitor` → `ConnectionThread(self.driver)` → `URDriver.connect()` → `on_connect_result` → `MonitorThread(self.driver)` → `URDriver.get_status()`；**断开**：`toggle_monitor` → `MonitorThread.requestInterruption()` → `URDriver.disconnect()`；**故障修复**：`toggle_monitor` / `trigger_connection_repair` → `ConnectionRepairThread(self.driver, ip)` → `URDriver.repair_connection(ip)` |
| 保存 | 工具栏保存按钮 `btn_save` | `save_current_script()` | 仅文件保存（无驱动调用） |
| 运行 / 暂停 / 继续 | 工具栏运行/暂停按钮 `btn_play_pause` | `_on_play_pause_clicked()` | **有生产任务**：`request_pause/request_resume` → `ProductionProcessor` → `SimpleDashboardDriver.pause()/play()`；**无生产任务**：`run_current_script()` → （生产模式）`ProductionProcessor` → `SimpleDashboardDriver.load_program()/play()`；（直连模式）`ScriptSendThread(self.driver)` → `URDriver.send_script()` |
| 停止 | 工具栏全局停止按钮 `btn_global_stop` | `stop_current_script()` | **有生产任务**：`ProductionProcessor.emergency_stop_action()` → `SimpleDashboardDriver.send("stop")` + secondary script；**无生产任务**：`StopThread(self.driver)` → `URDriver.stop()` |
| 上传 | 工具栏上传按钮 `btn_upload` | `upload_files()` | `upload_files` → `_begin_upload` → `SFTPUploadThread.run()` → paramiko SFTP（不经 URDriver） |
| （无文字）修复连接 | 工具栏“修复连接”图标按钮 `btn_repair_connection` | `trigger_connection_repair()` | `ConnectionRepairThread(self.driver, ip)` → `URDriver.repair_connection(ip)` |
| 添加 | 队列面板 `btn_queue_add` | `queue_add()` | 仅弹窗选择文件加入列表（无驱动调用） |
| 删除 | 队列面板 `btn_queue_del` | `queue_remove()` | 仅删除列表项（无驱动调用） |
| 清空 | 队列面板 `btn_queue_clear` | `queue_list.clear()` | 仅清空列表（无驱动调用） |
| 保存选中 | 队列面板 `btn_queue_save` | `save_selected_script()` | 保存当前编辑器内容到选中文件（无驱动调用） |
| 开始队列生产 | 队列面板 `btn_start_batch` | `start_production()` | `ProductionProcessor(...)` → `SimpleDashboardDriver.load_program()/play()` + SFTP 上传 |
| 停止 / 急停 | 队列面板 `btn_stop_batch` | `stop_production()` | `ProductionProcessor.emergency_stop_action()` → `SimpleDashboardDriver.send("stop")` + secondary script |

## QueueDialog（`ur_print_fdm/ui/widgets/queue_dialog.py`）

> 该对话框按钮多数转发到 MainWindow 的同名方法，再进入上表的调用链。

| 按钮文案 | 位置/用途 | 点击处理函数 | 关键调用链（到驱动/线程） |
|---|---|---|---|
| 添加 | 队列对话框 `btn_add` | `queue_add()` | 优先转发到主窗口 `queue_add_to_dialog()`（仅操作列表） |
| 删除 | 队列对话框 `btn_del` | `queue_remove()` | 转发到主窗口 `queue_remove_from_dialog()`（仅操作列表） |
| 清空 | 队列对话框 `btn_clr` | `queue_list.clear()` | 仅清空列表（无驱动调用） |
| 保存选中 | 队列对话框 `btn_save` | `save_selected_script()` | 转发到主窗口 `save_selected_script_dialog()`（无驱动调用） |
| 开始队列生产 | 队列对话框 `btn_start_batch` | `start_production()` | 转发到主窗口 `start_production_dialog()` → `ProductionProcessor` → `SimpleDashboardDriver.load_program()/play()` |
| 暂停 / 继续 | 队列对话框 `btn_pause_batch` | `pause_production()` | 转发到主窗口 `pause_production_dialog()` → `ProductionProcessor.request_pause/request_resume` → `SimpleDashboardDriver.pause()/play()` |
| 停止 / 急停 | 队列对话框 `btn_stop_batch` | `stop_production()` | 转发到主窗口 `stop_production_dialog()` → `ProductionProcessor.emergency_stop_action()` → `SimpleDashboardDriver.send("stop")` |
