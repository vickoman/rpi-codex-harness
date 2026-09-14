# Fase Plan

## Objetivo

Crear o revisar un plan ejecutable y trazable sin modificar fuente.

## Entradas

Lee `RESEARCH.md`, decisiones humanas, `GAPS.md` si existe y las instrucciones
`AGENTS.md` aplicables al proyecto. Confirma que el fingerprint no cambió.

## Contenido del plan

- objetivo, requisitos y criterios de aceptación observables;
- decisiones con evidencia y fuera de alcance;
- pasos atómicos con archivos y símbolos poseídos;
- precondiciones y dependencias entre pasos;
- cambio autorizado, validación realizable y resultado esperado;
- comportamiento ante fallo y rollback manual cuando aplique;
- riesgos, seguridad y ownership; `Parallel: yes` solo con writers disjuntos.

Evita refactors, limpieza y configurabilidad especulativa. Si una decisión
material sigue abierta, registra una brecha y no presentes un plan listo.

## Create y revise

En `plan_pending`, crea `PLAN.md`. En `plan_revision_pending`, archiva el plan
anterior y corrige únicamente los hallazgos de `PLAN_REVIEW.md` que permanezcan
dentro del alcance. Una revisión no puede eludir una brecha.

- Plan completo: aplica `plan-ready` y continúa a Review plan.
- Brecha: aplica `gap-opened` y pausa.
- Deriva o evidencia insuficiente: aplica `block`.
