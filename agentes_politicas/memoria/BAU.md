# Memoria — Política BAU

Slug: `BAU` · Nombre EOC: `BAU` · Agente: `.claude/agents/eoc-policy-bau.md`

## Contexto heredado (previo a este agente, de la memoria del proyecto)

- Mapeo `POLITICA_ID`: `BAU` → `BAU`.
- Es una de las 7 políticas (de 9-10) donde `users_to_impact` del funnel de EOC **no** calza exacto
  contra el `COUNT(*)` de BigQuery agrupado por `EXECUTION_GROUP_ID` (sólo ACTIVACION y VIP MP
  calzan siempre) — diferencia típica 6-22%, va a parar a filas con `POLITICA_ID` NULL/Sellers en
  `EOC_CAMPAIGN_EXECUTION_DETAIL`. El número de referencia para BQ es `EXECUTION_GROUP_ID`, y el de
  referencia para el funnel oficial es `get_campaign_execution_dashboard`, no al revés.
- `LIMITE_PRE_UPSELL` de `ACTIONABLE_COLUMNS` cubre BAU al 100% (no hace falta el fallback a
  `BT_VU_CREDIT` que sí necesitan PISOS/OPF).
- Evolución de reglas duras (aplican a todas las políticas, incluida BAU): 25 (Jun-26) → 26 (Jul) →
  29 (Ago-26).

## Historial de corridas del agente

_Sin corridas todavía — la primera ejecución de `eoc-policy-bau` agrega la primera entrada acá,
con fecha, `campaign_id`/`exec_id`, hallazgos y el razonamiento detrás de cada uno._
