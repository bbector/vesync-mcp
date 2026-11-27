"""Minimal VeSync cloud client for reading body-scale weigh-ins.

Talks to the same ``/cloud/`` endpoints the official VeSync app uses. These do
**not** require the request-signature header that the newer ``/api/`` endpoints
need, so a plain authenticated POST with your login token is enough.

The ``terminalId`` that the server validates is embedded in the token itself
(it is a JWT), so it is extracted from there automatically.
"""
from __future__ import annotations

import base64
import json
import time
from datetime import datetime, timezone
from typing import Any

import requests

API_BASE = "https://smartapi.vesync.com"
APP_VERSION = "VeSync 6.0.10"


def _jwt_field(token: str, field: str):
    """Return a field from the JWT payload embedded in a VeSync token."""
    i = token.find("eyJ")
    if i < 0:
        return None
    parts = token[i:].split(".")
    if len(parts) < 2:
        return None
    payload = parts[1] + "=" * (-len(parts[1]) % 4)
    try:
        return json.loads(base64.urlsafe_b64decode(payload)).get(field)
    except Exception:
        return None


class VeSyncError(RuntimeError):
    """Raised when VeSync returns a non-zero response code."""


class TokenExpired(VeSyncError):
    """Raised when the stored token is past its expiry."""


class VeSyncClient:
    """Reads weigh-ins from a VeSync account using a stored login token."""

    def __init__(self, token: str, account_id: str, time_zone: str = "UTC"):
        if not token or not account_id:
            raise ValueError("token and account_id are required")
        self.token = token
        self.account_id = account_id
        self.time_zone = time_zone
        self.terminal_id = _jwt_field(token, "terminalId")
        if not self.terminal_id:
            raise ValueError("could not read terminalId from token (is it a valid VeSync token?)")
        self._session = requests.Session()

    # -- construction ---------------------------------------------------------
    @classmethod
    def from_file(cls, path: str) -> "VeSyncClient":
        with open(path, encoding="utf-8") as f:
            d = json.load(f)
        return cls(d["token"], d["account_id"], d.get("time_zone", "UTC"))

    def token_expiry(self):
        exp = _jwt_field(self.token, "exp")
        return exp / 1000 if isinstance(exp, (int, float)) else None

    def is_expired(self) -> bool:
        exp = self.token_expiry()
        return bool(exp and exp < time.time())

    # -- low level ------------------------------------------------------------
    def _context(self, method: str) -> dict:
        return {
            "acceptLanguage": "en", "accountID": self.account_id, "appVersion": APP_VERSION,
            "clientInfo": "vesync-mcp", "clientType": "vesyncApp", "clientVersion": APP_VERSION,
            "debugMode": False, "method": method, "osInfo": "Android 11",
            "phoneBrand": "vesync-mcp", "phoneOS": "Android 11", "terminalId": self.terminal_id,
            "timeZone": self.time_zone, "token": self.token,
            "traceId": str(int(time.time() * 1000)), "userCountryCode": "US",
        }

    def _post(self, path: str, method: str, data: dict) -> dict:
        if self.is_expired():
            raise TokenExpired("The VeSync token has expired. Run `vesync-mcp login` again.")
        headers = {
            "Content-Type": "application/json; charset=UTF-8", "User-Agent": "okhttp/4.9.1",
            "tk": self.token, "accountId": self.account_id, "tz": self.time_zone,
        }
        r = self._session.post(API_BASE + path, headers=headers,
                               json={"context": self._context(method), "data": data}, timeout=30)
        r.raise_for_status()
        j = r.json()
        code = j.get("code")
        if code != 0:
            msg = j.get("msg")
            if code in (-11000022, -11001022, -11000086):  # token/session errors
                raise TokenExpired(f"VeSync session error {code}: {msg}. Run `vesync-mcp login` again.")
            raise VeSyncError(f"VeSync error {code}: {msg}")
        return j.get("result") or {}

    # -- public API -----------------------------------------------------------
    @staticmethod
    def _iso(ts):
        if not isinstance(ts, (int, float)):
            return None
        if ts > 1e12:
            ts = ts / 1000
        return datetime.fromtimestamp(ts, tz=timezone.utc).astimezone().isoformat(timespec="minutes")

    def recent_weight(self) -> dict:
        """Recent weigh-ins (the app's health-home view) plus the weight goal."""
        res = self._post("/cloud/v3/user/getHealthyHomeData", "getHealthyHomeData",
                         {"startTimestamp": None})
        weighins = []
        for w in (res.get("weekWeightList") or []) + (res.get("lastWeightList") or []):
            g = w.get("weightG")
            weighins.append({
                "date": self._iso(w.get("timestamp")), "timestamp": w.get("timestamp"),
                "weight_kg": round(g / 1000, 2) if isinstance(g, (int, float)) else None,
                "impedance": w.get("impedance"), "height_cm": w.get("heightCm"),
                "age": w.get("age"), "gender": w.get("gender"),
                "mac": w.get("macID"), "config_module": w.get("configModule"),
                "manual_input": w.get("isManualInput"),
            })
        seen, unique = set(), []
        for p in sorted(weighins, key=lambda x: x["timestamp"] or 0):
            if p["timestamp"] in seen:
                continue
            seen.add(p["timestamp"])
            unique.append(p)
        target = res.get("fitTargetInfo") or {}
        goal = {}
        if target.get("weightTargetG"):
            goal["target_kg"] = round(target["weightTargetG"] / 1000, 1)
        if target.get("initialWeightG"):
            goal["initial_kg"] = round(target["initialWeightG"] / 1000, 1)
        return {"account_id": self.account_id, "weighins": unique, "goal": goal}

    def devices(self) -> list[dict]:
        """List the devices on the account (to find a scale's config_module)."""
        res = self._post("/cloud/v1/deviceManaged/devices", "devices",
                         {"pageNo": 1, "pageSize": 100})
        out = []
        for d in res.get("list") or []:
            out.append({k: d.get(k) for k in
                        ("deviceName", "deviceType", "type", "configModule", "cid", "connectionType")})
        return out

    def weight_history(self, config_module: str, max_pages: int = 50) -> list[dict]:
        """Full stored weigh-in history for a scale (getWeighingDataV2)."""
        out: list[dict] = []
        for page in range(1, max_pages + 1):
            res = self._post("/cloud/v2/deviceManaged/getWeighingDataV2", "getWeighingDataV2",
                             {"configModule": config_module, "page": page, "pageSize": 100, "allData": True})
            batch = res.get("weightDatas") or res.get("weighingDataList") or res.get("list") or []
            if not isinstance(batch, list) or not batch:
                break
            for w in batch:
                g = w.get("weightG")
                out.append({
                    "date": self._iso(w.get("timestamp")), "timestamp": w.get("timestamp"),
                    "weight_kg": round(g / 1000, 2) if isinstance(g, (int, float)) else w.get("weightKg"),
                    "body_fat_pct": w.get("bfr"), "impedance": w.get("impedance"),
                    "bmi": w.get("bmi"), "muscle_mass": w.get("muscleMass"),
                    "body_water": w.get("bodyWater"), "bone_mass": w.get("boneMass"),
                })
            if len(batch) < 100:
                break
        out.sort(key=lambda x: x["timestamp"] or 0)
        return out
