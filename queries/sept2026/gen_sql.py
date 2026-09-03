import sys

def pol_union(exec_id, n=9):
    parts = []
    for i in range(1, n+1):
        parts.append(f"SELECT '{exec_id}-{i}' AS GRP, CAST(CUS_CUST_ID AS STRING) AS cid, SAFE_CAST(WANDA__CURRENT_LIMIT_CCARD AS FLOAT64) AS cur FROM `meli-bi-data.SBOX_CREDITSSIGMA.CAMP_EOC_RK_POLICY_{exec_id}-{i}`")
    return "\n  UNION ALL ".join(parts)

def metrics_sql(exec_id):
    return f"""WITH acc AS (
  SELECT
    CAST(CUS_CUST_ID AS STRING) AS cid,
    EXECUTION_GROUP_ID,
    CAST((SELECT elem.VALUE FROM UNNEST(ACTIONABLE_COLUMNS) elem WHERE elem.NAME = 'POLITICA_ID' LIMIT 1) AS STRING) AS politica,
    CAST((SELECT e.VALUE FROM UNNEST(ACTIONABLE_COLUMNS) e WHERE e.NAME = 'general_limit' LIMIT 1) AS FLOAT64) AS general_limit
  FROM `bq-cp-prd-o0b0uuv7cs2-furyid.campaign_schema.EOC_CAMPAIGN_EXECUTION_DETAIL`
  WHERE EXECUTION_ID = '{exec_id}'
),
pol AS (
  {pol_union(exec_id)}
)
SELECT
  a.politica,
  COUNT(*) AS usuarios,
  ROUND(AVG(p.cur), 0) AS lim_actual,
  ROUND(AVG(a.general_limit), 0) AS lim_final,
  ROUND(AVG(SAFE_DIVIDE(a.general_limit, p.cur)), 2) AS mult,
  ROUND(SUM(a.general_limit - p.cur), 0) AS exposicion
FROM acc a
JOIN pol p ON a.cid = p.cid AND a.EXECUTION_GROUP_ID = p.GRP
GROUP BY 1
ORDER BY usuarios DESC;"""

def rating_sql(exec_id):
    return f"""WITH acc AS (
  SELECT
    CAST(CUS_CUST_ID AS STRING) AS cid,
    EXECUTION_GROUP_ID,
    CAST((SELECT elem.VALUE FROM UNNEST(ACTIONABLE_COLUMNS) elem WHERE elem.NAME = 'POLITICA_ID' LIMIT 1) AS STRING) AS politica,
    CAST((SELECT e.VALUE FROM UNNEST(ACTIONABLE_COLUMNS) e WHERE e.NAME = 'INTERNAL_RATING_BEHAVIOR_TC' LIMIT 1) AS STRING) AS bhv,
    CAST((SELECT e.VALUE FROM UNNEST(ACTIONABLE_COLUMNS) e WHERE e.NAME = 'INTERNAL_RATING_UPSELL_TC' LIMIT 1) AS STRING) AS ups,
    CAST((SELECT e.VALUE FROM UNNEST(ACTIONABLE_COLUMNS) e WHERE e.NAME = 'general_limit' LIMIT 1) AS FLOAT64) AS lim_fin
  FROM `bq-cp-prd-o0b0uuv7cs2-furyid.campaign_schema.EOC_CAMPAIGN_EXECUTION_DETAIL`
  WHERE EXECUTION_ID = '{exec_id}'
),
pol AS (
  {pol_union(exec_id)}
)
SELECT
  a.politica,
  a.bhv,
  a.ups,
  COUNT(*) AS usuarios,
  ROUND(AVG(p.cur), 0) AS lim_actual,
  ROUND(AVG(a.lim_fin), 0) AS lim_final,
  ROUND(AVG(SAFE_DIVIDE(a.lim_fin, p.cur)), 3) AS mult
FROM acc a
JOIN pol p ON a.cid = p.cid AND a.EXECUTION_GROUP_ID = p.GRP
WHERE a.bhv IS NOT NULL AND a.ups IS NOT NULL
GROUP BY 1, 2, 3
ORDER BY 1, 2, 3;"""

if __name__ == '__main__':
    kind, exec_id = sys.argv[1], sys.argv[2]
    print(metrics_sql(exec_id) if kind == 'metrics' else rating_sql(exec_id))
