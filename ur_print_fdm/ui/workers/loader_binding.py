from __future__ import annotations


DEFAULT_REMOTE_LOADER_NAME = "remote_loader.script"


def build_loader_binding_note(loader_urp_path: str, remote_loader_name: str) -> str:
    """Explain that Dashboard loads the URP, not the script name directly."""
    loader_path = str(loader_urp_path or "").strip() or "loader.urp"
    remote_name = str(remote_loader_name or "").strip() or DEFAULT_REMOTE_LOADER_NAME
    return (
        f"注意：Dashboard 实际加载的是 {loader_path}；"
        f"若要执行 {remote_name}，请确认该 URP 内部 Script 节点引用的也是这个文件名。"
    )
