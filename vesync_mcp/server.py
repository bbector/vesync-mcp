"""MCP server exposing VeSync body-scale data.

Tools:
  - get_recent_weight       recent weigh-ins + goal (+ estimated body fat)
  - list_devices            devices on the account (find a scale's config_module)
  - get_weight_history      full stored history for a scale (by config_module)

Run with:  python -m vesync_mcp           (or the `vesync-mcp` command)
Authenticate first with:  python -m vesync_mcp login
"""
from __future__ import annotations

import sys

from mcp.server.fastmcp import FastMCP

from .bodyfat import estimate_body_fat
from .client import TokenExpired, VeSyncClient, VeSyncError
from .config import credentials_path

mcp = FastMCP("vesync")


def _log(msg: str) -> None:
    print(f"[vesync-mcp] {msg}", file=sys.stderr, flush=True)


def _client() -> VeSyncClient:
    return VeSyncClient.from_file(credentials_path())


@mcp.tool()
def get_recent_weight() -> dict:
    """Recent weigh-ins from the VeSync body scale, read from the cloud.

    Returns each weigh-in (date, weight in kg, raw impedance, height, age) plus
    the weight goal and an ESTIMATED body-fat % (Deurenberg formula; the scale's
    own computed value is not exposed by this endpoint). If not logged in or the
    token expired, returns an ``error`` field telling you to run the login.
    """
    try:
        data = _client().recent_weight()
    except FileNotFoundError:
        return {"error": "Not logged in. Run `python -m vesync_mcp login` first."}
    except TokenExpired as e:
        return {"error": str(e)}
    except (VeSyncError, Exception) as e:  # noqa: BLE001
        return {"error": f"Failed to read VeSync: {e}"}

    for w in data["weighins"]:
        bf = estimate_body_fat(w.get("weight_kg"), w.get("height_cm"), w.get("age"), w.get("gender"))
        w["estimated_body_fat_pct"] = bf
    data["note"] = ("estimated_body_fat_pct is a Deurenberg estimate (BMI+age+sex), "
                    "not the value the scale computes.")
    return data


@mcp.tool()
def list_devices() -> dict:
    """List VeSync devices on the account (use to find a scale's config_module)."""
    try:
        return {"devices": _client().devices()}
    except FileNotFoundError:
        return {"error": "Not logged in. Run `python -m vesync_mcp login` first."}
    except Exception as e:  # noqa: BLE001
        return {"error": f"Failed to read VeSync: {e}"}


@mcp.tool()
def get_weight_history(config_module: str) -> dict:
    """Full stored weigh-in history for a scale (pass its config_module).

    Uses the getWeighingDataV2 endpoint; includes body-fat %, BMI, muscle, water
    and bone mass when the scale recorded them. Use list_devices to get the
    config_module.
    """
    try:
        return {"config_module": config_module, "weighins": _client().weight_history(config_module)}
    except FileNotFoundError:
        return {"error": "Not logged in. Run `python -m vesync_mcp login` first."}
    except Exception as e:  # noqa: BLE001
        return {"error": f"Failed to read VeSync: {e}"}


def run() -> None:
    _log("starting VeSync MCP server")
    mcp.run()
