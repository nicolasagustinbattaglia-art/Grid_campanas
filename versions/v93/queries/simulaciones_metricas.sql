-- Métricas generales de una simulación EOC (GC + GI)
-- Alimenta las 5 cards de "Métricas generales" de la hoja Simulaciones.
--
-- Reemplazar [EXEC_ID_A] / [EXEC_ID_B] por los execution_id de cada simulación.
-- Las simulaciones de 1 grupo usan el sufijo -1 en las tablas SBOX.
-- No requiere BQ Sessions: son CTEs directas (a diferencia del flujo mensual de Individuos).

WITH acc AS (
  SELECT
    EXECUTION_ID,
    CAST(CUS_CUST_ID AS STRING) AS cid,
    CAST((SELECT e.VALUE FROM UNNEST(ACTIONABLE_COLUMNS) e
          WHERE e.NAME = 'general_limit' LIMIT 1) AS FLOAT64) AS general_limit
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
  a.EXECUTION_ID,
  COUNT(*)                                          AS usuarios,
  ROUND(AVG(p.cur), 0)                              AS lim_actual,
  ROUND(AVG(a.general_limit), 0)                    AS lim_final,
  ROUND(AVG(SAFE_DIVIDE(a.general_limit, p.cur)), 2) AS mult,
  ROUND(SUM(a.general_limit - p.cur), 0)            AS exposicion
FROM acc a
JOIN pol p ON a.cid = p.cid AND a.EXECUTION_ID = p.EXECUTION_ID
GROUP BY 1;

-- Validación: `usuarios` debe coincidir exacto con processing_funnel.users_to_impact
-- que devuelve get_campaign_execution_dashboard para esa simulación.
