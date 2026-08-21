# Zee.Media Client Reporting — MCP connector

Read-only remote MCP server that exposes the client-dashboard data (Supabase
`client_series` + `client_reports`) to claude.ai as a custom connector, so the
team can ask Claude about any client and it reads live. Read-only by design.

## Tools
`list_clients`, `get_dashboard(slug)`, `get_audit(slug)`, `get_reports(slug)`, `search(query)`

## Deploy (Render)
1. Push this repo to GitHub (done).
2. Render → New → Web Service → connect this repo. It reads `render.yaml`.
3. Set env vars: `SUPABASE_URL`, `SUPABASE_SERVICE_KEY`, `AUTHKIT_DOMAIN`, and
   `PUBLIC_URL` (= the Render URL, e.g. https://zm-reporting-mcp.onrender.com).
4. Deploy. MCP endpoint: `<PUBLIC_URL>/mcp/`.

## Auth (WorkOS AuthKit — free)
1. workos.com → create an AuthKit app; enable Dynamic Client Registration.
2. Add a Google connection; restrict to the zee.media workspace domain (team only).
3. Add redirect: `https://claude.ai/api/mcp/auth_callback`.
4. Copy the AuthKit domain → `AUTHKIT_DOMAIN` env on Render.

## Add to claude.ai
Settings → Connectors → Add custom connector → URL `<PUBLIC_URL>/mcp/` → authorize.
