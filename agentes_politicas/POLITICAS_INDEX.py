"""Fuente única de verdad para el mapeo política <-> EXECUTION_GROUP_ID.

Reexporta POLITICAS_INDEX desde queries/sept2026/gen_sql.py (no duplicar el
mapeo real) y agrega el slug estable de archivo/memoria para cada política.
El slug es estable entre meses -- a diferencia del policy_id numérico de EOC,
que se re-emite en cada campaña (ver gotcha en la memoria del proyecto:
data/policies/{policy_id}.json usa el id numérico y por eso NO sirve como
índice de memoria persistente).
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "queries", "sept2026"))
from gen_sql import POLITICAS_INDEX  # noqa: E402

SLUGS = {
    'REACTIVACION': 'REACTIVACION',
    'OPF': 'OPF',
    'JOURNEY 1A': 'JOURNEY_1A',
    'PISOS': 'PISOS',
    'ADECUACION DE RENTA': 'ADECUACION',
    'ACTIVACION': 'ACTIVACION',
    'BAU': 'BAU',
    'RIESGO MED. SOW': 'RIESGO_MED_SOW',
    'VIP MP': 'VIP_MP',
    'VIP MKPL': 'VIP_MKPL',
}


def execution_group_id(exec_id: str, politica: str) -> str:
    """Arma el EXECUTION_GROUP_ID de una política para una ejecución dada.

    El índice es posicional (1-based) dentro de POLITICAS_INDEX, no depende
    de POLITICA_ID (que viene NULL para políticas nuevas como VIP MKPL).
    """
    idx = POLITICAS_INDEX.index(politica) + 1
    return f"{exec_id}-{idx}"


def slug(politica: str) -> str:
    return SLUGS[politica]


if __name__ == '__main__':
    for p in POLITICAS_INDEX:
        print(f"{p!r:25s} -> slug={SLUGS[p]}")
