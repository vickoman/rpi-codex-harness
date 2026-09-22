# RPI Codex Harness

Plugin local para ejecutar cambios de código mediante investigación, plan,
revisión, implementación controlada y aceptación humana del diff.

## Estado

La versión v0.3 consolida el workflow en un skill autocontenido, añade una
máquina de estados determinista, snapshots para worktrees sucios, artifacts
atómicos, una suite de regresión y revisiones Jev opt-in por fase. Los runs v0.1
con `manifest.yaml` permanecen read-only.

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

## Uso cotidiano de RPI

RPI funciona sin Jev por defecto. Invócalo explícitamente desde el repositorio
en el que quieres realizar el cambio:

```text
Usa $rpi para implementar este cambio.
```

También puede activarse implícitamente ante una solicitud de cambio controlado.
El flujo avanza por investigación, plan y revisión sin modificar código. Para
riesgo `standard` o `high-risk`, se detiene antes de la primera escritura y
presenta el baseline y los archivos que necesitan aprobación.

Después de implementar, RPI ejecuta las validaciones previstas y presenta sólo
el delta atribuible al run. La revisión técnica y la aceptación humana del diff
son gates distintos. RPI no hace commit, push, PR, deploy ni rollback sin una
solicitud explícita adicional.

Comandos conversacionales habituales:

```text
Usa $rpi para implementar <cambio>.
Muéstrame el estado del run RPI activo.
Continúa el run RPI hasta el siguiente gate humano.
Acepto el diff del run RPI.
```

Para activar revisiones consultivas de Jev durante un run nuevo:

```text
Usa $rpi --jev para implementar <cambio>.
```

Sin `--jev`, RPI conserva el flujo tradicional, no importa el SDK de TypeSafe,
no exige credenciales y no envía contenido fuera del entorno local.

Los artifacts de cada ejecución viven en:

```text
<proyecto>/.codex/rpi/runs/<run-id>/
```

## Desarrollo y validación sin Jev

La suite determinista es el modo predeterminado y no necesita TypeSafe, una API
key ni dependencias adicionales:

```bash
python3 evals/run_evals.py
python3 ~/.codex/skills/.system/skill-creator/scripts/quick_validate.py skills/rpi
python3 ~/.codex/skills/.system/plugin-creator/scripts/validate_plugin.py .
```

`run_evals.py` valida el catálogo y ejecuta las pruebas de máquina de estados,
baseline, scope, gates, artifacts, redacción y helpers de evaluación. Su código
de salida es la autoridad para esta suite.

La comparación live de Codex también funciona sin Jev. Es opt-in porque ejecuta
Codex contra repositorios desechables y consume uso del modelo:

```bash
python3 evals/run_live_ab.py \
  --model <modelo-codex> \
  --reasoning-effort high \
  --repetitions 3
```

Cada repetición ejecuta las variantes en español e inglés sobre el mismo fixture.
El resultado se guarda bajo `evals/results/<timestamp>/summary.json` e incluye:

- pass rate determinista por variante;
- duración e intervalos aproximados;
- tokens reportados por Codex;
- estado final, tests, commits y archivos modificados por cada run.

## RPI con revisiones Jev por fase

Jev puede participar de forma aditiva en un run nuevo. Configura la credencial
en el proceso que ejecuta Codex y usa el flag conversacional:

```bash
export TYPESAFE_API_KEY="..."
```

```text
Usa $rpi --jev para implementar <cambio>.
```

El flag queda registrado en `manifest.json`. RPI ejecuta una llamada agrupada
en cada punto relevante:

| Momento | Artifact | Juicios principales |
| --- | --- | --- |
| Después de Research | `JEV_RESEARCH_REVIEW.json` | respaldo de evidencia, cobertura y brechas materiales |
| Después de Plan | `JEV_PLAN_REVIEW.json` | cobertura, trazabilidad, validación observable y scope |
| Después de validar y revisar el diff | `JEV_IMPLEMENT_REVIEW.json` | completitud, calidad de validación y alineación del diff |

Los resultados son consultivos y fail-open. Jev no aplica eventos, modifica el
riesgo, concede approvals ni sustituye gates humanos. Si falta la key o el SDK,
o la llamada falla, el artifact registra `not_configured`, `sdk_unavailable` o
`error` y RPI continúa por sus reglas normales.

La forma equivalente a bajo nivel para iniciar y revisar una fase es:

```bash
python3 skills/rpi/scripts/rpi_state.py start \
  --project-root /repo \
  --task "<cambio>" \
  --jev

python3 skills/rpi/scripts/rpi_jev.py \
  --run-dir /repo/.codex/rpi/runs/<run-id> \
  --phase research
```

`--jev-model` y `--jev-timeout` permiten cambiar los defaults `jev-latest` y
30 segundos al iniciar el run. La API key nunca se guarda en el manifest ni en
los artifacts.

## Evaluación semántica opcional del benchmark con Jev

El benchmark live conserva su grader independiente para comparar variantes
completas. Al igual que las revisiones de fase, no controla la máquina de
estados, riesgo, approvals ni gates humanos.

La integración es opcional y lazy. Sin `--typesafe-semantic-grade`, el runner no
importa el SDK, no requiere `TYPESAFE_API_KEY`, no envía contenido a TypeSafe y
no añade `semantic_grade` a los records.

### Configuración

Instala el SDK de Python de TypeSafe en el entorno desde el que ejecutarás el
runner siguiendo la documentación oficial del SDK. Después configura la
credencial únicamente como variable de entorno:

```bash
export TYPESAFE_API_KEY="..."
```

Ejecuta la comparación live activando el grader explícitamente:

```bash
python3 evals/run_live_ab.py \
  --model <modelo-codex> \
  --reasoning-effort high \
  --repetitions 3 \
  --typesafe-semantic-grade \
  --typesafe-model jev-latest \
  --typesafe-timeout 30
```

`--typesafe-model` y `--typesafe-timeout` son opcionales; sus defaults son
`jev-latest` y 30 segundos.

### Qué evalúa Jev

El grader envía cuatro preguntas tipadas e independientes sobre el mismo estado:

| Campo | Primitiva | Pregunta |
| --- | --- | --- |
| `research_supported` | `Noul` | ¿Las afirmaciones materiales de Research tienen evidencia? |
| `plan_covers_request` | `Noul` | ¿El plan cubre la solicitud con validación observable? |
| `validation_is_meaningful` | `Noul` | ¿La validación demuestra comportamiento y no sólo exit code? |
| `diff_alignment` | `Choice` | ¿El diff está alineado, incompleto, fuera de scope o no relacionado? |

El estado enviado contiene la solicitud del fixture, los artifacts RPI
disponibles y el diff de producto contra `HEAD`. Cada campo de texto se trunca a
12.000 caracteres antes de la llamada.

### Cómo interpretar los resultados

Cada ejecución con Jev añade un objeto `semantic_grade` al record:

```json
{
  "status": "success",
  "authoritative": false,
  "rubric_version": "rpi-semantic-v1",
  "model": "jev-latest",
  "answers": {
    "research_supported": {"noul": 0.91},
    "diff_alignment": {
      "choice": "aligned",
      "confidence": 0.87,
      "probabilities": {"aligned": 0.87}
    }
  },
  "usage": {"input_tokens": 123, "output_tokens": 0}
}
```

`summary.json` agrega conteos por status y medias con intervalos aproximados para
las señales numéricas. En esta fase no hay thresholds de aprobación calibrados:
los valores sirven para comparar variantes y descubrir casos que merecen
inspección.

Estados posibles:

| Status | Significado |
| --- | --- |
| `success` | TypeSafe devolvió respuestas tipadas. |
| `not_configured` | Falta `TYPESAFE_API_KEY`. |
| `sdk_unavailable` | El SDK de TypeSafe no está disponible en el entorno. |
| `error` | La llamada o el procesamiento externo falló; `error_type` identifica la clase. |

Los tres estados de fallo son informativos: no cambian `grade.passed`, el pass
rate determinista ni el código de salida del runner.

### Privacidad y límites

Con `--typesafe-semantic-grade`, parte del contenido del repositorio desechable
sale del entorno local. Usa el flag sólo con fixtures o código que estés
autorizado a enviar a TypeSafe. La API key no se escribe en los resultados y los
mensajes de excepción externos tampoco se persisten.

Jev aporta telemetría, no autoridad. Ninguna señal semántica aplica eventos,
aprueba planes o diffs, modifica riesgo, interpreta consentimiento ni sustituye
los gates humanos o deterministas.

### Troubleshooting

- `not_configured`: exporta `TYPESAFE_API_KEY` en el proceso que lanza el runner.
- `sdk_unavailable`: instala el SDK en ese mismo entorno de Python.
- `error` con `TimeoutError`: aumenta `--typesafe-timeout` o prueba nuevamente;
  el resultado determinista sigue siendo válido.
- Sin `semantic_grade`: confirma que incluiste `--typesafe-semantic-grade`.
- Para validar RPI sin red ni credenciales, vuelve a `python3 evals/run_evals.py`.

## Bootstrap local de artifacts

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
