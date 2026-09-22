# Fases Review

## Review plan

Parte de `plan_review_pending`. Revalida baseline y código real, y evalúa:

1. enfoque mínimo y orden correcto;
2. factibilidad, compatibilidad y seguridad;
3. validaciones realizables que cubren éxito y fallo;
4. claridad ejecutable, ownership y comportamiento ante fallo.

Cada hallazgo incluye severidad, evidencia, impacto y corrección concreta.

- Sin hallazgos materiales: escribe `PLAN_REVIEW.md`, aplica `plan-approved` y
  continúa al preflight.
- Corrección acotada: escribe la revisión y aplica `plan-rejected`.
- Decisión externa: abre brecha.
- Deriva o tercer ciclo: bloquea.

No edites `PLAN.md` durante la revisión.

## Review diff

Parte de `diff_review_pending`. Usa `rpi_diff.py`, no `git diff HEAD`, para
comparar el árbol actual con el snapshot exacto de inicio.

Mapea cada archivo/hunk a requisito y paso. Repite validaciones no destructivas
cuando aporten evidencia. En `high-risk`, revisa autorización, aislamiento,
datos, migraciones/borrados, fallo seguro y rollback aplicable.

- Dentro de alcance y validado: escribe `DIFF_REVIEW.md`, aplica `diff-approved`,
  presenta el diff y solicita aceptación humana.
- Cambio fuera de alcance, fallo o riesgo: aplica `diff-rejected` y pausa; no
  corrijas ni reviertas.
- Decisión externa: abre brecha.
- Baseline no confiable: bloquea.

La aprobación técnica no equivale a aceptación humana. Solo una respuesta
explícita permite `diff-accepted`.

Si el manifest habilita Jev, después de escribir `DIFF_REVIEW.md` ejecuta
`rpi_jev.py --phase implement` antes de decidir `diff-approved` o
`diff-rejected`. Jev compara solicitud, plan, delta y validación; la revisión
técnica determinista conserva toda la autoridad.

Tras `diff_rejected`, una dirección humana para corregir dentro del plan aplica
`rework-approved`. Un cambio de alcance requiere una brecha o un run nuevo.
