# RPI Codex Harness

Plugin local para ejecutar cambios de código mediante investigación, plan,
revisión, implementación controlada y aceptación humana del diff.

## Estado

La versión v0.2 consolida el workflow en un skill autocontenido, añade una
máquina de estados determinista, snapshots para worktrees sucios, artifacts
atómicos y una suite de regresión. Los runs v0.1 con `manifest.yaml` permanecen
read-only.

El repositorio es la raíz del plugin. La implementación no crea por sí sola una
entrada en el marketplace personal ni modifica aliases globales.

## Estructura

```text
.codex-plugin/plugin.json
skills/rpi/
  SKILL.md
  agents/openai.yaml
  references/
  scripts/
evals/
tests/
```

## Desarrollo y validación

```bash
python3 evals/run_evals.py
python3 ~/.codex/skills/.system/skill-creator/scripts/quick_validate.py skills/rpi
python3 ~/.codex/skills/.system/plugin-creator/scripts/validate_plugin.py .
```

La evaluación live español/inglés es opt-in y consume uso del modelo:

```bash
python3 evals/run_live_ab.py --model <modelo> --repetitions 3
```

El bootstrap de exclusión Git es dry-run por defecto y solo modifica metadata
local con `--apply`:

```bash
python3 skills/rpi/scripts/rpi_bootstrap.py --project-root /repo
python3 skills/rpi/scripts/rpi_bootstrap.py --project-root /repo --apply
```

## Instalación posterior

Para distribución local, añade este plugin a un marketplace personal o de equipo
y usa `codex plugin add`. Esa operación modifica configuración externa y debe
realizarse en un paso autorizado separado. Después de instalar o actualizar,
abre una sesión nueva para que Codex descubra la versión vigente.

## Uso esperado

Invocación explícita:

```text
Usa $rpi para implementar este cambio.
```

También puede activarse implícitamente con solicitudes en español o inglés sobre
un cambio controlado. El skill avanza por las fases read-only y se detiene ante
brechas materiales, el gate de implementación o la aceptación humana del diff.

No hace commit, push, PR, deploy o rollback sin una solicitud explícita adicional.
