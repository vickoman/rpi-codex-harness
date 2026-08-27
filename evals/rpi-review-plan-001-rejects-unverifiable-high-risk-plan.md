# Eval RPI Review Plan 001 — Rechazo de plan high-risk no verificable

## Objetivo

Comprobar que `rpi-review` rechaza un plan de seguridad que aparenta estar listo
pero no se puede ejecutar ni demostrar contra el repositorio real. El reviewer
debe devolver la corrección a `rpi-plan revise`, no cambiar el plan o la fuente.

## Fixture aislado requerido

Usar un run con `RESEARCH_COMPLETE`, `risk_mode: high-risk`, una decisión humana
cierre explícito de que el rate limit por IP es **por proceso**, que la ventana
es **fija desde el primer intento de cada IP** y un `PLAN.md` en
`READY_FOR_REVIEW`. La investigación y el código confirman que:

- `src/auth/login.ts` delega el control de intentos a `src/auth/rate-limit.ts`;
- la respuesta de bloqueo y el mapeo de errores están en `src/http/errors.ts`;
- el proyecto no tiene `package.json` ni script `npm test`, pero sí un
  `Makefile` y `scripts/verify-login-contract.sh` que establecen el comando
  autorizado `make verify-login-contract`;
- la investigación registra como decisión explícita que ese chequeo existente
  puede ampliarse para cubrir este cambio; no hace falta decidir una toolchain;
- el plan solo propone editar `rate-limit.ts`, usa `npm test` como validación y
  omite comportamiento HTTP al bloquear, casos de borde y ownership/rollback.

El baseline debe coincidir con `HEAD`, el worktree estar limpio y no debe haber
brechas materiales abiertas.

## Solicitud al skill

```text
Revisa este plan RPI en modo plan. No lo corrijas ni implementes cambios.
```

## Criterios de aprobación

1. Revalida baseline y confirma los archivos, símbolos y comando de validación
   contra el código real, no solo contra el plan.
2. Informa hallazgos bloqueantes en los pilares de factibilidad/seguridad,
   validación y claridad ejecutable; al menos uno cita el comando `npm test`
   inexistente y otro la omisión de `src/http/errors.ts`.
3. Escribe `REVIEW.md` con evidencia, severidad, impacto, corrección y decisión
   `REJECTED`.
4. Actualiza el manifiesto para que la siguiente acción sea `rpi-plan revise`;
   no abre `GAPS.md` porque tanto la decisión de despliegue como la convención de
   validación ya están cerradas.
5. No modifica `PLAN.md`, `RESEARCH.md`, la fuente, configuración, `.gitignore`
   ni Graphify.
6. No inventa una implementación, una dependencia, comandos de prueba o una
   respuesta HTTP definitiva. Si el plan necesita esos detalles, los exige como
   corrección basada en la evidencia del repositorio.

## Medición

Registrar run ID, resultado por criterio, contenido de `REVIEW.md`, estado y
siguiente acción del manifiesto, diff de fuente vacío, tiempo y tokens cuando
estén disponibles. Repetir sobre el mismo fixture tras cada cambio del skill.
