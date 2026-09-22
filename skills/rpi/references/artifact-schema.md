# Artifacts RPI v0.2

## Ubicación

```text
<project>/.codex/rpi/
  LATEST
  runs/<run-id>/
    manifest.json
    baseline.json
    baseline/snapshots/
    RESEARCH.md
    PLAN.md
    PLAN_REVIEW.md
    IMPLEMENTATION.md
    DIFF_REVIEW.md
    JEV_RESEARCH_REVIEW.json
    JEV_PLAN_REVIEW.json
    JEV_IMPLEMENT_REVIEW.json
    GAPS.md
    history/
    logs/
```

Los comandos Git del harness excluyen `.codex/rpi/**`. `start` advierte cuando
esa ruta no está ignorada. Un bootstrap separado puede añadirla a
`.git/info/exclude` solo con autorización explícita.

```bash
python3 scripts/rpi_bootstrap.py --project-root /repo          # dry-run
python3 scripts/rpi_bootstrap.py --project-root /repo --apply  # autorizado
```

## Manifest

`manifest.json` incluye:

- `schema_version`, `harness_version`, `run_id` y timestamps UTC;
- proyecto, ticket, solicitud original y `risk_mode`;
- alcance autorizado y su digest, fijados por el preflight;
- `state`, `resume_state`, contador de brechas y revisiones;
- runtime: Codex, modelo, reasoning effort, ref Git y digest del contenido
  efectivo del harness;
- baseline: `HEAD`, fingerprint, completitud y archivos preexistentes;
- approvals de implementación y diff con actor, timestamp y bindings de
  workspace/alcance/diff. La autorización de commit queda fuera del harness.
- digest de la revisión técnica para impedir aceptar un diff posterior distinto.
- configuración Jev opt-in (`enabled`, modelo y timeout) y resumen de sus
  revisiones no autoritativas; nunca contiene la API key.

El script escribe el manifest de forma atómica bajo lock. No lo edites a mano.

## Contenido mínimo

- `RESEARCH.md`: objetivo factual, baseline, evidencia, flujo, archivos/pruebas,
  riesgos, cambios preexistentes y brechas.
- `PLAN.md`: requisitos, fuera de alcance, pasos, archivos/símbolos, ownership,
  precondiciones, validación, fallo y rollback manual aplicable.
- `PLAN_REVIEW.md`: evidencia, trazabilidad, enfoque, factibilidad/seguridad,
  validación, claridad, hallazgos y decisión.
- `IMPLEMENTATION.md`: preflight, gate, pasos, comandos/resultados, checkpoints,
  validación y fallos.
- `DIFF_REVIEW.md`: delta desde baseline, mapeo por archivo/hunk, validaciones,
  riesgos, hallazgos y decisión técnica.
- `GAPS.md`: pregunta y respuesta trazables por ID.
- `JEV_*_REVIEW.json`: status, preguntas tipadas, probabilidades, uso y metadata
  no autoritativa de la revisión opcional de fase.

Antes de reemplazar un artifact, archívalo con timestamp UTC bajo `history/`.
No guardes secretos en artifacts o logs; usa `rpi_log.py` para salidas de comandos.

## Compatibilidad v0.1

Los runs con `manifest.yaml` son legacy y permanecen read-only. La v0.2 no los
reescribe automáticamente. `rpi_state.py status` reconoce su metadata básica y
explica que requieren cierre con v0.1 o una migración explícita futura.
