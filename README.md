# vesync-mcp

A small [Model Context Protocol](https://modelcontextprotocol.io) (MCP) server that reads your
**VeSync / Etekcity smart-scale weigh-ins from the cloud** and exposes them to any MCP client
(Claude Desktop, etc.). Ask your assistant *"what's my recent weight?"* and it pulls your
weigh-ins straight from your VeSync account.

> **Unofficial.** Not affiliated with, endorsed by, or supported by VeSync or Etekcity. It uses
> the same private cloud endpoints the official app uses. Use it with your own account, at your
> own risk. Endpoints may change at any time.

## Why

The VeSync app is a thin client: your body-scale history lives in VeSync's cloud, not on the
scale. This server talks to the app's **`/cloud/` endpoints**, which (unlike the newer `/api/`
ones) don't require a request signature — a plain authenticated request with your login token is
enough. The `terminalId` the server expects is read from the token itself (it's a JWT).

## Features

- `get_recent_weight` — recent weigh-ins (date, weight, raw impedance) + your weight goal, plus an
  *estimated* body-fat % (see note below).
- `list_devices` — devices on your account (to find a scale's `config_module`).
- `get_weight_history` — full stored history for a scale (includes body-fat %, BMI, muscle, water,
  bone mass when available).
- Login once; only the **token** is stored locally, never your password.

## Requirements

- Python 3.10+
- A VeSync account with a body scale (tested with an Etekcity ESF24).

## Install

```bash
pip install .
# or, for development:
pip install -e .
# or just the deps:
pip install -r requirements.txt
```

## Authenticate (once)

```bash
vesync-mcp login          # prompts for email + password
# or: python -m vesync_mcp login
```

Your password is used only to obtain a token and is **not** stored. The token is written to
`~/.vesync-mcp/credentials.json` (override with the `VESYNC_MCP_CREDENTIALS` environment variable).
VeSync tokens last roughly a month; when it expires, just run `login` again.

> VeSync occasionally rate-limits logins behind Cloudflare. If a login fails despite correct
> credentials, wait a bit and retry.

Check it works:

```bash
vesync-mcp test
```

## Use with Claude Desktop

Add the server to your `claude_desktop_config.json` (see
[`examples/claude_desktop_config.json`](examples/claude_desktop_config.json)):

```json
{
  "mcpServers": {
    "vesync": {
      "command": "vesync-mcp",
      "args": []
    }
  }
}
```

If `vesync-mcp` isn't on your PATH, use the full Python path instead:

```json
{
  "mcpServers": {
    "vesync": {
      "command": "/full/path/to/python",
      "args": ["-m", "vesync_mcp"]
    }
  }
}
```

Restart Claude Desktop, then ask: *"What are my recent weigh-ins?"*

## Tools

| Tool | Returns |
|------|---------|
| `get_recent_weight` | recent weigh-ins + goal + estimated body-fat % |
| `list_devices` | devices on the account (find a scale's `config_module`) |
| `get_weight_history` | full stored weigh-in history for a given `config_module` |

## Note on body fat

`get_recent_weight` returns the scale's **raw impedance** but not the body-fat percentage — the app
computes that on-device with a proprietary formula, and this cloud endpoint doesn't expose it. The
`estimated_body_fat_pct` field is a rough estimate from the Deurenberg equation (BMI + age + sex);
it won't match the app exactly. `get_weight_history` does include the stored body-fat % when the
scale recorded it. The gender→sex mapping used for the estimate is documented in
[`vesync_mcp/bodyfat.py`](vesync_mcp/bodyfat.py) — verify it against your profile.

## Library use

```python
from vesync_mcp import VeSyncClient
client = VeSyncClient.from_file("~/.vesync-mcp/credentials.json")
print(client.recent_weight())
```

## License

[MIT](LICENSE)
