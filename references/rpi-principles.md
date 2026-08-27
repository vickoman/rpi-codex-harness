# Principios RPI canónicos

Estos principios son la única fuente de verdad para el comportamiento RPI. Cada
skill carga únicamente los principios que necesita para su fase.

## P1 — Pensar antes de codificar

No asumir. Exponer ambigüedad. Presentar trade-offs.

- Investigar los hechos del repositorio antes de preguntar.
- No completar silenciosamente una brecha material.
- Presentar alternativas y evidencia cuando una decisión cambie producto,
  alcance, seguridad, comportamiento o una convención incompatible.
- Detener el avance afectado hasta que la persona usuaria cierre una brecha
  material.

Aplica principalmente a investigación, planificación y revisión.

## P2 — Simplicidad primero

La solución mínima que satisface el objetivo; nada especulativo.

- No introducir funcionalidad, abstracción o configuración no justificada por la
  investigación y el plan.
- Preferir la alternativa más pequeña compatible con el código existente.
- Las revisiones deben señalar sobreingeniería, flexibilidad especulativa y
  abstracciones prematuras.

Aplica principalmente a planificación y revisión.

## P3 — Cambios quirúrgicos

Cambiar solo lo necesario y preservar el trabajo ajeno.

- Cada paso del plan debe tener un propósito atómico y archivos/símbolos
  explícitos.
- No refactorizar, reformatear o «mejorar» código adyacente sin autorización.
- Respetar el estilo y las convenciones existentes.
- Eliminar únicamente los símbolos o imports que el propio cambio deje huérfanos.
- Cada línea modificada debe poder trazarse a un requisito autorizado.

Aplica principalmente a planificación, implementación y revisión.

## P4 — Ejecución guiada por el objetivo

Definir éxito observable y verificarlo antes de avanzar.

- Cada paso define validación concreta, resultado esperado y comportamiento ante
  fallo; cuando corresponda, también rollback manual.
- «Las pruebas pasan» no basta: el criterio de éxito debe reflejar el
  comportamiento solicitado.
- Un paso no termina hasta que su validación haya concluido satisfactoriamente.
- La investigación solo termina cuando permite planificar sin brechas materiales
  abiertas.

Aplica principalmente a investigación, planificación e implementación.
