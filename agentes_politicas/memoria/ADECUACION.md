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

### 2026-09-16 — campaign_id=7371, exec_id=dd7b0b0f-66f4-4596-b272-850bf10e64d4 (grupo -5)

Campaña de producción del condensador EOC (`202609-MLB-CROSS-TC FULL-UPSELL-BAU-POLITICAS-CONDENSADOR`),
ejecutada 2026-09-11, enviada por `mbotta`. Datos oficiales vía skill `eoc-ops:eoc-analyst`
(`get_campaign_execution_dashboard` + `get_policy_detail`, fallback HTTP documentado en
`queries/fetch_policies.py` porque el MCP `eoc-mcp` no estaba disponible como tool nativo en esta
sesión — 2 reintentos por 503 transitorio, luego OK) + BigQuery de refuerzo para cobertura de
segmentos.

**Policy_id confirmado: 2960** (nombre EOC `202609-MLB-IND-TC-FULL-UPSELL-TEST
COMBINADO-RENTA-ADECUACION-PS-1`), reemplazando **2720** (activo hasta la corrida de agosto/inicios
de septiembre que ya tenía documentada esta memoria). `2960` fue creado por **`nbattaglia`** el
2026-09-08, aprobado por `mbotta` y activado el **2026-09-10** — un día antes de esta ejecución.

**Funnel (nivel grupo, oficial EOC):**
- Universo (`MLB / CROSS / TC - ACEPTADA`): 21.554.811 → `total_users` funnel 21.515.295
- Killers RK (47 reglas): -19.394.949 → sobreviven 2.120.346
- Exclusión por atributos/cluster de política: -339.828 → 1.780.518
- Exceptions de política, en orden secuencial oficial:
  1. `EXCLUSION_LIM_RENTA`: -75.809 (4,3%) → 1.704.709
  2. `KILLER_FLAG_RCI_CURRENT_MAYOR_RCI_BHV - CON OPTIN`: -52.845 (3,1%) → 1.651.864
  3. `KILLER_FLAG_RCI_CURRENT_MAYOR_RCI_BHV - SIN OPTIN`: -256.307 (15,5%) → 1.395.557
  4. `KILLER_UPSELL_INSUFFICIENT`: -757.147 (54,3%) → 638.410
  5. `R - RENTA REAL`: -626.719 (98,2%) → **11.691 = `users_to_impact`** (grupo, pre-competencia)
- Control group configurado 10% pero `users_excluded_by_control_group: 0` en este grupo (no se
  restó nada acá).

**⚠ Ojo con "users_to_impact" en el condensador multi-política**: 11.691 es el funnel a nivel de
grupo de procesamiento, **antes** de la competencia cross-política del condensador. El
`campaign_dashboard.actions` muestra una ronda "COMPETENCIA" donde ADECUACION gana 8.791 de esos
11.691 (pierde 2.900 contra otras políticas individuales con prioridad mayor), y una segunda ronda
donde ese pool compite contra BAU/VIP MP/VIP MKPL. La audiencia final real que efectivamente queda
en `EOC_CAMPAIGN_EXECUTION_DETAIL` (la que se usa para armar el archivo de oferta) es **7.282**
usuarios — un 37,7% menos que el `users_to_impact` de grupo. Para reportar "cuántos clientes
recibieron oferta de ADECUACION" usar 7.282, no 11.691; para comparar el funnel interno de la
política (killers/exceptions) 11.691 sigue siendo el número correcto porque es el que expone EOC
antes de la competencia. Confirmar si esto es así en TODAS las corridas del condensador o es
específico de este mes — no estaba explícitamente documentado antes en esta memoria.

**🔑 HALLAZGO PRINCIPAL — `KILLER_SIN_INCREMENTO_INGRESO` fue ELIMINADO de la política, no
modificado ni renombrado.** Diff exhaustivo 2720 (agosto, `lkitahara`, INACTIVE) vs 2960 (septiembre,
`nbattaglia`, ACTIVE):
- 2720 tenía 40 exceptions, 2960 tiene 39 — la única diferencia estructural es que
  `KILLER_SIN_INCREMENTO_INGRESO` (excluye si `ASSUMED_INCOME_AMT <= WANDA.ASSUMED_INCOME_L30D_AMT`,
  exactamente la condición documentada en la investigación cerrada) ya no está en el array de
  exceptions de 2960.
- Los 48 settings segmentados y los settings fijos (`AJUSTE_CAP*`, `TOPE_*`, etc.) son
  **byte-a-byte idénticos** entre 2720 y 2960 — el diff no encontró un solo valor cambiado. La
  descripción de la política (`"Ajuste multiplicadores"`) es texto heredado/genérico, no refleja
  un ajuste real de multiplicadores en esta versión: el único cambio funcional es la eliminación
  de ese killer.
- Esto es totalmente consistente con la investigación previa ya cerrada en esta memoria: el killer
  quedó roto por la migración de tags de `ASSUMED_INCOME_SOURCE_TAG` (ruidoso, favorecía/perjudicaba
  segmentos de forma errática) y **`nbattaglia` lo sacó de la política como remediación**, aprobado
  el mismo día que se activó (10-sep), justo después de que la investigación identificara la causa
  raíz. No es un bug nuevo ni un dato para re-investigar — es la corrección esperada.
- Consecuencia práctica: **la comparación "¿el escalón de `KILLER_SIN_INCREMENTO_INGRESO` se
  mantuvo en ~63,2%?" ya no aplica** — ese killer no corre más en esta política. No hay drift que
  reportar sobre él porque desapareció, con causa y fecha conocidas.

**`KILLER_UPSELL_INSUFFICIENT`** (excluye si el % Y el $ de aumento de límite propuesto vs actual
son ambos menores a un mínimo configurado — `GENERAL_LIMIT/CURRENT_LIMIT_CCARD` y
`GENERAL_LIMIT-CURRENT_LIMIT_CCARD`) ya existía igual en 2720 (misma posición, misma fórmula) — no
es nuevo. Corta 54,3% en esta corrida; no hay serie histórica propia registrada acá todavía para
saber si es estable — a diferencir del `SIN_INCREMENTO_INGRESO`, esta lógica no depende de
`ASSUMED_INCOME_L30D_AMT`/tags de renta, así que no hereda el problema de esa investigación.

**`R - RENTA REAL` en 98,2%** — por encima del rango de ruido documentado (74-96%). Dado que (a) el
killer previo en la cadena (`KILLER_SIN_INCREMENTO_INGRESO`) desapareció, la población que llega a
este paso ya no es comparable 1:1 con meses anteriores (cambió el filtro previo, no solo el
tamaño), y (b) sigue siendo consistente con la inestabilidad de tag ya documentada (75% cambia de
tag en 13 días). Tratarlo como ruido esperado, pero está en el borde superior del rango conocido —
si el próximo mes también da >96% con `SIN_INCREMENTO_INGRESO` ya ausente, valdría la pena ampliar
el rango documentado a 74-98% en vez de 74-96%.

**Cobertura de segmentos (BHV × Upsell rating, sobre los 7.282 post-competencia, vía
`EOC_CAMPAIGN_EXECUTION_DETAIL` + fallback `BT_VU_CREDIT`):** cubre 15 de las 16 combinaciones
posibles (falta BHV=D × UPS=A, 0 usuarios — combinación rara/esperada, peor comportamiento con
mejor rating de upsell). Límite actual promedio $7.078, límite final promedio $8.798, multiplicador
promedio 1,30, exposición total ≈ $12,5M BRL.

**Snapshot crudo**: `agentes_politicas/data/ADECUACION/dd7b0b0f-66f4-4596-b272-850bf10e64d4.json`
(funnel, exceptions secuenciales, diff 2720 vs 2960, competencia cross-política, segmentos).
