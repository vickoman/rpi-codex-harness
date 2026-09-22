# Fase Research

## Objetivo

Producir un snapshot factual suficiente para planificar sin diseñar una solución
ni modificar fuente.

## Trabajo

1. Lee el manifest y confirma proyecto, baseline, solicitud y cambios
   preexistentes.
2. Si `graphify-out/graph.json` existe, valida `source_ref`, `generated_at`,
   `workspace_root` y cobertura antes de usarlo. Si no es confiable, registra la
   razón y usa inspección dirigida; no lo regeneres.
3. Sigue el flujo real desde entrada hasta datos, autorización, configuración,
   efectos y pruebas. Confirma hallazgos materiales en código.
4. Para librerías y servicios usa la documentación vigente exigida por el
   proyecto. Memoria no cuenta como evidencia de una API cambiante.
5. Eleva el riesgo si aparece auth, multi-tenancy, pagos, migraciones, borrado o
   datos sensibles.
6. Abre una brecha solo después de agotar evidencia disponible.

## Salida

Escribe `RESEARCH.md` con baseline, objetivo, ledger de evidencia, flujo,
archivos/símbolos/pruebas, riesgos, cambios a preservar y handoff factual.

- Sin brechas: aplica `research-complete` y continúa a Plan en el mismo turno.
- Con brecha: escribe `GAPS.md`, aplica `gap-opened`, pregunta lo mínimo y pausa.
- Sin evidencia suficiente: aplica `block` con causa y siguiente acción segura.

No incluyas pasos de implementación.

Si el manifest habilita Jev, ejecuta `rpi_jev.py --phase research` después de
escribir el artifact y antes de la transición. Su resultado es consultivo y no
cambia cuál de las transiciones anteriores corresponde.
