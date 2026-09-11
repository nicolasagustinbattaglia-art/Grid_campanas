# Dashboard EOC Condensador (TC Upsell MLB) — instrucciones para Claude

Leé esto antes de tocar cualquier archivo de este repo.

## 🔒 Regla crítica — Individuos vs Sellers

**Este dashboard SOLO se actualiza del lado de Individuos.** La sub-hoja/producto "Upsell Sellers"
**no se toca nunca** — ni se recalculan sus datos, ni se sube una versión que la modifique de paso
al subir cambios de Individuos. Antes de subir cualquier versión nueva del HTML a Grid, verificar
que los datos de Sellers (`POLICY_MAP_SELLERS`, bloques de Sellers en Killers/Historial) quedaron
**exactamente iguales** a la versión anterior. Si alguna vez hay que actualizar Sellers, es una
tarea separada y explícita — nunca "ya que estamos, actualizamos las dos".

## 📦 Control de versiones — commitear siempre

Este repo tiene remoto en GitHub: https://github.com/nicolasagustinbattaglia-art/Grid_campanas
(rama `master`, **público** — confirmado explícitamente por el dueño del proyecto, sabiendo que
tiene lógica de negocio interna de MELI).

- **Commitear cada cambio lógico** antes de dar una tarea por terminada — nunca dejar `git status`
  con cambios sueltos.
- **Pushear a `origin` solo cuando el usuario lo pida explícitamente** — el remoto está listo, pero
  no hay que asumir push automático después de cada commit.
- El HTML final también se sube a Grid (ver IDs abajo) — pero el commit a git es el que deja el
  historial auditable de *qué* cambió y *por qué*.

## 📖 Leer antes de cualquier cambio

**`INSTRUCTIVO.md`** en la raíz de este repo (o su versión en Grid, ver abajo) tiene el flujo
completo: cómo cargar una campaña/simulación, las queries de BigQuery correctas (y las que están
mal/descartadas y por qué), los gotchas conocidos, y un **CHANGELOG** con el detalle sesión por
sesión de todo lo hecho hasta ahora. Leerlo antes de asumir cómo funciona algo.

## Grid IDs
- Dashboard: `01KVB1DRFMEQYZ4THQ3SGHM3AR` → https://grid.adminml.com/d/01KVB1DRFMEQYZ4THQ3SGHM3AR/view
- Instructivo: `01KXGE5PEQ6EMZTB60B5NPG0HG` → https://grid.adminml.com/d/01KXGE5PEQ6EMZTB60B5NPG0HG/view
