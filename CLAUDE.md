# Dashboard EOC Condensador (TC Upsell MLB) — instrucciones para Claude

Leé esto antes de tocar cualquier archivo de este repo.

## 🔒 Regla crítica — Individuos vs Sellers

**Este dashboard SOLO se actualiza del lado de Individuos.** La sub-hoja/producto "Upsell Sellers"
**no se toca nunca** — ni se recalculan sus datos, ni se sube una versión que la modifique de paso
al subir cambios de Individuos. Antes de subir cualquier versión nueva del HTML a Grid, verificar
que los datos de Sellers (`POLICY_MAP_SELLERS`, bloques de Sellers en Killers/Historial) quedaron
**exactamente iguales** a la versión anterior. Si alguna vez hay que actualizar Sellers, es una
tarea separada y explícita — nunca "ya que estamos, actualizamos las dos".

## 📦 Control de versiones — SIEMPRE versión nueva, NUNCA pisar

Este repo tiene remoto en GitHub: https://github.com/nicolasagustinbattaglia-art/Grid_campanas
(rama `master`, **público** — confirmado explícitamente por el dueño del proyecto, sabiendo que
tiene lógica de negocio interna de MELI). Tiene más de un colaborador con acceso de escritura
(además del dueño, al menos `jmarquina`/Juan Maria Marquina) — no asumir que sos el único que
puede haber tocado el repo.

**🔒 Antes de arrancar CUALQUIER modificación a este tablero: `git fetch origin` y `git log
origin/master --oneline` (o `git pull`) para chequear si hay commits nuevos que tu copia local
no tiene.** Un compañero puede haber pusheado cambios (incluso del lado de Sellers) sin avisar
en esta conversación. Si hay commits nuevos, traerlos primero (`git pull`/merge, nunca descartar
con `reset --hard`) antes de empezar a editar — de lo contrario el próximo `file_new_version` a
Grid puede pisar trabajo ajeno que ni sabías que existía.

**Regla dura: cada cambio es un commit NUEVO. Nunca se reescribe ni se pisa el historial.**

- **Prohibido:** `git commit --amend`, `git push --force` / `--force-with-lease`, `git rebase` sobre
  commits ya pusheados, `git reset --hard` seguido de un commit "limpio", o cualquier operación que
  reemplace un commit existente en vez de agregar uno arriba. Si algo salió mal en un commit
  anterior, se corrige con un commit nuevo que lo arregla — no se reescribe el que ya existe.
- **Commitear cada cambio lógico** antes de dar una tarea por terminada — nunca dejar `git status`
  con cambios sueltos. Un commit por versión de simulación agregada, por fix, por feature — no
  amontonar varios cambios no relacionados en un solo commit gigante.
- **Pushear a `origin` solo cuando el usuario lo pida explícitamente** — el remoto está listo, pero
  no hay que asumir push automático después de cada commit. Una vez pusheado, un commit en
  `master` es historia pública — no se toca.
- El HTML final también se sube a Grid con `file_new_version: true` (**nunca** reemplazando la
  versión actual sin bump) — mismo principio: versión nueva siempre, nunca se pisa la anterior.
- El commit a git es el que deja el historial auditable de *qué* cambió y *por qué* — Grid guarda
  versiones del archivo pero no el razonamiento detrás de cada cambio.

## 📖 Leer antes de cualquier cambio

**`INSTRUCTIVO.md`** en la raíz de este repo (o su versión en Grid, ver abajo) tiene el flujo
completo: cómo cargar una campaña/simulación, las queries de BigQuery correctas (y las que están
mal/descartadas y por qué), los gotchas conocidos, y un **CHANGELOG** con el detalle sesión por
sesión de todo lo hecho hasta ahora. Leerlo antes de asumir cómo funciona algo.

## Grid IDs
- Dashboard: `01KVB1DRFMEQYZ4THQ3SGHM3AR` → https://grid.adminml.com/d/01KVB1DRFMEQYZ4THQ3SGHM3AR/view
- Instructivo: `01KXGE5PEQ6EMZTB60B5NPG0HG` → https://grid.adminml.com/d/01KXGE5PEQ6EMZTB60B5NPG0HG/view
