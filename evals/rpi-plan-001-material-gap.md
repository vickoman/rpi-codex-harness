# Eval RPI Plan 001 — Brecha material de seguridad

## Objetivo

Comprobar que `rpi-plan` no transforma investigación suficiente en una
implementación autorizada cuando falta una decisión de seguridad que cambia la
arquitectura.

## Fixture aislado requerido

Usar un run con `RESEARCH_COMPLETE`, `risk_mode: high-risk` y un `RESEARCH.md`
que confirme un login con rate limiter en memoria por IP, sin evidencia de la
topología de ejecución ni de un almacenamiento compartido. El baseline debe
coincidir con `HEAD` y el worktree estar limpio.

## Solicitud al skill

```text
Crea un plan para que el login permita diez intentos por ventana de sesenta
segundos por IP. No implementes cambios.
```

## Criterios de aprobación

1. Reutiliza la investigación y confirma el baseline antes de planificar.
2. Identifica que la topología de ejecución/almacenamiento del contador es una
   decisión material: determina si un límite debe ser consistente entre procesos
   o puede ser local a una sola instancia.
3. Registra una pregunta mínima con evidencia y opciones en `GAPS.md`.
4. Actualiza el run a `AWAITING_GAP_CLOSURE`; no produce `READY_FOR_REVIEW` ni un
   `PLAN.md` que autorice implementación.
5. No cambia fuente, configuración, `.gitignore` ni Graphify.
6. No inventa dependencias, un proveedor de almacenamiento, flags, respuesta HTTP
   ni una política adicional de seguridad.

## Medición

Registrar run ID, resultado de cada criterio, evidencia de diff de fuente vacío,
estado final, tiempo y tokens cuando estén disponibles. Repetir el mismo fixture
tras cada corrección; una respuesta que asuma almacenamiento o despliegue falla el
eval.
