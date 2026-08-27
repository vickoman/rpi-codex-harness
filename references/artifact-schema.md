# Esquema de artefactos RPI

## Ubicación y aislamiento

Los artefactos viven en el proyecto objetivo, no dentro de este harness:

```text
<target-root>/.codex/rpi/
  runs/
    <run-id>/
      manifest.yaml
      RESEARCH.md
      PLAN.md
      REVIEW.md
      IMPLEMENTATION.md
      GAPS.md                 # solo si existen brechas
      history/
      logs/
  LATEST
```

La configuración del proyecto debe ignorar `.codex/rpi/` en Git. Esta carpeta de
referencias es el diseño del harness; los runs son evidencia local del proyecto
en el que se trabaja.

## Run ID

```text
<TICKET|NO-TICKET>--<YYYYMMDDTHHMMSSZ>--<slug>--<suffix>
```

Ejemplos:

```text
VFE-566--20260827T153045Z--auth-rate-limit--a1b2
NO-TICKET--20260827T153045Z--auth-rate-limit--a1b2
```

- El ticket es opcional y únicamente se usa cuando lo proporciona la persona
  usuaria o resulta inequívoco de una entrada autorizada; nunca se infiere de la
  rama.
- Un ticket asociado después actualiza `manifest.yaml`, pero nunca renombra el
  directorio inmutable.
- La hora del ID y todos los timestamps del manifiesto usan UTC en ISO 8601.

## `manifest.yaml` mínimo

```yaml
rpi_version: 0.1
run_id: VFE-566--20260827T153045Z--auth-rate-limit--a1b2
project_root: /absolute/path/to/project
created_at: 2026-08-27T15:30:45Z
updated_at: 2026-08-27T15:30:45Z
closed_at: null
ticket: VFE-566 # o null
ticket_source: user # user | none
risk_mode: standard # simple | standard | high-risk
base_ref: <git-sha-or-unavailable>
working_tree: clean # clean | dirty
current_phase: research
status: in_progress
next_action: research
material_gaps_open: 0
review_revision_count: 0
human_gates:
  implementation_approved: false
  diff_review_approved: false
  commit_approved: false
```

`updated_at` se actualiza en cada transición o escritura de artefacto. `closed_at`
solo se completa al cerrar un run. El manifiesto conserva estados y gates, no
contenido duplicado de los informes.

## Artefactos por fase

| Archivo | Productor | Contenido mínimo |
| --- | --- | --- |
| `RESEARCH.md` | research | baseline, objetivo, ledger de evidencia, flujo, archivos/pruebas relevantes, riesgos, brechas y handoff. |
| `PLAN.md` | plan | requisitos mapeados, pasos, archivos/símbolos, precondiciones, cambio autorizado, validación, fallo, rollback y ownership. |
| `REVIEW.md` | review | modo, evidencia, resultados de los cuatro pilares o del diff, hallazgos y decisión. |
| `IMPLEMENTATION.md` | implement | preflight, aprobación humana, pasos realizados, comandos/resultados, checkpoints, validación final y salida. |
| `GAPS.md` | cualquier fase | ID, pregunta, importancia, evidencia, opciones, respuesta, estado y fase afectada. |

Las revisiones y planes reemplazados se conservan bajo `history/` con timestamp
UTC. `logs/` contiene las salidas de comandos que constituyen evidencia, sin
secretos.

## Resultados terminales y retención

Resultados de fase permitidos incluyen `AWAITING_GAP_CLOSURE`,
`AWAITING_IMPLEMENTATION_APPROVAL`, `BLOCKED`,
`SUPERSEDED`, `VALIDATION_FAILED`, `SECURITY_GATE_FAILED`, `STOPPED`, `VALIDATED`,
`DIFF_APPROVED`, `DIFF_REJECTED` y `CLOSED_UNCOMMITTED`.

No se borra nada automáticamente. Una futura limpieza debe:

1. Ejecutarse primero en modo dry-run.
2. Considerar solo runs cerrados y antiguos según `closed_at`.
3. Excluir por defecto runs `high-risk`, fallidos, bloqueados o con brechas.
4. Solicitar aprobación explícita antes de eliminar archivos.
