"""Zee.Media client-reporting MCP server (read-only).

Exposes the reporting data behind the client dashboards — series, audits, and
reports, all held in Supabase (public.client_series + public.client_reports) —
as MCP tools, so the team can ask Claude (claude.ai) about any client and it
reads live. READ-ONLY by construction: every call is a Supabase GET; there is
no code path that writes, so a public endpoint can never mutate client data.

Auth: WorkOS AuthKit (OAuth + Dynamic Client Registration, which claude.ai
requires). Gate access to your team in the WorkOS dashboard (e.g. Google login
restricted to the zee.media workspace). The Supabase service key stays server
-side only and is never exposed to the client.

Env vars (set in Render):
  SUPABASE_URL           https://dxocfmwjwzzseepujfji.supabase.co
  SUPABASE_SERVICE_KEY   (service role key — server-side only)
  AUTHKIT_DOMAIN         https://<your-app>.authkit.app
  PUBLIC_URL             https://<your-service>.onrender.com   (this server's public URL)
  PORT                   (provided by Render)
"""
import os
import requests

from fastmcp import FastMCP
from fastmcp.server.auth.providers.workos import AuthKitProvider

SUPABASE_URL = os.environ["SUPABASE_URL"].rstrip("/")
SUPABASE_KEY = os.environ["SUPABASE_SERVICE_KEY"]
_H = {"apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}"}

auth = AuthKitProvider(
    authkit_domain=os.environ["AUTHKIT_DOMAIN"],
    base_url=os.environ["PUBLIC_URL"],
)
mcp = FastMCP("Zee.Media Client Reporting", auth=auth)


def _get(table, params):
    r = requests.get(f"{SUPABASE_URL}/rest/v1/{table}", headers=_H, params=params, timeout=60)
    r.raise_for_status()
    return r.json()


@mcp.tool
def list_clients() -> list:
    """List every client with a reporting dashboard, with name, status, currency and scope."""
    rows = _get("client_series", {"select": "client_slug,data"})
    out = []
    for r in rows:
        d = r.get("data") or {}
        out.append({
            "slug": r["client_slug"],
            "name": d.get("name"),
            "currency": d.get("currency"),
            "scope": d.get("scope"),
            "months": len(d.get("months") or []),
            "has_audit": bool(d.get("audit")),
            "reports": [x.get("title") for x in (d.get("reports") or [])],
        })
    return sorted(out, key=lambda x: (x["name"] or x["slug"]).lower())


@mcp.tool
def get_dashboard(slug: str) -> dict:
    """Full dashboard series for one client (slug): monthly revenue by flow/campaign,
    subscribers, unsub/spam, RPR-by-flow, store revenue, order buckets, tiles, etc.
    Use list_clients first to get valid slugs."""
    rows = _get("client_series", {"client_slug": f"eq.{slug}", "select": "data"})
    if not rows:
        return {"error": f"no client '{slug}' — call list_clients for valid slugs"}
    return rows[0]["data"]


@mcp.tool
def get_audit(slug: str) -> dict:
    """The account audit for one client (findings, charts), or a note if it has none."""
    rows = _get("client_series", {"client_slug": f"eq.{slug}", "select": "data"})
    if not rows:
        return {"error": f"no client '{slug}'"}
    audit = (rows[0]["data"] or {}).get("audit")
    return audit or {"note": f"'{slug}' has no audit"}


@mcp.tool
def get_reports(slug: str) -> dict:
    """All reports for one client: custom one-off reports (e.g. the SMS holdout test)
    from the series, plus every monthly report snapshot, newest first."""
    rows = _get("client_series", {"client_slug": f"eq.{slug}", "select": "data"})
    custom = (rows[0]["data"] or {}).get("reports") if rows else None
    monthly = _get("client_reports", {"client_slug": f"eq.{slug}",
                                       "select": "month,data", "order": "month.desc"})
    return {"custom_reports": custom or [], "monthly_reports": monthly}


@mcp.tool
def search(query: str) -> list:
    """Find clients by name or slug (case-insensitive substring)."""
    q = (query or "").lower().strip()
    rows = _get("client_series", {"select": "client_slug,data"})
    hits = []
    for r in rows:
        d = r.get("data") or {}
        if q in r["client_slug"].lower() or q in (d.get("name") or "").lower():
            hits.append({"slug": r["client_slug"], "name": d.get("name")})
    return hits


if __name__ == "__main__":
    mcp.run(transport="http", host="0.0.0.0", port=int(os.environ.get("PORT", "8000")))
