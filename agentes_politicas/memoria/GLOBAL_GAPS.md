# Memoria — Análisis global de gaps (clientes elegibles sin ninguna oferta activa)

Producida por el orquestador (`.claude/commands/run-policy-agents.md`), no por un agente de
política individual. Objetivo: encontrar combinaciones NISE×BHV×rating (u otras dimensiones de
segmentación relevantes) que **sobreviven a las reglas duras** (`CAMP_EOC_RK`,
`ELIMINATED_BY_RK=false`) pero **no son impactadas por ninguna** de las políticas del condensador
(no aparecen en `users_to_impact` de ningún `EXECUTION_GROUP_ID` de la campaña).

Distinto de "volumen sub-explotado dentro de una política" (eso vive en la memoria de cada
política individual, no acá) — esto es específicamente universo elegible **sin ninguna oferta**.

## Cómo se calcula (referencia, ver plan)

`elegibles_totales (CAMP_EOC_RK, ELIMINATED_BY_RK=false) − UNIÓN(users_to_impact de las N políticas
del condensador, vía EXECUTION_GROUP_ID)`, agrupado por segmento. Extiende la query de
`queries/sept2026/gen_sql.py` (misma CTE base `acc`, mismo `POLITICAS_INDEX`).

## Historial de corridas

_Sin corridas todavía — la primera corrida del orquestador agrega la primera entrada acá: qué
segmentos aparecen sistemáticamente sin cobertura, con qué volumen, y si es explicable por
universo/killers/política o es un hueco real que vale la pena atacar con una política nueva._
