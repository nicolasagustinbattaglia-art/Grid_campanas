"""
Arma la tabla histórica de ADECUACION DE RENTA para el bot de Slack en VerdiFlow.

Extrae el grupo "ADECUACION DE RENTA" de los snapshots ya existentes en data/
(camp5588.json, camp6126.json, camp6816.json, c7371.json) -- no pega a EOC de
nuevo para Jun/Jul/Ago (ya confirmados en el dashboard). Sep-26 usa c7371.json,
que es la campaña de PRODUCCIÓN real (enviada por mbotta) -- OJO: c7360.json
es la v20 de la SIMULACIÓN previa al envío, no la campaña real, no usar esa
para esta tabla (error detectado y corregido el 2026-09-18). Genera un NDJSON
para bq load.

Uso:
    python3 queries/build_adecuacion_historia_bot.py > /tmp/adecuacion_historia.ndjson
    bq load --source_format=NEWLINE_DELIMITED_JSON --replace \
        meli-bi-data:SBOX_CREDITS_SB.NB619_ADECUACION_HISTORIA_BOT \
        /tmp/adecuacion_historia.ndjson \
        queries/adecuacion_historia_schema.json
"""
import json
import sys
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent / "data"

# (archivo, mes, policy_id, policy_name) -- policy_id/name de policy_diff.json / memoria del proyecto
SOURCES = [
    ("camp5588.json", "Jun-26", 2164, "202606-MLB-IND-TC-FULL-UPSELL-TEST COMBINADO-RENTA-ADECUACION-PS-1"),
    ("camp6126.json", "Jul-26", 2164, "202606-MLB-IND-TC-FULL-UPSELL-TEST COMBINADO-RENTA-ADECUACION-PS-1"),
    ("camp6816.json", "Ago-26", 2720, "202608-MLB-IND-TC-FULL-UPSELL-TEST COMBINADO-RENTA-ADECUACION-PS-1-v4"),
    ("c7371.json", "Sep-26", 2960, "202609-MLB-IND-TC-FULL-UPSELL-TEST COMBINADO-RENTA-ADECUACION-PS-1"),
]


def extract_adecuacion(campaign_json):
    for group in campaign_json["groups"]:
        if group["group_name"] == "ADECUACION DE RENTA":
            return group
    raise ValueError("No se encontró el grupo ADECUACION DE RENTA")


def main():
    rows = []
    for filename, mes, policy_id, policy_name in SOURCES:
        path = DATA_DIR / filename
        campaign = json.loads(path.read_text())
        group = extract_adecuacion(campaign)
        row = {
            "exec_id": campaign["exec_id"],
            "campaign_id": campaign["campaign_id"],
            "campaign_name": campaign["name"],
            "mes": mes,
            "policy_id": policy_id,
            "policy_name": policy_name,
            "execution_group_id": group.get("execution_group_id"),
            "funnel": group["funnel"],
            "killers": group["killers"],
        }
        rows.append(row)

    for row in rows:
        sys.stdout.write(json.dumps(row, ensure_ascii=False) + "\n")


if __name__ == "__main__":
    main()
