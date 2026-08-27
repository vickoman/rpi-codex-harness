---
name: rpi-plan
description: "Turn complete RPI research into an authorized, traceable implementation plan, or surface the material decisions that prevent one. Use after rpi-research, not to modify source code."
---

# RPI Plan

Convierte investigación factual en un plan autorizado y ejecutable. No muta el
proyecto ni completa silenciosamente decisiones de producto, seguridad o alcance.

## Referencias y entradas obligatorias

Antes de planificar, lee:

1. [principios RPI](../references/rpi-principles.md): P1, P2, P3 y P4.
2. [contrato operativo](../references/rpi-contract.md).
3. [esquema de artefactos](../references/artifact-schema.md).
4. `manifest.yaml`, `RESEARCH.md`, `GAPS.md` si existe, decisiones explícitas de
   la persona usuaria y `AGENTS.md` del proyecto objetivo.

Si falta investigación válida o el run no está en una transición de planificación
legal, devuelve el control a `rpi-next`; no reconstruyas investigación ni inicies
un run implícito.

## Permisos y límites

Puedes inspeccionar el proyecto y escribir únicamente dentro del run:
`manifest.yaml`, `PLAN.md`, `GAPS.md`, `history/` y `logs/`. Nunca escribas
fuente, configuración del proyecto, `.gitignore`, Graphify ni sistemas externos.

El plan autoriza un cambio futuro; no es autorización para implementarlo. Cada
línea propuesta debe ser necesaria para el objetivo y trazable a una evidencia o
decisión registrada.

## Modos

- `create`: parte de `RESEARCH_COMPLETE` y crea un primer `PLAN.md`.
- `revise`: modo interno tras un `REJECTED` de revisión de plan. Conserva la versión
  anterior bajo `history/`, aborda solo los hallazgos en alcance y exige una nueva
  revisión. No usar para eludir una brecha o reabrir el alcance.

## Cierre de decisiones

Antes de escribir un plan listo para revisión, comprueba cada dimensión. Debe
estar sustentada por una decisión explícita de la persona usuaria o por evidencia
del repositorio:

- alcance y comportamiento público;
- datos, migraciones y compatibilidad;
- autorización, privacidad y seguridad;
- dependencias;
- validación y criterios de aceptación;
- rollback, despliegue, flags y observabilidad cuando correspondan;
- ownership de archivos y paralelismo.

Investiga los hechos que falten antes de preguntar. Si persiste una decisión
material, registra en `GAPS.md` el ID, pregunta mínima, importancia, evidencia y
opciones. Actualiza el run a `AWAITING_GAP_CLOSURE` y detente. No escribas un plan
que parezca `READY_FOR_REVIEW` mientras tenga una brecha material abierta.

## Construcción del plan

1. Vuelve a comprobar `base_ref`, estado del worktree y precondiciones citadas por
   la investigación. La deriva material invalida el handoff; no planees contra
   hechos obsoletos.
2. Mapea cada requisito autorizado a uno o más pasos y declara qué queda fuera de
   alcance. Mantén la solución mínima compatible con el código existente.
3. Para cada paso incluye: resultado observable, archivos/símbolos poseídos,
   precondiciones con evidencia, cambio autorizado, dependencias/`Parallel: yes`
   solo si hay propiedad disjunta, validación con comando y resultado esperado,
   comportamiento ante fallo y rollback manual cuando corresponda.
4. Declara los criterios de aceptación observables, riesgos y cobertura de
   seguridad. Para `high-risk`, cubre de forma explícita auth/autorización,
   aislamiento de tenants si aplica, datos sensibles, migraciones/borrados y la
   verificación final del diff.
5. Comprueba que no haya refactors, limpieza o configurabilidad especulativa, que
   ningún archivo tenga dos writers y que las validaciones sean factibles. Si una
   validación no se puede ejecutar, explica la causa y el siguiente mejor chequeo.

## Salidas

`PLAN.md` contiene como mínimo: baseline, objetivo, requisitos y trazabilidad,
decisiones/evidencia, alcance y fuera de alcance, pasos ejecutables, criterios de
aceptación, validaciones, riesgos/seguridad, rollback y ownership.

Con decisiones cerradas y precondiciones verificadas, actualiza el manifiesto a
`READY_FOR_REVIEW` y entrega a `rpi-next` para `rpi-review` en modo plan. Con una
brecha material usa `AWAITING_GAP_CLOSURE`; con deriva o evidencia insuficiente,
`BLOCKED`. Ninguna de esas salidas habilita implementación.

## Respuesta conversacional

Resume run ID, baseline, modo, requisitos cubiertos, brechas o decisiones
cerradas, archivos poseídos, validaciones, riesgos y la salida legal siguiente.
No implementes ni presentes el plan como aprobado hasta que `rpi-review` lo
apruebe.
