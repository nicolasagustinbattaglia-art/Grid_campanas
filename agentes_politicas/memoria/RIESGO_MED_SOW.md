# Memoria — Política RIESGO MED. SOW

Slug: `RIESGO_MED_SOW` · Nombre EOC: `RIESGO MED. SOW` · Agente: `.claude/agents/eoc-policy-riesgo-med-sow.md`

## Contexto heredado (previo a este agente, de la memoria del proyecto)

- Mapeo `POLITICA_ID`: `SOW_RM` → `RIESGO MED. SOW`.
- Mide Share of Wallet con `ATENDIMENTO_PRE_UPS` (`WANDA.ATTEND_PCT`) y `ATENDIMENTO_POST_UPSELL`
  (`GENERAL_LIMIT / MAX_DEUDA_INGRESO`).
- **⚠ SOW se calcula pero no filtra**: el paso POST es `POLICY_MODIFY` (paso 49 de 51), no
  `POLICY_EXCLUDE`; y el killer que sí filtraría por atendimento alto (`K-TC-ATENDIMENTO`) no
  estaba en las campañas principales de Jun/Jul/Ago — solo en ACTIVACION de agosto. Medido en la
  campaña 6970: de 62.659 impactados, 3.563 quedan con SOW 100-200% y 154 arriba de 200% (ya venían
  por encima de 1 antes del upsell).
- **Campaña extra de Ago-26 (6970)**: extra sobre esta política, saca `K-MLB-RATING_CAPTURA_SALDO`
  y `K-PORC-USO-TC-MIM-POR-ANTIG-4M-18M`, suma variante `ATEN` → 62.659 pasan vs 27.333 de la
  principal (+129%), impacto real 56.394 (10% grupo control). Si se relajan killers buscando
  volumen acá, vigilar que no se cuele el hueco de sellers (`K-SELLERS-2` es la única barrera).

## Historial de corridas del agente

_Sin corridas todavía — la primera ejecución de `eoc-policy-riesgo-med-sow` agrega la primera
entrada acá, con fecha, `campaign_id`/`exec_id`, hallazgos y el razonamiento detrás de cada uno._
