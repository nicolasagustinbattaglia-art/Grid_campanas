"""Arma dos tablas BigQuery nuevas para el bot de Slack (ADECUACION) a partir del dump crudo
de eoc-mcp para la campaña 7371 (sep-26, producción) en data/mcp_raw/:

1. NB619_ADECUACION_REGLAS_DURAS: las 47 reglas duras (RULE_EXCLUDE) que aplican al grupo
   ADECUACION DE RENTA, con fórmula y condiciones completas -- hoy el bot solo conoce 2-3 nombres
   de ejemplo. Fuente: 7371_campaign_detail.json -> rules_killers, filtrado por
   processing_group_name == "ADECUACION DE RENTA".

2. NB619_ADECUACION_OFERTA_SEGMENTO: oferta desagregada por segmento (rating upsell x rating BHV x
   antigüedad), 44 combinaciones para la campaña 7371. Fuente: 7371_dashboard_offer.json ->
   processing_group_dashboard[ADECUACION DE RENTA].offer_by_attributes.

Snapshot de un solo momento (no histórico como NB619_ADECUACION_HISTORIA_BOT) -- si las reglas
duras cambian o se corre una campaña nueva, hay que re-extraer y recargar con --replace.

Uso:
    python3 queries/build_adecuacion_reglas_ofertas.py reglas   > /tmp/reglas.ndjson
    python3 queries/build_adecuacion_reglas_ofertas.py ofertas  > /tmp/ofertas.ndjson

    bq load --source_format=NEWLINE_DELIMITED_JSON --replace \
        meli-bi-data:SBOX_CREDITS_SB.NB619_ADECUACION_REGLAS_DURAS \
        /tmp/reglas.ndjson queries/adecuacion_reglas_duras_schema.json

    bq load --source_format=NEWLINE_DELIMITED_JSON --replace \
        meli-bi-data:SBOX_CREDITS_SB.NB619_ADECUACION_OFERTA_SEGMENTO \
        /tmp/ofertas.ndjson queries/adecuacion_oferta_segmento_schema.json
"""
import json
import sys
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent / "data" / "mcp_raw"
CAMPAIGN_ID = 7371
MES = "Sep-26"


def metric_value(offer_block, title, label=""):
    for section in offer_block:
        if section["title"] == title:
            for m in section["metrics"]:
                if m["label"] == label or (label == "" and len(section["metrics"]) == 1):
                    return m["value"]
    return None


def build_reglas():
    d = json.loads((DATA_DIR / f"{CAMPAIGN_ID}_campaign_detail.json").read_text())
    reglas = [r for r in d["rules_killers"] if r["processing_group_name"] == "ADECUACION DE RENTA"]
    for r in reglas:
        row = {
            "rule_id": r["rules_killers_id"],
            "rule_name": r["rules_killers_name"],
            "rule_type": r["rules_killers_type"],
            "state": r["state"],
            "formula": r["formula"],
            "logical_operator": r["logical_operator"],
            "conditions": [
                {
                    "alias": c["alias"],
                    "column": c["column"],
                    "comparator": c["comparator"]["comparator"],
                    "comparator_name": c["comparator"]["name"],
                    "value": str(c["value"]),
                    "is_pii": c["is_pii"],
                    "condition_index": c["condition_index"],
                }
                for c in r["conditions"]
            ],
        }
        sys.stdout.write(json.dumps(row, ensure_ascii=False) + "\n")


def build_ofertas():
    d = json.loads((DATA_DIR / f"{CAMPAIGN_ID}_dashboard_offer.json").read_text())
    group = next(g for g in d["processing_group_dashboard"] if g["group_name"] == "ADECUACION DE RENTA")
    exec_id = group["execution_group_id"].rsplit("-", 1)[0]
    for entry in group["offer_by_attributes"]:
        attrs = entry["attributes"]
        antiguedades = [int(a["value"]) for a in attrs if a["name"] == "WANDA.FULL_TC_ACTIVE_DAYS_SINCE_QTY"]
        rating_upsell = next(a["value"] for a in attrs if a["name"] == "WANDA.INTERNAL_RATING_UPSELL_TC_LATEST_TAG")
        rating_bhv = next(a["value"] for a in attrs if a["name"] == "WANDA.INTERNAL_RATING_BEHAVIOR_TC_LATEST_TAG")
        offer = entry["offer"]
        row = {
            "exec_id": exec_id,
            "campaign_id": CAMPAIGN_ID,
            "mes": MES,
            "rating_upsell": rating_upsell,
            "rating_bhv": rating_bhv,
            "antiguedad_desde_dias": min(antiguedades),
            "antiguedad_hasta_dias": max(antiguedades),
            "volumen": int(metric_value(offer, "Cantidad de usuarios accionados", "Volumen total")),
            "share_pct": float(metric_value(offer, "Share")),
            "oferta_total": float(metric_value(offer, "Propuestas totales (Suma de la oferta)", "Total")),
            "oferta_min": float(metric_value(offer, "Oferta", "Mínima")),
            "oferta_prom": float(metric_value(offer, "Oferta", "Promedio")),
            "oferta_max": float(metric_value(offer, "Oferta", "Máxima")),
        }
        sys.stdout.write(json.dumps(row, ensure_ascii=False) + "\n")


if __name__ == "__main__":
    if sys.argv[1] == "reglas":
        build_reglas()
    elif sys.argv[1] == "ofertas":
        build_ofertas()
    else:
        raise SystemExit("uso: build_adecuacion_reglas_ofertas.py {reglas|ofertas}")
