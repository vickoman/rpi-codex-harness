# Máquina de estados RPI v0.2

`manifest.json.state` es la única autoridad. La fase y la siguiente acción se
derivan del estado; no se almacenan como campos independientes.

## Estados y eventos principales

| Estado | Evento permitido | Siguiente estado |
| --- | --- | --- |
| `research_pending` | `research-complete` | `plan_pending` |
| `plan_pending` | `plan-ready` | `plan_review_pending` |
| `plan_revision_pending` | `plan-ready` | `plan_review_pending` |
| `plan_review_pending` | `plan-approved` | `implementation_preflight` |
| `plan_review_pending` | `plan-rejected` | `plan_revision_pending` |
| `implementation_preflight` | `preflight-complete --scope ...` | `implementation_approval_pending` o `implementing` para `simple` |
| `implementation_approval_pending` | `implementation-approved` | `implementing` |
| `implementing` | `validation-passed` | `diff_review_pending`, o `security_review_pending` para `high-risk` |
| `implementing` | `validation-failed` | `validation_failed` |
| `security_review_pending` | `security-passed` | `diff_review_pending` |
| `security_review_pending` | `security-failed` | `security_gate_failed` |
| `diff_review_pending` | `diff-approved` | `diff_acceptance_pending` |
| `diff_review_pending` | `diff-rejected` | `diff_rejected` |
| `diff_rejected` | `rework-approved` | `implementing` |
| `diff_acceptance_pending` | `diff-accepted` | `ready_to_close` |
| `ready_to_close` | `close-uncommitted` | `closed_uncommitted` |

`gap-opened`, `block` y `stop` guardan el estado previo en `resume_state` y
pasan a `waiting_for_gap`, `blocked` o `stopped`. `gap-answered` reanuda solo
cuando `material_gaps_open` llega a cero. `resume` requiere dirección humana.
`security-failed` pasa a `security_gate_failed`.

`rework-approved` requiere dirección humana y solo vuelve a implementación para
corregir dentro del alcance aprobado. Si la corrección cambia alcance o una
decisión material, abre una brecha o inicia un run nuevo.

El máximo es dos eventos `plan-rejected`. El script rechaza el tercero.

## Comandos

```bash
python3 scripts/rpi_state.py start --project-root /repo --task "objetivo"
python3 scripts/rpi_state.py status --run-dir /repo/.codex/rpi/runs/<run-id>
python3 scripts/rpi_state.py event --run-dir <run> --event research-complete
python3 scripts/rpi_state.py event --run-dir <run> --event gap-opened
python3 scripts/rpi_state.py event --run-dir <run> --event gap-answered
python3 scripts/rpi_state.py event --run-dir <run> \
  --event implementation-approved --actor user --scope src/a.py tests/test_a.py
python3 scripts/rpi_state.py event --run-dir <run> \
  --event diff-accepted --actor user
```

No pases `--actor user` a menos que la persona usuaria haya expresado esa
decisión en la conversación actual. El script valida estructura y binding, pero
el agente conserva la responsabilidad de no inventar consentimiento.

## Transición conversacional

Tras cada comando informa:

```text
run_id, state, baseline, artifact actualizado, gate/bloqueo y siguiente acción
```

No copies la tabla al artifact del run; referencia la versión del harness.
