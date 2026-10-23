"""LibreNMS API HTTP client."""

import httpx
from typing import Any, Optional


class LibreNMSClient:
    def __init__(self, base_url: str, token: str):
        if not base_url or not token:
            raise ValueError(
                "LibreNMS base_url and token are required "
                "(set them in the config file, see config.example.yaml)"
            )
        self.base_url = base_url.rstrip("/")
        self.token = token
        self.api_base = f"{self.base_url}/api/v0"
        self.headers = {"X-Auth-Token": self.token, "Content-Type": "application/json"}

    def _get(self, path: str, params: Optional[dict] = None) -> dict:
        url = f"{self.api_base}{path}"
        with httpx.Client(verify=False, timeout=30) as client:
            resp = client.get(url, headers=self.headers, params=params)
            resp.raise_for_status()
            return resp.json()

    def _post(self, path: str, data: Optional[dict] = None) -> dict:
        url = f"{self.api_base}{path}"
        with httpx.Client(verify=False, timeout=30) as client:
            resp = client.post(url, headers=self.headers, json=data or {})
            resp.raise_for_status()
            return resp.json()

    def _put(self, path: str, data: Optional[dict] = None) -> dict:
        url = f"{self.api_base}{path}"
        with httpx.Client(verify=False, timeout=30) as client:
            resp = client.put(url, headers=self.headers, json=data or {})
            resp.raise_for_status()
            return resp.json()

    def _patch(self, path: str, data: Optional[dict] = None) -> dict:
        url = f"{self.api_base}{path}"
        with httpx.Client(verify=False, timeout=30) as client:
            resp = client.patch(url, headers=self.headers, json=data or {})
            resp.raise_for_status()
            return resp.json()

    def _delete(self, path: str) -> dict:
        url = f"{self.api_base}{path}"
        with httpx.Client(verify=False, timeout=30) as client:
            resp = client.delete(url, headers=self.headers)
            resp.raise_for_status()
            return resp.json()

    # ── System ────────────────────────────────────────────────────────────────
    def ping(self) -> dict:
        return self._get("/ping")

    def system_info(self) -> dict:
        return self._get("/system")

    # ── Devices ───────────────────────────────────────────────────────────────
    def list_devices(self, **params) -> dict:
        return self._get("/devices", params=params or None)

    def get_device(self, hostname: str) -> dict:
        return self._get(f"/devices/{hostname}")

    def discover_device(self, hostname: str) -> dict:
        return self._get(f"/devices/{hostname}/discover")

    def get_device_ports(self, hostname: str, **params) -> dict:
        return self._get(f"/devices/{hostname}/ports", params=params or None)

    def get_device_ip_addresses(self, hostname: str) -> dict:
        return self._get(f"/devices/{hostname}/ip")

    def get_device_availability(self, hostname: str) -> dict:
        return self._get(f"/devices/{hostname}/availability")

    def get_device_outages(self, hostname: str) -> dict:
        return self._get(f"/devices/{hostname}/outages")

    def get_device_groups(self, hostname: str) -> dict:
        return self._get(f"/devices/{hostname}/groups")

    def get_device_graphs(self, hostname: str) -> dict:
        return self._get(f"/devices/{hostname}/graphs")

    def get_device_components(self, hostname: str) -> dict:
        return self._get(f"/devices/{hostname}/components")

    def get_device_maintenance(self, hostname: str) -> dict:
        return self._get(f"/devices/{hostname}/maintenance")

    def add_device_eventlog(self, hostname: str, text: str, severity: str = "2") -> dict:
        return self._post(f"/devices/{hostname}/eventlog", {"text": text, "severity": severity})

    # ── Alerts ────────────────────────────────────────────────────────────────
    def list_alerts(self, **params) -> dict:
        return self._get("/alerts", params=params or None)

    def get_alert(self, alert_id: int) -> dict:
        return self._get(f"/alerts/{alert_id}")

    def ack_alert(self, alert_id: int) -> dict:
        return self._put(f"/alerts/{alert_id}")

    def unmute_alert(self, alert_id: int) -> dict:
        return self._put(f"/alerts/unmute/{alert_id}")

    def list_alert_rules(self) -> dict:
        return self._get("/rules")

    def get_alert_rule(self, rule_id: int) -> dict:
        return self._get(f"/rules/{rule_id}")

    # ── Ports ─────────────────────────────────────────────────────────────────
    def get_all_ports(self, columns: Optional[str] = None) -> dict:
        params = {"columns": columns} if columns else None
        return self._get("/ports", params=params)

    def search_ports(self, field: str, search: str, columns: Optional[str] = None) -> dict:
        params = {"columns": columns} if columns else None
        return self._get(f"/ports/search/{field}/{search}", params=params)

    def get_port_info(self, port_id: int) -> dict:
        return self._get(f"/ports/{port_id}")

    def get_port_ip_info(self, port_id: int) -> dict:
        return self._get(f"/ports/{port_id}/ip")

    def ports_with_mac(self, mac: str) -> dict:
        return self._get(f"/ports/mac/{mac}")

    def update_port_description(self, port_id: int, description: str) -> dict:
        return self._patch(f"/ports/{port_id}/description", {"description": description})

    # ── Logs ──────────────────────────────────────────────────────────────────
    def list_eventlog(self, hostname: Optional[str] = None, **params) -> dict:
        path = f"/logs/eventlog/{hostname}" if hostname else "/logs/eventlog"
        return self._get(path, params=params or None)

    def list_syslog(self, hostname: Optional[str] = None, **params) -> dict:
        path = f"/logs/syslog/{hostname}" if hostname else "/logs/syslog"
        return self._get(path, params=params or None)

    def list_alertlog(self, hostname: Optional[str] = None, **params) -> dict:
        path = f"/logs/alertlog/{hostname}" if hostname else "/logs/alertlog"
        return self._get(path, params=params or None)

    def list_authlog(self, **params) -> dict:
        return self._get("/logs/authlog", params=params or None)

    # ── Locations ─────────────────────────────────────────────────────────────
    def list_locations(self) -> dict:
        return self._get("/resources/locations")

    def get_location(self, location: str) -> dict:
        return self._get(f"/location/{location}")

    # ── Sensors ───────────────────────────────────────────────────────────────
    def list_sensors(self) -> dict:
        return self._get("/resources/sensors")

    # ── Device Groups ─────────────────────────────────────────────────────────
    def list_devicegroups(self) -> dict:
        return self._get("/devicegroups")

    def get_devicegroup(self, name: str) -> dict:
        return self._get(f"/devicegroups/{name}")

    # ── ARP ───────────────────────────────────────────────────────────────────
    def list_arp(self, query: str, **params) -> dict:
        return self._get(f"/resources/ip/arp/{query}", params=params or None)

    # ── Services ──────────────────────────────────────────────────────────────
    def list_services(self, hostname: Optional[str] = None) -> dict:
        if hostname:
            return self._get(f"/services/{hostname}")
        return self._get("/services")

    # ── Inventory ─────────────────────────────────────────────────────────────
    def get_inventory(self, hostname: str, **params) -> dict:
        return self._get(f"/inventory/{hostname}", params=params or None)

    # ── Routing ─────────────────────────────────────────────────────────────
    def list_bgp(self) -> dict:
        return self._get("/bgp")

    def get_bgp(self, peer_id: int) -> dict:
        return self._get(f"/bgp/{peer_id}")

    def list_ospf(self) -> dict:
        return self._get("/ospf")

    def list_ospf_ports(self) -> dict:
        return self._get("/ospf_ports")

    def list_ospfv3(self) -> dict:
        return self._get("/ospfv3")

    def list_ospfv3_ports(self) -> dict:
        return self._get("/ospfv3_ports")

    # ── Health / VLAN / MAC ─────────────────────────────────────────────────
    def get_device_health(self, hostname: str) -> dict:
        return self._get(f"/devices/{hostname}/health")

    def list_vlans(self) -> dict:
        return self._get("/resources/vlans")

    def get_device_vlans(self, hostname: str) -> dict:
        return self._get(f"/devices/{hostname}/vlans")

    def list_mac(self, hostname: str) -> dict:
        return self._get(f"/devices/{hostname}/fdb")

    def get_mac(self, mac: str) -> dict:
        return self._get(f"/resources/fdb/{mac}")

    def search_mac(self, mac: str) -> dict:
        return self._get(f"/resources/fdb/{mac}/detail")
