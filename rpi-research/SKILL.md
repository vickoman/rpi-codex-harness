---
name: rpi-research
description: "Investigate a requested code change into an evidence-backed RPI snapshot without designing, planning, or modifying source code. Use after rpi-next starts an RPI research phase."
---

# RPI Research

Produce el snapshot factual que permite planificar un cambio sin suposiciones. No
diseña una solución ni modifica código fuente.

## Referencias obligatorias

Antes de investigar, lee:

1. [principios RPI](../references/rpi-principles.md): P1 y P4.
2. [contrato operativo](../references/rpi-contract.md).
3. [esquema de artefactos](../references/artifact-schema.md).

El `manifest.yaml` del run y las instrucciones `AGENTS.md` del proyecto objetivo
también son entradas obligatorias. Si falta un run válido, devuelve el control a
`rpi-next`; no crees uno implícitamente.

## Permisos y límites

Puedes leer el proyecto y escribir únicamente dentro del directorio del run:
`manifest.yaml`, `RESEARCH.md`, `GAPS.md`, `history/` y `logs/`. Nunca escribas
fuente, configuración del proyecto, `.gitignore`, Graphify ni sistemas externos.

No propongas diseño, pasos de implementación, estimaciones, refactors ni una
decisión de producto. Describe hechos, riesgos y brechas con evidencia.

## Método de investigación

1. **Establece el baseline.** Registra proyecto resuelto, ref/commit, estado del
   worktree, solicitud original, ticket conocido y archivos cambiados por la
   persona usuaria. Si el baseline necesario es imposible de obtener, reporta la
   limitación; no inventes uno.
2. **Usa Graphify primero.** Comprueba
   `<target-root>/graphify-out/graph.json` y sus metadatos. Úsalo para navegar solo
   si cubre el alcance y corresponde al `base_ref` actual. Si falta, es parcial o
   está desactualizado, registra por qué y continúa con inspección dirigida. Nunca
   lo regeneres.
3. **Sigue el flujo real.** Con Graphify o búsquedas concretas, localiza el punto
   de entrada, llamadas relevantes, datos, configuración, middleware/autorización
   y pruebas. Lee código fuente para confirmar cada hallazgo material, de baja
   confianza o fuera de cobertura de Graphify. Evita volcar directorios o leer
   archivos no relacionados.
4. **Sustenta los hechos.** Cada afirmación importante lleva `archivo:línea` o
   comando y resultado. Para hechos de librerías o frameworks, usa la fuente de
   documentación vigente exigida por las instrucciones del proyecto y registra la
   fuente; no trates memoria como evidencia.
5. **Clasifica incertidumbre.** Una decisión material no demostrable se convierte
   en una brecha. Investiga primero; si persiste, registra ID, pregunta, por qué
   importa, evidencia y opciones en `GAPS.md`, y pide solo la información mínima.
6. **Determina riesgo.** Conserva el modo del manifiesto o elévalo con evidencia;
   no lo rebajes por inferencia. Señala auth, multi-tenancy, pagos, migraciones,
   borrado y datos sensibles cuando entren en alcance.

## Entregable y salida

Escribe `RESEARCH.md` con:

- metadata y baseline;
- objetivo y alcance factual investigado;
- ledger de evidencia;
- flujo actual y archivos/símbolos/pruebas relevantes;
- riesgos y cambios existentes a preservar;
- brechas materiales, o la declaración explícita de que no quedan;
- handoff factual para `rpi-plan`.

Con brechas materiales abiertas, actualiza el run a `AWAITING_GAP_CLOSURE` y no
continúes. Sin ellas y con baseline verificado, registra `RESEARCH_COMPLETE` y
entrega el control a `rpi-next`. Si falta evidencia o el repositorio no permite
concluir, usa `BLOCKED` con la causa y la siguiente acción segura.

## Respuesta conversacional

Resume: run ID, estado del baseline, ruta Graphify elegida y razón, hallazgos
confirmados, riesgo, brechas (si existen) y la salida/handoff. No presentes un
plan de implementación.
