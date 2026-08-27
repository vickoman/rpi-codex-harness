# Contrato operativo RPI

## Propósito y alcance

RPI controla cambios de código mediante el flujo:

```text
Research → Plan → Review plan → Implement → Review diff → commit opcional
```

Separa hechos, decisiones, crítica y mutación. Este contrato rige a `rpi-next` y
a todas las fases. No reemplaza las instrucciones `AGENTS.md` del repositorio
objetivo.

## Evidencia y brechas

- Cada hecho debe tener evidencia del repositorio (`archivo:línea`, comando y
  resultado) o una fuente externa autoritativa.
- Una decisión de producto, alcance, seguridad, comportamiento o convención que
  no pueda demostrarse se convierte en una brecha material.
- Antes de consultar, investigar los hechos disponibles; si la brecha persiste,
  formular una pregunta concreta, explicar por qué importa y ofrecer opciones
  sustentadas cuando existan.
- Registrar las brechas materiales en `GAPS.md`. La fase afectada queda en
  `AWAITING_GAP_CLOSURE`; nunca se infiere una respuesta.

## Investigación Graphify-first

- Resolver el repositorio objetivo con `git rev-parse --show-toplevel`; si no es
  posible, usar el directorio de trabajo actual.
- Consultar primero `<target-root>/graphify-out/graph.json`.
- Es utilizable solo si acredita el `base_ref` actual y cubre el alcance. Debe
  exponer `source_ref`, `generated_at`, `workspace_root` y `files_indexed`.
- Cuando sea utilizable, Graphify navega; el código fuente confirma hallazgos
  materiales, de baja confianza o fuera de cobertura.
- Si falta, está desactualizado o es parcial, hacer inspección dirigida del
  código. RPI no regenera Graphify automáticamente.

## Riesgo y controles humanos

| Modo | Selección | Controles |
| --- | --- | --- |
| `simple` | Solo si la persona usuaria lo declara. | Investigación y plan compactos; el alcance aprobado sigue siendo obligatorio. |
| `standard` | Predeterminado. | Flujo completo, revisión de plan, aprobación antes de escribir y revisión conversacional del diff. |
| `high-risk` | Se eleva por evidencia: auth, datos multi-tenant, pagos, migraciones, borrado o datos sensibles. | Controles `standard` más cobertura explícita de seguridad y rollback, y gate final de seguridad. |

El riesgo puede elevarse por evidencia, nunca rebajarse por inferencia.

Para `standard` y `high-risk`, tras un preflight correcto y justo antes de la
primera escritura de código, la persona usuaria debe aprobar explícitamente la
implementación.

## Límites de acción

- Ninguna fase hace commits, despliegues, PRs, rollbacks, ni escrituras externas
  automáticamente.
- Tras `DIFF_APPROVED`, un commit solo se prepara si la persona usuaria lo pide y
  aprueba su mensaje. Un run puede cerrarse sin commit.
- Una validación fallida, cambio inesperado, dependencia faltante, problema de
  seguridad, deriva material o acción fuera del plan detiene la ejecución. Se
  informa evidencia y se espera dirección; no hay arreglos ni rollback automáticos.
- Los cambios existentes de la persona usuaria se preservan.

## Propiedad y concurrencia

- El plan autoriza cambios; el árbol actual del proyecto es la autoridad de los
  hechos. Una deriva material invalida el handoff.
- Un único writer posee cada archivo. La escritura paralela exige `Parallel: yes`,
  propiedad de archivos disjunta y ausencia de dependencias de orden, datos o
  configuración.

## Fases y transiciones

| Fase | Responsabilidad | Salida que permite avanzar |
| --- | --- | --- |
| `research` | Snapshot factual sin diseñar ni modificar fuente. | `RESEARCH_COMPLETE` sin brechas materiales. |
| `plan` | Plan autorizado; `revise` es interno tras rechazo del review. | `READY_FOR_REVIEW`. |
| `review plan` | Revisión read-only: enfoque/orden, factibilidad/seguridad, validación y claridad. | `APPROVED` o `APPROVED_WITH_WARNINGS`. |
| `implement` | Única fase que muta fuente, tras gate humano. | `VALIDATED`. |
| `review diff` | Revisión read-only del diff real versus plan y validaciones, presentada en conversación. | `DIFF_APPROVED`. |

Un `REJECTED` del review de plan entra en `plan revise` únicamente si la corrección
sigue en alcance; luego hay revisión nueva. El máximo es dos ciclos automáticos
review/revise. Si depende de una decisión, abre una brecha. Un `DIFF_REJECTED` no
inicia un arreglo de código automático.

`rpi-next` valida una única transición legal y carga solo el contrato de la fase
siguiente. Si hay varios runs activos y falta `run_id`, pregunta; no elige uno.
