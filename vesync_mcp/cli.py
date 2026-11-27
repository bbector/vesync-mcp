"""Command line entry point: `vesync-mcp [login|serve|test]`.

  login   authenticate (prompts for password) and store the token
  serve   run the MCP server over stdio (this is the default)
  test    print your recent weigh-ins (handy to check the login works)
"""
from __future__ import annotations

import argparse
import getpass
import json
import sys

from .config import credentials_path


def _do_login(args) -> int:
    from .auth import login
    email = args.email or input("VeSync email: ").strip()
    password = getpass.getpass("VeSync password: ")
    if not email or not password:
        print("email and password are required", file=sys.stderr)
        return 1
    path = login(email, password, country_code=args.country,
                 time_zone=args.timezone, out_path=credentials_path())
    print(f"Logged in. Token saved to {path} (your password was not stored).")
    return 0


def _do_test(_args) -> int:
    from .client import VeSyncClient
    try:
        client = VeSyncClient.from_file(credentials_path())
    except FileNotFoundError:
        print("Not logged in. Run `vesync-mcp login` first.", file=sys.stderr)
        return 1
    data = client.recent_weight()
    if not data["weighins"]:
        print("No recent weigh-ins found.")
    for w in data["weighins"]:
        print(f"  {w['date']}   {w['weight_kg']} kg")
    if data["goal"].get("target_kg"):
        print(f"  goal: {data['goal']['target_kg']} kg")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(prog="vesync-mcp",
                                 description="VeSync body-scale MCP server")
    sub = ap.add_subparsers(dest="cmd")

    lp = sub.add_parser("login", help="authenticate and store the token")
    lp.add_argument("--email", help="VeSync account email (prompted if omitted)")
    lp.add_argument("--country", default="US", help="country code (default US)")
    lp.add_argument("--timezone", default="UTC", help="IANA time zone (default UTC)")

    sub.add_parser("serve", help="run the MCP server (default)")
    sub.add_parser("test", help="print recent weigh-ins")

    args = ap.parse_args()
    if args.cmd == "login":
        return _do_login(args)
    if args.cmd == "test":
        return _do_test(args)
    # default: serve
    from .server import run
    run()
    return 0


if __name__ == "__main__":
    sys.exit(main())
