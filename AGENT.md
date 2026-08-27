# RPI Codex Harness

## Propósito

Construir y mejorar de forma controlada un harness RPI para Codex. Su objetivo es
convertir una solicitud en evidencia, un plan revisable, una implementación
validada y una revisión conversacional del diff, sin asumir decisiones materiales
ni hacer commits automáticos.

## Estado inicial

- Fecha: 2026-08-27
- Estado: diseño v0.1, referencias compartidas, `rpi-next`, `rpi-research`,
  `rpi-plan`, `rpi-review` y `rpi-implement` definidos. `rpi-research`,
  `rpi-plan`, `rpi-review` y `rpi-implement` pasaron sus primeros evals
  aislados. Los skills siguen sin instalación global.
- Especificación inicial: `../rpi-claude-skills/RPI_CODEX_SPEC.md`.
- Principios canónicos: P1 Pensar antes de codificar, P2 Simplicidad primero,
  P3 Cambios quirúrgicos y P4 Ejecución guiada por el objetivo.

## Contrato vigente

- Flujo: investigación → plan → revisión del plan → implementación → revisión
  conversacional del diff → commit opcional solicitado explícitamente.
- Graphify es la primera fuente de navegación cuando `graphify-out/graph.json`
  existe, corresponde al ref actual y cubre el alcance; el código verifica los
  hallazgos materiales.
- Los artefactos viven en el proyecto objetivo:
  `.codex/rpi/runs/<run-id>/`, con ticket opcional o prefijo `NO-TICKET`.
- Las brechas materiales se investigan primero y, si siguen abiertas, se cierran
  con la persona usuaria; se registran en `GAPS.md`.
- Un plan rechazado puede entrar en `revise` hasta dos veces y volver a revisión.
  Nunca se corrige código automáticamente tras una revisión de diff o un fallo de
  validación.
- Riesgo `standard` por defecto; `simple` solo si se declara; `high-risk` para
  ámbitos sensibles. `standard` y `high-risk` requieren aprobación humana justo
  antes de la primera escritura de código.
- No hay commits, despliegues, PRs, rollbacks ni escrituras externas automáticas.

## Ciclo semanal de mejora

Cada semana, revisar ejecuciones reales y registrar aquí una entrada con:

1. Caso evaluado y resultado esperado.
2. Evidencia: run-id, artefactos, validaciones y decisión humana.
3. Señales: objetivo alcanzado, brechas detectadas tarde, errores de suposición,
   bloqueos de revisión, cobertura de validación, tiempo y tokens cuando estén
   disponibles.
4. Hipótesis de mejora y cambio mínimo propuesto.
5. Evaluación comparativa antes/después y decisión: adoptar, ajustar o revertir.

No se modifica un contrato por una anécdota: todo cambio debe tener un caso
representativo y una regresión comprobable.

## Próximo hito autorizado

Revisión humana del harness integrado. No instalar globalmente ni crear commits
hasta que la persona usuaria revise los archivos y solicite explícitamente ese
paso.

## Registro semanal

| Fecha | Cambio o hallazgo | Evidencia | Decisión |
| --- | --- | --- | --- |
| 2026-08-27 | Se creó el espacio paralelo y este registro. | Diseño v0.1 en el repositorio fuente. | Pendiente de primera implementación. |
| 2026-08-27 | Se añadieron principios, contrato y esquema de artefactos. | `references/` en este harness. | Usar como única fuente compartida al crear `rpi-next`. |
| 2026-08-27 | Se creó el skill local `rpi-next`. | `rpi-next/SKILL.md`; `quick_validate.py` aprobado. | No instalar ni invocar hasta completar la evaluación inicial. |
| 2026-08-27 | Se creó el skill local `rpi-research` y el eval 001. | `rpi-research/SKILL.md` validado y `evals/rpi-research-001-stale-graphify.md`. | Ejecutar solo en fixture aislado. |
| 2026-08-27 | Eval RPI Research 001 aprobado. | Fixture temporal: Graphify stale detectado, inspección dirigida, `RESEARCH.md`, riesgo `high-risk`, sin cambios de fuente. | Para runners macOS aislados, habilitar la ruta canónica del run como writable; no instalar globalmente todavía. |
| 2026-08-27 | Se creó el skill local `rpi-plan` y el eval 001. | `rpi-plan/SKILL.md` validado y `evals/rpi-plan-001-material-gap.md`. | Ejecutar en fixture aislado. |
| 2026-08-27 | Eval RPI Plan 001 aprobado. | Fixture temporal: `GAP-001` con evidencia/opciones, `AWAITING_GAP_CLOSURE`, sin `PLAN.md` ni diff de fuente. | Ninguna; continuar con `rpi-review` en modo plan. |
| 2026-08-27 | Se creó `rpi-review` en modo plan y el eval 001 de rechazo high-risk. | `rpi-review/SKILL.md` validado y `evals/rpi-review-plan-001-rejects-unverifiable-high-risk-plan.md`. | Ejecutar únicamente en fixture aislado. |
| 2026-08-27 | Eval RPI Review Plan 001 aprobado. | Fixture final temporal `NO-TICKET--20260827T173000Z--login-rate-limit--r003`: `REJECTED`, `next_action: rpi-plan revise`, sin `GAPS.md`, `make verify-login-contract` pasó, `npm test` falló como esperaba y diff de fuente vacío. | Mantener decisiones de comportamiento y validación explícitas en fixtures: dos variantes previas abrieron gaps correctos por toolchain o semántica de ventana no decididas. |
| 2026-08-27 | Se creó `rpi-implement` y el eval 001 de gate humano. | `rpi-implement/SKILL.md` validado y `evals/rpi-implement-001-requires-human-gate.md`. | Ejecutar únicamente en fixture aislado. |
| 2026-08-27 | Eval RPI Implement 001 aprobado. | Fixture temporal `NO-TICKET--20260827T180000Z--login-rate-limit--i001`: preflight registrado, `AWAITING_IMPLEMENTATION_APPROVAL`, gate `false`, solicitud que liga run/baseline/archivo y diff de fuente vacío. | El pedido genérico de implementar no sustituye el gate; continuar con revisión de diff. |
| 2026-08-27 | Se añadió `mode: diff` a `rpi-review` y su eval de cambio fuera de alcance. | `rpi-review/SKILL.md` y `evals/rpi-review-diff-001-rejects-out-of-scope.md`. | Validar estructura y ejecutar únicamente en fixture aislado. |
| 2026-08-27 | Se completó la integración de `rpi-next` con la tabla de transiciones y la matriz E2E. | `rpi-next/SKILL.md`, `evals/rpi-next-e2e-001-transition-matrix.md`; Codex devolvió los 7 handoffs, mantuvo el gate standard falso, bloqueó `DIFF_REJECTED`, trató `CLOSED_UNCOMMITTED` como terminal y pidió `run_id` ante 8 runs activos. Fixture limpio y código fuente sin cambios. | Integración funcional completa para revisión humana; instalación, commits y empaquetado quedan fuera hasta autorización explícita. |
| 2026-08-27 | Eval RPI Review Diff 001 aprobado. | Fixture temporal `NO-TICKET--20260827T190000Z--login-rate-limit--d001`: `DIFF_REJECTED`, hunk autorizado separado del archivo `src/auth/debug.ts` fuera de alcance, validación repetida, sin rollback/commit y gate de diff falso. | Mantener archivos no rastreados visibles en la revisión; `git diff` por sí solo no basta para detectar deriva. |
