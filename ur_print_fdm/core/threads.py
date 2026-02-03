"""
Legacy compatibility module.

Qt worker threads were migrated to `ui.workers.threads` so that the `core` layer
can be gradually decoupled from PyQt.
"""

from ur_print_fdm.ui.workers.threads import (  # noqa: F401
    ConnectionThread,
    ControlReconnectThread,
    DashboardCmdThread,
    MonitorThread,
    ProgramManagementThread,
    ScriptSendThread,
    SFTPUploadThread,
    StopThread,
)

__all__ = [
    "ScriptSendThread",
    "StopThread",
    "ConnectionThread",
    "MonitorThread",
    "ControlReconnectThread",
    "DashboardCmdThread",
    "SFTPUploadThread",
    "ProgramManagementThread",
]
