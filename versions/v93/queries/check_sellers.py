"""¿La campaña 6970 excluye sellers a nivel política, además del killer K-SELLERS-2?

Baja el detalle de la campaña y de su política, y busca cualquier referencia a
merchant / seller / PJ en atributos de segmentación, condiciones y excepciones.
"""
import asyncio, json, os, re, sys, urllib.request

sys.path.insert(0, os.path.expanduser("~/.mcp-remote-proxy/venv/lib/python3.11/site-packages"))
from mcp_remote_proxy import furyauth

BASE = "https://eoc-mcp.melioffice.com/mcp"
PATRON = re.compile(r"MERCHANT|SELLER|_PJ\b|\bPJ_|MERCADO_?PAGO|SHOP", re.I)


async def main():
    token = await furyauth.get_fury_auth_token_async()
    H = {"Content-Type": "application/json",
         "Accept": "application/json, text/event-stream",
         "X-Tiger-Token": token}

    def call(payload, sid=None):
        h = dict(H)
        if sid:
            h["Mcp-Session-Id"] = sid
        req = urllib.request.Request(BASE, data=json.dumps(payload).encode(), headers=h, method="POST")
        resp = urllib.request.urlopen(req, timeout=120)
        raw = resp.read().decode()
        for line in raw.split("\n"):
            if line.startswith("data:"):
                return json.loads(line[5:].strip()), resp.headers.get("mcp-session-id", sid)
        return {}, sid

    _, sid = call({"jsonrpc": "2.0", "id": 1, "method": "initialize",
                   "params": {"protocolVersion": "2024-11-05", "capabilities": {},
                              "clientInfo": {"name": "claude", "version": "1.0"}}})

    # 1. Campaña -> policy_id y universo
    r, _ = call({"jsonrpc": "2.0", "id": 2, "method": "tools/call",
                 "params": {"name": "get_campaign_detail",
                            "arguments": {"campaign_id": 6970,
                                          "sections": ["policy", "universe"]}}}, sid)
    camp = json.loads(r["result"]["content"][0]["text"])
    json.dump(camp, open("/tmp/sim/camp6970_detail.json", "w"), ensure_ascii=False)

    pids = sorted(set(re.findall(r'"policy_id":\s*(\d+)', json.dumps(camp))))
    print("policy_ids de la campaña 6970:", pids)

    # Universo: a veces el filtro de sellers está acá y no en la política
    uni = json.dumps(camp.get("universe", {}), ensure_ascii=False)
    hits_uni = sorted(set(PATRON.findall(uni)))
    print("universo — menciones a seller/merchant:", hits_uni or "ninguna")
    print("universo (recorte):", uni[:400] if uni != "{}" else "(vacío)")

    # 2. Política -> atributos, settings, exceptions
    for pid in pids:
        r, _ = call({"jsonrpc": "2.0", "id": 3, "method": "tools/call",
                     "params": {"name": "get_policy_detail",
                                "arguments": {"policy_id": int(pid)}}}, sid)
        pol = json.loads(r["result"]["content"][0]["text"])
        json.dump(pol, open(f"/tmp/sim/policies/{pid}.json", "w"), ensure_ascii=False)
        nombre = pol["policy"].get("name") or pol["policy"].get("policy_name")
        print(f"\n=== política {pid} — {nombre} ===")

        cols = {a["column"] for a in pol.get("attributes", [])}
        print("  atributos de segmentación:", sorted(cols))

        # Cualquier condición o valor en toda la política
        encontrados = []
        for s in pol.get("settings", []):
            for c in s.get("conditions", []):
                blob = f'{c.get("column","")} {c.get("value","")}'
                if PATRON.search(blob):
                    encontrados.append(("setting", blob))
        for e in pol.get("exceptions", []):
            blob = json.dumps(e, ensure_ascii=False)
            if PATRON.search(blob):
                encontrados.append(("exception", e.get("conditional_name")))
        print("  referencias a seller/merchant:", encontrados or "NINGUNA")


asyncio.run(main())
