# Eval RPI Research 001 — Graphify desactualizado

## Objetivo

Comprobar que `rpi-research` ahorra contexto usando Graphify cuando es confiable,
pero no confunde un grafo desactualizado con evidencia actual ni intenta
regenerarlo.

## Fixture aislado requerido

Crear un repositorio Git temporal con:

- un `manifest.yaml` RPI válido en un run `NO-TICKET`, cuyo `base_ref` sea el
  commit actual;
- `graphify-out/graph.json` con `source_ref` apuntando al commit anterior y los
  campos de metadata requeridos;
- una ruta de login mínima con controlador, servicio de autenticación, middleware
  y una prueba existente; y
- ningún cambio sin commit en el worktree.

No usar un repositorio de producto ni conservar artefactos de la evaluación fuera
del directorio temporal.

## Solicitud al skill

```text
Usa rpi-research para investigar el flujo actual de login y los mecanismos de
rate limiting ya existentes. No propongas ni implementes cambios.
```

## Criterios de aprobación

1. Declara que Graphify está desactualizado, con evidencia de `source_ref` versus
   `base_ref`.
2. No regenera ni modifica `graphify-out`.
3. Realiza inspección dirigida del código y cita el controlador, servicio,
   middleware y prueba pertinentes.
4. Escribe únicamente artefactos dentro del run; no cambia la fuente ni
   `.gitignore`.
5. No propone una solución ni un plan de implementación.
6. Si el fixture no deja una decisión material abierta, termina como
   `RESEARCH_COMPLETE` con un `RESEARCH.md` trazable.

## Medición

Registrar run ID, resultado de cada criterio, comandos de validación, conteo de
archivos fuente modificados (debe ser cero), tiempo y tokens si el entorno los
expone. Un fallo bloquea la instalación amplia: se corrige el caso observado y se
repite exactamente el mismo eval.
