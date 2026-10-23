"""Read-only access to the LibreNMS database.

LibreNMS collects the full prefix-level routing table from each device and
stores it in the ``route`` table, but this data is NOT exposed via the REST
API — it is only available in the web UI or by querying the database directly.
This module provides a strictly read-only way to query that data.

Only SELECT statements are ever issued. No writes are performed.
"""
from __future__ import annotations

from typing import Any, Optional

# IANA "Routing Protocol" numbers (IANAipRouteProtocol, RFC 4293). A single
# protocol can be reported under several numbers depending on device/vendor,
# so we keep both a name lookup and a name -> numbers mapping.
PROTO_NAMES = {
    0: "unassigned", 1: "rip", 2: "ospf", 3: "isis", 4: "idpr", 5: "eigrp",
    6: "bgp", 7: "rid", 8: "abr-internal", 9: "egp", 10: "bgp4", 11: "oispr",
    12: "arp", 13: "rarp", 14: "mobile", 15: "dynamic", 16: "bgpv4",
    17: "direct", 18: "application", 19: "cspf", 20: "pim", 21: "ircp",
    22: "route-reflector", 23: "bgpv4", 24: "named-pipe", 25: "traffic-based",
    26: "vsrp", 27: "unassigned", 28: "babel", 29: "bgp4", 30: "pbr",
    31: "lfa", 32: "ospfv3", 33: "ospfv3-ia", 34: "ospfv3-external",
    35: "ospfv3-ia", 36: "ospfv3-router", 37: "lisp", 38: "bfd", 39: "flap",
    40: "mgmt", 41: "bgp-ls", 42: "srv6",
}

# Protocol name -> set of IANA numbers it may be reported under.
PROTO_NUMBERS = {
    "bgp": {6, 10, 16, 23, 29},
    "ospf": {2, 32, 33, 34, 35, 36},
    "static": {8, 17},
    "isis": {3},
    "eigrp": {5, 21},
    "rip": {1},
}


def _connect(cfg: dict):
    """Open a read-only DB connection based on the config dict."""
    db_type = str(cfg.get("type") or "mysql").lower()
    host = cfg.get("host") or "127.0.0.1"
    default_port = 3306 if db_type.startswith(("mysql", "mariadb")) else 5432
    port = int(cfg.get("port") or default_port)
    user = cfg.get("user")
    password = cfg.get("password")
    name = cfg.get("name")
    if not user or not name:
        raise ValueError("database.user and database.name are required")
    if db_type.startswith(("mysql", "mariadb")):
        import pymysql
        return pymysql.connect(
            host=host, port=port, user=user, password=password,
            database=name, charset="utf8mb4",
            cursorclass=pymysql.cursors.DictCursor,
            connect_timeout=10, read_timeout=60,
        )
    if db_type.startswith(("postgres", "postgresql")):
        import psycopg2
        return psycopg2.connect(
            host=host, port=port, user=user, password=password,
            dbname=name, connect_timeout=10,
        )
    raise ValueError(
        f"Unsupported database.type: {db_type!r} (use 'mysql' or 'postgresql')"
    )


def list_routes(cfg: dict, hostname: Optional[str] = None,
                protocol: Optional[str] = "bgp", limit: int = 1000) -> dict:
    """Query the LibreNMS ``route`` table (read-only) and return prefix routes.

    Args:
        cfg: The ``database`` config section (type/host/port/name/user/password).
        hostname: Optional device hostname to filter by.
        protocol: 'bgp' (default), 'ospf', 'static', 'isis', 'eigrp', 'rip',
            or 'all' for every route.
        limit: Maximum number of routes to return (clamped to 1..10000).
    """
    limit = max(1, min(int(limit), 10000))
    proto = (protocol or "all").strip().lower()

    where: list[str] = []
    params: list[Any] = []
    if hostname:
        where.append("d.hostname = %s")
        params.append(hostname)
    if proto != "all" and proto in PROTO_NUMBERS:
        nums = sorted(PROTO_NUMBERS[proto])
        where.append("r.inetCidrRouteProto IN (%s)" % ", ".join(["%s"] * len(nums)))
        params.extend(nums)

    where_sql = (" WHERE " + " AND ".join(where)) if where else ""
    sql = (
        "SELECT r.inetCidrRouteDest AS prefix, r.inetCidrRouteProto AS proto, "
        "r.inetCidrRouteNextHop AS next_hop, r.inetCidrRouteNextHopAS AS next_hop_as, "
        "r.inetCidrRouteMetric1 AS metric, r.inetCidrRouteDestType AS dest_type, "
        "r.context_name AS context_name, d.hostname AS hostname "
        "FROM route r JOIN devices d ON d.device_id = r.device_id"
        + where_sql
        + " ORDER BY d.hostname, r.inetCidrRouteDest LIMIT %s"
    )
    params.append(limit)

    conn = _connect(cfg)
    try:
        cur = conn.cursor()
        cur.execute(sql, params)
        rows = cur.fetchall()
    finally:
        conn.close()

    routes = []
    for row in rows:
        pnum = int(row["proto"])
        routes.append({
            "hostname": row["hostname"],
            "prefix": row["prefix"],
            "proto": pnum,
            "proto_name": PROTO_NAMES.get(pnum, f"unknown({pnum})"),
            "next_hop": row["next_hop"],
            "next_hop_as": int(row["next_hop_as"]) if row["next_hop_as"] is not None else None,
            "metric": int(row["metric"]) if row["metric"] is not None else None,
            "dest_type": row["dest_type"],
            "context_name": row["context_name"] or "",
        })

    result: dict[str, Any] = {
        "status": "ok",
        "count": len(routes),
        "protocol": proto,
        "routes": routes,
    }
    if proto != "all" and proto in PROTO_NUMBERS and not routes:
        result["note"] = (
            f"No routes matched protocol '{proto}' (IANA numbers "
            f"{sorted(PROTO_NUMBERS[proto])}). Devices may report this protocol "
            "under a different number. Call again with protocol='all' to list "
            "every route with its protocol number."
        )
    return result