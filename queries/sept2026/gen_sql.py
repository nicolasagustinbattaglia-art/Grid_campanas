import sys

# Orden fijo de los grupos de procesamiento de Individuos (confirmado estable
# desde el condensador de agosto/septiembre: el índice -N del EXECUTION_GROUP_ID
# siempre corresponde a la misma política, independientemente de cuántas políticas
# tenga la campaña).
POLITICAS_INDEX = [
    'REACTIVACION', 'OPF', 'JOURNEY 1A', 'PISOS', 'ADECUACION DE RENTA',
    'ACTIVACION', 'BAU', 'RIESGO MED. SOW', 'VIP MP', 'VIP MKPL',
]

def combined_sql(exec_id, n_politicas=9):
    """Métricas + matriz de ratings para el flujo multi-política (Individuos + Sellers).

    Agrupa por EXECUTION_GROUP_ID (no por POLITICA_ID de ACTIONABLE_COLUMNS):
    POLITICA_ID no siempre está poblado para políticas nuevas (confirmado con
    VIP MKPL en v12/7296 — cae en NULL) y además arrastra el problema histórico
    de "clientes duales" mal etiquetados como Sellers. El EXECUTION_GROUP_ID no
    tiene ese problema: agrupando por él, los números para las 9 políticas
    conocidas coinciden exacto con el agrupado por POLITICA_ID (verificado).
    El mapeo de índice -> nombre de política usa POLITICAS_INDEX; pasar
    n_politicas=10 (u otro valor) cuando el condensador sume/reste políticas.

    No usa SBOX_CREDITSSIGMA.CAMP_EOC_RK_POLICY_* — esa tabla quedó de un flujo
    viejo y dejó de poblarse (confirmado vía INFORMATION_SCHEMA + job history:
    ningún job la consultó jamás para las simulaciones de septiembre).

    La fuente real: ACTIONABLE_COLUMNS de EOC_CAMPAIGN_EXECUTION_DETAIL ya trae
    LIMITE_PRE_UPSELL (límite actual) sin necesidad de joins — cubre BAU, JOURNEY,
    VIP_MP, REACTIVACION, ACTIVACION, SOW_RM y ADECUACION al 100%. Para PISOS y
    OPF (y presumiblemente políticas nuevas como VIP MKPL) ese campo viene null,
    así que cae a BT_VU_CREDIT como fallback.
    """
    group_ids = ", ".join(f"'{exec_id}-{i}'" for i in range(1, n_politicas + 1))
    return f"""WITH acc AS (
  SELECT
    CAST(CUS_CUST_ID AS STRING) AS cid,
    EXECUTION_GROUP_ID,
    CAST((SELECT e.VALUE FROM UNNEST(ACTIONABLE_COLUMNS) e WHERE e.NAME='general_limit' LIMIT 1) AS FLOAT64) AS lim_final,
    CAST((SELECT e.VALUE FROM UNNEST(ACTIONABLE_COLUMNS) e WHERE e.NAME='LIMITE_PRE_UPSELL' LIMIT 1) AS FLOAT64) AS lim_pre,
    CAST((SELECT e.VALUE FROM UNNEST(ACTIONABLE_COLUMNS) e WHERE e.NAME='INTERNAL_RATING_BEHAVIOR_TC' LIMIT 1) AS STRING) AS bhv,
    CAST((SELECT e.VALUE FROM UNNEST(ACTIONABLE_COLUMNS) e WHERE e.NAME='INTERNAL_RATING_UPSELL_TC' LIMIT 1) AS STRING) AS ups
  FROM `bq-cp-prd-o0b0uuv7cs2-furyid.campaign_schema.EOC_CAMPAIGN_EXECUTION_DETAIL`
  WHERE EXECUTION_ID = '{exec_id}'
    AND EXECUTION_GROUP_ID IN ({group_ids})
),
credit AS (
  SELECT CAST(cus_cust_id AS STRING) AS cid, CREDIT_AMT
  FROM `meli-bi-data.WHOWNER.BT_VU_CREDIT`
  WHERE sit_site_id = 'MLB' AND CRD_PROD_DEF_TYPE_SK = 3 AND VALID_TO_DT = '2099-12-31'
),
joined AS (
  SELECT
    a.EXECUTION_GROUP_ID, a.bhv, a.ups, a.lim_final,
    COALESCE(a.lim_pre, c.CREDIT_AMT) AS lim_actual
  FROM acc a
  LEFT JOIN credit c ON a.cid = c.cid
)
SELECT 'METRICS' AS tipo, EXECUTION_GROUP_ID, CAST(NULL AS STRING) AS bhv, CAST(NULL AS STRING) AS ups,
  COUNT(*) AS usuarios,
  ROUND(AVG(lim_actual),0) AS lim_actual,
  ROUND(AVG(lim_final),0) AS lim_final,
  ROUND(AVG(SAFE_DIVIDE(lim_final,lim_actual)),2) AS mult,
  ROUND(SUM(lim_final-lim_actual),0) AS exposicion
FROM joined GROUP BY EXECUTION_GROUP_ID

UNION ALL

SELECT 'RATING' AS tipo, EXECUTION_GROUP_ID, bhv, ups,
  COUNT(*) AS usuarios,
  ROUND(AVG(lim_actual),0) AS lim_actual,
  ROUND(AVG(lim_final),0) AS lim_final,
  ROUND(AVG(SAFE_DIVIDE(lim_final,lim_actual)),3) AS mult,
  CAST(NULL AS FLOAT64) AS exposicion
FROM joined
WHERE bhv IS NOT NULL AND ups IS NOT NULL
GROUP BY EXECUTION_GROUP_ID, bhv, ups
ORDER BY tipo, EXECUTION_GROUP_ID, bhv, ups;"""

if __name__ == '__main__':
    exec_id = sys.argv[1]
    n = int(sys.argv[2]) if len(sys.argv) > 2 else 9
    print(combined_sql(exec_id, n))
