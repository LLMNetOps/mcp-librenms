# mcp-librenms

MCP (Model Context Protocol) server that exposes the [LibreNMS](https://www.librenms.org/) REST API as MCP tools. Built with [FastMCP](https://github.com/jlowin/fastmcp). Connect AI assistants (Claude Desktop, GitHub Copilot, etc.) to your LibreNMS instance to query monitored devices, ports, alerts, logs, routing, and more. All tools are **read-only** — they never add, modify, or delete anything in LibreNMS.

## Features

~51 read-only tools covering:

| Category | Tools |
|---|---|
| **System** | `ping`, `system_info` |
| **Devices** | `list_devices`, `get_device`, `discover_device`, `get_device_ports`, `get_device_ip_addresses`, `get_device_availability`, `get_device_outages`, `get_device_groups`, `get_device_components`, `get_device_graphs`, `get_device_maintenance` |
| **Alerts** | `list_alerts`, `get_alert`, `list_alert_rules`, `get_alert_rule` |
| **Ports** | `get_all_ports`, `search_ports`, `get_port_info`, `get_port_ip_info`, `ports_with_mac` |
| **Logs** | `list_eventlog`, `list_syslog`, `list_alertlog`, `list_authlog` |
| **Locations** | `list_locations`, `get_location` |
| **Sensors** | `list_sensors` |
| **Device groups** | `list_devicegroups`, `get_devicegroup` |
| **ARP** | `list_arp` |
| **Services** | `list_services` |
| **Inventory** | `get_inventory` |
| **Routing** | `get_routing_table`, `list_bgp_peers`, `get_bgp_peer`, `list_bgp_prefix_counters`, `list_ospf_neighbors`, `list_ospf_ports`, `list_ospfv3_neighbors`, `list_ospfv3_ports` |
| **Health / VLAN / MAC** | `get_device_health`, `list_vlans`, `get_device_vlans`, `list_mac`, `get_mac`, `search_mac` |
| **Lookup / BGP / Report** | `lookup_device`, `bgp_session`, `device_report` |

## Requirements

- Python 3.9+
- A LibreNMS instance with API access
- An API token (LibreNMS web UI: **Settings > API > API Settings**)

## Setup

```bash
# 1. Create and activate a virtual environment
python -m venv .venv
.venv\Scripts\activate        # Windows
source .venv/bin/activate     # Linux/macOS

# 2. Install the package (editable)
pip install -e .

# 3. Configure
copy config.example.yaml config.yaml   # Windows
# cp config.example.yaml config.yaml   # Linux/macOS
# then edit config.yaml with your LibreNMS URL and API token

Or
# from a local clone of this repository
pipx install mcp-librenms

Or
# or straight from GitHub (replace <your-username>)
pipx install "git+https://github.com/LLMNetOps/mcp-librenms.git"
```

### Configuration

`config.yaml` (gitignored — never commit it):

```yaml
librenms:
  url: "http://your-librenms-host"   # base URL, no trailing slash
  token: "your-api-token"            # LibreNMS web UI: Settings > API > API Settings
```

## Running

The server speaks MCP over **streamable HTTP** by default, bound to `0.0.0.0:5757`:

```bash
# Console script (foreground)
mcp-librenms --config config.yaml

# Or as a module
python -m mcp_librenms --config config.yaml
```

Endpoint: **http://\<IP\>:5757/mcp**

### Options

| Flag | Default | Description |
|---|---|---|
| `--config FILE` | `config.yaml` | Path to YAML config file (CWD, then project root) |
| `--host IP` | `0.0.0.0` | Bind address |
| `--port PORT` | `5757` | Bind port |
| `--daemon` | off | Run in background (detached process) |
| `--stdio` | off | Use stdio transport instead of HTTP |

Examples:

```bash
# Background on a custom address/port
mcp-librenms --config config.yaml --daemon --host 192.168.1.10 --port 8080
# → http://192.168.1.10:8080/mcp

# stdio transport (for MCP clients that spawn the server)
mcp-librenms --config config.yaml --stdio
```

### MCP client configuration

Example for any MCP client that supports streamable HTTP servers:

```json
{
  "mcpServers": {
    "librenms": {
      "url": "http://your-librenms-host:5757/mcp"
    }
  }
}
```

For stdio-based clients (Claude Desktop, etc.), spawn the server with `--stdio` and point `--config` at your config file:

```json
{
  "mcpServers": {
    "librenms": {
      "command": "D:\\path\\to\\.venv\\Scripts\\mcp-librenms.exe",
      "args": ["--config", "D:\\path\\to\\mcp-librenms\\config.yaml", "--stdio"]
    }
  }
}
```

> **Note:** the client uses `verify=False` for TLS, so it works with LibreNMS instances behind self-signed certificates.

## Project structure

```
mcp-librenms/
├── config.example.yaml   # Template for local configuration
├── config.yaml           # Your local configuration (gitignored)
├── .gitignore
├── README.md
├── pyproject.toml        # Package metadata + console script
├── requirements.txt      # Flat dependency list
└── mcp_librenms/
    ├── __init__.py
    ├── __main__.py       # python -m mcp_librenms
    ├── client.py         # LibreNMS REST API HTTP client
    └── server.py         # MCP server + tool definitions
```

## License

MIT
