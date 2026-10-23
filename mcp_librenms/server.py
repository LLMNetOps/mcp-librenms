"""LibreNMS MCP Server — exposes LibreNMS API operations as MCP tools (FastMCP)."""

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Optional
from datetime import datetime, timezone

import yaml
from fastmcp import FastMCP

mcp = FastMCP("librenms-mcp")

PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Lazy-initialised client so the config is loaded before the first tool call
_client = None
_config: dict = {}


def _resolve_config(path: str) -> Path:
    """Resolve a (possibly relative) config path: CWD first, then project root."""
    p = Path(path)
    if not p.is_absolute():
        cwd_candidate = Path.cwd() / p
        if cwd_candidate.exists():
            return cwd_candidate
        return PROJECT_ROOT / p
    return p


def load_config(path: str) -> dict:
    """Load and validate the YAML config file."""
    p = _resolve_config(path)
    if not p.exists():
        raise FileNotFoundError(
            f"Config file not found: {p} "
            f"(copy config.example.yaml to config.yaml and fill in your values)"
        )
    with open(p, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    lib = data.get("librenms") or {}
    url = str(lib.get("url") or "").strip()
    token = str(lib.get("token") or "").strip()
    if not url or not token:
        raise ValueError(
            f"Config file {p} must define non-empty librenms.url and librenms.token"
        )
    return {"url": url, "token": token}


def client():
    global _client
    if _client is None:
        from mcp_librenms.client import LibreNMSClient
        _client = LibreNMSClient(_config["url"], _config["token"])
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
def list_alert_rules() -> str:
    """List all configured alert rules."""
    return _json(client().list_alert_rules())


@mcp.tool
def get_alert_rule(rule_id: int) -> str:
    """Get details for a specific alert rule by ID."""
    return _json(client().get_alert_rule(rule_id))


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


# ── Routing ───────────────────────────────────────────────────────────────────

# Key fields kept per entry in the compact routing-table view.
_BGP_FIELDS = (
    "bgpPeer_id", "device_id", "bgpPeerRemoteAddr", "bgpPeerRemoteAs",
    "astext", "bgpPeerState", "bgpPeerAdminStatus", "bgpPeerIface",
    "bgpLocalAddr", "bgpPeerDescr",
)
_OSPF_NBR_FIELDS = (
    "id", "device_id", "port_id", "ospfNbrIpAddr", "ospfNbrRtrId",
    "ospfNbrState", "ospfNbmaNbrStatus",
)
_OSPF_PORT_FIELDS = (
    "id", "device_id", "port_id", "ospfIfIpAddress", "ospfIfAreaId",
    "ospfIfType", "ospfIfState", "ospfIfDesignatedRouter",
)
_OSPFV3_NBR_FIELDS = (
    "id", "device_id", "port_id", "ospfv3NbrRtrId", "ospfv3NbrAddress",
    "ospfv3NbrState",
)
_OSPFV3_PORT_FIELDS = (
    "id", "device_id", "ospfv3_area_id", "ospfv3IfAreaId", "ospfv3IfType",
    "ospfv3IfState", "ospfv3IfDesignatedRouter",
)


def _compact(items: list, fields: tuple) -> list:
    """Reduce each entry to the given key fields (missing keys become null)."""
    return [{f: item.get(f) for f in fields} for item in items]


def _routing_table(protocol: Optional[str]) -> dict:
    """Fetch and compact the routing data for the requested protocol(s)."""
    c = client()
    result: dict = {}
    want = (protocol or "all").lower()

    if want in ("all", "bgp"):
        sessions = c.list_bgp().get("bgp_sessions", [])
        result["bgp_sessions"] = _compact(sessions, _BGP_FIELDS)
    if want in ("all", "ospf"):
        nbrs = c.list_ospf().get("ospf_neighbours", [])
        ports = c.list_ospf_ports().get("ospf_ports", [])
        result["ospf_neighbours"] = _compact(nbrs, _OSPF_NBR_FIELDS)
        result["ospf_ports"] = _compact(ports, _OSPF_PORT_FIELDS)
    if want in ("all", "ospfv3"):
        nbrs = c.list_ospfv3().get("ospfv3_neighbours", [])
        ports = c.list_ospfv3_ports().get("ospfv3_ports", [])
        result["ospfv3_neighbours"] = _compact(nbrs, _OSPFV3_NBR_FIELDS)
        result["ospfv3_ports"] = _compact(ports, _OSPFV3_PORT_FIELDS)

    if not result:
        raise ValueError(
            f"Unknown protocol '{protocol}'. Use 'bgp', 'ospf', 'ospfv3' or 'all'."
        )
    return result


@mcp.tool
def get_routing_table(protocol: Optional[str] = None) -> str:
    """Get the complete routing table from LibreNMS across all monitored devices.

    Returns every BGP session/peer and OSPF/OSPFv3 neighbour and port in a
    compact form (key fields only). Optional `protocol` to limit the output to
    a single protocol: 'bgp', 'ospf', 'ospfv3' (default: all).

    Note: LibreNMS tracks routing *protocol state* (BGP/OSPF sessions and
    neighbours), not a prefix-level route list. Use the per-protocol tools
    (list_bgp_peers, list_ospf_neighbors, ...) for full field detail.
    """
    return _json(_routing_table(protocol))


@mcp.tool
def list_bgp_peers() -> str:
    """List all BGP sessions/peers across every monitored device (full detail)."""
    return _json(client().list_bgp())


@mcp.tool
def get_bgp_peer(peer_id: int) -> str:
    """Get full details for a single BGP session/peer by its bgpPeer_id."""
    return _json(client().get_bgp(peer_id))


@mcp.tool
def list_bgp_prefix_counters(hostname: Optional[str] = None) -> str:
    """List BGP prefix counters per peer (accepted/advertised/denied/suppressed/
    withdrawn, plus per-protocol deltas and admin limits).

    NOTE: LibreNMS does not expose a prefix-level routing table (RIB) via its
    REST API — this returns the BGP prefix *counters* per peer, which is the
    closest available prefix-related routing data. Use get_routing_table for
    routing protocol state (BGP/OSPF sessions and neighbours).

    Args:
        hostname: Optional device hostname to filter by.
    """
    return _json(client().list_cbgp(**{"hostname": hostname} if hostname else {}))


@mcp.tool
def list_ospf_neighbors() -> str:
    """List all OSPF (v2) neighbours across every monitored device (full detail)."""
    return _json(client().list_ospf())


@mcp.tool
def list_ospf_ports() -> str:
    """List all OSPF (v2) ports/interfaces across every monitored device (full detail)."""
    return _json(client().list_ospf_ports())


@mcp.tool
def list_ospfv3_neighbors() -> str:
    """List all OSPFv3 neighbours across every monitored device (full detail)."""
    return _json(client().list_ospfv3())


@mcp.tool
def list_ospfv3_ports() -> str:
    """List all OSPFv3 ports/interfaces across every monitored device (full detail)."""
    return _json(client().list_ospfv3_ports())


# ── Health / VLAN / MAC ───────────────────────────────────────────────────────

@mcp.tool
def get_device_health(hostname: str) -> str:
    """Get health status and available health graphs for a device.

    Returns overall status (ok/warning/critical) plus the list of health
    graphs (device state, temperature, processor, memory, current, etc.).
    """
    return _json(client().get_device_health(hostname))


@mcp.tool
def list_vlans() -> str:
    """List all VLANs across every monitored device."""
    return _json(client().list_vlans())


@mcp.tool
def get_device_vlans(hostname: str) -> str:
    """List all VLANs on a specific device."""
    return _json(client().get_device_vlans(hostname))


@mcp.tool
def list_mac(hostname: str) -> str:
    """List all MAC addresses (FDB) learned on a specific device."""
    return _json(client().list_mac(hostname))


@mcp.tool
def get_mac(mac: str) -> str:
    """Find where a specific MAC address is seen (ports/FDB entries)."""
    return _json(client().get_mac(mac))


@mcp.tool
def search_mac(mac: str) -> str:
    """Search a MAC address and return detailed location info (device, port, last seen)."""
    return _json(client().search_mac(mac))


# ── Lookup / BGP / Report ─────────────────────────────────────────────────────

@mcp.tool
def lookup_device(query: str) -> str:
    """Look up a single device by hostname or IP address.

    Returns the full device record (identity, status, uptime, OS, hardware,
    location, IP, SNMP settings, last polled, etc.). Accepts either the device
    hostname or its IPv4/IPv6 address.
    """
    c = client()
    # 1) Direct hostname lookup
    try:
        devices = c.get_device(query).get("devices") or []
        if devices:
            return _json({"query": query, "matched_by": "hostname", "device": devices[0]})
    except Exception:
        pass
    # 2) IP lookup (v4 / v6)
    for key in ("ipv4", "ipv6"):
        try:
            devices = c.list_devices(**{key: query}).get("devices") or []
        except Exception:
            continue
        if devices:
            return _json({"query": query, "matched_by": key, "device": devices[0]})
    # 3) Fallback: hostname search
    try:
        devices = c.list_devices(hostname=query).get("devices") or []
    except Exception:
        devices = []
    if devices:
        return _json({"query": query, "matched_by": "hostname-search", "device": devices[0]})
    return _json({"query": query, "matched_by": None, "device": None,
                  "message": f"No device found matching '{query}'."})


@mcp.tool
def bgp_session(hostname: Optional[str] = None) -> str:
    """List BGP sessions/peers, optionally for a single device.

    Without `hostname`, returns every BGP session across all monitored devices.
    With `hostname`, returns only the sessions on that device. Each session
    includes peer address, remote AS, state, admin status, interface, and
    in/out update counters.
    """
    params = {"hostname": hostname} if hostname else {}
    return _json(client().list_bgp(**params))


def _report_section(fetch):
    """Run one report section, returning its data or an error message."""
    try:
        return fetch()
    except Exception as exc:
        return {"error": str(exc)}


@mcp.tool
def device_report(hostname: str) -> str:
    """Build a complete read-only report for a single device.

    Aggregates the device's identity/status, health, available graphs,
    routing (BGP/OSPF/OSPFv3), ports, IP addresses, availability, outages,
    groups, components, VLANs, MAC/FDB table, services, inventory, sensors,
    and maintenance status into one structured document. Each section is
    fetched independently, so a missing or empty section does not fail the
    whole report.
    """
    c = client()
    report: dict = {
        "hostname": hostname,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }

    def _device():
        devices = c.get_device(hostname).get("devices") or []
        return devices[0] if devices else None

    report["device"] = _report_section(_device)
    device_id = report["device"].get("device_id") if isinstance(report["device"], dict) else None

    report["health"] = _report_section(lambda: c.get_device_health(hostname))
    report["graphs"] = _report_section(lambda: c.get_device_graphs(hostname))

    report["routing"] = {
        "bgp_sessions": _report_section(lambda: c.list_bgp(hostname=hostname).get("bgp_sessions", [])),
        "ospf_neighbours": _report_section(lambda: c.list_ospf(hostname=hostname).get("ospf_neighbours", [])),
        "ospf_ports": _report_section(lambda: c.list_ospf_ports(hostname=hostname).get("ospf_ports", [])),
        "ospfv3_neighbours": _report_section(lambda: c.list_ospfv3(hostname=hostname).get("ospfv3_neighbours", [])),
        "ospfv3_ports": _report_section(lambda: c.list_ospfv3_ports(hostname=hostname).get("ospfv3_ports", [])),
    }

    report["ports"] = _report_section(lambda: c.get_device_ports(hostname))
    report["ip_addresses"] = _report_section(lambda: c.get_device_ip_addresses(hostname))
    report["availability"] = _report_section(lambda: c.get_device_availability(hostname))
    report["outages"] = _report_section(lambda: c.get_device_outages(hostname))
    report["groups"] = _report_section(lambda: c.get_device_groups(hostname))
    report["components"] = _report_section(lambda: c.get_device_components(hostname))
    report["vlans"] = _report_section(lambda: c.get_device_vlans(hostname))
    report["mac_fdb"] = _report_section(lambda: c.list_mac(hostname))
    report["services"] = _report_section(lambda: c.list_services(hostname))
    report["inventory"] = _report_section(lambda: c.get_inventory(hostname))
    report["maintenance"] = _report_section(lambda: c.get_device_maintenance(hostname))

    def _sensors():
        if device_id is None:
            return []
        all_sensors = c.list_sensors().get("sensors", [])
        return [s for s in all_sensors if s.get("device_id") == device_id]

    report["sensors"] = _report_section(_sensors)

    return _json(report)


def _spawn_daemon(args: argparse.Namespace) -> None:
    """Re-launch this server as a detached background process."""
    cmd = [sys.executable, "-m", "mcp_librenms",
           "--config", str(_resolve_config(args.config)),
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
    Options: --config (YAML config), --daemon (background), --host, --port, --stdio.
    """
    parser = argparse.ArgumentParser(description="LibreNMS MCP server (FastMCP)")
    parser.add_argument("--config", default="config.yaml",
                        help="path to YAML config file (default: config.yaml)")
    parser.add_argument("--daemon", action="store_true",
                        help="run in background (detached process)")
    parser.add_argument("--host", default="0.0.0.0",
                        help="bind address (default: 0.0.0.0)")
    parser.add_argument("--port", type=int, default=5757,
                        help="bind port (default: 5757)")
    parser.add_argument("--stdio", action="store_true",
                        help="use stdio transport instead of HTTP")
    args = parser.parse_args()

    global _config
    try:
        _config = load_config(args.config)
    except (FileNotFoundError, ValueError) as e:
        parser.error(str(e))

    if args.daemon:
        _spawn_daemon(args)
        return

    if args.stdio:
        mcp.run(transport="stdio")
    else:
        mcp.run(transport="http", host=args.host, port=args.port)


if __name__ == "__main__":
    run()
