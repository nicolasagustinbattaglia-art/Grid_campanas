# Tablero de Upsell — Dashboard EOC Condensador (TC MLB)

Dashboard HTML del Condensador EOC para Tarjeta de Crédito en Brasil. Vive en Grid y se actualiza
mes a mes con los resultados de cada campaña.

| Recurso | ID / Link |
|---|---|
| Dashboard | `01KVB1DRFMEQYZ4THQ3SGHM3AR` — [abrir](https://grid.adminml.com/d/01KVB1DRFMEQYZ4THQ3SGHM3AR/view) |
| Instructivo de actualización | `01KXGE5PEQ6EMZTB60B5NPG0HG` — [abrir](https://grid.adminml.com/d/01KXGE5PEQ6EMZTB60B5NPG0HG/view) |

## Estructura del dashboard

```
UPSELL INDIVIDUOS  |  UPSELL SELLERS      ← nav de producto
  ├─ Campañas               ← comparación mes a mes (flujo mensual del instructivo)
  ├─ Simulaciones           ← comparación entre versiones de un experimento
  └─ Historial de cambios   ← qué cambió mes a mes, declarado y verificado
```

Las sub-hojas existen sólo dentro de **Upsell Individuos**. Al pasar a Sellers la barra desaparece.

### Campañas
Comparación mes A vs mes B. Métricas generales, funnel de killers, apertura GC/GI, apertura
dinámica (NISE / antigüedad / ratings), distribución, matriz de ratings, buscador de killers y
vista Consolidado con competencia de políticas. El flujo completo de carga está en el instructivo.

### Simulaciones
Las simulaciones se agrupan por **campaña** (`SIM_GRUPOS`): cada grupo es un experimento
independiente, con su propia versión original como base. La barra de arriba cambia de grupo y
todo el resto de la hoja se recalcula.

Dentro de un grupo, cada sección tiene su propio filtro:

| Sección | Qué compara |
|---|---|
| Métricas generales | la versión elegida en A **siempre contra la original** |
| Apertura por versión | todas las versiones, cada una contra la original |
| Resumen del funnel | todas las versiones, cada una contra la original |
| Diferencias + Funnel de killers | par propio de selectores |
| Matriz de ratings BHV × Upsell | par propio + 4 vistas (% clientes, límite final/actual avg, multiplicador) |

La **original se marca con el flag `es_original`**, no por posición: reordenar el objeto no
cambia la base de comparación.

### Historial de cambios
Tres bloques, con un filtro de política común:

1. **Línea de tiempo** — novedades declaradas a mano (`MONTH_COMMENTS` + `KILLER_NOTES`),
   consolidadas mes a mes en lugar de filtradas por política como en Campañas.
2. **Diff de campañas** — killers, automático contra EOC. Usa **tasa de corte**, no volumen
   absoluto: el universo de entrada cambia mes a mes y comparar absolutos marca como "cambio"
   casi todos los killers.
3. **Cambios de política** — parámetros por segmento, automático. Ver sección más abajo.

Los bloques 2 y 3 sirven para **auditar** el bloque 1: ya detectaron notas incorrectas.

## Contenido del repo

```
dashboard_eoc.html                      copia del HTML publicado en Grid
data/c6965.json                         funnel de killers — simulación 6965 (original)
data/c6964.json                         funnel de killers — simulación 6964 (v2)
data/matrix.json                         matriz BHV × Upsell de ambas simulaciones (salida BQ)
queries/simulaciones_metricas.sql       métricas generales por simulación
queries/simulaciones_matriz_ratings.sql matriz BHV × Upsell por simulación
```

## Cómo cargar una simulación nueva

1. **Funnel de killers** — desde el MCP de EOC:
   ```
   get_campaign_execution_dashboard(campaign_id=<ID>, include="killer_rules")
   ```
   Guardar `name` + `accumulated_users` **en el orden exacto** que devuelve EOC, junto con
   `processing_funnel` (`total_users`, `excluded_by_policy`, `users_to_impact`).

2. **Métricas y matriz** — correr las dos queries de `queries/` reemplazando los `[EXEC_ID_*]`.

3. **Inyectar** en `SIM_GRUPOS`, dentro del grupo que corresponda:
   ```js
   const SIM_GRUPOS = {
     "<NOMBRE DE LA CAMPAÑA DE SIMULACIÓN>": {
       "<label>": {                       // ej: "6969 — v4". La más nueva va primera.
         campaign_id, name, exec_id, group_name, eoc_url,
         funnel:  { total_users, excluded_by_rules, excluded_by_policy, users_to_impact },
         killers: [{ name, excluded, accumulated }, ...],
         metrics: { usuarios, lim_actual, lim_final, mult, exposicion },
         rating_matrix: { "<BHV>": { "<UPS>": { usuarios, lim_actual, lim_final, mult } } },
         es_original: true                // sólo en la versión base del experimento
       }
     }
   };
   ```
   Para un experimento nuevo, agregar una clave de grupo — el resto del render no se toca.
   Los selectores se pueblan solos con `Object.keys()` del grupo activo.

4. **Subir** a Grid con `file_new_version: true` sobre el `doc_id` del dashboard.

## Cosas que conviene saber

- **`renderMetrics` y `renderFunnels` son compartidos** entre Campañas y Simulaciones. Aceptan un
  último argumento opcional con los IDs del DOM donde escribir; si se omite, usan los de Campañas.
  Al tocarlos hay que probar las dos hojas.
- **Las simulaciones no tienen grupo control** (`CAMPAIGN_CONTROL_GROUP` siempre false), a diferencia
  de las campañas productivas. Por eso la matriz de Simulaciones no filtra por GI.
- **Un killer puede excluir distinto sin haber cambiado.** Si un killer previo desaparece, a los
  siguientes les entra más gente y excluyen más en términos absolutos. El panel de diferencias
  avisa de esto explícitamente — no confundir efecto cascada con cambio de lógica.
- **Validar siempre contra EOC**: la cantidad de usuarios que devuelve la query de métricas tiene
  que coincidir exacto con `users_to_impact` del dashboard de EOC.
- **Si los killers vienen transcriptos y no extraídos programáticamente**, verificar la cadena
  `acumulado[i] = acumulado[i-1] − excluidos[i]` en toda la secuencia. Un error de tipeo la rompe.
  Tiene que cerrar además contra `total − excluded_by_rules` y contra
  `impactados + excluded_by_policy`.
- **`SIMULACIONES` es `let`, no `const`** — apunta al grupo activo de `SIM_GRUPOS` y
  `switchSimGrupo` la reasigna. El resto del render la consume sin saber que hay grupos.

## Testing

El HTML se puede validar headless con jsdom antes de subirlo — cubre que ambas sub-hojas rendericen,
que los selectores respondan y que no haya errores de JS:

```bash
npm i jsdom
node -e "
const {JSDOM} = require('jsdom'), fs = require('fs');
const dom = new JSDOM(fs.readFileSync('dashboard_eoc.html','utf8'), {runScripts:'dangerously'});
const w = dom.window, d = w.document;
w.switchSubTab('simulaciones');
console.log('cards:', d.getElementById('simMetricsRow').querySelectorAll('.metric-card').length);
console.log('funnel:', d.getElementById('simFunnelBody').querySelectorAll('.funnel-row').length);
"
```

## Diff de políticas (hoja Historial)

`queries/fetch_policies.py` baja el detalle crudo de las políticas desde el MCP de EOC vía
HTTP y lo persiste en `data/policies/{policy_id}.json`. Se usa el fallback HTTP en lugar de
las tools MCP a propósito: 18 políticas pasando por el contexto de un agente se transcriben
a mano y eso es un vector de error grande. Acá el payload llega a disco tal cual lo devuelve EOC.

`queries/diff_policies.py` compara las políticas de dos campañas y genera el diff.

**Reglas de matcheo** (importan para no producir un diff que engañe):

- Los segmentos se matchean por su **tupla de condiciones normalizada**, nunca por
  `attribute_index` ni por ids. El índice es sólo orden de carga en la UI, y los
  `parameter_id` / `attribute_definition_id` son distintos en cada política.
- Los nombres de columna se **normalizan a mayúsculas**: la misma columna aparece como
  `withdraw_limit` en una política y `WITHDRAW_LIMIT` en otra.
- Los valores de condición se toman como **string literal** — pueden ser expresiones (`=in(A,B)`).
- Lo que no matchea **no se fuerza**: va a `seg_solo_a` / `seg_solo_b` y la UI lo marca.
- Los valores viven en `parameter_values` para los settings y en `parameter_modify` para las
  exceptions. Leer sólo uno devuelve "sin cambios" en silencio, que es el peor modo de fallar.
- En exceptions se compara nombre, contenido **y orden**: la pipeline es secuencial, así que
  insertar una excepción en el medio cambia el resultado aunque ninguna otra se toque.

Para actualizarlo el mes que viene: editar el dict `POLICIES` de los dos scripts con los
`policy_id` de cada campaña (salen de `MONTHS[mes].meta.policies` del HTML), correr
`fetch_policies.py` y después `diff_policies.py`, y regenerar `data/pol_diff_ui.json`.

## Verificar exclusiones (universo / política / killers)

Cuando una campaña relaja killers conviene chequear que las exclusiones que importan sigan en pie.
Hay **tres niveles** donde se puede excluir población y hay que mirar los tres:

| Nivel | Cómo se consulta |
|---|---|
| Universo | `get_campaign_detail(id, sections=["universe"])` |
| Política | `get_policy_detail(policy_id)` → `attributes`, `settings[].conditions`, `exceptions` |
| Killers | `get_campaign_execution_dashboard(id, include="killer_rules")` |

`queries/check_sellers.py` hace exactamente esto para sellers y sirve de plantilla para cualquier
otra exclusión.

**Hallazgo (Ago-26, campaña 6970):** los sellers se excluyen **sólo** por el killer `K-SELLERS-2`
(`PROSPECT_UNIVERSE.RISK_MANAGEMENT_TAG == MERCHANT`). La política de Riesgo Medio segmenta
únicamente por antigüedad y ratings; el universo (`MLB / CROSS / TC - ACEPTADA`) no filtra por tipo
de cliente. Verificado en BQ: de 62.659 impactados, **0** con tag MERCHANT, y los 3,57M de merchants
del universo quedaron todos afuera.

> ⚠ **No hay defensa en profundidad.** Si se saca o modifica `K-SELLERS-2` buscando volumen, entran
> 3,5M de merchants sin que nada más los frene. Vale tenerlo presente en las campañas extra, que
> justamente existen para relajar killers.
