-- Matriz BHV × Upsell de una simulación EOC
-- Alimenta la sección "Matriz de ratings" de la hoja Simulaciones, en sus 4 vistas:
-- % de clientes, límite final avg, límite actual avg y multiplicador avg.
--
-- Los ratings se leen de ACTIONABLE_COLUMNS (la foto del momento de la corrida),
-- NO de BT_VU_MODEL_RATING. Es más fiel y evita depender de VALID_FROM/VALID_TO.

WITH base AS (
  SELECT
    EXECUTION_ID,
    CAST(CUS_CUST_ID AS STRING) AS cid,
    CAMPAIGN_CONTROL_GROUP AS gc,
    CAST((SELECT e.VALUE FROM UNNEST(ACTIONABLE_COLUMNS) e
          WHERE e.NAME = 'INTERNAL_RATING_BEHAVIOR_TC' LIMIT 1) AS STRING) AS bhv,
    CAST((SELECT e.VALUE FROM UNNEST(ACTIONABLE_COLUMNS) e
          WHERE e.NAME = 'INTERNAL_RATING_UPSELL_TC' LIMIT 1) AS STRING) AS ups,
    CAST((SELECT e.VALUE FROM UNNEST(ACTIONABLE_COLUMNS) e
          WHERE e.NAME = 'general_limit' LIMIT 1) AS FLOAT64) AS lim_fin
  FROM `bq-cp-prd-o0b0uuv7cs2-furyid.campaign_schema.EOC_CAMPAIGN_EXECUTION_DETAIL`
  WHERE EXECUTION_ID IN ('[EXEC_ID_A]', '[EXEC_ID_B]')
),
pol AS (
  SELECT '[EXEC_ID_A]' AS EXECUTION_ID,
         CAST(CUS_CUST_ID AS STRING) AS cid,
         SAFE_CAST(WANDA__CURRENT_LIMIT_CCARD AS FLOAT64) AS cur
  FROM `meli-bi-data.SBOX_CREDITSSIGMA.CAMP_EOC_RK_POLICY_[EXEC_ID_A]-1`
  UNION ALL
  SELECT '[EXEC_ID_B]',
         CAST(CUS_CUST_ID AS STRING),
         SAFE_CAST(WANDA__CURRENT_LIMIT_CCARD AS FLOAT64)
  FROM `meli-bi-data.SBOX_CREDITSSIGMA.CAMP_EOC_RK_POLICY_[EXEC_ID_B]-1`
)
SELECT
  b.EXECUTION_ID,
  b.bhv,
  b.ups,
  COUNT(*)                                          AS usuarios,
  ROUND(AVG(p.cur), 0)                              AS lim_actual,
  ROUND(AVG(b.lim_fin), 0)                          AS lim_final,
  ROUND(AVG(SAFE_DIVIDE(b.lim_fin, p.cur)), 3)      AS mult
FROM base b
JOIN pol p ON b.cid = p.cid AND b.EXECUTION_ID = p.EXECUTION_ID
WHERE b.bhv IS NOT NULL AND b.ups IS NOT NULL
GROUP BY 1, 2, 3
ORDER BY 1, 2, 3;

-- Nota: las simulaciones normalmente NO tienen grupo control (COUNTIF(gc) = 0),
-- así que no hace falta el filtro `CAMPAIGN_CONTROL_GROUP = false` que sí usa
-- la matriz de la hoja Campañas. Verificarlo antes de asumirlo.
--
-- Validación: la suma de `usuarios` por EXECUTION_ID debe dar el total de
-- impactados de esa simulación (salvo filas con rating NULL, que se descartan).
