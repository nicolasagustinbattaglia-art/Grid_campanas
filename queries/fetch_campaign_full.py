"""Baja TODO lo que expone eoc-mcp para una campaña puntual y lo persiste a disco tal cual.

Mismo patrón de fallback HTTP que fetch_policies.py (el MCP nativo estaba desconectado en esta
sesión). Trae get_campaign_detail completo (sin filtrar sections) + get_campaign_execution_dashboard
con los 3 includes disponibles (killer_rules, policy, offer) en llamadas separadas, porque el
parámetro 'include' del tool solo acepta un valor por llamada.

Uso:
    python3 queries/fetch_campaign_full.py 7371
"""
import asyncio, json, os, sys, urllib.request

sys.path.insert(0, os.path.expanduser("~/.mcp-remote-proxy/venv/lib/python3.12/site-packages"))
from mcp_remote_proxy import furyauth

BASE = "https://eoc-mcp.melioffice.com/mcp"
OUT = "/Users/nbattaglia/Documents/tablero-upsell/data/mcp_raw"


async def main():
    campaign_id = int(sys.argv[1])
    token = await furyauth.get_fury_auth_token_async()
    H = {"Content-Type": "application/json",
         "Accept": "application/json, text/event-stream",
         "X-Tiger-Token": token}

    def call(payload, sid=None):
        h = dict(H)
        if sid:
            h["Mcp-Session-Id"] = sid
        req = urllib.request.Request(BASE, data=json.dumps(payload).encode(),
                                     headers=h, method="POST")
        resp = urllib.request.urlopen(req, timeout=180)
        sid_out = resp.headers.get("mcp-session-id", sid)
        raw = resp.read().decode()
        for line in raw.split("\n"):
            if line.startswith("data:"):
                return json.loads(line[5:].strip()), sid_out
        return {}, sid_out

    _, sid = call({"jsonrpc": "2.0", "id": 1, "method": "initialize",
                   "params": {"protocolVersion": "2024-11-05", "capabilities": {},
                              "clientInfo": {"name": "claude", "version": "1.0"}}})

    os.makedirs(OUT, exist_ok=True)

    def tool_call(n, name, arguments):
        result, _ = call({"jsonrpc": "2.0", "id": n, "method": "tools/call",
                          "params": {"name": name, "arguments": arguments}}, sid)
        return json.loads(result["result"]["content"][0]["text"])

    jobs = [
        ("campaign_detail", "get_campaign_detail", {"campaign_id": campaign_id}),
        ("dashboard_killer_rules", "get_campaign_execution_dashboard",
         {"campaign_id": campaign_id, "include": "killer_rules"}),
        ("dashboard_policy", "get_campaign_execution_dashboard",
         {"campaign_id": campaign_id, "include": "policy"}),
        ("dashboard_offer", "get_campaign_execution_dashboard",
         {"campaign_id": campaign_id, "include": "offer"}),
    ]

    for n, (label, tool, args) in enumerate(jobs, start=100):
        data = tool_call(n, tool, args)
        path = f"{OUT}/{campaign_id}_{label}.json"
        with open(path, "w") as f:
            json.dump(data, f, ensure_ascii=False)
        print(f"{label:26s} -> {path} ({os.path.getsize(path)} bytes)")


asyncio.run(main())
