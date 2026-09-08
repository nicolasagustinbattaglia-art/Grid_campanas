import sys

POLITICAS = ('BAU','PISOS','OPF','VIP_MP','SOW_RM','REACTIVACION','ACTIVACION','JOURNEY','ADECUACION')

def combined_sql(exec_id):
    """Métricas + matriz de ratings en una sola query, para el flujo multi-política
    (Individuos + Sellers). No usa SBOX_CREDITSSIGMA.CAMP_EOC_RK_POLICY_* — esa tabla
    quedó de un flujo viejo y dejó de poblarse (confirmado vía INFORMATION_SCHEMA:
    ninguna tabla de ese patrón se creó después del 2026-08-31, y ningún job de
    BigQuery la consultó jamás para las simulaciones de septiembre).

    La fuente real: ACTIONABLE_COLUMNS de EOC_CAMPAIGN_EXECUTION_DETAIL ya trae
    LIMITE_PRE_UPSELL (límite actual) sin necesidad de joins — cubre BAU, JOURNEY,
    VIP_MP, REACTIVACION, ACTIVACION, SOW_RM y ADECUACION al 100%. Para PISOS y OPF
    ese campo viene null, así que cae a BT_VU_CREDIT como fallback."""
    return f"""WITH acc AS (
  SELECT
    CAST(CUS_CUST_ID AS STRING) AS cid,
    CAST((SELECT elem.VALUE FROM UNNEST(ACTIONABLE_COLUMNS) elem WHERE elem.NAME='POLITICA_ID' LIMIT 1) AS STRING) AS politica,
    CAST((SELECT e.VALUE FROM UNNEST(ACTIONABLE_COLUMNS) e WHERE e.NAME='general_limit' LIMIT 1) AS FLOAT64) AS lim_final,
    CAST((SELECT e.VALUE FROM UNNEST(ACTIONABLE_COLUMNS) e WHERE e.NAME='LIMITE_PRE_UPSELL' LIMIT 1) AS FLOAT64) AS lim_pre,
    CAST((SELECT e.VALUE FROM UNNEST(ACTIONABLE_COLUMNS) e WHERE e.NAME='INTERNAL_RATING_BEHAVIOR_TC' LIMIT 1) AS STRING) AS bhv,
    CAST((SELECT e.VALUE FROM UNNEST(ACTIONABLE_COLUMNS) e WHERE e.NAME='INTERNAL_RATING_UPSELL_TC' LIMIT 1) AS STRING) AS ups
  FROM `bq-cp-prd-o0b0uuv7cs2-furyid.campaign_schema.EOC_CAMPAIGN_EXECUTION_DETAIL`
  WHERE EXECUTION_ID = '{exec_id}'
),
credit AS (
  SELECT CAST(cus_cust_id AS STRING) AS cid, CREDIT_AMT
  FROM `meli-bi-data.WHOWNER.BT_VU_CREDIT`
  WHERE sit_site_id = 'MLB' AND CRD_PROD_DEF_TYPE_SK = 3 AND VALID_TO_DT = '2099-12-31'
),
joined AS (
  SELECT
    a.politica, a.bhv, a.ups, a.lim_final,
    COALESCE(a.lim_pre, c.CREDIT_AMT) AS lim_actual
  FROM acc a
  LEFT JOIN credit c ON a.cid = c.cid
  WHERE a.politica IN {POLITICAS}
)
SELECT 'METRICS' AS tipo, politica, CAST(NULL AS STRING) AS bhv, CAST(NULL AS STRING) AS ups,
  COUNT(*) AS usuarios,
  ROUND(AVG(lim_actual),0) AS lim_actual,
  ROUND(AVG(lim_final),0) AS lim_final,
  ROUND(AVG(SAFE_DIVIDE(lim_final,lim_actual)),2) AS mult,
  ROUND(SUM(lim_final-lim_actual),0) AS exposicion
FROM joined GROUP BY politica

UNION ALL

SELECT 'RATING' AS tipo, politica, bhv, ups,
  COUNT(*) AS usuarios,
  ROUND(AVG(lim_actual),0) AS lim_actual,
  ROUND(AVG(lim_final),0) AS lim_final,
  ROUND(AVG(SAFE_DIVIDE(lim_final,lim_actual)),3) AS mult,
  CAST(NULL AS FLOAT64) AS exposicion
FROM joined
WHERE bhv IS NOT NULL AND ups IS NOT NULL
GROUP BY politica, bhv, ups
ORDER BY tipo, politica, bhv, ups;"""

if __name__ == '__main__':
    exec_id = sys.argv[1]
    print(combined_sql(exec_id))
