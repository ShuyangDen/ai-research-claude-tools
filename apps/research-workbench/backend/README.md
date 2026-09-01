# AI Research Workbench backend

FastAPI backend for the local Research Workbench. It reads the existing Paper
Tracker, AI Education, idea-vault, skill, and Research Core files. Workbench-only
state is written atomically below `<workflow_state_root>/workbench`.

```powershell
python -m pip install -e packages/research-core -e "apps/research-workbench/backend[test]"
research-workbench --port 8765
```

The server always binds to `127.0.0.1`; no remote-host override is exposed.
The browser receives a CSRF token from `/api/bootstrap`; all mutating requests
must echo it in `X-Workbench-CSRF`.

`GET /api/sync` reports sanitized Git state for the configured research roots.
`POST /api/sync` accepts only their opaque repository IDs and one of `fetch`,
`pull`, `push`, or `sync`. It never stages or commits files, uses fast-forward-only
pulls, and never exposes an arbitrary path or command surface to the browser.
