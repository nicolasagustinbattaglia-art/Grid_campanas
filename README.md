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
  ├─ Campañas          ← sub-hoja: comparación mes a mes (flujo mensual del instructivo)
  └─ Simulaciones      ← sub-hoja: comparación entre dos corridas de simulación
```

Las sub-hojas existen sólo dentro de **Upsell Individuos**. Al pasar a Sellers la barra desaparece.

### Campañas
Comparación mes A vs mes B. Métricas generales, funnel de killers, apertura GC/GI, apertura
dinámica (NISE / antigüedad / ratings), distribución, matriz de ratings, buscador de killers y
vista Consolidado con competencia de políticas. El flujo completo de carga está en el instructivo.

### Simulaciones
Comparación entre dos simulaciones EOC, con el mismo formato visual que Campañas:

- **Métricas generales** — 5 cards (usuarios, límite actual, límite final, multiplicador, exposición)
- **Apertura por versión** — una fila por simulación con Δ contra la versión de referencia (A)
- **Resumen del funnel** — universo, sobrevivientes a killers, tasa de aprobación de política
- **Diferencias detectadas** — killers sólo en A 🔴, sólo en B 🟢, y con distinto volumen 🟡
- **Matriz de ratings BHV × Upsell** — selector con 4 vistas: % de clientes, límite final avg,
  límite actual avg y multiplicador avg. Ejes comunes a las dos versiones para comparar celda a celda.
- **Funnel de killers** — barras comparativas, mismo render que Campañas

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

3. **Inyectar** en la constante `SIMULACIONES` del HTML:
   ```js
   "<label>": {
     campaign_id, name, exec_id, group_name, eoc_url,
     funnel:  { total_users, excluded_by_rules, excluded_by_policy, users_to_impact },
     killers: [{ name, excluded, accumulated }, ...],
     metrics: { usuarios, lim_actual, lim_final, mult, exposicion },
     rating_matrix: { "<BHV>": { "<UPS>": { usuarios, lim_actual, lim_final, mult } } }
   }
   ```
   Los selectores A/B se pueblan solos con `Object.keys(SIMULACIONES)`.

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
