---
description: Orquesta los agentes de política EOC (análisis independiente por política + gap global de clientes elegibles sin oferta)
argument-hint: <campaign_id>
---

Vas a orquestar el análisis de campaña del condensador EOC de TC Upsell MLB descripto en
`agentes_politicas/README.md`. El `campaign_id` viene en `$ARGUMENTS`.

**Estado actual: piloto con 3 agentes** (`eoc-policy-bau`, `eoc-policy-adecuacion`,
`eoc-policy-riesgo-med-sow`). Las demás políticas (`REACTIVACION`, `OPF`, `JOURNEY 1A`, `PISOS`,
`ACTIVACION`, `VIP MP`, `VIP MKPL`) todavía no tienen agente — si el usuario pide correr el ciclo
completo, primero generá los agentes que falten siguiendo exactamente el template de los 3
existentes en `.claude/agents/eoc-policy-*.md` (mismo formato de frontmatter y de pasos, adaptado al
nombre/slug de cada política) antes de lanzarlos.

## Pasos

1. **`git fetch origin && git log origin/master --oneline -5`** en este repo — chequear que no haya
   commits nuevos que no tengas localmente antes de tocar nada (regla del `CLAUDE.md` del repo).

2. **Resolvé el `exec_id`** de la campaña `$ARGUMENTS` con la skill `eoc-ops:eoc-analyst`
   (`get_campaigns`/`get_campaign_detail`) — necesitás el `EXECUTION_ID` para construir los
   `EXECUTION_GROUP_ID` de cada política vía `agentes_politicas/POLITICAS_INDEX.py`.

3. **Lanzá todos los agentes de política disponibles EN PARALELO** (un solo mensaje, un tool call de
   `Agent` por política, pasándole `campaign_id` y `exec_id`) — cada uno analiza su política de
   forma independiente y actualiza su propia memoria. No los ejecutes secuencialmente: el requisito
   explícito del usuario es que el análisis por política sea independiente y paralelo.

4. **Juntá los resúmenes estructurados** que devuelve cada agente
   (`{slug, exec_id, users_to_impact, top_killers, segmentos_cubiertos, hallazgos_clave}`).

5. **Corré el análisis global de gaps**: extendé la query de `queries/sept2026/gen_sql.py` (misma
   CTE base `acc` sobre `EOC_CAMPAIGN_EXECUTION_DETAIL`, mismo `POLITICAS_INDEX`) agregando una CTE
   que tome el universo elegible de `CAMP_EOC_RK` (`ELIMINATED_BY_RK=false`) para este
   `EXECUTION_ID` y le reste la unión de `cid` que aparecen en `acc` (es decir, en cualquiera de los
   `EXECUTION_GROUP_ID` de las políticas del condensador) — agrupá el resultado por NISE×BHV×rating
   (mismos campos que ya trae `ACTIONABLE_COLUMNS`: `INTERNAL_RATING_BEHAVIOR_TC`,
   `INTERNAL_RATING_UPSELL_TC`, y el tag de NISE si está disponible en la misma tabla o via
   `SBOX_CREDITSSIGMA.CAMP_EOC_RK_POLICY_*`/`BT_VU_ASSUMED_INCOME__NISE_TAG` si hace falta joinear).
   Recordá exportar `CLOUDSDK_CONFIG=~/.gcloud-config` antes de correr `bq`/`gcloud`.

6. **Guardá el resultado**: agregá una entrada fechada a `agentes_politicas/memoria/GLOBAL_GAPS.md`
   (narrativa: qué segmentos aparecen sistemáticamente sin cobertura, con qué volumen, y si es
   explicable por universo/killers/política o es un hueco real) y el JSON crudo en
   `agentes_politicas/data/GLOBAL_GAPS/<exec_id>.json`.

7. **Commiteá** los cambios (memoria + data de cada política + gap global) en un commit por corrida,
   siguiendo las reglas de `CLAUDE.md` del repo (nunca `--amend`/`--force`, push solo si el usuario
   lo pide explícitamente). No toques `dashboard_eoc.html` ni nada de Sellers como parte de este
   flujo.

8. **Reportá al usuario** un resumen corto: qué política tuvo el hallazgo más relevante, y el
   tamaño/perfil del hueco global encontrado (si lo hay).
