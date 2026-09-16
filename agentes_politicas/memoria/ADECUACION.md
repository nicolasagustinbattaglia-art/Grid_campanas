# Memoria — Política ADECUACION DE RENTA

Slug: `ADECUACION` · Nombre EOC: `ADECUACION DE RENTA` · Agente: `.claude/agents/eoc-policy-adecuacion.md`

## Contexto heredado (previo a este agente, de la memoria del proyecto — investigación extensa)

Esta política tuvo la investigación más profunda del proyecto hasta ahora (Ago-26 → Sep-26). Puntos
que el agente **no debería re-investigar desde cero**:

- **Caída fuerte Ago→Sep (6816→7218), policy_id 2720 sin modificar**: causa fue el killer
  `KILLER_SIN_INCREMENTO_INGRESO` (excluye si `ASSUMED_INCOME_AMT <= WANDA.ASSUMED_INCOME_L30D_AMT`),
  que pasó de ~90% de exclusión (estable 4 meses) a 63,2% justo en el corte Ago→Sep — un escalón
  limpio, no ruido.
- **`R - RENTA REAL` (excluye por `ASSUMED_INCOME_SOURCE_TAG` fuera de una whitelist de 5 fuentes) es
  intrínsecamente ruidoso mes a mes (74-96%)** — 75% de los clientes cambia de tag en sólo 13 días
  (`ASSUMED_INCOME_SOURCE_TAG` no es estable a nivel cliente). No confundir ese ruido normal con una
  señal real.
- **Causa raíz del escalón**: el pipeline de ingreso dejó de "parquear" ~66% de la gente en el tag
  `PREVIOUS_DECISION` (sin evaluación fresca) y empezó a evaluar a casi todos — pero la mayoría de
  los recién evaluados cae en categorías de **estimador/modelo** (`OPF_ESTIMATOR` etc.), no de dato
  real, y la política exige dato real. Es un cambio de cobertura del pipeline de ingreso, no un bug
  de la política.
- **`SIN_INCREMENTO_INGRESO` invirtió a quién favorece**: en agosto el segmento "premium" (tag real)
  tenía 25pp menos exclusión que el resto; en Sep se invirtió (86,1% vs 61,2%) — pendiente de
  explorar si es una caída real de `ASSUMED_INCOME_AMT` o un artefacto de la ventana de 30 días.
- **⚠ `WANDA.ASSUMED_INCOME_L30D_AMT` y `BT_VU_ASSUMED_INCOME.ASSUMED_INCOME_AMT` vía
  `CAMP_EOC_POLICY`/`COLUMNS_VARIABLES_POLICY` dan 100% NULL siempre** (son campos `is_pii`, no
  expuestos por esa tabla, ni frescos ni retroactivos) — si se necesita el valor real, ir directo a
  `meli-bi-data.WHOWNER.BT_VU_ASSUMED_INCOME`, nunca a `CAMP_EOC_POLICY` para estos dos campos.
- **Gotcha de excepciones secuenciales**: el array `EXCEPTIONS` de `CAMP_EOC_POLICY` no tiene
  short-circuit — para reproducir el `excluded_users` oficial de EOC hay que filtrar
  `excluded_before` (excepciones previas con `ACTION='POLICY_EXCLUDE'` y `INDEX_EXCEPTION` menor),
  no un `LOGICAL_OR` simple (sobrecuenta).

## Historial de corridas del agente

_Sin corridas todavía — la primera ejecución de `eoc-policy-adecuacion` agrega la primera entrada
acá, con fecha, `campaign_id`/`exec_id`, hallazgos y el razonamiento detrás de cada uno._
