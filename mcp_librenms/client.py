"""LibreNMS API HTTP client."""

import os
import httpx
from typing import Any, Optional


class LibreNMSClient:
    def __init__(self):
        self.base_url = os.environ.get("LIBRENMS_URL", "").rstrip("/")
        self.token = os.environ.get("LIBRENMS_TOKEN", "")
        if not self.base_url or not self.token:
            raise ValueError(
                "LIBRENMS_URL and LIBRENMS_TOKEN environment variables must be set"
            )
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

    def add_device(self, data: dict) -> dict:
        return self._post("/devices", data)

    def delete_device(self, hostname: str) -> dict:
        return self._delete(f"/devices/{hostname}")

    def update_device_field(self, hostname: str, field: str, data: dict) -> dict:
        return self._patch(f"/devices/{hostname}", {"field": field, **data})

    def rename_device(self, hostname: str, new_hostname: str) -> dict:
        return self._patch(f"/devices/{hostname}/rename/{new_hostname}")

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

    def set_device_maintenance(self, hostname: str, data: dict) -> dict:
        return self._post(f"/devices/{hostname}/maintenance", data)

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

    def delete_alert_rule(self, rule_id: int) -> dict:
        return self._delete(f"/rules/{rule_id}")

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

    def add_location(self, data: dict) -> dict:
        return self._post("/locations", data)

    def delete_location(self, location: str) -> dict:
        return self._delete(f"/locations/{location}")

    def edit_location(self, location: str, data: dict) -> dict:
        return self._patch(f"/locations/{location}", data)

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
