"""LibreNMS MCP Server — exposes LibreNMS API operations as MCP tools (FastMCP)."""

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
from fastmcp import FastMCP

# Load .env from CWD first, then fall back to the project root (package parent)
load_dotenv()
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

mcp = FastMCP("librenms-mcp")

# Lazy-initialised client so env vars can be loaded before import
_client = None


def client():
    global _client
    if _client is None:
        from mcp_librenms.client import LibreNMSClient
        _client = LibreNMSClient()
    return _client


def _json(data) -> str:
    return json.dumps(data, indent=2, ensure_ascii=False)


# ── System ────────────────────────────────────────────────────────────────────

@mcp.tool
def ping() -> str:
    """Check LibreNMS API availability. Sends exactly 3 ping requests (not continuous)
    and reports the result of each."""
    c = client()
    results = []
    for i in range(1, 4):
        try:
            results.append({"ping": i, "status": "ok", "response": c.ping()})
        except Exception as e:
            results.append({"ping": i, "status": "fail", "error": str(e)})
    return _json({
        "pings": results,
        "success": sum(1 for r in results if r["status"] == "ok"),
        "total": len(results),
    })


@mcp.tool
def system_info() -> str:
    """Display LibreNMS instance information (version, PHP, DB, RRDtool, etc.)."""
    return _json(client().system_info())


# ── Devices ───────────────────────────────────────────────────────────────────

@mcp.tool
def list_devices(
    type: Optional[str] = None,
    os: Optional[str] = None,
    mac: Optional[str] = None,
    ipv4: Optional[str] = None,
    ipv6: Optional[str] = None,
    hostname: Optional[str] = None,
    sysName: Optional[str] = None,
    location: Optional[str] = None,
    status: Optional[int] = None,
) -> str:
    """List all devices monitored by LibreNMS.

    Optional filters: type (router/switch/etc.), os, mac, ipv4, ipv6, hostname,
    sysName, location, status (0=down, 1=up).
    """
    params = {
        "type": type, "os": os, "mac": mac, "ipv4": ipv4, "ipv6": ipv6,
        "hostname": hostname, "sysName": sysName, "location": location,
        "status": status,
    }
    return _json(client().list_devices(**{k: v for k, v in params.items() if v is not None}))


@mcp.tool
def get_device(hostname: str) -> str:
    """Get detailed information about a specific device by hostname or device ID."""
    return _json(client().get_device(hostname))


@mcp.tool
def add_device(
    hostname: str,
    snmpver: Optional[str] = None,
    community: Optional[str] = None,
    port: Optional[int] = None,
    transport: Optional[str] = None,
    authlevel: Optional[str] = None,
    authname: Optional[str] = None,
    authpass: Optional[str] = None,
    authalgo: Optional[str] = None,
    cryptopass: Optional[str] = None,
    cryptoalgo: Optional[str] = None,
    force_add: Optional[bool] = None,
) -> str:
    """Add a new device to LibreNMS monitoring.

    Required: hostname. Common optional fields: snmpver (v1/v2c/v3), community
    (SNMPv1/v2c), authlevel, authname, authpass, authalgo, cryptopass, cryptoalgo
    (SNMPv3), port, transport (udp/tcp/udp6/tcp6), force_add.
    """
    data = {
        "hostname": hostname, "snmpver": snmpver, "community": community,
        "port": port, "transport": transport, "authlevel": authlevel,
        "authname": authname, "authpass": authpass, "authalgo": authalgo,
        "cryptopass": cryptopass, "cryptoalgo": cryptoalgo, "force_add": force_add,
    }
    return _json(client().add_device({k: v for k, v in data.items() if v is not None}))


@mcp.tool
def delete_device(hostname: str) -> str:
    """Remove a device from LibreNMS monitoring."""
    return _json(client().delete_device(hostname))


@mcp.tool
def update_device_field(hostname: str, field: str, data: dict) -> str:
    """Update a field on a device (e.g. location, notes, ignore, disable, etc.)."""
    return _json(client().update_device_field(hostname, field, data))


@mcp.tool
def rename_device(hostname: str, new_hostname: str) -> str:
    """Rename a device to a new hostname."""
    return _json(client().rename_device(hostname, new_hostname))


@mcp.tool
def discover_device(hostname: str) -> str:
    """Trigger immediate SNMP discovery for a device."""
    return _json(client().discover_device(hostname))


@mcp.tool
def get_device_ports(hostname: str, columns: Optional[str] = None) -> str:
    """List all network ports/interfaces for a device.

    Optional: columns — comma-separated column names to return.
    """
    params = {"columns": columns} if columns else {}
    return _json(client().get_device_ports(hostname, **params))


@mcp.tool
def get_device_ip_addresses(hostname: str) -> str:
    """Get all IP addresses (v4 and v6) assigned to a device."""
    return _json(client().get_device_ip_addresses(hostname))


@mcp.tool
def get_device_availability(hostname: str) -> str:
    """Get uptime/availability statistics for a device."""
    return _json(client().get_device_availability(hostname))


@mcp.tool
def get_device_outages(hostname: str) -> str:
    """Get outage history for a device."""
    return _json(client().get_device_outages(hostname))


@mcp.tool
def get_device_groups(hostname: str) -> str:
    """List device groups that a specific device belongs to."""
    return _json(client().get_device_groups(hostname))


@mcp.tool
def get_device_components(hostname: str) -> str:
    """List hardware/software components discovered on a device."""
    return _json(client().get_device_components(hostname))


@mcp.tool
def get_device_graphs(hostname: str) -> str:
    """List available graphs for a device."""
    return _json(client().get_device_graphs(hostname))


@mcp.tool
def get_device_maintenance(hostname: str) -> str:
    """Get current maintenance schedule status for a device."""
    return _json(client().get_device_maintenance(hostname))


@mcp.tool
def set_device_maintenance(
    hostname: str,
    duration: str,
    title: Optional[str] = None,
    notes: Optional[str] = None,
    start: Optional[str] = None,
) -> str:
    """Put a device into maintenance mode.

    Required: duration (format H:i e.g. '02:00').
    Optional: title, notes, start (format 'Y-m-d H:i:00').
    """
    data = {"duration": duration}
    for key, value in (("title", title), ("notes", notes), ("start", start)):
        if value is not None:
            data[key] = value
    return _json(client().set_device_maintenance(hostname, data))


@mcp.tool
def add_device_eventlog(hostname: str, text: str, severity: str = "2") -> str:
    """Add a custom event log entry for a device.

    Severity: 1=ok, 2=info, 3=notice, 4=warning, 5=error.
    """
    return _json(client().add_device_eventlog(hostname, text, severity))


# ── Alerts ────────────────────────────────────────────────────────────────────

@mcp.tool
def list_alerts(
    state: Optional[int] = None,
    severity: Optional[str] = None,
    alert_rule_id: Optional[int] = None,
) -> str:
    """List all alerts.

    Optional filters: state (0=ok, 1=alert, 2=acknowledged),
    severity (ok/warning/critical), alert_rule_id.
    """
    params = {
        "state": state, "severity": severity, "alert_rule_id": alert_rule_id,
    }
    return _json(client().list_alerts(**{k: v for k, v in params.items() if v is not None}))


@mcp.tool
def get_alert(alert_id: int) -> str:
    """Get details for a specific alert by ID."""
    return _json(client().get_alert(alert_id))


@mcp.tool
def ack_alert(alert_id: int) -> str:
    """Acknowledge an active alert to suppress further notifications."""
    return _json(client().ack_alert(alert_id))


@mcp.tool
def unmute_alert(alert_id: int) -> str:
    """Unmute a muted/acknowledged alert so it can fire again."""
    return _json(client().unmute_alert(alert_id))


@mcp.tool
def list_alert_rules() -> str:
    """List all configured alert rules."""
    return _json(client().list_alert_rules())


@mcp.tool
def get_alert_rule(rule_id: int) -> str:
    """Get details for a specific alert rule by ID."""
    return _json(client().get_alert_rule(rule_id))


@mcp.tool
def delete_alert_rule(rule_id: int) -> str:
    """Delete an alert rule by ID."""
    return _json(client().delete_alert_rule(rule_id))


# ── Ports ─────────────────────────────────────────────────────────────────────

@mcp.tool
def get_all_ports(columns: Optional[str] = None) -> str:
    """Get info for all ports across all devices.

    Use 'columns' to limit returned fields, e.g. 'ifName,port_id,device_id'.
    """
    return _json(client().get_all_ports(columns))


@mcp.tool
def search_ports(field: str, search: str, columns: Optional[str] = None) -> str:
    """Search for ports matching a string across specified fields.

    field: comma-separated field(s) to search, e.g. 'ifAlias,ifDescr,ifName'.
    """
    return _json(client().search_ports(field, search, columns))


@mcp.tool
def get_port_info(port_id: int) -> str:
    """Get all information for a specific port by port ID."""
    return _json(client().get_port_info(port_id))


@mcp.tool
def get_port_ip_info(port_id: int) -> str:
    """Get all IP addresses (v4 and v6) for a specific port by port ID."""
    return _json(client().get_port_ip_info(port_id))


@mcp.tool
def ports_with_mac(mac: str) -> str:
    """Find ports associated with a specific MAC address (various formats accepted)."""
    return _json(client().ports_with_mac(mac))


@mcp.tool
def update_port_description(port_id: int, description: str) -> str:
    """Update the ifAlias/description for a port. Send empty string to reset to default."""
    return _json(client().update_port_description(port_id, description))


# ── Logs ──────────────────────────────────────────────────────────────────────

@mcp.tool
def list_eventlog(
    hostname: Optional[str] = None,
    start: Optional[int] = None,
    limit: Optional[int] = None,
    from_: Optional[str] = None,
    to: Optional[str] = None,
    sortorder: Optional[str] = None,
) -> str:
    """List event log entries.

    Optional: hostname to filter by device. Params: start (page), limit,
    from_ (start datetime or event_id), to, sortorder (ASC/DESC).
    """
    params = {
        "start": start, "limit": limit, "from": from_, "to": to,
        "sortorder": sortorder,
    }
    return _json(client().list_eventlog(hostname, **{k: v for k, v in params.items() if v is not None}))


@mcp.tool
def list_syslog(
    hostname: Optional[str] = None,
    start: Optional[int] = None,
    limit: Optional[int] = None,
    from_: Optional[str] = None,
    to: Optional[str] = None,
    sortorder: Optional[str] = None,
) -> str:
    """List syslog entries.

    Optional: hostname to filter by device. Supports same params as list_eventlog.
    """
    params = {
        "start": start, "limit": limit, "from": from_, "to": to,
        "sortorder": sortorder,
    }
    return _json(client().list_syslog(hostname, **{k: v for k, v in params.items() if v is not None}))


@mcp.tool
def list_alertlog(
    hostname: Optional[str] = None,
    start: Optional[int] = None,
    limit: Optional[int] = None,
    from_: Optional[str] = None,
    to: Optional[str] = None,
) -> str:
    """List alert log entries. Optional: hostname to filter by device."""
    params = {"start": start, "limit": limit, "from": from_, "to": to}
    return _json(client().list_alertlog(hostname, **{k: v for k, v in params.items() if v is not None}))


@mcp.tool
def list_authlog(start: Optional[int] = None, limit: Optional[int] = None) -> str:
    """List authentication log entries."""
    params = {"start": start, "limit": limit}
    return _json(client().list_authlog(**{k: v for k, v in params.items() if v is not None}))


# ── Locations ─────────────────────────────────────────────────────────────────

@mcp.tool
def list_locations() -> str:
    """List all configured locations with coordinates."""
    return _json(client().list_locations())


@mcp.tool
def get_location(location: str) -> str:
    """Get details for a specific location by name or ID."""
    return _json(client().get_location(location))


@mcp.tool
def add_location(
    location: str,
    lat: Optional[str] = None,
    lng: Optional[str] = None,
    fixed_coordinates: Optional[int] = None,
) -> str:
    """Add a new location with coordinates.

    fixed_coordinates: 1=fixed, 0=auto-update from device.
    """
    data = {
        "location": location, "lat": lat, "lng": lng,
        "fixed_coordinates": fixed_coordinates,
    }
    return _json(client().add_location({k: v for k, v in data.items() if v is not None}))


@mcp.tool
def delete_location(location: str) -> str:
    """Delete a location by name or ID."""
    return _json(client().delete_location(location))


@mcp.tool
def edit_location(
    location: str,
    lat: Optional[str] = None,
    lng: Optional[str] = None,
) -> str:
    """Edit a location's coordinates."""
    data = {"lat": lat, "lng": lng}
    return _json(client().edit_location(location, {k: v for k, v in data.items() if v is not None}))


# ── Sensors ───────────────────────────────────────────────────────────────────

@mcp.tool
def list_sensors() -> str:
    """List all sensors discovered across all devices (temperature, humidity, voltage, etc.)."""
    return _json(client().list_sensors())


# ── Device Groups ─────────────────────────────────────────────────────────────

@mcp.tool
def list_devicegroups() -> str:
    """List all device groups."""
    return _json(client().list_devicegroups())


@mcp.tool
def get_devicegroup(name: str) -> str:
    """Get devices belonging to a specific device group."""
    return _json(client().get_devicegroup(name))


# ── ARP ───────────────────────────────────────────────────────────────────────

@mcp.tool
def list_arp(query: str, device: Optional[str] = None) -> str:
    """Look up ARP table entries by IP address, MAC address or CIDR range.

    Optional: device to filter by device hostname.
    """
    params = {"device": device} if device else {}
    return _json(client().list_arp(query, **params))


# ── Services ──────────────────────────────────────────────────────────────────

@mcp.tool
def list_services(hostname: Optional[str] = None) -> str:
    """List Nagios-compatible service checks. Optional: filter by device hostname."""
    return _json(client().list_services(hostname))


# ── Inventory ─────────────────────────────────────────────────────────────────

@mcp.tool
def get_inventory(hostname: str, entPhysicalClass: Optional[str] = None) -> str:
    """Get hardware inventory (modules, cards, chassis) for a device.

    Optional: entPhysicalClass to filter by physical class.
    """
    params = {"entPhysicalClass": entPhysicalClass} if entPhysicalClass else {}
    return _json(client().get_inventory(hostname, **params))


def _spawn_daemon(args: argparse.Namespace) -> None:
    """Re-launch this server as a detached background process."""
    cmd = [sys.executable, "-m", "mcp_librenms",
           "--host", args.host, "--port", str(args.port)]
    kwargs = dict(
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        stdin=subprocess.DEVNULL,
        cwd=str(Path(__file__).resolve().parent.parent),
    )
    if os.name == "nt":
        # DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP
        kwargs["creationflags"] = 0x00000008 | 0x00000200
    else:
        kwargs["start_new_session"] = True
    proc = subprocess.Popen(cmd, **kwargs)
    print(f"mcp-librenms started in background (PID {proc.pid})")
    print(f"Endpoint: http://{args.host}:{args.port}/mcp")


def run():
    """Console-script entry point.

    Default: HTTP transport on 0.0.0.0:5757 (endpoint http://<ip>:5757/mcp).
    Options: --daemon (background), --host, --port, --stdio.
    """
    parser = argparse.ArgumentParser(description="LibreNMS MCP server (FastMCP)")
    parser.add_argument("--daemon", action="store_true",
                        help="run in background (detached process)")
    parser.add_argument("--host", default="0.0.0.0",
                        help="bind address (default: 0.0.0.0)")
    parser.add_argument("--port", type=int, default=5757,
                        help="bind port (default: 5757)")
    parser.add_argument("--stdio", action="store_true",
                        help="use stdio transport instead of HTTP")
    args = parser.parse_args()

    if args.daemon:
        _spawn_daemon(args)
        return

    if args.stdio:
        mcp.run(transport="stdio")
    else:
        mcp.run(transport="http", host=args.host, port=args.port)


if __name__ == "__main__":
    run()