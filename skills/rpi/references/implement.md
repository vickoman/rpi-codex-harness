# Fase Implement

## Preflight

Parte de `implementation_preflight`. Confirma manifest, fingerprint, plan,
revisión aprobada, archivos/símbolos, comandos y cambios preexistentes. Escribe
`IMPLEMENTATION.md` antes de tocar fuente y aplica `preflight-complete --scope`
con la lista exacta de archivos autorizados.

Para `standard` y `high-risk`, muestra run, `HEAD` y lista de archivos, y pausa en
`implementation_approval_pending`. Solo una aprobación explícita permite:

```bash
python3 scripts/rpi_state.py event --run-dir <run> \
  --event implementation-approved --actor user --scope <archivos...>
```

Si el fingerprint cambió, el script rechaza el gate. Investiga la deriva y
bloquea; no uses reset o stash.

## Escritura y validación

En `implementing`, modifica únicamente archivos/símbolos del alcance aprobado y
sigue dependencias del plan. Registra cambios y comandos mediante `rpi_log.py`.
Después de cada cambio relevante inspecciona `rpi_diff.py`.

- Éxito completo: aplica `validation-passed`. En `high-risk`, registra el gate
  final con `security-passed` antes de continuar a Review diff.
- Fallo reversible dentro del mismo alcance: `simple` permite un intento acotado;
  `standard`, uno solo si no altera riesgo ni decisiones. Registra el intento.
- Fallo restante: aplica `validation-failed`.
- Preocupación de seguridad durante implementación: aplica `block`. Si una
  validación completa de `high-risk` llega a `security_review_pending` y el gate
  falla, aplica `security-failed`.
- Cambio inesperado o dependencia faltante: aplica `block`.

No cambies el plan, dependencias no autorizadas, Graphify, historial Git ni
sistemas externos. No hagas commit, rollback, PR o deploy.
