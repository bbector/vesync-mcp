"""vesync-mcp — a Model Context Protocol server for VeSync body scales.

Reads your recent weigh-ins from the VeSync cloud and exposes them to any MCP
client (Claude Desktop, etc.). Unofficial; not affiliated with VeSync/Etekcity.
"""
from .client import VeSyncClient, VeSyncError, TokenExpired

__version__ = "0.1.0"
__all__ = ["VeSyncClient", "VeSyncError", "TokenExpired", "__version__"]
