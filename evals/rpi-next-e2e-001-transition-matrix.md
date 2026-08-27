# Eval RPI Next E2E 001 — Matriz completa de transiciones

## Objetivo

Comprobar que `rpi-next` integra los workers sin duplicar su trabajo, nunca salta
una fase ni una aprobación y distingue bloqueos humanos de transiciones legales.

## Fixture aislado requerido

Crear un repositorio limpio con varios runs ignorados bajo `.codex/rpi/runs/`,
cada uno con el baseline actual y los artefactos mínimos de su estado:

1. `research-start`: `in_progress`, `current_phase: research`,
   `next_action: research`.
2. `plan-ready`: `RESEARCH_COMPLETE`, `current_phase: research`,
   `next_action: plan`, `RESEARCH.md` sin brechas.
3. `review-ready`: `READY_FOR_REVIEW`, `current_phase: plan`, `PLAN.md` presente.
4. `implement-ready`: `APPROVED`, `current_phase: review`, sin brechas y gate de
   implementación falso.
5. `diff-ready`: `VALIDATED`, `current_phase: implement`,
   `IMPLEMENTATION.md` completo y `next_action: rpi-review-diff`.
6. `diff-rejected`: `DIFF_REJECTED`, `current_phase: review`, con un hallazgo
   fuera de alcance y sin rollback.
7. `closed`: `CLOSED_UNCOMMITTED`, `closed_at` presente y sin `next_action`.

También deja dos runs no terminales activos y prepara una llamada sin `run_id`.
No hay fuente modificada, Graphify ni dependencias externas.

## Solicitud al skill

Para cada caso, invoca `rpi-next` con el `run_id` explícito y `mode: next`, salvo
el caso de runs múltiples donde omites `run_id`:

```text
Selecciona la siguiente transición legal de este run. No ejecutes el worker ni
modifiques código; entrega solo el handoff conversacional.
```

## Criterios de aprobación

1. Devuelve `rpi-research`, `rpi-plan create`, `rpi-review mode: plan`,
   `rpi-implement`, `rpi-review mode: diff` respectivamente para los primeros
   cinco estados, sin saltos ni trabajo especializado simulado.
2. Para `implement-ready`, conserva el gate falso y solicita la aprobación
   específica antes de escribir; no lo infiere de `APPROVED`.
3. Para `diff-rejected`, espera dirección humana y no enruta a un arreglo,
   rollback, commit o `rpi-plan revise` automático.
4. Para `closed`, informa que no existe siguiente transición.
5. Con múltiples runs activos y sin `run_id`, pide identificación; no elige uno.
6. No cambia fuente, Graphify, configuración ni artefactos de los runs durante
   el enrutamiento, salvo el manifiesto cuando una transición o gate explícito lo
   autorice.
7. Cada respuesta incluye `run_id`, proyecto, baseline, estado, hecho,
   bloqueo/gate, siguiente y regla contractual.

## Medición

Registrar la tabla de casos, handoff devuelto, estado antes/después, artefactos
modificados y diff de fuente vacío. Este eval prueba el orquestador; los workers
ya tienen evals aislados propios.
