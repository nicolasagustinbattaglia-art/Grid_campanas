# Agentes por política — Condensador EOC (TC Upsell MLB)

Capa de análisis nueva, en paralelo al dashboard (`dashboard_eoc.html`). No lo modifica ni depende
de él — no hay riesgo de romper lo que ya está publicado en Grid.

## Qué es esto

Un subagente de Claude Code por política del condensador (`.claude/agents/eoc-policy-<slug>.md`),
cada uno con memoria propia (`memoria/<SLUG>.md` + `data/<SLUG>/<exec_id>.json`), que:

1. Analiza **de forma independiente** la ejecución de su política en una campaña (funnel, killers,
   excepciones, cobertura de segmentos NISE×BHV×rating).
2. Compara contra su propia historia (memoria) y registra hallazgos + el *por qué*, no solo números.

Un comando orquestador (`/run-policy-agents <campaign_id>`, ver `.claude/commands/run-policy-agents.md`)
lanza todos los agentes en paralelo y después corre un análisis **global**: cruza las políticas para
encontrar clientes elegibles (sobreviven reglas duras) que **ninguna política impacta**.

## Por qué el slug y no `policy_id`

`policy_id` (el id numérico de EOC, ej. `2721`) se re-emite cada campaña/mes — no sirve como índice
de memoria persistente. El slug (`BAU`, `RIESGO_MED_SOW`, ...) es estable. Ver `POLITICAS_INDEX.py`
para el mapeo canónico política ↔ `EXECUTION_GROUP_ID` ↔ slug (reexporta `POLITICAS_INDEX` de
`queries/sept2026/gen_sql.py`, no lo duplica).

## Estado: piloto

Implementado para 3 políticas (BAU, ADECUACION, RIESGO_MED_SOW) — con historia rica ya conocida en
`../` (memoria del proyecto) para validar el formato antes de escalar a las 10. Una vez validado el
piloto, generar el resto de los agentes siguiendo el mismo template.

## Estructura

```
agentes_politicas/
├── POLITICAS_INDEX.py       # mapeo slug <-> EXECUTION_GROUP_ID (fuente única de verdad)
├── memoria/<SLUG>.md        # historial narrativo de hallazgos, por política + GLOBAL_GAPS.md
└── data/<SLUG>/<exec_id>.json   # snapshot crudo por corrida (funnel, killers, exceptions, segmentos)
```

Agentes: `.claude/agents/eoc-policy-<slug>.md`. Orquestador: `.claude/commands/run-policy-agents.md`.

## Reglas heredadas del repo (ver `CLAUDE.md` raíz)

- `git fetch`/`git pull` antes de tocar nada — hay más de un colaborador.
- Nunca tocar Sellers, nunca `--amend`/`--force`/`reset --hard`.
- Esto no toca `dashboard_eoc.html` ni el flujo de Grid — commitear acá no requiere las mismas
  precauciones de "versión nueva a Grid", pero sí las de git normales (fetch antes, commit por
  cambio lógico, push solo si se pide).
