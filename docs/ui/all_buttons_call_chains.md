# ??? UI ??/?? ??????

> ??????? `ur_print_fdm/ui/**.py` ?? QPushButton/QToolButton/QAction ?? `.addAction("text", handler)` ???
> ???????????????????????????????????????

| ?? | ?? | ??/Action | ?? | ???? | ??????/??? | ?? | ?? |
|---|---|---|---|---|---|---|---|
| ??/?? | 复制 | ur_print_fdm/ui/widgets/log_display.py:61 `copy_action` | triggered | `self.copy` |  |  | ur_print_fdm/ui/widgets/log_display.py:61 |
| ??/?? | 复制全部 | ur_print_fdm/ui/widgets/log_display.py:65 `copy_all_action` | triggered | `self.copy_all_logs` |  |  | ur_print_fdm/ui/widgets/log_display.py:65 |
| ??/?? | 全部 | ur_print_fdm/ui/widgets/log_display.py:76 `filter_all` | triggered | `lambda: self._set_filter("ALL")` |  |  | ur_print_fdm/ui/widgets/log_display.py:76 |
| ??/?? | 警告及以上 | ur_print_fdm/ui/widgets/log_display.py:82 `filter_warn` | triggered | `lambda: self._set_filter("WARN")` |  |  | ur_print_fdm/ui/widgets/log_display.py:82 |
| ??/?? | 仅错误 | ur_print_fdm/ui/widgets/log_display.py:88 `filter_error` | triggered | `lambda: self._set_filter("ERROR")` |  |  | ur_print_fdm/ui/widgets/log_display.py:88 |
| ??/?? | 自动滚动 | ur_print_fdm/ui/widgets/log_display.py:97 `auto_scroll_action` | triggered | `self._toggle_auto_scroll` |  |  | ur_print_fdm/ui/widgets/log_display.py:97 |
| ??/?? | 滚动到底部 | ur_print_fdm/ui/widgets/log_display.py:101 `scroll_bottom_action` | triggered | `self.scroll_to_bottom` |  |  | ur_print_fdm/ui/widgets/log_display.py:101 |
| ??/?? | 清除日志 | ur_print_fdm/ui/widgets/log_display.py:108 `clear_action` | triggered | `self.clear_log` |  |  | ur_print_fdm/ui/widgets/log_display.py:108 |
| ??/?? | (icon-only) | ur_print_fdm/ui/widgets/preferences_dialog.py:312 `ip_list` | itemDoubleClicked | `lambda _: btn_default.click()` |  |  | ur_print_fdm/ui/widgets/preferences_dialog.py:312 |
| ??/?? | 添加… | ur_print_fdm/ui/widgets/preferences_dialog.py:363 `btn_add` | clicked | `_add_ip` |  |  | ur_print_fdm/ui/widgets/preferences_dialog.py:363 |
| ??/?? | 移除 | ur_print_fdm/ui/widgets/preferences_dialog.py:364 `btn_remove` | clicked | `_remove_ip` |  |  | ur_print_fdm/ui/widgets/preferences_dialog.py:364 |
| ??/?? | 上移 | ur_print_fdm/ui/widgets/preferences_dialog.py:365 `btn_up` | clicked | `lambda: _move(-1)` |  |  | ur_print_fdm/ui/widgets/preferences_dialog.py:365 |
| ??/?? | 下移 | ur_print_fdm/ui/widgets/preferences_dialog.py:366 `btn_down` | clicked | `lambda: _move(1)` |  |  | ur_print_fdm/ui/widgets/preferences_dialog.py:366 |
| ??/?? | 设为默认 | ur_print_fdm/ui/widgets/preferences_dialog.py:367 `btn_default` | clicked | `_set_default` |  |  | ur_print_fdm/ui/widgets/preferences_dialog.py:367 |
| ??/?? | 浏览… | ur_print_fdm/ui/widgets/preferences_dialog.py:579 `btn_browse` | clicked | `_browse` |  |  | ur_print_fdm/ui/widgets/preferences_dialog.py:579 |
| ??/?? | 清空 | ur_print_fdm/ui/widgets/preferences_dialog.py:580 `btn_clear` | clicked | `_clear` |  |  | ur_print_fdm/ui/widgets/preferences_dialog.py:580 |
| ??/?? | 选择… | ur_print_fdm/ui/widgets/preferences_dialog.py:732 `btn_dir` | clicked | `_browse_dir` |  |  | ur_print_fdm/ui/widgets/preferences_dialog.py:732 |
| ??/?? | 从当前设置生成 | ur_print_fdm/ui/widgets/preferences_dialog.py:814 `btn_reload` | clicked | `_reload` |  |  | ur_print_fdm/ui/widgets/preferences_dialog.py:814 |
| ??/?? | 校验 | ur_print_fdm/ui/widgets/preferences_dialog.py:815 `btn_validate` | clicked | `_validate` |  |  | ur_print_fdm/ui/widgets/preferences_dialog.py:815 |
| ??/?? | 应用到工作副本 | ur_print_fdm/ui/widgets/preferences_dialog.py:816 `btn_apply` | clicked | `_apply_json` |  |  | ur_print_fdm/ui/widgets/preferences_dialog.py:816 |
| ??/?? | 添加 | ur_print_fdm/ui/widgets/queue_dialog.py:62 `btn_add` | clicked | `self.queue_add` |  |  | ur_print_fdm/ui/widgets/queue_dialog.py:62 |
| ??/?? | 删除 | ur_print_fdm/ui/widgets/queue_dialog.py:65 `btn_del` | clicked | `self.queue_remove` |  |  | ur_print_fdm/ui/widgets/queue_dialog.py:65 |
| ??/?? | 清空 | ur_print_fdm/ui/widgets/queue_dialog.py:67 `btn_clr` | clicked | `self.queue_list.clear` |  |  | ur_print_fdm/ui/widgets/queue_dialog.py:67 |
| ??/?? | 保存选中 | ur_print_fdm/ui/widgets/queue_dialog.py:70 `btn_save` | clicked | `self.save_selected_script` |  |  | ur_print_fdm/ui/widgets/queue_dialog.py:70 |
| ??/??? | 查找和替换 (Ctrl+H) | ur_print_fdm/ui/widgets/editor/core.py:368 `find_act` | triggered | `self.show_find_replace_dialog` |  |  | ur_print_fdm/ui/widgets/editor/core.py:368 |
| ??/??? | 撤销 | ur_print_fdm/ui/widgets/editor/core.py:371 `(menu.addAction)` | triggered | `self.undo` |  |  | ur_print_fdm/ui/widgets/editor/core.py:371 |
| ??/??? | 重做 | ur_print_fdm/ui/widgets/editor/core.py:372 `(menu.addAction)` | triggered | `self.redo` |  |  | ur_print_fdm/ui/widgets/editor/core.py:372 |
| ??/??? | 剪切 | ur_print_fdm/ui/widgets/editor/core.py:374 `(menu.addAction)` | triggered | `self.cut` |  |  | ur_print_fdm/ui/widgets/editor/core.py:374 |
| ??/??? | 复制 | ur_print_fdm/ui/widgets/editor/core.py:375 `(menu.addAction)` | triggered | `self.copy` |  |  | ur_print_fdm/ui/widgets/editor/core.py:375 |
| ??/??? | 粘贴 | ur_print_fdm/ui/widgets/editor/core.py:376 `(menu.addAction)` | triggered | `self.paste` |  |  | ur_print_fdm/ui/widgets/editor/core.py:376 |
| ??/??? | 查找上一个 | ur_print_fdm/ui/widgets/editor/dialogs.py:68 `btn_prev` | clicked | `self.find_prev` |  |  | ur_print_fdm/ui/widgets/editor/dialogs.py:68 |
| ??/??? | 查找下一个 | ur_print_fdm/ui/widgets/editor/dialogs.py:70 `btn_next` | clicked | `self.find_next` |  |  | ur_print_fdm/ui/widgets/editor/dialogs.py:70 |
| ??/??? | 关闭 | ur_print_fdm/ui/widgets/editor/manager.py:897 `act_close` | triggered | `lambda: self.close_tab(idx)` |  |  | ur_print_fdm/ui/widgets/editor/manager.py:897 |
| ??/??? | 关闭其他标签 | ur_print_fdm/ui/widgets/editor/manager.py:903 `act_close_others` | triggered | `lambda: self._close_other_tabs(idx)` |  |  | ur_print_fdm/ui/widgets/editor/manager.py:903 |
| ??/??? | 关闭所有标签 | ur_print_fdm/ui/widgets/editor/manager.py:908 `act_close_all` | triggered | `self._close_all_tabs` |  |  | ur_print_fdm/ui/widgets/editor/manager.py:908 |
| ??/??? | 在资源管理器中打开 | ur_print_fdm/ui/widgets/editor/manager.py:915 `act_open` | triggered | `lambda: self._open_explorer(path)` |  |  | ur_print_fdm/ui/widgets/editor/manager.py:915 |
| ??/??? | 复制路径 | ur_print_fdm/ui/widgets/editor/manager.py:919 `act_copy` | triggered | `lambda: QApplication.clipboard().setText(path)` |  |  | ur_print_fdm/ui/widgets/editor/manager.py:919 |
| ??/????? | (icon-only) | ur_print_fdm/ui/widgets/file_explorer.py:185 `btn` | clicked | `slot` |  |  | ur_print_fdm/ui/widgets/file_explorer.py:185 |
| ??/????? | open | ur_print_fdm/ui/widgets/file_explorer.py:395 `action_open` | triggered | `lambda: self.open_file_requested(item_path)` |  |  | ur_print_fdm/ui/widgets/file_explorer.py:395 |
| ??/????? | 脚本估算... | ur_print_fdm/ui/widgets/file_explorer.py:400 `action_estimate` | triggered | `lambda: self.estimate_requested.emit(item_path)` |  |  | ur_print_fdm/ui/widgets/file_explorer.py:400 |
| ??/????? | rename | ur_print_fdm/ui/widgets/file_explorer.py:405 `action_rename` | triggered | `lambda: self.rename_file(item, item_path)` |  |  | ur_print_fdm/ui/widgets/file_explorer.py:405 |
| ??/????? | delete | ur_print_fdm/ui/widgets/file_explorer.py:410 `action_delete` | triggered | `lambda: self.delete_file(item, item_path)` |  |  | ur_print_fdm/ui/widgets/file_explorer.py:410 |
| ??/????? | copy_path | ur_print_fdm/ui/widgets/file_explorer.py:415 `action_copy_path` | triggered | `lambda: self.copy_file_path(item_path)` |  |  | ur_print_fdm/ui/widgets/file_explorer.py:415 |
| ??/????? | 上传到机器人 | ur_print_fdm/ui/widgets/file_explorer.py:424 `action_upload` | triggered | `lambda: self.upload_requested.emit(selected_files)` |  |  | ur_print_fdm/ui/widgets/file_explorer.py:424 |
| ??/????? | new_file | ur_print_fdm/ui/widgets/file_explorer.py:437 `action_new_script` | triggered | `lambda: self.new_script_file(current_dir)` |  |  | ur_print_fdm/ui/widgets/file_explorer.py:437 |
| ??/????? | new_folder | ur_print_fdm/ui/widgets/file_explorer.py:442 `action_new_folder` | triggered | `lambda: self.new_folder(current_dir)` |  |  | ur_print_fdm/ui/widgets/file_explorer.py:442 |
| ??/????? | search | ur_print_fdm/ui/widgets/file_explorer.py:449 `action_find` | triggered | `self.quick_find_file` |  |  | ur_print_fdm/ui/widgets/file_explorer.py:449 |
| ??/????? | refresh | ur_print_fdm/ui/widgets/file_explorer.py:454 `action_refresh` | triggered | `self.refresh_project` |  |  | ur_print_fdm/ui/widgets/file_explorer.py:454 |
| ??/????? | open_explorer | ur_print_fdm/ui/widgets/file_explorer.py:460 `action_open_explorer` | triggered | `lambda: self.open_in_explorer(item_path)` |  |  | ur_print_fdm/ui/widgets/file_explorer.py:460 |
| ??/????? | (icon-only) | ur_print_fdm/ui/widgets/file_explorer.py:729 `results_list` | itemDoubleClicked | `on_item_activated` |  |  | ur_print_fdm/ui/widgets/file_explorer.py:729 |
| ??/????? | (icon-only) | ur_print_fdm/ui/widgets/file_explorer.py:730 `results_list` | itemActivated | `on_item_activated` |  |  | ur_print_fdm/ui/widgets/file_explorer.py:730 |
| ??/????? | (icon-only) | ur_print_fdm/ui/widgets/file_explorer.py:737 `search_input` | returnPressed | `on_return_pressed` |  |  | ur_print_fdm/ui/widgets/file_explorer.py:737 |
| ???/??/??? | 新建脚本(&N) | ur_print_fdm/ui/main_window.py:291 `act_new` | triggered | `self.create_new_tab` |  |  | ur_print_fdm/ui/main_window.py:291 |
| ???/??/??? | 打开项目(&O)... | ur_print_fdm/ui/main_window.py:298 `act_open_project` | triggered | `self.open_project` |  |  | ur_print_fdm/ui/main_window.py:298 |
| ???/??/??? | 保存(&S) | ur_print_fdm/ui/main_window.py:305 `act_save` | triggered | `self.save_current_script` |  |  | ur_print_fdm/ui/main_window.py:305 |
| ???/??/??? | 退出(&X) | ur_print_fdm/ui/main_window.py:314 `act_exit` | triggered | `self.close` |  |  | ur_print_fdm/ui/main_window.py:314 |
| ???/??/??? | 流量控制 | ur_print_fdm/ui/main_window.py:331 `act_flow` | triggered | `lambda: self.show_specific_calculator('flow')` |  |  | ur_print_fdm/ui/main_window.py:331 |
| ???/??/??? | 纤维补偿 | ur_print_fdm/ui/main_window.py:336 `act_fiber` | triggered | `lambda: self.show_specific_calculator('fiber')` |  |  | ur_print_fdm/ui/main_window.py:336 |
| ???/??/??? | 压力补偿 | ur_print_fdm/ui/main_window.py:341 `act_pressure` | triggered | `lambda: self.show_specific_calculator('pressure')` |  |  | ur_print_fdm/ui/main_window.py:341 |
| ???/??/??? | 切线跟随 | ur_print_fdm/ui/main_window.py:349 `act_tangent` | triggered | `lambda: self.show_specific_calculator('tangent')` |  |  | ur_print_fdm/ui/main_window.py:349 |
| ???/??/??? | 倾角计算 | ur_print_fdm/ui/main_window.py:354 `act_tilt` | triggered | `lambda: self.show_specific_calculator('tilt')` |  |  | ur_print_fdm/ui/main_window.py:354 |
| ???/??/??? | 曲率校验 | ur_print_fdm/ui/main_window.py:359 `act_curvature` | triggered | `lambda: self.show_specific_calculator('curvature')` |  |  | ur_print_fdm/ui/main_window.py:359 |
| ???/??/??? | 转台同步 | ur_print_fdm/ui/main_window.py:367 `act_turntable` | triggered | `lambda: self.show_specific_calculator('turntable')` |  |  | ur_print_fdm/ui/main_window.py:367 |
| ???/??/??? | 外部轴映射 | ur_print_fdm/ui/main_window.py:372 `act_external` | triggered | `lambda: self.show_specific_calculator('external')` |  |  | ur_print_fdm/ui/main_window.py:372 |
| ???/??/??? | 加热功率 | ur_print_fdm/ui/main_window.py:377 `act_heat` | triggered | `lambda: self.show_specific_calculator('heat')` |  |  | ur_print_fdm/ui/main_window.py:377 |
| ???/??/??? | 位姿偏置 | ur_print_fdm/ui/main_window.py:385 `act_offset` | triggered | `lambda: self.show_specific_calculator('offset')` |  |  | ur_print_fdm/ui/main_window.py:385 |
| ???/??/??? | TCP 转换 | ur_print_fdm/ui/main_window.py:390 `act_tcp` | triggered | `lambda: self.show_specific_calculator('tcp')` |  |  | ur_print_fdm/ui/main_window.py:390 |
| ???/??/??? | 单位转换 | ur_print_fdm/ui/main_window.py:395 `act_unit` | triggered | `lambda: self.show_specific_calculator('unit')` |  |  | ur_print_fdm/ui/main_window.py:395 |
| ???/??/??? | 样件生成库(&L)... | ur_print_fdm/ui/main_window.py:404 `act_library` | triggered | `self.show_library_panel` |  |  | ur_print_fdm/ui/main_window.py:404 |
| ???/??/??? | 平面标定(&C)... | ur_print_fdm/ui/main_window.py:410 `act_calibration` | triggered | `self.show_calibration_panel` |  |  | ur_print_fdm/ui/main_window.py:410 |
| ???/??/??? | G-code 转换... | ur_print_fdm/ui/main_window.py:420 `act_gcode` | triggered | `self.tool_gcode_convert` |  |  | ur_print_fdm/ui/main_window.py:420 |
| ???/??/??? | 脚本分割... | ur_print_fdm/ui/main_window.py:425 `act_split` | triggered | `self.tool_split_script` |  |  | ur_print_fdm/ui/main_window.py:425 |
| ???/??/??? | 插入标志... | ur_print_fdm/ui/main_window.py:430 `act_flag` | triggered | `self.tool_insert_flag` |  |  | ur_print_fdm/ui/main_window.py:430 |
| ???/??/??? | 脚本估算... | ur_print_fdm/ui/main_window.py:435 `act_estimate` | triggered | `self.tool_script_estimate` |  |  | ur_print_fdm/ui/main_window.py:435 |
| ???/??/??? | 生产队列(&Q)... | ur_print_fdm/ui/main_window.py:444 `act_queue` | triggered | `self.show_queue_panel` |  |  | ur_print_fdm/ui/main_window.py:444 |
| ???/??/??? | 设置中心 / 首选项(&P)... | ur_print_fdm/ui/main_window.py:455 `act_settings` | triggered | `self.show_settings_panel` |  |  | ur_print_fdm/ui/main_window.py:455 |
| ???/??/??? | 打开日志目录(&L) | ur_print_fdm/ui/main_window.py:460 `act_open_logs` | triggered | `self.open_logs_directory` |  |  | ur_print_fdm/ui/main_window.py:460 |
| ???/??/??? | 说明文档(&D)... | ur_print_fdm/ui/main_window.py:470 `act_help` | triggered | `self.show_help_dialog` |  |  | ur_print_fdm/ui/main_window.py:470 |
| ???/??/??? | 打印注意事项(&N)... | ur_print_fdm/ui/main_window.py:475 `act_notes` | triggered | `self.show_printing_notes_dialog` |  |  | ur_print_fdm/ui/main_window.py:475 |
| ???/??/??? | 关于(&A) | ur_print_fdm/ui/main_window.py:482 `act_about` | triggered | `self._show_about_dialog` |  |  | ur_print_fdm/ui/main_window.py:482 |
| UI/?????? | 拟合平面 & 计算 Feature | ur_print_fdm/ui/widgets/calibration.py:54 `btn_calc` | clicked | `self.do_calculate` |  |  | ur_print_fdm/ui/widgets/calibration.py:54 |
| UI/?????? | (icon-only) | ur_print_fdm/ui/widgets/styled_message_box.py:166 `btn` | clicked | `lambda: self._on_button_clicked(role)` |  |  | ur_print_fdm/ui/widgets/styled_message_box.py:166 |