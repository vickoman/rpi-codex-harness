---
name: rpi
description: Ejecuta cambios de código mediante investigación, plan, implementación controlada y revisión del diff.
---

Corrige el cambio solicitado de principio a fin con evidencia y alcance mínimo.
Investiga el código antes de diseñar, crea un plan ejecutable y revisa el plan.
En modo simple puedes implementar sin un segundo gate, pero debes validar el
comportamiento y revisar únicamente el delta desde el baseline. No hagas commits,
push, PR, despliegues ni rollback. Detente después de mostrar el diff validado y
solicitar su aceptación humana. Usa los scripts disponibles para crear el run,
aplicar transiciones y calcular el delta; no edites el manifest manualmente.
