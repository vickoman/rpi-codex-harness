---
name: rpi-implement
description: "Implement an approved RPI plan with a mandatory human gate for standard and high-risk runs, exact scope control, and evidence-backed validation. Use only after plan review approval."
---

# RPI Implement

Ejecuta únicamente un plan RPI aprobado. Esta es la única fase que puede mutar
fuente, y solo después de un preflight y del gate humano requerido. No amplía el
plan, no repara fallos automáticamente y no hace commits.

## Referencias y entradas obligatorias

Antes de escribir, lee:

1. [principios RPI](../references/rpi-principles.md): P1, P2, P3 y P4.
2. [contrato operativo](../references/rpi-contract.md).
3. [esquema de artefactos](../references/artifact-schema.md).
4. `manifest.yaml`, `RESEARCH.md`, `PLAN.md`, `REVIEW.md`, `GAPS.md` si existe,
   decisiones explícitas de la persona usuaria y `AGENTS.md` del proyecto
   objetivo.

La transición es legal solo desde una revisión de plan `APPROVED` o
`APPROVED_WITH_WARNINGS`, sin brechas materiales abiertas. Si falta una entrada,
hay un rechazo, el run supera los ciclos permitidos o el estado no es legal,
devuelve el control a `rpi-next`; no reconstruyas ni edites las fases previas.

## Permisos y límites

Antes del gate puedes escribir únicamente evidencia dentro del run:
`manifest.yaml`, `IMPLEMENTATION.md`, `GAPS.md` si aparece una decisión
material nueva, `history/` y `logs/`.

Después del gate puedes modificar solo los archivos y símbolos autorizados por el
`PLAN.md`, además de esos artefactos. Nunca cambies `PLAN.md`, `RESEARCH.md`,
`REVIEW.md`, `.gitignore`, Graphify, dependencias no autorizadas, sistemas
externos ni el historial Git. Nunca hagas commit, despliegue, PR, rollback o
reintentos automáticos.

## Preflight y gate humano

1. Confirma el repositorio objetivo, `base_ref`, worktree, entradas del plan,
   decisiones, archivos/símbolos y comandos de validación. Registra la evidencia
   y el alcance autorizado en `IMPLEMENTATION.md`.
2. Compara el árbol real con el handoff. Conserva cambios ajenos; una deriva
   material dentro del alcance, precondiciones falsas, archivos inesperados o un
   plan obsoleto deja el run en `BLOCKED`. No uses reset, stash ni rollback.
3. Para `standard` y `high-risk`, **justo antes de la primera escritura de
   fuente**, exige una confirmación explícita de la persona usuaria ligada a este
   run, baseline y lista de archivos. La confirmación debe estar reflejada en
   `human_gates.implementation_approved: true`.
4. Si falta esa confirmación, actualiza el run a
   `AWAITING_IMPLEMENTATION_APPROVAL`, mantiene el gate en `false`, no ejecuta
   comandos mutantes y pregunta: “¿Autorizas implementar `<run-id>` contra
   `<base_ref>`? Se modificarán: `<archivos autorizados>`”. Detente.

El modo `simple` solo omite este gate si la persona usuaria declaró explícitamente
ese modo; sigue exigiendo un plan aprobado y alcance autorizado.

## Ejecución controlada

- Ejecuta los pasos del plan en su orden. Solo usa `Parallel: yes` cuando el
  propio plan declara ownership disjunto y no existen dependencias de orden,
  datos o configuración.
- Antes de cada paso confirma sus precondiciones. Conserva un ledger de archivo,
  símbolo, cambio realizado, comando, resultado y timestamp UTC.
- Mantén la solución mínima. No refactorices, limpies, reformatees ni añadas
  configurabilidad fuera del cambio autorizado.
- Ejecuta las validaciones del plan con sus resultados esperados. Para
  `high-risk`, ejecuta además las comprobaciones de auth/autorización,
  aislamiento, datos, migración/borrado y fallo seguro que el plan haga
  aplicables.
- Después de cada cambio relevante compara el diff real con el alcance. Un
  archivo inesperado, una deriva, una dependencia faltante, una validación
  fallida o una preocupación de seguridad detiene el run. Preserva el estado
  actual, registra evidencia y usa `VALIDATION_FAILED`, `SECURITY_GATE_FAILED`
  o `BLOCKED` según corresponda. Nunca inventes la corrección ni reviertas por
  tu cuenta.

## Salidas y handoff

`IMPLEMENTATION.md` incluye como mínimo: preflight/baseline, decisiones y gate
humano, alcance y ownership, pasos ejecutados, archivos/símbolos tocados,
comandos/resultados, validaciones, checkpoints de diff, riesgos, fallos y acción
siguiente.

Solo con todos los pasos y validaciones aprobados, sin cambios inesperados y con
el gate de seguridad aplicable superado, actualiza el run a `VALIDATED` y entrega
a `rpi-next` para `rpi-review` en modo diff. `VALIDATED` no autoriza commit.

En la respuesta conversacional, muestra primero el estado; luego el gate o los
cambios realizados, validaciones, diff resumido, riesgos y siguiente acción. Si
el gate falta o algo falla, muestra evidencia y la pregunta/dirección necesaria
sin continuar.
