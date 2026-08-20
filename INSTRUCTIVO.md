# PROMPT: Actualizar Dashboard EOC Condensador en Grid

Pegá este bloque completo en Claude Code (con el plugin EOC y gcloud configurados).
Reemplazá los valores entre `[CORCHETES]` antes de ejecutar.

---

## ⚡ FLUJO COMPLETO EN UN SOLO PASO

Cuando el analista pase el nombre de una campaña, Claude debe:
1. Hacer las preguntas del **Paso 0** (empezando por individuos vs sellers) y esperar respuestas
2. Con las respuestas, elegir el flujo correcto:
   - **Individuos** → Partes 1–6 (funnels, métricas, NISE, GC/GI, ratings, competencia)
   - **Sellers** → Parte Sellers (queries CTE directas, sin NISE, sin ratings, antigüedad en 3 buckets)
3. Ejecutar todo el flujo de forma autónoma y subir al Grid en una sola versión final

**No pedir confirmación entre pasos** — solo reportar el resultado final con un resumen de todo lo que se cargó.

---

## SETUP PREVIO — Verificar antes de empezar

Hacer esto **una sola vez por máquina** (o si el token expiró).

### 1. Autenticación BigQuery

```bash
gcloud auth application-default login
gcloud auth application-default set-quota-project meli-bi-data
```

El primer comando abre el browser para loguear con tu cuenta Meli. El segundo fija el proyecto de quota para que las queries vayan contra `meli-bi-data`.

### 2. Verificar acceso a BQ

Correr esta query en BigQuery (o desde Python) para confirmar que tenés acceso a las tablas necesarias:

```sql
-- Tabla de ejecuciones EOC (siempre accesible)
SELECT COUNT(*) FROM `bq-cp-prd-o0b0uuv7cs2-furyid.campaign_schema.EOC_CAMPAIGN_EXECUTION_DETAIL` LIMIT 1;

-- Tablas SBOX (permisos individuales — reemplazar con un EXEC_ID real)
SELECT COUNT(*) FROM `meli-bi-data.SBOX_CREDITSSIGMA.CAMP_EOC_RK_POLICY_[EXEC_ID]-1` LIMIT 1;

-- Modelos de rating
SELECT COUNT(*) FROM `meli-bi-data.WHOWNER.BT_VU_MODEL_RATING` WHERE SIT_SITE_ID = 'MLB' LIMIT 1;

-- Antigüedad de crédito
SELECT COUNT(*) FROM `meli-bi-data.WHOWNER.BT_VU_CREDIT` WHERE SIT_SITE_ID = 'MLB' LIMIT 1;
```

Si alguna tira `403 Access Denied` → pedir acceso al equipo de data antes de continuar.

> **Nota:** `BT_VU_ASSUMED_INCOME` suele dar 403. No es un problema — el dashboard no usa ese campo. El NISE tag viene de las tablas SBOX directamente (campo `BT_VU_ASSUMED_INCOME__NISE_TAG`).

### 3. Verificar Python con cliente BQ

```bash
python3 -c "from google.cloud import bigquery; print('OK')"
```

Si da `ModuleNotFoundError`: usar `/usr/bin/python3` (Python 3.9 del sistema suele tener el paquete instalado). Verificar con `/usr/bin/python3 -c "from google.cloud import bigquery; print('OK')"`.

### 4. EOC MCP

Verificar que el skill `eoc-ops:eoc-analyst` esté disponible en tu Claude Code (aparece en la lista de skills). Si no aparece:
- Pedir al equipo que comparta el plugin
- O usar el fallback HTTP documentado al final del instructivo (requiere `~/.mcp-remote-proxy/venv/` instalado)

### 5. VPN

Todo lo anterior (Grid + EOC + BQ) requiere **VPN Meli activa**. Si una llamada falla con redirect a `zscaler` o `artl-gateway`, reconectar VPN y reintentar.

---

## PASO 0 — PREGUNTAS OBLIGATORIAS ANTES DE EMPEZAR

Antes de tocar ningún dato, Claude debe hacer las siguientes preguntas al analista.
**No avanzar hasta tener todas las respuestas.**

```
Antes de cargar la campaña, necesito que me confirmes:

0. ¿Esta carga es de Individuos o Sellers?
   → INDIVIDUOS: grupos 1-9, métricas con NISE + Ratings + Antigüedad
   → SELLERS: grupos 10-15 (BAU/PISOS/OPF × PF LT/SMB), solo Antigüedad (3 buckets)
   Con la respuesta elijo el flujo correcto.

--- Si es INDIVIDUOS, también responder: ---

1. ¿Hubo killers NUEVOS esta campaña vs el mes anterior?
   → Si SÍ: ¿cuáles son? ¿aplican a TODAS las políticas o solo a algunas?
   → Para cada killer nuevo: ¿qué hace / qué condición aplica? (para cargarlo en el buscador)

2. ¿Hubo killers ELIMINADOS vs el mes anterior?
   → Si SÍ: ¿cuáles son? ¿aplican a TODAS las políticas o solo a algunas?

3. ¿Hubo killers MODIFICADOS (mismo nombre pero lógica/umbral diferente)?
   → Si SÍ: ¿cuáles son? ¿qué cambió exactamente?
   → Para cada killer modificado: ¿cuál es el nuevo comportamiento?

4. ¿Hubo cambios en las políticas (límites, RCI, topes, multiplicadores, etc.) vs el mes anterior?
   → Si SÍ: ¿qué cambió? ¿en qué políticas?

5. ¿Hay algún otro contexto de negocio relevante para este mes
   (ej: cambio de modelo, nueva segmentación, test específico)?

--- Si es SELLERS: ---

Solo necesito el nombre de la campaña y la fecha de ejecución.
Los sellers no tienen novedades por killer separadas — el flujo es más acotado
(métricas generales + antigüedad por grupo, sin NISE ni ratings).
```

Con las respuestas de individuos, Claude va a:
- Anotar los killers nuevos con ícono 🟢 (KILLER_NOTES en el HTML)
- Anotar los killers eliminados con ícono 🔴
- Anotar los killers modificados con ícono 🟡
- Agregar/actualizar las definiciones de negocio en `KILLER_DEFS` para que aparezcan en el buscador
- Cargar los comentarios del mes en la sección "Novedades del período" del dashboard

---

## CONTEXTO

Dashboard HTML del Condensador EOC:
https://grid.adminml.com/d/01KVB1DRFMEQYZ4THQ3SGHM3AR/view

Repo local con el HTML, las queries y los datos: `/Users/nbattaglia/Documents/tablero-upsell/`

### Navegación

```
UPSELL INDIVIDUOS  |  UPSELL SELLERS      ← nav de producto
  ├─ Campañas               ← comparación mes a mes (todo este instructivo)
  ├─ Simulaciones           ← versiones de un experimento (ver flujo al final)
  └─ Historial de cambios   ← qué cambió mes a mes, declarado y verificado
```

Las sub-hojas **existen sólo dentro de Upsell Individuos**. Al pasar a Sellers la barra desaparece.
Todo lo que sigue (Partes 1–6 y flujo Sellers) aplica a la sub-hoja **Campañas**.

El dashboard tiene **dos modos**:

**Por política seleccionada:**
1. **Header de campaña** — nombre y fecha de las dos campañas comparadas
2. **Métricas generales (GC + GI)** — límite actual, final, multiplicador, exposición
3. **Novedades del período** — cambios del mes para la política seleccionada
4. **Funnel de killers** — cascada comparativa entre dos meses, con hover de definición
5. **Apertura GC/GI** — mismas métricas separadas por grupo control e impacto
6. **Apertura dinámica** — breakdown por NISE/Antigüedad/Ratings con opción consolidado o GC/GI (en GC/GI muestra Δ vs GC automáticamente)
7. **Distribución** — donuts de NISE y Antigüedad + matriz cruzada BHV × Upsell con colores semánticos
8. **Buscador de killers** — busca cualquier killer y muestra definición + fórmula técnica

**Vista Consolidado (todas las políticas):**
- Totales GI/GC (usuarios + exposición)
- Apertura por política — GI: Usuarios, Δ%, Lim. Act., Δ%, Lim. Fin., Δ%, Mult., Δ, Exposición, Δ%
- Competencia de políticas — tablas por etapa (ESPECIALES + RIESGO MEDIO / PRIORIZACION) con audiencia, descartados y % descarte comparado

**Campaña a cargar:** `[NOMBRE_EXACTO_DE_LA_CAMPAÑA_EN_EOC]`
**Nombre del mes en el dashboard:** `[Ej: Ago-26]`
**Fecha de ejecución de la campaña:** `[Ej: 2026-08-15]` ← necesario para query de ingresos y header

---

## ──────────────────────────────────────────
## FLUJO INDIVIDUOS (grupos 1–9)
## ──────────────────────────────────────────

## PARTE 1 — FUNNEL DE KILLERS

### Paso 1: Descargar el HTML actual desde Grid

```
Herramienta: Grid skill — download_doc_id: 01KVB1DRFMEQYZ4THQ3SGHM3AR
```

Guardarlo localmente como `dashboard_eoc.html`.

### Paso 2: Buscar la campaña en EOC

```
Herramienta: get_campaigns
campaign_type: CAMPAIGN
q: [NOMBRE_EXACTO_DE_LA_CAMPAÑA]
site: MLB
```

Anotar: `campaign_id`, `execution_id`, `execution_state`, `sent_at` (fecha de ejecución).
Preferir campañas en estado **DONE** — si está en PENDING el dashboard de ejecución puede fallar.

### Paso 3a: Dashboard con killers

```
Herramienta: get_campaign_execution_dashboard
campaign_id: [EL QUE OBTUVISTE]
include: killer_rules
```

Si da timeout/circuit breaker: reintentar 3-5 veces. Si persiste, reportar a #feedback-mcp-eoc.

**Extraer por cada grupo:**
- `group_name`, `processing_funnel.total_users`, `processing_funnel.users_to_impact`, `processing_funnel.excluded_by_policy`
- `killer_rules[]`: `name` + `accumulated_users` en orden exacto (no reordenar)

### Paso 3b: Dashboard con excepciones de política

```
Herramienta: get_campaign_execution_dashboard
campaign_id: [EL QUE OBTUVISTE]
include: policy
```

**Extraer por cada grupo:**
- `policy.excluded_by_attributes` → usuarios excluidos por atributos de corte de la política
- `policy.exceptions[]` → killers internos de la política: `name` + `accumulated_users`

**Cálculo del acumulado para "Detalle por atributos de corte":**
```python
after_killers = users_to_impact + excluded_by_policy
atributos_accumulated = after_killers - policy["excluded_by_attributes"]
```

**Estructura final del funnel** (agregar campo `policy` a cada grupo):
```javascript
"BAU": {
  "total": N,
  "killers": [...],   // de Paso 3a
  "policy": {
    "name": "...",
    "atributos_accumulated": N,   // calculado arriba
    "exceptions": [
      {"name": "KILLER RCI CONJUNTA < TOPE CONJUNTO (TC OPTIN)", "accumulated": N},
      // ... todas las excepciones en orden
    ]
  }
}
```

El dashboard muestra: killers → "Detalle por atributos de corte" → excepciones de política → impactados finales.

### Paso 4: Guardar JSON de referencia

```python
import json
reference = {
    "campaign_name": "[NOMBRE]", "execution_id": "[EXEC_ID]",
    "groups": [{
        "group_name": g["group_name"],
        "total_users": g["processing_funnel"]["total_users"],
        "users_to_impact": g["processing_funnel"]["users_to_impact"],
        "killer_rules": [{"name": k["name"], "accumulated_users": k["accumulated_users"]}
                         for k in g["killer_rules"]]
    } for g in dashboard["processing_group_dashboard"]]
}
with open("eoc_reference_[MES].json", "w") as f:
    json.dump(reference, f, ensure_ascii=False, indent=2)
```

### Paso 5: Inyectar funnels en el HTML

```javascript
const [MES]_FUNNELS = {
  "REACTIVACION": { "total": N, "killers": [{"name": "K-...", "accumulated": N}, ...] },
  "OPF": { ... }, "JOURNEY 1A": { ... }, "PISOS": { ... },
  "ADECUACION DE RENTA": { ... },  // nombre exacto con "DE RENTA"
  "ACTIVACION": { ... }, "BAU": { ... },
  "RIESGO MED. SOW": { ... },       // nombre exacto
  "VIP MP": { ... }
};
```

### Paso 6: Agregar el mes al objeto MONTHS (formato completo)

```javascript
"[MES]": {
  rating_matrix: [MES]_RATING_MATRIX,  // se carga en Parte 5
  metrics: [MES]_METRICS,              // se carga en Parte 2
  nise: [MES]_NISE,                    // se carga en Parte 2
  funnels: [MES]_FUNNELS,              // se cargó en Paso 5
  gc_pol: [MES]_GC_POL,               // se carga en Parte 3
  gc_dim: [MES]_GC_DIM,               // se carga en Parte 3
  competencia: [MES]_COMPETENCIA,      // se carga en Parte 6
  meta: {
    campaign: "[NOMBRE_CAMPAÑA]",
    fecha: "[FECHA_CORRIDA]",           // formato YYYY-MM-DD
    exec_id: "[EXEC_ID]",
    campaign_id: [CAMPAIGN_ID],         // necesario para la URL de EOC
    eoc_url: "https://credits-admin.adminml.com/eoc/campaigns/audience/[CAMPAIGN_ID]?executionId=[EXEC_ID]&tab=campaign"
  }
},
```

**Orden en MONTHS:** el objeto está ordenado newest-first. Insertar el nuevo mes **antes** del mes anterior en el objeto MONTHS.

**Selectores:** `selMonthA` y `selMonthB` se populan automáticamente con `Object.keys(MONTHS)` — no hace falta modificar HTML adicional.

### Paso 7: KILLER_NOTES — anotar cambios del mes

Basándote en las respuestas del Paso 0:

```javascript
const KILLER_NOTES = {
  // 🟢 Nuevo: agregar nota en el MES NUEVO
  "[POLITICA]": {
    "[NOMBRE_KILLER]": { "[MES]": "Killer nuevo en [MES]: [qué hace]." }
  },
  // 🔴 Eliminado: agregar nota en el MES ANTERIOR (donde aún existía)
  "[POLITICA]": {
    "[NOMBRE_KILLER]": { "[MES_ANTERIOR]": "Killer eliminado en [MES]: [descripción]." }
  },
  // 🟡 Modificado
  "[POLITICA]": {
    "[NOMBRE_KILLER]": { "[MES]": "Modificado en [MES]: [qué cambió]." }
  }
};
```

### Paso 7b: KILLER_DEFS — agregar/actualizar definiciones

Si hay killers nuevos o modificados, actualizar el objeto `KILLER_DEFS` del HTML con su definición para el buscador:

```javascript
const KILLER_DEFS = {
  // ... definiciones existentes ...
  "[NOMBRE_KILLER_NUEVO]": {
    "type": "Regla de exclusión",   // o "Regla de selección"
    "negocio": "[Descripción en lenguaje de negocio que proporcionó el analista]",
    "tecnica": "Fórmula: `=A`\nA: `VARIABLE` Condición Valor"
  }
};
```

La definición técnica se puede obtener automáticamente desde EOC:
```
Herramienta: get_campaign_detail
campaign_id: [CAMPAIGN_ID]
sections: ["rules_killers"]
```
Y parsear las condiciones del killer específico.

### Paso 8: MONTH_COMMENTS — novedades del período

```javascript
const MONTH_COMMENTS = {
  "[MES]": [
    "[Comentario sobre killers nuevos/eliminados/modificados]",
    "[Comentario sobre cambios en políticas si los hay]",
    "[Contexto de negocio adicional del Paso 0]"
  ]
};
```

### Paso 9: DOBLE-CHECK — verificación killer por killer

```python
import json, re

with open("eoc_reference_[MES].json") as f:
    eoc = json.load(f)
with open("dashboard_eoc.html") as f:
    html = f.read()

matches = re.findall(r'const [A-Z0-9_]+_FUNNELS = ({.*?}) ;', html, re.DOTALL)
loaded = json.loads(matches[-1])

errors = []
total = 0
for group in eoc["groups"]:
    gname = group["group_name"]
    if gname not in loaded:
        errors.append(f"MISSING GROUP: {gname}"); continue
    eoc_k = group["killer_rules"]
    load_k = loaded[gname]["killers"]
    if len(eoc_k) != len(load_k):
        errors.append(f"{gname}: EOC={len(eoc_k)} HTML={len(load_k)}"); continue
    for i, (e, l) in enumerate(zip(eoc_k, load_k)):
        total += 1
        if e["name"] != l["name"]:
            errors.append(f"{gname}[{i}] NOMBRE: EOC='{e['name']}' HTML='{l['name']}'")
        if e["accumulated_users"] != l["accumulated"]:
            errors.append(f"{gname}[{i}] ACUMULADO '{e['name']}': EOC={e['accumulated_users']} HTML={l['accumulated']}")

if errors:
    print(f"❌ {len(errors)} DIFERENCIAS:"); [print(f"  - {e}") for e in errors]
else:
    print(f"✅ DOBLE-CHECK OK — {total} killers verificados, 0 diferencias")
```

**Si hay diferencias: corregir y re-verificar antes de subir.**

### Paso 10: Subir al Grid

Solo si el doble-check pasó con 0 diferencias:

```
Herramienta: Grid skill
doc_id: 01KVB1DRFMEQYZ4THQ3SGHM3AR
file_new_version: true
```

---

## PARTE 2 — MÉTRICAS GENERALES Y NISE

### Verificar datos BQ

```sql
SELECT EXECUTION_GROUP_ID, COUNT(*) as usuarios
FROM `bq-cp-prd-o0b0uuv7cs2-furyid.campaign_schema.EOC_CAMPAIGN_EXECUTION_DETAIL`
WHERE EXECUTION_ID = '[EXEC_ID]'
GROUP BY 1 ORDER BY 1
```

Si retorna 9 grupos → continuar. Si retorna 0 → campaña sin datos aún.

### Query completa (reemplazar [EXEC_ID] y [FECHA_CORRIDA])

> **⚠ BQ Sessions requeridas:** las queries usan tablas temporales (`BASE_CONDENSADOR`, `BASE_FULL`) que no persisten entre jobs independientes. Hay que correr todo dentro de una misma sesión BQ. En Python: `QueryJobConfig(create_session=True)` en el primer job, luego pasar el `session_id` en los siguientes via `ConnectionProperty("session_id", session_id)`.

> **⚠ `BT_VU_ASSUMED_INCOME` sin acceso (403):** el dashboard no muestra RCI ni ingreso asumido — esos campos no se renderizan en el HTML. La NISE tag viene directamente de `SBOX_CREDITSSIGMA.CAMP_EOC_RK_POLICY_*` (campo `BT_VU_ASSUMED_INCOME__NISE_TAG`), que sí es accesible. No hay que joinear `BT_VU_ASSUMED_INCOME`.

```sql
-- JOB 1 (create_session=True): crear tablas base
CREATE OR REPLACE TEMP TABLE BASE_CONDENSADOR AS
SELECT *,
  CAST((SELECT elem.VALUE FROM UNNEST(ACTIONABLE_COLUMNS) elem WHERE elem.NAME = 'POLITICA_ID' LIMIT 1) AS STRING) AS POLITICA
FROM `bq-cp-prd-o0b0uuv7cs2-furyid.campaign_schema.EOC_CAMPAIGN_EXECUTION_DETAIL`
WHERE EXECUTION_ID = '[EXEC_ID]';

CREATE OR REPLACE TEMP TABLE BASE_FULL AS
WITH ALL_POLICY AS (
  SELECT POL.CUS_CUST_ID, POL.WANDA__CURRENT_LIMIT_CCARD, POL.BT_VU_ASSUMED_INCOME__NISE_TAG, RK.eliminated_by_rk, '[EXEC_ID]-1' AS GRP
  FROM `meli-bi-data.SBOX_CREDITSSIGMA.CAMP_EOC_RK_POLICY_[EXEC_ID]-1` POL INNER JOIN `meli-bi-data.SBOX_CREDITSSIGMA.CAMP_EOC_RK_[EXEC_ID]-1` RK ON POL.CUS_CUST_ID = RK.CUS_CUST_ID
  UNION ALL SELECT POL.CUS_CUST_ID, POL.WANDA__CURRENT_LIMIT_CCARD, POL.BT_VU_ASSUMED_INCOME__NISE_TAG, RK.eliminated_by_rk, '[EXEC_ID]-2'
  FROM `meli-bi-data.SBOX_CREDITSSIGMA.CAMP_EOC_RK_POLICY_[EXEC_ID]-2` POL INNER JOIN `meli-bi-data.SBOX_CREDITSSIGMA.CAMP_EOC_RK_[EXEC_ID]-2` RK ON POL.CUS_CUST_ID = RK.CUS_CUST_ID
  UNION ALL SELECT POL.CUS_CUST_ID, POL.WANDA__CURRENT_LIMIT_CCARD, POL.BT_VU_ASSUMED_INCOME__NISE_TAG, RK.eliminated_by_rk, '[EXEC_ID]-3'
  FROM `meli-bi-data.SBOX_CREDITSSIGMA.CAMP_EOC_RK_POLICY_[EXEC_ID]-3` POL INNER JOIN `meli-bi-data.SBOX_CREDITSSIGMA.CAMP_EOC_RK_[EXEC_ID]-3` RK ON POL.CUS_CUST_ID = RK.CUS_CUST_ID
  UNION ALL SELECT POL.CUS_CUST_ID, POL.WANDA__CURRENT_LIMIT_CCARD, POL.BT_VU_ASSUMED_INCOME__NISE_TAG, RK.eliminated_by_rk, '[EXEC_ID]-4'
  FROM `meli-bi-data.SBOX_CREDITSSIGMA.CAMP_EOC_RK_POLICY_[EXEC_ID]-4` POL INNER JOIN `meli-bi-data.SBOX_CREDITSSIGMA.CAMP_EOC_RK_[EXEC_ID]-4` RK ON POL.CUS_CUST_ID = RK.CUS_CUST_ID
  UNION ALL SELECT POL.CUS_CUST_ID, POL.WANDA__CURRENT_LIMIT_CCARD, POL.BT_VU_ASSUMED_INCOME__NISE_TAG, RK.eliminated_by_rk, '[EXEC_ID]-5'
  FROM `meli-bi-data.SBOX_CREDITSSIGMA.CAMP_EOC_RK_POLICY_[EXEC_ID]-5` POL INNER JOIN `meli-bi-data.SBOX_CREDITSSIGMA.CAMP_EOC_RK_[EXEC_ID]-5` RK ON POL.CUS_CUST_ID = RK.CUS_CUST_ID
  UNION ALL SELECT POL.CUS_CUST_ID, POL.WANDA__CURRENT_LIMIT_CCARD, POL.BT_VU_ASSUMED_INCOME__NISE_TAG, RK.eliminated_by_rk, '[EXEC_ID]-6'
  FROM `meli-bi-data.SBOX_CREDITSSIGMA.CAMP_EOC_RK_POLICY_[EXEC_ID]-6` POL INNER JOIN `meli-bi-data.SBOX_CREDITSSIGMA.CAMP_EOC_RK_[EXEC_ID]-6` RK ON POL.CUS_CUST_ID = RK.CUS_CUST_ID
  UNION ALL SELECT POL.CUS_CUST_ID, POL.WANDA__CURRENT_LIMIT_CCARD, POL.BT_VU_ASSUMED_INCOME__NISE_TAG, RK.eliminated_by_rk, '[EXEC_ID]-7'
  FROM `meli-bi-data.SBOX_CREDITSSIGMA.CAMP_EOC_RK_POLICY_[EXEC_ID]-7` POL INNER JOIN `meli-bi-data.SBOX_CREDITSSIGMA.CAMP_EOC_RK_[EXEC_ID]-7` RK ON POL.CUS_CUST_ID = RK.CUS_CUST_ID
  UNION ALL SELECT POL.CUS_CUST_ID, POL.WANDA__CURRENT_LIMIT_CCARD, POL.BT_VU_ASSUMED_INCOME__NISE_TAG, RK.eliminated_by_rk, '[EXEC_ID]-8'
  FROM `meli-bi-data.SBOX_CREDITSSIGMA.CAMP_EOC_RK_POLICY_[EXEC_ID]-8` POL INNER JOIN `meli-bi-data.SBOX_CREDITSSIGMA.CAMP_EOC_RK_[EXEC_ID]-8` RK ON POL.CUS_CUST_ID = RK.CUS_CUST_ID
  UNION ALL SELECT POL.CUS_CUST_ID, POL.WANDA__CURRENT_LIMIT_CCARD, POL.BT_VU_ASSUMED_INCOME__NISE_TAG, RK.eliminated_by_rk, '[EXEC_ID]-9'
  FROM `meli-bi-data.SBOX_CREDITSSIGMA.CAMP_EOC_RK_POLICY_[EXEC_ID]-9` POL INNER JOIN `meli-bi-data.SBOX_CREDITSSIGMA.CAMP_EOC_RK_[EXEC_ID]-9` RK ON POL.CUS_CUST_ID = RK.CUS_CUST_ID
)
SELECT B.CUS_CUST_ID, B.POLITICA, B.CAMPAIGN_CONTROL_GROUP,
  SAFE_CAST(P.WANDA__CURRENT_LIMIT_CCARD AS FLOAT64) AS CURRENT_LIMIT,
  CAST((SELECT elem.VALUE FROM UNNEST(B.ACTIONABLE_COLUMNS) elem WHERE elem.NAME = 'general_limit' LIMIT 1) AS FLOAT64) AS GENERAL_LIMIT,
  CASE P.BT_VU_ASSUMED_INCOME__NISE_TAG
    WHEN 'BRONZE' THEN 'a.bronze' WHEN 'SILVER' THEN 'b.silver'
    WHEN 'GOLD' THEN 'c.gold' WHEN 'PLATINUM' THEN 'd.platinum'
  END AS NISE_ORDENADO,  -- ⚠ normalizar a 'Bronze'/'Silver'/'Gold'/'Platinum' al inyectar (ver abajo)
  CAST((SELECT elem.VALUE FROM UNNEST(B.ACTIONABLE_COLUMNS) elem WHERE elem.NAME = 'INTERNAL_RATING_UPSELL_TC' LIMIT 1) AS STRING) AS RATING_UPSELL,
  CAST((SELECT elem.VALUE FROM UNNEST(B.ACTIONABLE_COLUMNS) elem WHERE elem.NAME = 'INTERNAL_RATING_BEHAVIOR_TC' LIMIT 1) AS STRING) AS RATING_BHV,
  CAST((SELECT elem.VALUE FROM UNNEST(B.ACTIONABLE_COLUMNS) elem WHERE elem.NAME = 'PAGO_MIN_TC_UPS' LIMIT 1) AS FLOAT64) AS PAGO_MIN_TC_UPS,
  CAST((SELECT elem.VALUE FROM UNNEST(B.ACTIONABLE_COLUMNS) elem WHERE elem.NAME = 'NIVEL_USO_TC_UPS' LIMIT 1) AS FLOAT64) AS NIVEL_USO_TC_UPS
FROM BASE_CONDENSADOR B
LEFT JOIN ALL_POLICY P ON B.CUS_CUST_ID = P.CUS_CUST_ID AND B.EXECUTION_GROUP_ID = P.GRP;

-- JOB 2+ (misma sesión): queries de agregación sobre BASE_FULL

-- MÉTRICAS POR POLÍTICA (GC + GI combinados)
SELECT POLITICA, COUNT(*) AS Q_USUARIOS,
  ROUND(AVG(CURRENT_LIMIT),0) AS LIMITE_ACTUAL, ROUND(AVG(GENERAL_LIMIT),0) AS LIMITE_FINAL,
  ROUND(AVG(SAFE_DIVIDE(GENERAL_LIMIT,CURRENT_LIMIT)),2) AS MULTIPLICADOR,
  ROUND(SUM(GENERAL_LIMIT-CURRENT_LIMIT),0) AS EXPOSICION
FROM BASE_FULL GROUP BY POLITICA ORDER BY Q_USUARIOS DESC;

-- MÉTRICAS POR NISE (GC + GI combinados)
SELECT POLITICA, NISE_ORDENADO AS NISE, COUNT(DISTINCT CUS_CUST_ID) AS USUARIOS,
  ROUND(AVG(CURRENT_LIMIT),0) AS CURRENT_LIMIT, ROUND(AVG(GENERAL_LIMIT),0) AS LIMITE_FINAL,
  ROUND(AVG(SAFE_DIVIDE(GENERAL_LIMIT,CURRENT_LIMIT)),2) AS MULTIPLICADOR,
  ROUND(SUM(GENERAL_LIMIT-CURRENT_LIMIT),0) AS EXPO_ADICIONAL
FROM BASE_FULL GROUP BY POLITICA, NISE_ORDENADO ORDER BY POLITICA, NISE_ORDENADO;
```

### Inyectar métricas en el HTML

> **Filtrado de sellers:** si la campaña incluye grupos de sellers (POLITICA_ID = `BAU_PF_LT`, `BAU_PF_SMB`, `PISOS SELLERS`, `None`), ignorar esas filas al construir los JS constants — el dashboard de individuos solo acepta las 9 políticas del POLICY_MAP. Los sellers tienen su propia sección en el dashboard.

Mapear POLITICA_ID → nombre de grupo del POLICY_MAP:

| POLITICA_ID | Nombre en HTML |
|---|---|
| BAU | BAU |
| JOURNEY | JOURNEY 1A |
| VIP_MP | VIP MP |
| PISOS | PISOS |
| OPF | OPF |
| SOW_RM | RIESGO MED. SOW |
| REACTIVACION | REACTIVACION |
| ACTIVACION | ACTIVACION |
| ADECUACION | ADECUACION DE RENTA |

> **⚠ Normalización NISE:** BQ devuelve `a.bronze/b.silver/c.gold/d.platinum` (con prefijo de orden). Al construir los JS constants hay que mapear a `Bronze/Silver/Gold/Platinum` para que el dashboard los alinee correctamente entre meses.
>
> ```python
> NISE_MAP = {'a.bronze': 'Bronze', 'b.silver': 'Silver', 'c.gold': 'Gold', 'd.platinum': 'Platinum'}
> row['nise'] = NISE_MAP.get(row['nise'], row['nise'])
> # igual para las keys de gc_dim['NISE']
> ```

```javascript
const [MES]_METRICS = {
  "BAU": {"usuarios": X, "lim_actual": X, "lim_final": X, "mult": X, "exposicion": X},
  // ... 9 políticas
};
const [MES]_NISE = {
  "BAU": [{"nise":"Bronze","usuarios":X,"lim_actual":X,"lim_final":X,"mult":X,"exposicion":X}, ...],
  // ... 9 políticas — NISE keys: Bronze/Silver/Gold/Platinum (sin prefijo)
};
```

---

## PARTE 3 — APERTURA GC/GI Y TABLA DINÁMICA

### Query GC/GI por política y NISE × GC/GI

Usar la misma `BASE_FULL` de Parte 2 (misma sesión BQ):

```sql
-- GC/GI por política (para sección 5 del dashboard)
SELECT POLITICA, CAMPAIGN_CONTROL_GROUP AS GC,
  COUNT(*) AS Q_USUARIOS,
  ROUND(AVG(CURRENT_LIMIT),0) AS LIMITE_ACTUAL, ROUND(AVG(GENERAL_LIMIT),0) AS LIMITE_FINAL,
  ROUND(AVG(SAFE_DIVIDE(GENERAL_LIMIT,CURRENT_LIMIT)),2) AS MULTIPLICADOR,
  ROUND(SUM(GENERAL_LIMIT-CURRENT_LIMIT),0) AS EXPOSICION,
  ROUND(100*COUNT(*)/SUM(COUNT(*)) OVER (PARTITION BY POLITICA),1) AS PCT_GC
FROM BASE_FULL GROUP BY POLITICA, GC ORDER BY POLITICA, GC;

-- NISE × GC/GI (para sección 6 — apertura dinámica con GC/GI)
SELECT POLITICA, NISE_ORDENADO AS NISE, CAMPAIGN_CONTROL_GROUP AS GC,
  COUNT(DISTINCT CUS_CUST_ID) AS USUARIOS,
  ROUND(AVG(CURRENT_LIMIT),0) AS CURRENT_LIMIT, ROUND(AVG(GENERAL_LIMIT),0) AS LIMITE_FINAL,
  ROUND(AVG(SAFE_DIVIDE(GENERAL_LIMIT,CURRENT_LIMIT)),2) AS MULTIPLICADOR,
  ROUND(SUM(GENERAL_LIMIT-CURRENT_LIMIT),0) AS EXPOSICION
FROM BASE_FULL GROUP BY POLITICA, NISE, GC ORDER BY POLITICA, NISE, GC;
```

### Inyectar en el HTML

```javascript
const [MES]_GC_POL = {
  "BAU": {
    "GI": {"usuarios": X, "lim_actual": X, "lim_final": X, "mult": X, "exposicion": X, "pct_gc": X},
    "GC": {"usuarios": X, "lim_actual": X, "lim_final": X, "mult": X, "exposicion": X, "pct_gc": X}
  },
  // ... 9 políticas
};
const [MES]_GC_DIM = {
  "NISE": {
    "BAU": {
      "a.bronze": { "GI": {usuarios, lim_actual, lim_final, mult, exposicion}, "GC": {...} },
      // Bronze, Silver, Gold, Platinum
    },
    // ... 9 políticas
  }
};
```

**Nota sobre GC/GI:** `GC=true` en BQ = Grupo Control (no recibe oferta). `GC=false` = GI (Grupo Impacto, recibe la oferta).

**Nota sobre Apertura dinámica:** cuando el usuario selecciona la vista "GC/GI", el dashboard muestra automáticamente columnas de variación (Δ vs GC) para cada métrica — esto es generado por el código del dashboard a partir de los datos de `gc_dim`, no requiere datos adicionales.

**Nota sobre el Consolidado:** `gc_pol` también alimenta la tabla "Apertura por política" del Consolidado, que muestra Usuarios, Lim. Act., Lim. Fin., Mult. y Exposición del Mes A con sus variaciones vs Mes B. No requiere datos extras — solo que `gc_pol` esté correctamente inyectado.

---

## PARTE 4 — ANTIGÜEDAD, RATING BHV Y RATING UPSELL

Estas dimensiones se calculan en la misma pasada que las métricas GC/GI. **No crear una query separada** — extender la `BASE_FULL` con los JOINs adicionales.

### Query completa optimizada (reemplazar [EXEC_ID] y [FECHA_CORRIDA])

`[FECHA_CORRIDA]` es el `sent_at` de la campaña. **Usar siempre la fecha del accionable**, no `CURRENT_DATE()`, para consultar la foto exacta del momento de la campaña.

Versiones de modelos fijas (hasta nuevo aviso): BHV = v8, Upsell = v4.

```sql
-- Agregar a BASE_FULL los siguientes CTEs y JOINs:

CREDITO AS (
  SELECT DISTINCT CUS_CUST_ID, CRD_CREDIT_CREATION_DT
  FROM `meli-bi-data.WHOWNER.BT_VU_CREDIT`
  WHERE SIT_SITE_ID = 'MLB'
    AND CRD_PROD_DEF_TYPE_SK = 3
    AND CRD_CREDIT_STATUS IN ('ACTIVE','OVERDUE')
    AND CREDIT_AMT >= 500
    AND VALID_FROM_DT < '[FECHA_CORRIDA]'
    AND VALID_TO_DT  >= '[FECHA_CORRIDA]'
),
RATINGS AS (
  -- Un solo JOIN para BHV y Upsell (optimizado vs dos joins separados)
  SELECT CUS_CUST_ID,
    MAX(CASE WHEN CRD_MODEL = 'CONSUMERS_BEHAVIOR_CREDIT_CARD' AND CRD_VERSION = 8 THEN INTERNAL_RATING_TAG END) AS rating_bhv,
    MAX(CASE WHEN CRD_MODEL = 'CONSUMERS_UPSELL_TC'            AND CRD_VERSION = 4 THEN INTERNAL_RATING_TAG END) AS rating_upsell
  FROM `meli-bi-data.WHOWNER.BT_VU_MODEL_RATING`
  WHERE SIT_SITE_ID = 'MLB'
    AND CRD_MODEL IN ('CONSUMERS_BEHAVIOR_CREDIT_CARD','CONSUMERS_UPSELL_TC')
    AND VALID_FROM_DT < '[FECHA_CORRIDA]'
    AND VALID_TO_DT  >= '[FECHA_CORRIDA]'
  GROUP BY CUS_CUST_ID
)
-- En BASE_FULL, agregar estos campos al SELECT:
CASE
  WHEN DATE_DIFF(DATE('[FECHA_CORRIDA]'), DATE(C.CRD_CREDIT_CREATION_DT), MONTH) < 6  THEN '1. 0-6 meses'
  WHEN DATE_DIFF(DATE('[FECHA_CORRIDA]'), DATE(C.CRD_CREDIT_CREATION_DT), MONTH) < 12 THEN '2. 6-12 meses'
  WHEN DATE_DIFF(DATE('[FECHA_CORRIDA]'), DATE(C.CRD_CREDIT_CREATION_DT), MONTH) < 24 THEN '3. 12-24 meses'
  ELSE '4. +24 meses'
END AS ANTIGUEDAD,
R.rating_bhv,
R.rating_upsell
-- Y los JOINs:
LEFT JOIN CREDITO C ON B.CUS_CUST_ID = C.CUS_CUST_ID
LEFT JOIN RATINGS R ON B.CUS_CUST_ID = R.CUS_CUST_ID
```

### Queries de agregación (una por dimensión, misma estructura)

```sql
-- ANTIGÜEDAD × GC/GI
SELECT POLITICA, ANTIGUEDAD AS DIM, CAMPAIGN_CONTROL_GROUP AS GC,
  COUNT(DISTINCT CUS_CUST_ID) AS USUARIOS,
  ROUND(AVG(CURRENT_LIMIT),0) AS CURRENT_LIMIT, ROUND(AVG(GENERAL_LIMIT),0) AS LIMITE_FINAL,
  ROUND(AVG(SAFE_DIVIDE(GENERAL_LIMIT,CURRENT_LIMIT)),2) AS MULTIPLICADOR,
  ROUND(SUM(GENERAL_LIMIT-CURRENT_LIMIT),0) AS EXPOSICION
FROM BASE_FULL WHERE ANTIGUEDAD IS NOT NULL
GROUP BY POLITICA, DIM, GC ORDER BY POLITICA, DIM, GC;

-- RATING BHV × GC/GI
SELECT POLITICA, rating_bhv AS DIM, CAMPAIGN_CONTROL_GROUP AS GC,
  COUNT(DISTINCT CUS_CUST_ID) AS USUARIOS,
  ROUND(AVG(CURRENT_LIMIT),0) AS CURRENT_LIMIT, ROUND(AVG(GENERAL_LIMIT),0) AS LIMITE_FINAL,
  ROUND(AVG(SAFE_DIVIDE(GENERAL_LIMIT,CURRENT_LIMIT)),2) AS MULTIPLICADOR,
  ROUND(SUM(GENERAL_LIMIT-CURRENT_LIMIT),0) AS EXPOSICION
FROM BASE_FULL WHERE rating_bhv IS NOT NULL
GROUP BY POLITICA, DIM, GC ORDER BY POLITICA, DIM, GC;

-- RATING UPSELL × GC/GI
SELECT POLITICA, rating_upsell AS DIM, CAMPAIGN_CONTROL_GROUP AS GC,
  COUNT(DISTINCT CUS_CUST_ID) AS USUARIOS,
  ROUND(AVG(CURRENT_LIMIT),0) AS CURRENT_LIMIT, ROUND(AVG(GENERAL_LIMIT),0) AS LIMITE_FINAL,
  ROUND(AVG(SAFE_DIVIDE(GENERAL_LIMIT,CURRENT_LIMIT)),2) AS MULTIPLICADOR,
  ROUND(SUM(GENERAL_LIMIT-CURRENT_LIMIT),0) AS EXPOSICION
FROM BASE_FULL WHERE rating_upsell IS NOT NULL
GROUP BY POLITICA, DIM, GC ORDER BY POLITICA, DIM, GC;
```

### Inyectar en el HTML (agregar a `gc_dim`)

```javascript
const [MES]_GC_DIM = {
  "NISE":      { "BAU": { "a.bronze": { "GI": {...}, "GC": {...} }, ... }, ... },
  "ANTIGUEDAD":{ "BAU": { "1. 0-6 meses": { "GI": {...}, "GC": {...} }, ... }, ... },
  "RATING_BHV":{ "BAU": { "A": { "GI": {...}, "GC": {...} }, "B": {...}, ... }, ... },
  "RATING_UPS":{ "BAU": { "A": { "GI": {...}, "GC": {...} }, "B": {...}, ... }, ... },
};
```

El selector "Dimensión" del dashboard mostrará automáticamente las opciones disponibles.

---

## PARTE 5 — MATRIZ DE RATINGS (BHV × Upsell)

Agrega datos para la sección "Distribución" del dashboard (donuts de NISE/Antigüedad + matriz cruzada de ratings).

Los donuts de NISE y Antigüedad usan datos ya calculados en Partes 3 y 4. Solo necesitás correr esta query adicional para la **matriz de ratings**.

### Query cross-tab BHV × Upsell (GI only)

```sql
WITH BASE AS (
  SELECT *, CAST((SELECT elem.VALUE FROM UNNEST(ACTIONABLE_COLUMNS) elem WHERE elem.NAME='POLITICA_ID' LIMIT 1) AS STRING) AS POLITICA
  FROM `bq-cp-prd-o0b0uuv7cs2-furyid.campaign_schema.EOC_CAMPAIGN_EXECUTION_DETAIL`
  WHERE EXECUTION_ID='[EXEC_ID]'
),
RATINGS AS (
  SELECT CUS_CUST_ID,
    MAX(CASE WHEN CRD_MODEL='CONSUMERS_BEHAVIOR_CREDIT_CARD' AND CRD_VERSION=8 THEN INTERNAL_RATING_TAG END) AS rating_bhv,
    MAX(CASE WHEN CRD_MODEL='CONSUMERS_UPSELL_TC'           AND CRD_VERSION=4 THEN INTERNAL_RATING_TAG END) AS rating_upsell
  FROM `meli-bi-data.WHOWNER.BT_VU_MODEL_RATING`
  WHERE SIT_SITE_ID='MLB'
    AND CRD_MODEL IN ('CONSUMERS_BEHAVIOR_CREDIT_CARD','CONSUMERS_UPSELL_TC')
    AND VALID_FROM_DT < '[FECHA_CORRIDA]'
    AND VALID_TO_DT  >= '[FECHA_CORRIDA]'
  GROUP BY CUS_CUST_ID
)
SELECT B.POLITICA, R.rating_bhv, R.rating_upsell,
  COUNT(DISTINCT B.CUS_CUST_ID) AS USUARIOS
FROM BASE B
INNER JOIN RATINGS R ON B.CUS_CUST_ID=R.CUS_CUST_ID
WHERE R.rating_bhv IS NOT NULL AND R.rating_upsell IS NOT NULL
  AND B.CAMPAIGN_CONTROL_GROUP = false   -- solo GI (grupo impacto)
GROUP BY 1,2,3 ORDER BY 1,2,3
```

**Notas:**
- Versiones fijas: BHV v8, Upsell v4 — actualizar si cambian los modelos productivos
- Solo usuarios GI (`CAMPAIGN_CONTROL_GROUP = false`)
- **El color en la matriz es semántico** — no se basa solo en el signo del cambio:
  - 🟢 Verde = buenos combos (A-A, A-B, B-A) creciendo en Mes A, o malos combos decreciendo
  - 🔴 Rojo = malos combos (C-C, C-D, D-C) creciendo en Mes A, o buenos combos decreciendo
  - Umbral: ≥2.5pp suave, ≥5pp intenso
  - El código calcula `qualityScore = rank(bhv) + rank(ups)` donde A=1, B=2, C=3... — score bajo = combo bueno

### Inyectar en el HTML

```javascript
const [MES]_RATING_MATRIX = {
  "BAU": {
    "A": { "A": 1200, "B": 800, "C": 200 },
    "B": { "A": 50, "B": 3000, "C": 1500 },
    // ... bhv_rating: { ups_rating: usuarios_GI }
  },
  // ... 9 políticas
};
```

Y agregar a MONTHS: `rating_matrix: [MES]_RATING_MATRIX` (ya está incluido en la entrada completa del Paso 6 de Parte 1).

---

## PARTE 6 — COMPETENCIA DE POLÍTICAS (CONSOLIDADO)

Esta sección alimenta las tablas "Competencia de políticas" en el Consolidado del dashboard. Muestran cuántos usuarios se descartaron en cada etapa de competencia y el % de descarte vs el mes de comparación.

**No requiere queries BQ** — los datos vienen directamente del dashboard de EOC (sin `include`).

### Paso 1: Traer datos de campaña desde EOC

```
Herramienta: get_campaign_execution_dashboard
campaign_id: [EL QUE OBTUVISTE EN PARTE 1]
(sin parámetro include)
```

Extraer `campaign_dashboard.actions` — lista de etapas de competencia.

**Estructura que devuelve EOC:**
```json
{
  "campaign_dashboard": {
    "actions": [
      {
        "config_name": "ESPECIALES + RIESGO MEDIO",
        "output_users": 445579,
        "entries": [
          { "entry_name": "REACTIVACION", "entry_users": 35118, "discarded_entry_users": 1369 },
          { "entry_name": "OPF",          "entry_users": 63843, "discarded_entry_users": 1523 },
          { "entry_name": "JOURNEY 1A",   "entry_users": 217752, "discarded_entry_users": 10923 },
          { "entry_name": "PISOS",        "entry_users": 55813,  "discarded_entry_users": 16583 },
          { "entry_name": "ADECUACION DE RENTA", "entry_users": 14733, "discarded_entry_users": 2905 },
          { "entry_name": "ACTIVACION",   "entry_users": 25467,  "discarded_entry_users": 1 },
          { "entry_name": "RIESGO MED. SOW", "entry_users": 32853, "discarded_entry_users": 2402 }
        ]
      },
      {
        "config_name": "PRIORIZACION",
        "output_users": 771452,
        "entries": [
          { "entry_name": "VIP MP",                    "entry_users": 106769, "discarded_entry_users": 0 },
          { "entry_name": "BAU",                       "entry_users": 253668, "discarded_entry_users": 53458 },
          { "entry_name": "ESPECIALES + RIESGO MEDIO", "entry_users": 411015, "discarded_entry_users": 34564 }
        ]
      }
    ]
  }
}
```

**¿Qué significa cada campo?**
- `entry_users`: audiencia que entró a la competencia para esa política/grupo
- `discarded_entry_users`: usuarios que calificaban para esa política pero la perdieron (la ganó otra política con mayor prioridad)
- `% descartado = discarded_entry_users / entry_users × 100`

### Paso 2: Inyectar en el HTML

```javascript
const [MES]_COMPETENCIA = {
  "ESPECIALES + RIESGO MEDIO": [
    {pol:"REACTIVACION",         audiencia: N, descartados: N},
    {pol:"OPF",                  audiencia: N, descartados: N},
    {pol:"JOURNEY 1A",           audiencia: N, descartados: N},
    {pol:"PISOS",                audiencia: N, descartados: N},
    {pol:"ADECUACION DE RENTA",  audiencia: N, descartados: N},
    {pol:"ACTIVACION",           audiencia: N, descartados: N},
    {pol:"RIESGO MED. SOW",      audiencia: N, descartados: N},
  ],
  "PRIORIZACION": [
    {pol:"VIP MP",                    audiencia: N, descartados: N},
    {pol:"BAU",                       audiencia: N, descartados: N},
    {pol:"ESPECIALES + RIESGO MEDIO", audiencia: N, descartados: N},
  ]
};
```

Copiar `entry_name` → `pol`, `entry_users` → `audiencia` y `discarded_entry_users` → `descartados`.

---

## CHECKLIST FINAL — INDIVIDUOS

**Datos de EOC (sin BQ):**
- [ ] Paso 0 completado — preguntas sobre killers (incluyendo definiciones de killers nuevos)
- [ ] Doble-check Python pasó con 0 diferencias
- [ ] Los 9 grupos están presentes en `[MES]_FUNNELS`
- [ ] Ningún killer fue salteado ni reordenado
- [ ] Killers nuevos/eliminados/modificados anotados en `KILLER_NOTES`
- [ ] Definiciones de killers nuevos/modificados actualizadas en `KILLER_DEFS`
- [ ] Comentarios del mes cargados en `MONTH_COMMENTS`
- [ ] `[MES]_COMPETENCIA` inyectado (2 etapas: ESPECIALES + RIESGO MEDIO y PRIORIZACION)

**Datos de BigQuery:**
- [ ] `[MES]_METRICS` inyectado (9 políticas)
- [ ] `[MES]_NISE` inyectado (9 políticas × 4 NISE)
- [ ] `[MES]_GC_POL` inyectado (9 políticas, GI + GC)
- [ ] `[MES]_GC_DIM` inyectado (NISE, ANTIGÜEDAD, RATING_BHV, RATING_UPS — cada una con GI + GC)
- [ ] `[MES]_RATING_MATRIX` inyectado (9 políticas × BHV × Upsell, solo GI)
- [ ] Las métricas tienen Q_USUARIOS coherente con el funnel EOC

**Configuración del HTML:**
- [ ] `meta` del mes incluye campaign, fecha, exec_id, campaign_id y eoc_url
- [ ] El nuevo mes aparece en ambos selectores HTML (`selMonthA` y `selMonthB`)
- [ ] MONTHS entry incluye todos los campos: rating_matrix, metrics, nise, funnels, gc_pol, gc_dim, competencia, meta

**Subida:**
- [ ] Doble-check OK antes de subir al Grid

---

## ──────────────────────────────────────────
## FLUJO SELLERS (grupos 10–15)
## ──────────────────────────────────────────

Los sellers comparten el mismo EXEC_ID que la campaña de individuos, pero usan los grupos 10–15 de las tablas SBOX. No tienen NISE, ni ratings BHV/Upsell, ni competencia. La antigüedad usa 3 buckets (no 4) y un filtro de crédito diferente.

### Diferencias clave vs Individuos

| Aspecto | Individuos | Sellers |
|---|---|---|
| Grupos SBOX | 1–9 | 10–15 |
| Identificador de grupo | POLITICA_ID (campo ACTIONABLE_COLUMNS) | group_idx extraído de EXECUTION_GROUP_ID |
| NISE | ✅ | ❌ |
| Rating BHV / Upsell | ✅ | ❌ |
| Antigüedad buckets | 0-6m, 6-12m, 12-24m, >24m (4) | 0-12m, 12-24m, >24m (3) |
| Filtro BT_VU_CREDIT | `IN ('ACTIVE','OVERDUE')` + `CREDIT_AMT >= 500` | `NOT IN ('DEFAULTED','CANCELLED','ANNULLED','PENDING','IN_CAPTURE')` + QUALIFY para crédito más antiguo |
| BQ Sessions | Requeridas (TEMP TABLEs) | No — queries CTE directas |
| Inyectar en | `MONTHS` | `MONTHS_SELLERS` |
| Mapa de grupos | `POLICY_MAP` (9 políticas) | `POLICY_MAP_SELLERS_DATA` |

### Grupos sellers actuales

| group_idx | Nombre en dashboard |
|---|---|
| 10 | BAU PF LT |
| 11 | BAU PF SMB |
| 12 | PISOS PF LT |
| 13 | PISOS PF SMB |
| 14 | OPF PF LT |
| 15 | OPF PF SMB |

Si en el futuro se agregan grupos PJ (idx 16+), agregar a `POLICY_MAP_SELLERS_DATA`.

---

### Paso S1: Funnels desde EOC

Usar **el mismo campaign_id** que individuos (comparten campaña):

```
Herramienta: get_campaign_execution_dashboard
campaign_id: [CAMPAIGN_ID]
include: killer_rules
```

Filtrar solo grupos con `execution_group_id` terminado en `-10`, `-11`, `-12`, `-13`, `-14`, `-15`.

Luego una segunda llamada para las policy exceptions:

```
Herramienta: get_campaign_execution_dashboard
campaign_id: [CAMPAIGN_ID]
include: policy
```

**Estructura de funnels sellers** (igual que individuos pero con nombres de grupos sellers):
```javascript
const [MES]S_FUNNELS = {
  "BAU PF LT":   { "total": N, "killers": [...], "policy": { "name": "...", "atributos_accumulated": N, "exceptions": [...] } },
  "BAU PF SMB":  { ... },
  "PISOS PF LT": { ... },
  "PISOS PF SMB":{ ... },
  "OPF PF LT":   { ... },
  "OPF PF SMB":  { ... }
};
```

> Nota: `atributos_accumulated` = `policy["accumulated_users"]` (usuarios que entran a la política antes de las excepciones). No es lo mismo que `after_killers - excluded_by_attributes` — leer el campo directamente de `policy.accumulated_users` en la respuesta EOC.

---

### Paso S2: Métricas generales (BQ)

Sin BQ Sessions. CTEs directas. Reemplazar `[EXEC_ID]` y `[FECHA_CORRIDA]`.

```sql
WITH acc AS (
  SELECT CUS_CUST_ID,
         CAST(REGEXP_EXTRACT(EXECUTION_GROUP_ID, r'(\d+)$') AS INT64) AS group_idx,
         MAX(IF(c.NAME='general_limit', SAFE_CAST(c.VALUE AS FLOAT64), NULL)) AS general_limit
  FROM `bq-cp-prd-o0b0uuv7cs2-furyid.campaign_schema.EOC_CAMPAIGN_EXECUTION_DETAIL`,
       UNNEST(ACTIONABLE_COLUMNS) AS c
  WHERE EXECUTION_ID = '[EXEC_ID]'
  GROUP BY CUS_CUST_ID, group_idx
),
ratings AS (
  SELECT 10 AS group_idx, CAST(cus_cust_id AS STRING) AS cus_cust_id,
         SAFE_CAST(WANDA__CURRENT_LIMIT_CCARD AS FLOAT64) AS limite_actual
  FROM `meli-bi-data.SBOX_CREDITSSIGMA.CAMP_EOC_RK_POLICY_[EXEC_ID]-10`
  UNION ALL SELECT 11, CAST(cus_cust_id AS STRING), SAFE_CAST(WANDA__CURRENT_LIMIT_CCARD AS FLOAT64)
  FROM `meli-bi-data.SBOX_CREDITSSIGMA.CAMP_EOC_RK_POLICY_[EXEC_ID]-11`
  UNION ALL SELECT 12, CAST(cus_cust_id AS STRING), SAFE_CAST(WANDA__CURRENT_LIMIT_CCARD AS FLOAT64)
  FROM `meli-bi-data.SBOX_CREDITSSIGMA.CAMP_EOC_RK_POLICY_[EXEC_ID]-12`
  UNION ALL SELECT 13, CAST(cus_cust_id AS STRING), SAFE_CAST(WANDA__CURRENT_LIMIT_CCARD AS FLOAT64)
  FROM `meli-bi-data.SBOX_CREDITSSIGMA.CAMP_EOC_RK_POLICY_[EXEC_ID]-13`
  UNION ALL SELECT 14, CAST(cus_cust_id AS STRING), SAFE_CAST(WANDA__CURRENT_LIMIT_CCARD AS FLOAT64)
  FROM `meli-bi-data.SBOX_CREDITSSIGMA.CAMP_EOC_RK_POLICY_[EXEC_ID]-14`
  UNION ALL SELECT 15, CAST(cus_cust_id AS STRING), SAFE_CAST(WANDA__CURRENT_LIMIT_CCARD AS FLOAT64)
  FROM `meli-bi-data.SBOX_CREDITSSIGMA.CAMP_EOC_RK_POLICY_[EXEC_ID]-15`
)
SELECT
  CASE a.group_idx
    WHEN 10 THEN 'BAU PF LT'   WHEN 11 THEN 'BAU PF SMB'
    WHEN 12 THEN 'PISOS PF LT' WHEN 13 THEN 'PISOS PF SMB'
    WHEN 14 THEN 'OPF PF LT'   WHEN 15 THEN 'OPF PF SMB'
  END AS grupo,
  COUNT(*)                                                    AS usuarios,
  ROUND(AVG(r.limite_actual), 2)                             AS limite_actual,
  ROUND(AVG(a.general_limit), 2)                             AS limite_final,
  ROUND(AVG(SAFE_DIVIDE(a.general_limit, r.limite_actual)), 3) AS multiplicador,
  ROUND(SUM(a.general_limit - r.limite_actual), 2)          AS exposicion
FROM acc a
JOIN ratings r
  ON CAST(a.CUS_CUST_ID AS STRING) = r.cus_cust_id AND a.group_idx = r.group_idx
WHERE a.group_idx BETWEEN 10 AND 15
GROUP BY grupo ORDER BY grupo
```

**Resultado → `[MES]S_METRICS`:** mapear campos `limite_actual → lim_actual`, `limite_final → lim_final`, `multiplicador → mult`.

---

### Paso S3: Antigüedad × GC/GI (BQ)

Esta query produce tanto el `gc_pol` (totales GC/GI por grupo) como el `gc_dim['ANTIGUEDAD']`. Se pueden derivar los dos de un solo resultset.

```sql
WITH acc AS (
  SELECT CUS_CUST_ID,
         CAST(REGEXP_EXTRACT(EXECUTION_GROUP_ID, r'(\d+)$') AS INT64) AS group_idx,
         CASE WHEN CAST(CAMPAIGN_CONTROL_GROUP AS STRING) = 'true' THEN 'GC' ELSE 'GI' END AS grupo_test,
         MAX(IF(c.NAME='general_limit', SAFE_CAST(c.VALUE AS FLOAT64), NULL)) AS general_limit
  FROM `bq-cp-prd-o0b0uuv7cs2-furyid.campaign_schema.EOC_CAMPAIGN_EXECUTION_DETAIL`,
       UNNEST(ACTIONABLE_COLUMNS) AS c
  WHERE EXECUTION_ID = '[EXEC_ID]'
  GROUP BY CUS_CUST_ID, group_idx, grupo_test
),
ratings AS (
  -- idéntico al Paso S2
  SELECT 10 AS group_idx, CAST(cus_cust_id AS STRING) AS cus_cust_id,
         SAFE_CAST(WANDA__CURRENT_LIMIT_CCARD AS FLOAT64) AS limite_actual
  FROM `meli-bi-data.SBOX_CREDITSSIGMA.CAMP_EOC_RK_POLICY_[EXEC_ID]-10`
  UNION ALL SELECT 11, CAST(cus_cust_id AS STRING), SAFE_CAST(WANDA__CURRENT_LIMIT_CCARD AS FLOAT64)
  FROM `meli-bi-data.SBOX_CREDITSSIGMA.CAMP_EOC_RK_POLICY_[EXEC_ID]-11`
  UNION ALL SELECT 12, CAST(cus_cust_id AS STRING), SAFE_CAST(WANDA__CURRENT_LIMIT_CCARD AS FLOAT64)
  FROM `meli-bi-data.SBOX_CREDITSSIGMA.CAMP_EOC_RK_POLICY_[EXEC_ID]-12`
  UNION ALL SELECT 13, CAST(cus_cust_id AS STRING), SAFE_CAST(WANDA__CURRENT_LIMIT_CCARD AS FLOAT64)
  FROM `meli-bi-data.SBOX_CREDITSSIGMA.CAMP_EOC_RK_POLICY_[EXEC_ID]-13`
  UNION ALL SELECT 14, CAST(cus_cust_id AS STRING), SAFE_CAST(WANDA__CURRENT_LIMIT_CCARD AS FLOAT64)
  FROM `meli-bi-data.SBOX_CREDITSSIGMA.CAMP_EOC_RK_POLICY_[EXEC_ID]-14`
  UNION ALL SELECT 15, CAST(cus_cust_id AS STRING), SAFE_CAST(WANDA__CURRENT_LIMIT_CCARD AS FLOAT64)
  FROM `meli-bi-data.SBOX_CREDITSSIGMA.CAMP_EOC_RK_POLICY_[EXEC_ID]-15`
),
credito AS (
  SELECT CAST(CUS_CUST_ID AS STRING) AS cus_cust_id,
         DATE_DIFF(DATE '[FECHA_CORRIDA]', CRD_CREDIT_CREATION_DT, MONTH) AS antiguedad_meses
  FROM `meli-bi-data.WHOWNER.BT_VU_CREDIT`
  WHERE SIT_SITE_ID = 'MLB'
    AND CRD_PROD_DEF_TYPE_SK = 3                -- TC
    AND VALID_FROM_DT <  '[FECHA_CORRIDA]'
    AND VALID_TO_DT   >= '[FECHA_CORRIDA]'
    AND CRD_CREDIT_STATUS NOT IN ('DEFAULTED','CANCELLED','ANNULLED','PENDING','IN_CAPTURE')
  QUALIFY ROW_NUMBER() OVER (PARTITION BY CUS_CUST_ID ORDER BY CRD_CREDIT_CREATION_DT ASC) = 1
  -- ↑ tomar el crédito más antiguo del usuario (no el más reciente como en individuos)
)
SELECT
  CASE a.group_idx
    WHEN 10 THEN 'BAU PF LT'   WHEN 11 THEN 'BAU PF SMB'
    WHEN 12 THEN 'PISOS PF LT' WHEN 13 THEN 'PISOS PF SMB'
    WHEN 14 THEN 'OPF PF LT'   WHEN 15 THEN 'OPF PF SMB'
  END AS grupo,
  a.grupo_test,
  CASE
    WHEN cr.antiguedad_meses < 12  THEN '1. 0-12m'
    WHEN cr.antiguedad_meses < 24  THEN '2. 12-24m'
    WHEN cr.antiguedad_meses >= 24 THEN '3. >24m'
    ELSE '4. sin dato'
  END AS antiguedad,
  COUNT(*)                                                    AS usuarios,
  ROUND(AVG(r.limite_actual), 2)                             AS limite_actual,
  ROUND(AVG(a.general_limit), 2)                             AS limite_final,
  ROUND(AVG(SAFE_DIVIDE(a.general_limit, r.limite_actual)), 3) AS multiplicador,
  ROUND(SUM(a.general_limit - r.limite_actual), 2)          AS exposicion
FROM acc a
JOIN ratings r
  ON CAST(a.CUS_CUST_ID AS STRING) = r.cus_cust_id AND a.group_idx = r.group_idx
LEFT JOIN credito cr
  ON CAST(a.CUS_CUST_ID AS STRING) = cr.cus_cust_id
WHERE a.group_idx BETWEEN 10 AND 15
GROUP BY grupo, a.grupo_test, antiguedad
ORDER BY grupo, a.grupo_test, antiguedad
```

---

### Paso S4: Transformar a constantes JS (Python)

El script toma los resultados BQ + los datos EOC y genera los 5 constants necesarios.

```python
import json

GRUPO_MAP = {
    '10': 'BAU PF LT', '11': 'BAU PF SMB',
    '12': 'PISOS PF LT', '13': 'PISOS PF SMB',
    '14': 'OPF PF LT',  '15': 'OPF PF SMB',
}

# ── Funnels (desde EOC) ───────────────────────────────────────────────────────
# killer_data[suffix] = { 'funnel': {...}, 'killers': [...] }  (de include: killer_rules)
# policy_data[suffix] = { 'name': ..., 'accumulated_users': N, 'exceptions': [...] }  (de include: policy)

MES_S_FUNNELS = {}
for suffix, grupo in GRUPO_MAP.items():
    kd = killer_data[suffix]
    pd = policy_data[suffix]
    MES_S_FUNNELS[grupo] = {
        "total": kd['funnel']['total_users'],
        "killers": [{"name": k['name'].strip(), "accumulated": k['accumulated_users']} for k in kd['killers']],
        "policy": {
            "name": pd.get('name', '').strip(),
            "atributos_accumulated": pd.get('accumulated_users', 0),
            "exceptions": [{"name": e['name'].strip(), "accumulated": e['accumulated_users']} for e in pd.get('exceptions', [])],
        }
    }

# ── Métricas generales (GC + GI) ─────────────────────────────────────────────
MES_S_METRICS = {}
for r in metrics_rows:
    g = r['grupo']
    MES_S_METRICS[g] = {
        "usuarios":   r['usuarios'],
        "lim_actual": round(r['limite_actual'], 0),
        "lim_final":  round(r['limite_final'], 0),
        "mult":       r['multiplicador'],
        "exposicion": round(r['exposicion'], 0),
    }

# ── gc_pol: derivado de antigüedad, sumando buckets por grupo × GC/GI ─────────
gc_pol_accum = {}  # { grupo: { 'GI'/'GC': { usuarios, sum_la, sum_lf, exposicion } } }

def make_acc():
    return {'usuarios': 0, 'sum_la': 0.0, 'sum_lf': 0.0, 'exposicion': 0.0}

for r in ant_rows:
    g, gt = r['grupo'], r['grupo_test']
    n = r['usuarios']
    gc_pol_accum.setdefault(g, {}).setdefault(gt, make_acc())
    v = gc_pol_accum[g][gt]
    v['usuarios']  += n
    v['sum_la']    += (r['limite_actual'] or 0) * n
    v['sum_lf']    += (r['limite_final'] or 0) * n
    v['exposicion'] += (r['exposicion'] or 0)

MES_S_GC_POL = {}
for g, groups in gc_pol_accum.items():
    total_u = sum(v['usuarios'] for v in groups.values())
    gc_u    = groups.get('GC', {}).get('usuarios', 0)
    pct_gc  = round(100 * gc_u / total_u, 1) if total_u > 0 else 0.0
    MES_S_GC_POL[g] = {}
    for gt, v in groups.items():
        n = v['usuarios']
        la = round(v['sum_la'] / n, 2) if n > 0 else 0
        lf = round(v['sum_lf'] / n, 2) if n > 0 else 0
        pct = pct_gc if gt == 'GC' else round(100 - pct_gc, 1)
        MES_S_GC_POL[g][gt] = {
            "usuarios":   n,
            "lim_actual": la,
            "lim_final":  lf,
            "mult":       round(lf / la, 3) if la > 0 else 0,
            "exposicion": round(v['exposicion'], 0),
            "pct_gc":     pct,
        }

# ── gc_dim: ANTIGUEDAD × GC/GI (incluye CONSOLIDADO) ─────────────────────────
ant_accum  = {}   # { grupo: { segment: { GI/GC: make_acc() } } }
cons_accum = {}   # { segment: { GI/GC: make_acc() } }

for r in ant_rows:
    g, gt, ant = r['grupo'], r['grupo_test'], r['antiguedad']
    n  = r['usuarios']
    la = r['limite_actual'] or 0
    lf = r['limite_final'] or 0
    ex = r['exposicion'] or 0
    ant_accum.setdefault(g, {}).setdefault(ant, {}).setdefault(gt, make_acc())
    cons_accum.setdefault(ant, {}).setdefault(gt, make_acc())
    for acc in [ant_accum[g][ant][gt], cons_accum[ant][gt]]:
        acc['usuarios']  += n
        acc['sum_la']    += la * n
        acc['sum_lf']    += lf * n
        acc['exposicion'] += ex

def build_seg(by_gt):
    res = {}
    for gt, v in by_gt.items():
        n = v['usuarios']
        la = round(v['sum_la'] / n, 2) if n > 0 else 0
        lf = round(v['sum_lf'] / n, 2) if n > 0 else 0
        res[gt] = {
            "usuarios": n, "lim_actual": la, "lim_final": lf,
            "mult": round(lf / la, 3) if la > 0 else 0,
            "exposicion": round(v['exposicion'], 0),
        }
    return res

ant_dim = {g: {seg: build_seg(gts) for seg, gts in segs.items()} for g, segs in ant_accum.items()}
ant_dim['CONSOLIDADO'] = {seg: build_seg(gts) for seg, gts in cons_accum.items()}

MES_S_GC_DIM = {"ANTIGUEDAD": ant_dim}

# ── Constantes JS ─────────────────────────────────────────────────────────────
def js_const(name, val):
    return f"const {name} = {json.dumps(val, ensure_ascii=False)} ;\n"

MES = "[MES]"   # Ej: "Ago-26"
constants = (
    js_const(f"{MES.replace('-','').upper()}S_FUNNELS",     MES_S_FUNNELS) +
    js_const(f"{MES.replace('-','').upper()}S_METRICS",     MES_S_METRICS) +
    js_const(f"{MES.replace('-','').upper()}S_GC_POL",      MES_S_GC_POL) +
    js_const(f"{MES.replace('-','').upper()}S_GC_DIM",      MES_S_GC_DIM) +
    js_const(f"{MES.replace('-','').upper()}S_COMPETENCIA",  {})
)
```

---

### Paso S5: Inyectar en el HTML

**Variables JS a agregar** (antes de `const MONTHS_SELLERS =`):

```javascript
const [MES]S_FUNNELS     = { ... } ;
const [MES]S_METRICS     = { ... } ;
const [MES]S_GC_POL      = { ... } ;
const [MES]S_GC_DIM      = { ... } ;
const [MES]S_COMPETENCIA = {} ;     // dejar vacío si no hay datos de competencia
```

**Entrada en MONTHS_SELLERS** (insertar como primer elemento, newest-first):

```javascript
const MONTHS_SELLERS = {
  "[MES]": {
    funnels: [MES]S_FUNNELS, metrics: [MES]S_METRICS, gc_pol: [MES]S_GC_POL,
    gc_dim: [MES]S_GC_DIM, nise: {}, rating_matrix: {}, competencia: [MES]S_COMPETENCIA,
    meta: {
      campaign: "[NOMBRE_CAMPAÑA]",
      fecha: "[FECHA_CORRIDA]",
      exec_id: "[EXEC_ID]",
      campaign_id: [CAMPAIGN_ID],
      eoc_url: "https://credits-admin.adminml.com/eoc/campaigns/audience/[CAMPAIGN_ID]?executionId=[EXEC_ID]&tab=campaign"
    }
  },
  "Jul-26": { ... },   // mes anterior — no tocar
};
```

> **Nota:** `nise: {}` y `rating_matrix: {}` siempre vacíos para sellers. El dashboard muestra "Sin datos" para NISE, Rating BHV y Rating Upsell — es el comportamiento esperado.

**Actualizar POLICY_MAP_SELLERS_DATA** si el mes tiene grupos nuevos (ej: primera vez que aparece BAU PF LT):

```javascript
const POLICY_MAP_SELLERS_DATA = {
  "BAU PF LT": "BAU PF LT", "BAU PF SMB": "BAU PF SMB",
  "PISOS PF LT": "PISOS PF LT", "PISOS PF SMB": "PISOS PF SMB",
  "OPF PF LT": "OPF PF LT", "OPF PF SMB": "OPF PF SMB",
  // Agregar PJ si aparecen en el futuro
} ;
```

---

## CHECKLIST FINAL — SELLERS

- [ ] Paso 0 completado — confirmado que es SELLERS
- [ ] Funnels EOC extraídos (killer_rules + policy) para grupos 10–15
- [ ] Query S2 (métricas) corrida sin errores
- [ ] Query S3 (antigüedad × GC/GI) corrida sin errores
- [ ] Constantes `[MES]S_FUNNELS`, `[MES]S_METRICS`, `[MES]S_GC_POL`, `[MES]S_GC_DIM`, `[MES]S_COMPETENCIA` inyectadas
- [ ] `MONTHS_SELLERS` tiene el nuevo mes como primer elemento (newest-first)
- [ ] `POLICY_MAP_SELLERS_DATA` actualizado si hay grupos nuevos
- [ ] El nuevo mes aparece en los selectores de comparación de meses
- [ ] Subido al Grid

---

## ──────────────────────────────────────────
## FLUJO SIMULACIONES (sub-hoja Simulaciones)
## ──────────────────────────────────────────

Compara **dos corridas de tipo SIMULATION** entre sí, en vez de dos meses. Sirve para medir el
impacto de un cambio antes de llevarlo a producción: sacar un killer, mover un umbral, probar
una política nueva.

No reemplaza al flujo mensual — es una hoja aparte, con sus propios datos y su propia constante JS.

### Diferencias clave vs el flujo mensual

| Aspecto | Campañas (mensual) | Simulaciones |
|---|---|---|
| Qué compara | Mes A vs Mes B | Simulación A vs Simulación B |
| Constante JS | `MONTHS` | `SIMULACIONES` |
| Orden del objeto | newest-first | newest-first (la versión nueva primero) |
| Tipo en EOC | `CAMPAIGN` | `SIMULATION` |
| Grupos | 9 políticas | normalmente 1 grupo por corrida |
| Grupo control | Sí (GC/GI) | **No** — `CAMPAIGN_CONTROL_GROUP` siempre false |
| BQ Sessions | Requeridas | **No** — CTEs directas |
| Origen de ratings | `BT_VU_MODEL_RATING` | `ACTIONABLE_COLUMNS` |
| Novedades / KILLER_NOTES | Sí | No aplica |
| Competencia de políticas | Sí | No aplica |

### Qué muestra la hoja

- **Métricas generales** — 5 cards (usuarios, límite actual, límite final, multiplicador, exposición)
- **Apertura por versión** — una fila por simulación con Δ contra la versión de referencia (A)
- **Resumen del funnel** — universo, sobrevivientes a killers, tasa de aprobación de política
- **Diferencias detectadas** — killers 🔴 sólo en A, 🟢 sólo en B, 🟡 con distinto volumen excluido
- **Matriz de ratings BHV × Upsell** — selector con 4 vistas: % de clientes, límite final avg,
  límite actual avg, multiplicador avg. Ejes comunes a las dos versiones para comparar celda a celda
- **Funnel de killers** — barras comparativas, mismo render que Campañas

### Paso SIM-1: Funnel de killers desde EOC

Para **cada** simulación a comparar:

```
Herramienta: get_campaign_execution_dashboard
campaign_id: [ID_SIMULACION]
include: killer_rules
```

Extraer, respetando el orden exacto que devuelve EOC (no reordenar):
- `processing_funnel`: `total_users`, `excluded_by_rules`, `excluded_by_policy`, `users_to_impact`
- `killer_rules[]`: `name`, `excluded_users`, `accumulated_users`
- `execution.id` (el `exec_id`, necesario para las queries BQ) y `group_name`

### Paso SIM-2: Métricas generales (BQ)

Correr `queries/simulaciones_metricas.sql` del repo, reemplazando `[EXEC_ID_A]` y `[EXEC_ID_B]`.
Devuelve usuarios, límite actual avg, límite final avg, multiplicador y exposición por simulación.

> **Validación obligatoria:** `usuarios` tiene que coincidir **exacto** con `users_to_impact` que
> devolvió EOC en el Paso SIM-1. Si no coinciden, algo está mal en el join y no hay que seguir.

### Paso SIM-3: Matriz de ratings (BQ)

Correr `queries/simulaciones_matriz_ratings.sql`. Devuelve el cruce BHV × Upsell con usuarios,
límite actual avg, límite final avg y multiplicador por celda.

Los ratings salen de `ACTIONABLE_COLUMNS` (`INTERNAL_RATING_BEHAVIOR_TC` e
`INTERNAL_RATING_UPSELL_TC`) — es la foto del momento de la corrida y evita depender de
`VALID_FROM_DT` / `VALID_TO_DT` como hace el flujo mensual.

### Paso SIM-4: Inyectar en el HTML

Las simulaciones se agrupan por **campaña** en `SIM_GRUPOS`. Cada grupo es un experimento
independiente con su propia versión original; para arrancar un experimento nuevo se agrega una
clave de grupo y no se toca nada del render.

> **⚠ Orden: newest-first.** Dentro de cada grupo, la versión **más nueva va primera**.
>
> El motivo: los selectores toman `Object.keys()[0]` como **A**, y todo el dashboard interpreta
> **A = versión bajo análisis**. Con ese orden los Δ se leen "nuevo vs base" y dan **positivos**
> cuando la versión nueva crece.
>
> Si se invierte el orden no se rompe nada — las etiquetas se recalculan solas a partir de los
> selectores — pero todos los Δ aparecen con el signo cambiado y el killer eliminado se muestra
> como agregado. **Siempre la nueva primero.**

> **⚠ La original se marca con `es_original: true`**, no por posición. Es la línea base contra la
> que se miden todas las versiones del grupo en métricas, apertura y resumen del funnel. Si falta
> el flag, el dashboard cae a la última del objeto — que suele ser la correcta, pero no siempre.

```js
const SIM_GRUPOS = {
  "[NOMBRE DE LA CAMPAÑA DE SIMULACIÓN]": {   // ej: "202608-MLB-CROSS-TC FULL-UPSELL-BAU-ADHOC"
  "[ID] — [etiqueta]": {          // NUEVA primero. Ej: "6969 — v4"
    campaign_id: [ID],
    name: "[NOMBRE_EN_EOC]",
    exec_id: "[EXEC_ID]",
    group_name: "[GRUPO]",
    eoc_url: "https://credits-admin.adminml.com/eoc/campaigns/audience/[ID]?executionId=[EXEC_ID]&tab=campaign",
    funnel:  { total_users: N, excluded_by_rules: N, excluded_by_policy: N, users_to_impact: N },
    killers: [{ name: "K-...", excluded: N, accumulated: N }, ...],
    metrics: { usuarios: N, lim_actual: N, lim_final: N, mult: N, exposicion: N },
    rating_matrix: { "A": { "B": { usuarios: N, lim_actual: N, lim_final: N, mult: N }, ... }, ... },
    es_original: true             // SÓLO en la versión base del experimento
  },
  // ... versiones anteriores del mismo experimento, de más nueva a más vieja
  },
  // ... otros experimentos, cada uno con su propio grupo
} ;
```

Los selectores se pueblan solos con `Object.keys()` del grupo activo — no hay que tocar el HTML.

**Qué filtra cada sección:**

| Sección | Compara |
|---|---|
| Métricas generales | la versión de A **siempre contra la original** |
| Apertura por versión | todas las versiones del grupo, cada una contra la original |
| Resumen del funnel | todas las versiones del grupo, cada una contra la original |
| Diferencias + Funnel de killers | par propio de selectores |
| Matriz de ratings | par propio de selectores |

**Cómo leer A vs B:**

| | A | B |
|---|---|---|
| Cards de métricas | valor destacado en azul | valor gris de referencia |
| Apertura por versión | fila con los Δ | fila marcada "original — base" |
| Diferencias | sólo en A → 🟢 killer **agregado** | sólo en B → 🔴 killer **eliminado** |
| Funnel | barra azul | barra gris |

### Paso SIM-5: Validar y subir

Validar headless con jsdom antes de subir (ver README del repo). Chequea que las dos sub-hojas
rendericen y que no haya errores de JS:

```bash
npm i jsdom
node -e "
const {JSDOM} = require('jsdom'), fs = require('fs');
const dom = new JSDOM(fs.readFileSync('dashboard_eoc.html','utf8'), {runScripts:'dangerously'});
const w = dom.window, d = w.document;
w.switchSubTab('simulaciones');
console.log('cards:', d.getElementById('simMetricsRow').querySelectorAll('.metric-card').length);
console.log('funnel:', d.getElementById('simFunnelBody').querySelectorAll('.funnel-row').length);
w.switchSubTab('campanas');
const sp = d.getElementById('selPolicy'); sp.value='BAU'; sp.dispatchEvent(new w.Event('change'));
console.log('campañas funnel:', d.getElementById('funnelBody').querySelectorAll('.funnel-row').length);
"
```

Después subir con `file_new_version: true` sobre el `doc_id` del dashboard.

### Trampas conocidas

- **`renderMetrics` y `renderFunnels` son compartidos** entre Campañas y Simulaciones. Aceptan un
  último argumento opcional con los IDs del DOM donde escribir; si se omite usan los de Campañas.
  **Al tocarlos hay que probar las dos hojas**, no sólo la que estás cambiando.
- **Si los Δ dan todos negativos, revisá el orden de `SIMULACIONES`.** Casi siempre significa que la
  versión vieja quedó primera y el dashboard la tomó como A. Es el error más fácil de cometer al
  cargar una simulación nueva, y no da ningún error: los números están bien, el signo al revés.
- **Un killer puede excluir distinto sin haber cambiado.** Si desaparece un killer previo, a los
  siguientes les entra más gente y excluyen más en absoluto. El panel de diferencias lo aclara,
  pero al interpretar los números no hay que confundir efecto cascada con cambio de lógica.
- **Las simulaciones no tienen grupo control.** Verificar con `COUNTIF(CAMPAIGN_CONTROL_GROUP)`
  antes de asumir que la matriz necesita el filtro GI que sí usa Campañas.
- **La apertura por versión asume un grupo por simulación.** Si comparás corridas multi-grupo hay
  que extender esa tabla para abrir por grupo además de por versión.

### CHECKLIST — SIMULACIONES

- [ ] Funnels EOC extraídos para las dos simulaciones (`include: killer_rules`)
- [ ] Query de métricas corrida — `usuarios` coincide exacto con `users_to_impact` de EOC
- [ ] Query de matriz de ratings corrida — suma de usuarios coherente con el total
- [ ] Entrada agregada a `SIMULACIONES` con los 7 campos (incluye `metrics` y `rating_matrix`)
- [ ] `SIMULACIONES` ordenado newest-first — la nueva primero, y los Δ por defecto dan positivos
- [ ] Validación jsdom OK — ambas sub-hojas renderizan, 0 errores de JS
- [ ] Hoja Campañas verificada sin regresiones
- [ ] Subido al Grid con `file_new_version: true`

---

## ──────────────────────────────────────────
## HOJA HISTORIAL DE CAMBIOS
## ──────────────────────────────────────────

Responde "qué cambió de un mes al otro" con tres bloques, filtrables por política:

1. **Línea de tiempo** — las novedades **declaradas** a mano. Sale de `MONTH_COMMENTS` y
   `KILLER_NOTES`, que ya se cargan en el flujo mensual (Partes 1 y 7-8). La hoja sólo las
   consolida: en Campañas se ven filtradas por la política seleccionada, acá se ven todas juntas.
2. **Diff de campañas** — killers, **automático** contra EOC.
3. **Cambios de política** — parámetros por segmento, **automático** contra EOC.

Los bloques 2 y 3 existen para **auditar** el bloque 1. En la primera corrida encontraron tres
notas incorrectas de Ago-26 (un killer nuevo sin declarar, uno declarado como eliminado que seguía
activo en 5 de 9 políticas, y un reemplazo declarado para todas que sólo ocurrió en BAU).

### Diff de campañas (killers)

Datos: `get_campaign_execution_dashboard(campaign_id, include="killer_rules")` para las dos
campañas. Se excluyen los grupos de sellers de la campaña más nueva si la otra no los tiene —
no son políticas nuevas, son otro producto con su propia hoja.

> **⚠ Comparar tasa de corte, no volumen absoluto.** El universo de entrada cambia mes a mes, así
> que en absoluto casi todos los killers "cambian" y el diff se vuelve ruido (330 falsos positivos
> en Ago vs Jul). La tasa de corte de cada killer — excluidos sobre los que le entran — sí es
> comparable; con umbral de 2pp quedan 17 movimientos reales.

### Campañas extra del mes

Además de la campaña principal del condensador, un mes puede tener **campañas adicionales**:
ejecuciones aparte, sobre una sola política, con killers relajados para cerrar un gap de volumen.
Se cargan en `CAMPANAS_EXTRA` y se muestran dentro del bloque del mes en la línea de tiempo, con
el motivo, los killers tocados, el impacto contra la campaña principal y un bloque de
verificaciones.

```js
const CAMPANAS_EXTRA = {
  "[MES]": [{
    campaign_id, name, exec_id, estado,     // estado: PROCESSED / PENDING / ...
    politica: "[nombre del grupo en EOC]",  // ej "RIESGO MED. SOW" — no la etiqueta corta
    eoc_url, motivo,
    quitados:  [{ n: "K-...", d: "por qué / por qué se reemplazó" }],
    agregados: [{ n: "K-...", d: "qué contempla" }],
    base: { campaign_id, grupo, impactados, sobreviven, n_killers },  // la campaña principal
    funnel, n_killers, sobreviven,
    gc_pct, gc_users, gi_users,             // el impacto real es gi_users, no users_to_impact
    verificaciones: [{ ok: true|false|null, t: "..." }],
  }]
};
```

**Siempre verificar los killers declarados contra EOC** antes de cargarlos. El diff automático ya
encontró notas incorrectas más de una vez.

> **⚠ `users_to_impact` incluye el grupo control.** Si la campaña tiene GC, el volumen incremental
> real es `users_to_impact − gc_users`. En la 6970 de Ago-26 la diferencia fue 62.659 vs 56.394.

> **⚠ Chequear el `execution_state`.** Si está en `PENDING` los números todavía pueden moverse;
> conviene volver a traerlos cuando pase a `PROCESSED`. La tarjeta lo marca con un badge.

#### Verificar qué se excluye y dónde

Cuando una campaña relaja killers, conviene chequear que las exclusiones que importan sigan en
pie. Hay **tres lugares** donde se puede excluir población, y hay que mirar los tres:

| Nivel | Cómo se consulta |
|---|---|
| Universo | `get_campaign_detail(id, sections=["universe"])` |
| Política | `get_policy_detail(policy_id)` → `attributes`, `settings[].conditions`, `exceptions` |
| Killers | `get_campaign_execution_dashboard(id, include="killer_rules")` |

El script `queries/check_sellers.py` hace exactamente esto para el caso de sellers y sirve de
plantilla para cualquier otra exclusión.

**Resultado del chequeo en la 6970 (Ago-26):** los sellers se excluyen **sólo** por el killer
`K-SELLERS-2` (`PROSPECT_UNIVERSE.RISK_MANAGEMENT_TAG == MERCHANT`). La política de Riesgo Medio
segmenta únicamente por antigüedad y ratings, y el universo (`MLB / CROSS / TC - ACEPTADA`) no
filtra por tipo de cliente. Verificado en BQ: de los 62.659 impactados, **0** tienen tag MERCHANT,
y los 3,57M de merchants del universo quedaron todos afuera.

> **⚠ La exclusión de sellers cuelga de un solo killer.** No hay respaldo en política ni universo.
> Si en una iteración se saca o modifica `K-SELLERS-2` buscando volumen, entran 3,5M de merchants
> sin que nada más los frene. Tenerlo presente justamente en las campañas extra, que existen para
> relajar killers.

### Cambios de política

Los scripts están en el repo: `queries/fetch_policies.py` baja las políticas crudas y
`queries/diff_policies.py` genera el diff.

> **⚠ Bajar las políticas a disco, no por contexto.** `fetch_policies.py` usa el fallback HTTP del
> MCP (documentado al final de este instructivo) y persiste el JSON tal cual lo devuelve EOC. Pedir
> 18 políticas por las tools y transcribirlas es un vector de error grande.

Reglas de matcheo, todas necesarias para que el diff no engañe:

- Los segmentos se matchean por su **tupla de condiciones normalizada** (rating upsell, rating BHV,
  rango de antigüedad), **nunca por `attribute_index` ni por ids**: el índice es sólo orden de carga
  en la UI y los `parameter_id` / `attribute_definition_id` son distintos en cada política.
- **Normalizar el case** de los nombres de columna: la misma columna aparece como `withdraw_limit`
  en una política y `WITHDRAW_LIMIT` en otra.
- Los valores de condición son **string literal** — pueden ser expresiones tipo `=in(A,B)`.
- Lo que no matchea **no se fuerza**: va a un balde aparte y la UI lo marca.
- **Los valores viven en `parameter_values` para los settings y en `parameter_modify` para las
  exceptions.** Leer sólo uno devuelve "sin cambios" en silencio — el peor modo de fallar, porque
  parece que no pasó nada.
- En exceptions comparar nombre, contenido **y orden**: la pipeline es secuencial, cada excepción
  lee el resultado de la anterior, así que insertar una en el medio cambia el cálculo.

Para actualizarlo: cambiar el dict `POLICIES` de los dos scripts con los `policy_id` de cada
campaña (salen de `MONTHS[mes].meta.policies`), correr `fetch_policies.py`, después
`diff_policies.py`, y regenerar el `POL_DIFF` del HTML.

---

## Grid IDs
- **Dashboard:** `01KVB1DRFMEQYZ4THQ3SGHM3AR` → https://grid.adminml.com/d/01KVB1DRFMEQYZ4THQ3SGHM3AR/view
- **Este instructivo:** `01KXGE5PEQ6EMZTB60B5NPG0HG` → https://grid.adminml.com/d/01KXGE5PEQ6EMZTB60B5NPG0HG/view
- **Repo local:** `/Users/nbattaglia/Documents/tablero-upsell/` — HTML publicado, queries BQ (`queries/`), datos de simulaciones (`data/`) y README

---

### Cómo llamar al EOC MCP cuando las tools no están disponibles en contexto

Si al iniciar la sesión los tools de `eoc-mcp` no aparecen (por compactación de contexto), usar el skill `eoc-ops:eoc-analyst` que los re-expone. Si tampoco funciona, llamar directamente via HTTP con Tiger token:

```python
import asyncio, json, urllib.request
from mcp_remote_proxy import furyauth  # requiere ~/.mcp-remote-proxy/venv activado

async def main():
    token = await furyauth.get_fury_auth_token_async()
    BASE = "https://eoc-mcp.melioffice.com/mcp"
    H = {"Content-Type":"application/json","Accept":"application/json, text/event-stream","X-Tiger-Token":token}

    def call(payload, sid=None):
        h = dict(H)
        if sid: h["Mcp-Session-Id"] = sid
        req = urllib.request.Request(BASE, data=json.dumps(payload).encode(), headers=h, method="POST")
        resp = urllib.request.urlopen(req, timeout=60)
        sid_out = resp.headers.get("mcp-session-id", sid)
        raw = resp.read().decode()
        for line in raw.split('\n'):
            if line.startswith('data:'): return json.loads(line[5:].strip()), sid_out
        return {}, sid_out

    _, sid = call({"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"claude","version":"1.0"}}})
    result, _ = call({"jsonrpc":"2.0","id":2,"method":"tools/call","params":{"name":"get_campaign_execution_dashboard","arguments":{"campaign_id": CAMPAIGN_ID}}}, sid)
    data = json.loads(result["result"]["content"][0]["text"])
    print(json.dumps(data["campaign_dashboard"]["actions"], indent=2, ensure_ascii=False))

asyncio.run(main())
```
