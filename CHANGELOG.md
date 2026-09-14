# Changelog

## 0.2.0 — 2026-09-14

- Empaqueta el harness como plugin con un único skill `rpi` autocontenido.
- Reemplaza estado YAML editado por el modelo con manifest JSON y transiciones
  deterministas, atómicas y bloqueadas.
- Añade eventos completos para brechas, implementación, aceptación del diff,
  reanudación y cierre.
- Captura snapshots de cambios preexistentes y calcula el delta desde el inicio
  real del run.
- Separa revisión de plan y revisión de diff para preservar evidencia.
- Añade redacción de logs, validación de rutas y bindings de approvals.
- Convierte la matriz de evals en catálogo machine-readable y pruebas ejecutables.
- Añade runner live A/B español/inglés opt-in.

## 0.1.0 — 2026-08-27

- Diseña cinco skills RPI separados, referencias compartidas y seis evals
  manuales iniciales.
