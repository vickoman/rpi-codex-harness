---
name: rpi
description: "Run an evidence-driven Research → Plan → Implement workflow for controlled code changes. Usa RPI para investigar, planificar, implementar, reanudar o revisar cambios de código con trazabilidad y gates humanos."
---

# RPI

Convierte una solicitud de cambio de código en investigación verificable, un plan
revisable, implementación acotada y aceptación conversacional del diff.

Las instrucciones explícitas de la persona usuaria prevalecen sobre preferencias
del workflow. Los límites de seguridad, alcance aprobado y acciones externas no
se amplían por inferencia.

## Antes de actuar

Lee siempre [el contrato](references/contract.md) y
[la máquina de estados](references/state-machine.md). Lee además una sola guía de
fase según el estado actual:

- `research_pending`: [research](references/research.md)
- `plan_pending` o `plan_revision_pending`: [plan](references/plan.md)
- `plan_review_pending`, `diff_review_pending` o `diff_acceptance_pending`:
  [review](references/review.md)
- `implementation_preflight`, `implementation_approval_pending` o
  `implementing`: [implement](references/implement.md)

Para crear, validar o cambiar un run usa
`python3 <skill-root>/scripts/rpi_state.py`; para obtener el diff desde el inicio
real del run usa `python3 <skill-root>/scripts/rpi_diff.py`. No edites
`manifest.json` manualmente.

Escribe artifacts con `rpi_artifact.py` para archivado atómico y captura salidas
de comandos con `rpi_log.py` para redactar secretos.

## Modos conversacionales

- **start/run:** crea un run y avanza por las fases de solo lectura hasta una
  brecha, un bloqueo o `implementation_approval_pending`.
- **status:** usa `rpi_state.py status`; no escribe.
- **answer gap:** registra la respuesta en `GAPS.md`, aplica `gap-answered` y
  reanuda desde `resume_state` cuando no queden brechas.
- **approve implementation:** solo ante una aprobación explícita de la persona
  usuaria ligada al run y archivos mostrados; aplica `implementation-approved`.
- **accept diff:** solo ante aceptación explícita del diff mostrado; aplica
  `diff-accepted`.
- **close:** aplica `close-uncommitted` únicamente por solicitud explícita.

Si la solicitud es inequívoca, no pidas elegir un modo. Avanza por trabajo ya
autorizado y pausa únicamente cuando falte una decisión material, un gate real o
evidencia necesaria.

## Invariantes

- `standard` y `high-risk` requieren aprobación humana después del preflight y
  antes de la primera escritura de fuente.
- Ningún modo hace commit, push, PR, deploy, rollback o escritura externa sin una
  solicitud explícita adicional.
- Conserva cambios preexistentes. Usa el diff de RPI, no `git diff HEAD`, para
  atribuir cambios al run.
- Solo la implementación modifica fuente, y solo dentro del alcance aprobado.
- Una decisión material no demostrable abre una brecha; no inventes su respuesta.
- Presenta el resultado principal, evidencia, bloqueo o gate y siguiente acción.

El formato de artifacts y compatibilidad v0.1 están en
[artifact schema](references/artifact-schema.md). Para mantener o evaluar este
skill lee [evals](references/evals.md).
