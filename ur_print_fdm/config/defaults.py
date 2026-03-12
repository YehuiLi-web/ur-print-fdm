from ur_print_fdm.config.robot_targets import robot_target_defaults


DEFAULTS: dict = {
    "robot": {
        "ip_addresses": ["192.168.1.106"],
        "default_ip": "192.168.1.106",
        "backend_id": "ur_rtde_cb3",
        "dashboard": {
            "loader_urp_path": "/home/ur/ursim-current/programs/loader.urp",
            "remote_loader_name": "remote_loader.script",
        },
        "sftp": {
            "port": 22,
            "username": "ur",
            "password": "easybot",
            "remote_dir": "/home/ur/ursim-current/programs",
        },
        "targets": robot_target_defaults(),
    },
    "printing": {
        "extruder_io_pin": 0,
        "default_filament_diameter": 1.75,
        "default_base_register": 4000,
        "default_line_width": 1.0,
        "default_layer_height": 0.5,
        "default_print_speed": 5.0,
        "modbus_extruder": "MODBUS_1",
        "modbus_turntable_pin": "pin",
        "modbus_turntable_bu": "bu",
    },
    "safety": {
        "watchdog_timeout": 120.0,
        "watchdog_speed_threshold": 0.002,
    },
    "production": {
        # Maximum runtime in seconds. 0 means no timeout.
        "max_program_timeout": 0,
    },
    "project": {
        "last_project_path": "",
        "confirm_deletion": True,
    },
    "ui": {
        "window_size": [1400, 900],
        "dark_theme": True,
        # When enabled, estimate URScript time/material once when starting a run.
        # Disabled by default to avoid unexpected overhead/UI changes.
        "urscript_estimate_on_run": False,
        # "production" = SFTP + loader.urp + Dashboard (CB3 recommended)
        # "direct"      = RTDE send script (no reliable pause/resume)
        "run_mode": "production",
        "auto_scroll_log": True,
        "log_max_lines": 2000,
        "status_dock": {
            "collapsed": False,
            "expanded_width": 236,
        },
        "panels": {
            "joint_panel_collapsed": False,
            "tcp_panel_collapsed": False,
            "offset_panel_collapsed": False,
            "stats_panel_collapsed": False,
            "motion_panel_collapsed": False,
            "extrusion_panel_collapsed": False,
        },
    },
    "logging": {
        # File logging
        "level": "INFO",
        "retention_days": 14,
        # Optional override. When empty, uses `~/.ur_print_fdm/logs`.
        "dir": "",

        # UI log viewer behavior
        "ui_level": "INFO",
        "ui_show_third_party": False,
    },
    "printing_notes": {
        "data": None,
    },
}
