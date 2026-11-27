"""Where the login token is stored.

Default: ``~/.vesync-mcp/credentials.json`` (override with the
``VESYNC_MCP_CREDENTIALS`` environment variable). The file holds only the token
and account id returned by the login — never your password.
"""
import os


def credentials_path() -> str:
    env = os.environ.get("VESYNC_MCP_CREDENTIALS")
    if env:
        return os.path.abspath(os.path.expanduser(env))
    return os.path.join(os.path.expanduser("~"), ".vesync-mcp", "credentials.json")
