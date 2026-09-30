# mcp-librenms

MCP (Model Context Protocol) server that exposes the [LibreNMS](https://www.librenms.org/) REST API as MCP tools. Built with [FastMCP](https://github.com/jlowin/fastmcp). Connect AI assistants (Claude Desktop, GitHub Copilot, etc.) to your LibreNMS instance to query and manage monitored devices, ports, alerts, logs, and more.

## Features

~40 tools covering:

| Category | Tools |
|---|---|
| **System** | `ping`, `system_info` |
| **Devices** | `list_devices`, `get_device`, `add_device`, `delete_device`, `update_device_field`, `rename_device`, `discover_device`, `get_device_ports`, `get_device_ip_addresses`, `get_device_availability`, `get_device_outages`, `get_device_groups`, `get_device_components`, `get_device_graphs`, `get_device_maintenance`, `set_device_maintenance`, `add_device_eventlog` |
| **Alerts** | `list_alerts`, `get_alert`, `ack_alert`, `unmute_alert`, `list_alert_rules`, `get_alert_rule`, `delete_alert_rule` |
| **Ports** | `get_all_ports`, `search_ports`, `get_port_info`, `get_port_ip_info`, `ports_with_mac`, `update_port_description` |
| **Logs** | `list_eventlog`, `list_syslog`, `list_alertlog`, `list_authlog` |
| **Locations** | `list_locations`, `get_location`, `add_location`, `delete_location`, `edit_location` |
| **Sensors** | `list_sensors` |
| **Device groups** | `list_devicegroups`, `get_devicegroup` |
| **ARP** | `list_arp` |
| **Services** | `list_services` |
| **Inventory** | `get_inventory` |

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
copy .env.example .env        # Windows
# cp .env.example .env        # Linux/macOS
# then edit .env with your LibreNMS URL and API token
```

## Running

The server speaks MCP over **stdio**:

```bash
# Console script
mcp-librenms

# Or as a module
python -m mcp_librenms
```

### MCP client configuration

Example for Claude Desktop / any MCP client that uses stdio servers:

```json
{
  "mcpServers": {
    "librenms": {
      "command": "D:\\path\\to\\.venv\\Scripts\\mcp-librenms.exe",
      "env": {
        "LIBRENMS_URL": "http://your-librenms-host",
        "LIBRENMS_TOKEN": "your-api-token"
      }
    }
  }
}
```

> **Note:** the client uses `verify=False` for TLS, so it works with LibreNMS instances behind self-signed certificates.

## Project structure

```
mcp-librenms/
├── .env.example          # Template for local configuration
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