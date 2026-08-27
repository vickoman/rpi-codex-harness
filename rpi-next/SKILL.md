---
name: rpi-next
description: "Route and govern an RPI code-change run: create, resume, report, close, or select its one legal next phase. Use for RPI start/next/status/resume/close, not for research, planning, implementation, or review itself."
---

# RPI Next — orquestador

Gestiona el estado de un run RPI y dirige exactamente una transición legal. El
resultado es un handoff claro, no el trabajo especializado de una fase.

`rpi-next` es el único orquestador de estado. No duplica la investigación,
planificación, implementación ni revisión de los workers; decide solo si el
handoff es legal, qué worker sigue y qué debe aprobar o responder la persona
usuaria.

## Referencias obligatorias

Antes de decidir o escribir estado, lee:

1. [principios RPI](../references/rpi-principles.md): P1 y P4.
2. [contrato operativo](../references/rpi-contract.md).
3. [esquema de artefactos](../references/artifact-schema.md).

Las referencias son la autoridad de políticas, estados y esquema. No las copies ni
inventes reglas adicionales en el run.

## Modos

- `start`: crea un nuevo run y lo sitúa en `research`.
- `next`: valida el run activo y selecciona su única transición legal.
- `status`: informa el estado sin escribir nada.
- `resume`: comprueba el baseline antes de continuar un run detenido.
- `close`: cierra, sin commit, un run `DIFF_APPROVED` cuando la persona usuaria lo
  solicita explícitamente.

Si el modo no es explícito, infiérelo solo cuando la petición lo haga inequívoco;
de otro modo pregunta cuál desea la persona usuaria.

## Resolución del run y del proyecto

1. Resuelve el proyecto objetivo con `git rev-parse --show-toplevel`; si falla,
   usa el directorio de trabajo actual y decláralo en el resultado.
2. Ubica los runs en `<target-root>/.codex/rpi/runs/` conforme al esquema.
3. Si se indicó `run_id`, úsalo solo si existe en ese proyecto. Si no se indicó y
   hay exactamente un run no terminal, úsalo. Si hay cero o más de uno, no elijas:
   informa o solicita el `run_id`.
4. Respeta `AGENTS.md` del proyecto objetivo y conserva cualquier cambio de la
   persona usuaria.

Un run no terminal incluye cualquiera que aún tenga una transición o gate pendiente.
`CLOSED_UNCOMMITTED` es terminal. Nunca uses el nombre de una rama para deducir un
ticket.

## Reglas de cada modo

### `start`

- Rechaza un `run_id` duplicado y no alteres runs existentes.
- Genera el ID inmutable definido por el esquema: ticket provisto por la persona
  usuaria o prefijo `NO-TICKET`, timestamp UTC, slug y sufijo.
- Crea únicamente el directorio del run, `manifest.yaml` y `LATEST`; no modifica
  código fuente, `.gitignore`, Graphify, ni ningún sistema externo.
- Captura el `base_ref` y el estado de worktree como evidencia. Si `.codex/rpi/`
  no está ignorado por Git, informa una advertencia pero no lo cambies.
- Deja `current_phase: research`, `status: in_progress` y `next_action: research`.
- Si el worker `rpi-research` no está disponible, responde
  `NEXT_WORKER_UNAVAILABLE` con el handoff requerido; no investigues en su lugar.

### `next`

- Lee `manifest.yaml` y los artefactos que la transición necesita. Comprueba que
  el baseline no haya derivado cuando el contrato lo exige.
- Aplica estrictamente esta tabla, sin saltos ni inferencias:

  | Estado/fase del run | Precondición | Siguiente handoff |
  | --- | --- | --- |
  | `in_progress` / `research` | run nuevo y baseline capturado | `rpi-research` |
  | `RESEARCH_COMPLETE` / `research` | sin brechas materiales | `rpi-plan create` |
  | `AWAITING_GAP_CLOSURE` | `GAPS.md` abierto | persona usuaria; no avanzar |
  | `READY_FOR_REVIEW` / `plan` | `PLAN.md` presente y baseline vigente | `rpi-review mode: plan` |
  | `REJECTED` / `review` | `review_revision_count < 2`, rechazo corregible en alcance | `rpi-plan revise` |
  | `REJECTED` / `review` | contador en 2 o decisión externa | persona usuaria; no tercer ciclo |
  | `APPROVED` o `APPROVED_WITH_WARNINGS` / `review` | sin brechas | `rpi-implement` y gate aplicable |
  | `AWAITING_IMPLEMENTATION_APPROVAL` / `implement` | gate falso | persona usuaria; no escribir fuente |
  | `VALIDATED` / `implement` | implementación y validaciones completas | `rpi-review mode: diff` |
  | `DIFF_APPROVED` / `review` | gate de diff falso o verdadero, sin commit implícito | `close` solo si se solicita |
  | `DIFF_REJECTED` | deriva, cambio fuera de alcance o fallo | persona usuaria; no corregir ni revertir |
  | `BLOCKED`, `VALIDATION_FAILED`, `SECURITY_GATE_FAILED`, `STOPPED` | dirección y baseline vigente | `resume` solo tras confirmación |
  | `CLOSED_UNCOMMITTED` | estado terminal | ninguna |

- Si `standard`/`high-risk` llegan a implementación sin aprobación explícita
  ligada a run, baseline y archivos, conserva el gate falso y dirige a
  `AWAITING_IMPLEMENTATION_APPROVAL`; nunca lo infieras de `APPROVED`.
- Actualiza el manifiesto solo para reflejar una transición legal o un gate
  explícitamente concedido. Conserva historial en vez de sobrescribir evidencia.
- Para la fase siguiente, carga solo el worker correspondiente:
  `research → rpi-research`, `plan → rpi-plan`, `review → rpi-review`,
  `implement → rpi-implement`. Si aún no existe o no está disponible, responde
  `NEXT_WORKER_UNAVAILABLE` con la entrada esperada; no sustituyas el worker ni
  modifiques código.

### `status`

- Lee únicamente. Reporta la verdad del manifiesto y la evidencia disponible; no
  «arregles» estado incompleto o inconsistente.

### `resume`

- Verifica `base_ref`, estado del worktree, precondiciones relevantes y solapamiento
  con otros runs antes de cambiar de `STOPPED`, `BLOCKED`, `VALIDATION_FAILED` o
  `SECURITY_GATE_FAILED`. Reanuda solo con dirección explícita; un `DIFF_REJECTED`
  requiere primero una decisión humana sobre el diff.
- Ante deriva material, cambio inesperado o precondición rota, conserva el estado,
  reporta la evidencia y espera dirección.

### `close`

- Requiere petición explícita de cierre y estado `DIFF_APPROVED` sin commit.
- Establece `status: CLOSED_UNCOMMITTED`, limpia `next_action`, actualiza
  `closed_at` y `updated_at` en UTC. No genera un commit.

## Salida conversacional requerida

En cada respuesta entrega, de forma breve:

```text
run_id: <id o no creado>
proyecto: <root>
baseline: <ref y clean/dirty/unavailable>
estado: <status / fase>
hecho: <acción o verificación realizada>
bloqueo_o_gate: <ninguno o detalle>
siguiente: <worker, acción del usuario o sin acción>
regla: <referencia breve al contrato que seleccionó el resultado>
```

Ante una brecha material, formula la pregunta necesaria y no avances. Ante una
transición inválida, explica el estado actual y la transición permitida.

## Límites

`rpi-next` no ejecuta investigación, planificación, revisión, implementación,
pruebas, regeneración de Graphify, commits, despliegues, PRs, rollback ni arreglos
automáticos. Tampoco decide por la persona usuaria un ticket, una brecha material,
un riesgo que deba elevarse o una aprobación requerida.
