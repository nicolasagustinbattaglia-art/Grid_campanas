"""Baja el detalle crudo de las políticas EOC y lo persiste a disco.

Se usa el fallback HTTP del MCP (documentado en el instructivo) en lugar de las tools
para que el payload no pase por el contexto del agente: 18 políticas transcriptas a mano
son un vector de error grande, y acá el JSON llega a disco tal cual lo devuelve EOC.
"""
import asyncio, json, os, sys, urllib.request

sys.path.insert(0, os.path.expanduser("~/.mcp-remote-proxy/venv/lib/python3.11/site-packages"))
from mcp_remote_proxy import furyauth

BASE = "https://eoc-mcp.melioffice.com/mcp"
OUT = "/tmp/sim/policies"

POLICIES = {
    "Ago-26": {"BAU": 2721, "JOURNEY 1A": 2678, "VIP MP": 2722, "PISOS": 2679, "OPF": 2717,
               "RIESGO MED. SOW": 2723, "REACTIVACION": 2712, "ACTIVACION": 2719,
               "ADECUACION DE RENTA": 2720},
    "Jul-26": {"BAU": 2159, "JOURNEY 1A": 2168, "VIP MP": 2161, "PISOS": 2165, "OPF": 2160,
               "RIESGO MED. SOW": 2163, "REACTIVACION": 2166, "ACTIVACION": 2167,
               "ADECUACION DE RENTA": 2164},
}


async def main():
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
        resp = urllib.request.urlopen(req, timeout=120)
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
    n = 0
    for mes, pols in POLICIES.items():
        for pol, pid in pols.items():
            result, _ = call({"jsonrpc": "2.0", "id": 100 + n, "method": "tools/call",
                              "params": {"name": "get_policy_detail",
                                         "arguments": {"policy_id": pid}}}, sid)
            data = json.loads(result["result"]["content"][0]["text"])
            path = f"{OUT}/{pid}.json"
            with open(path, "w") as f:
                json.dump(data, f, ensure_ascii=False)
            n += 1
            print(f"{mes:8s} {pol:22s} id={pid:5d} -> {os.path.getsize(path):7d} bytes")
    print(f"\n{n} políticas guardadas en {OUT}")


asyncio.run(main())
