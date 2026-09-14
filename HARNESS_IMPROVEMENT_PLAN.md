# Plan de mejora del RPI Codex Harness

## Objetivo

Llevar el harness de su diseño v0.1 a una versión v0.2 que Codex pueda descubrir,
ejecutar y evaluar de forma reproducible, preservando sus principios: evidencia
antes de diseño, cambios quirúrgicos, aprobación humana en operaciones sensibles
y ausencia de commits o despliegues implícitos.

Este documento autoriza únicamente la planificación. No autoriza implementar,
instalar skills, modificar aliases globales ni migrar runs existentes.

## Estado de ejecución — 2026-09-14

La implementación local de v0.2 fue autorizada posteriormente y ya está
incorporada en este repositorio. Las fases 0–4 están materializadas en el plugin,
scripts deterministas, documentación y suite automatizada. La fase 5 incluye un
runner A/B reproducible, pero su ejecución live queda opt-in porque consume uso
del modelo. La instalación externa, los pilotos y el rollout de la fase 6 siguen
pendientes de autorización separada; no se modificaron marketplaces, aliases ni
runs reales.

## Diagnóstico que motiva el plan

1. **Descubrimiento incompleto.** Los cinco skills están en la raíz del harness,
   no bajo una ubicación que Codex escanee (`.agents/skills`). El lanzador usa
   `--add-dir`, opción que concede escritura sobre un directorio adicional, pero
   no instala ni registra skills. El archivo raíz se llama `AGENT.md`; Codex busca
   `AGENTS.md` salvo que exista una configuración explícita de fallback, que no
   está presente en la configuración local revisada.
2. **Paquete no autocontenido.** Cada skill enlaza `../references/`. Copiar o
   instalar un skill individual deja esas referencias fuera de su directorio y
   rompe la portabilidad.
3. **Máquina de estados incompleta.** `AWAITING_GAP_CLOSURE` y
   `AWAITING_IMPLEMENTATION_APPROVAL` describen la pausa, pero no hay eventos y
   transiciones completas para registrar la respuesta humana y reanudar la fase
   correcta. `diff_review_approved` y `commit_approved` existen en el manifiesto,
   pero su semántica no está cerrada.
4. **Baseline insuficiente para un worktree sucio.** Un SHA de `HEAD` y el valor
   `clean|dirty` no permiten separar cambios preexistentes de la persona usuaria
   de cambios realizados por RPI. Un `git diff <base_ref>` mezcla ambos.
5. **Artefactos que pueden contaminar Git.** Los runs se escriben dentro del
   repositorio, pero RPI no configura su exclusión. Si `.codex/rpi/` no estaba
   ignorado, el propio run altera el estado que después usa como evidencia.
6. **Estado actualizado por lenguaje natural.** No existe un comando determinista
   que valide el esquema, aplique una transición legal y escriba el manifiesto de
   forma atómica. El modelo debe interpretar y editar YAML directamente.
7. **Evals no reproducibles.** Los archivos actuales definen buenos casos y
   criterios, pero no incluyen fixtures versionados, runner, grader, repeticiones
   ni resultados comparables. Por ello no se puede medir regresión, latencia,
   tokens ni el efecto real de español frente a inglés.
8. **Instrucciones extensas y muy restrictivas.** Varias reglas se repiten entre
   contrato y skills. El flujo obliga una interacción por transición y detiene
   cualquier autocorrección, incluso cuando el fallo es reversible y permanece
   dentro del plan. Esto favorece control, pero aumenta tokens, turnos y bloqueos.
9. **Trazabilidad incompleta de versiones.** El run no registra versión de Codex,
   modelo, razonamiento, versión exacta del harness ni configuración de Graphify.
   Un resultado histórico no se puede reproducir con precisión.

## Decisiones propuestas para aprobación

### D1. Idioma

Mantener en español las instrucciones operativas y la conversación. Mantener en
inglés los identificadores de máquina: nombres de skills, campos, estados,
eventos, comandos y nombres de archivos. Hacer bilingües y breves las
descripciones usadas para activación implícita.

No traducir todo el harness sin evidencia. Ejecutar primero el A/B definido en la
fase 5. Adoptar una versión inglesa solo si mejora de forma repetible la tasa de
éxito o el costo total sin introducir regresiones.

### D2. Forma de distribución

Recomendación: empaquetar RPI como un plugin personal con un único skill de
entrada `rpi`. Su `SKILL.md` será un router corto y las instrucciones de cada fase
vivirán en referencias cargadas bajo demanda. El plugin podrá incluir scripts y
todos los recursos necesarios, sin enlaces fuera del paquete.

Alternativa de menor cambio: conservar cinco skills y exponerlos mediante
symlinks en `~/.agents/skills`. Es válida para uso personal, pero mantiene más
superficie de activación y una distribución menos clara.

### D3. Nivel de autonomía

Para v0.2, conservar el gate humano antes de escribir en `standard` y
`high-risk`. Permitir que las fases de solo lectura avancen automáticamente hasta
encontrar una brecha material o llegar al gate. Evaluar después una política más
autónoma para `simple` y correcciones acotadas dentro del plan.

### D4. Artefactos

Conservar `.codex/rpi/` por compatibilidad, pero excluirlo explícitamente de todos
los comandos de baseline y diff. Añadir un bootstrap opcional y explícito que lo
registre en `.git/info/exclude`; no modificar `.gitignore` automáticamente.

## Implementación propuesta

### Fase 0 — Congelar el comportamiento v0.1

**Resultado:** existe una línea base medible antes de cambiar prompts o estados.

- Convertir cada eval Markdown actual en un caso identificable con entrada,
  fixture, resultado esperado y criterios machine-readable.
- Añadir un happy path E2E y casos para worktree sucio, archivos no rastreados,
  rutas con espacios, varios runs, Graphify ausente/parcial/stale y fallo de una
  validación.
- Registrar por ejecución: versión de Codex, modelo, reasoning effort, versión
  del harness, duración, turnos, tokens si están disponibles, mutaciones fuera de
  alcance y causa de cualquier pausa.
- Ejecutar al menos tres repeticiones por caso no determinista y conservar un
  resumen; no versionar contenido sensible de repositorios reales.

**Archivos previstos:** `evals/cases/`, `evals/fixtures/`, `evals/results/`,
`scripts/run-evals.*`, `README.md`.

**Aceptación:** la suite reproduce los seis casos actuales y entrega un reporte
con pass/fail por criterio; el worktree del fixture queda verificablemente dentro
del alcance esperado.

### Fase 1 — Hacer el harness descubrible y autocontenido

**Resultado:** una sesión nueva puede listar e invocar RPI sin que el prompt le
indique rutas internas.

- Crear el paquete de plugin y el skill `rpi` con frontmatter y metadata válidos.
- Mover el contrato, esquema, principios y fases dentro del paquete.
- Reducir `SKILL.md` a triggers, modos, prioridades y reglas de carga progresiva.
- Añadir un `AGENTS.md` real al repositorio del harness para mantenimiento del
  propio código. Mover el historial y estado de proyecto de `AGENT.md` a
  `README.md` o `CHANGELOG.md`; no cargar ese historial como instrucción.
- Sustituir el alias por un lanzador que invoque el skill instalado y verifique su
  disponibilidad. `--add-dir` solo se conservará cuando RPI necesite escribir en
  una ruta adicional concreta.

**Archivos previstos:** `.codex-plugin/plugin.json`, `skills/rpi/`, `AGENTS.md`,
`README.md`, `CHANGELOG.md`, documentación del instalador/lanzador.

**Aceptación:** `/skills` muestra RPI en una sesión nueva desde un repositorio
ajeno; una invocación explícita y otra implícita activan el skill correcto; todas
las referencias resuelven desde el paquete instalado.

### Fase 2 — Formalizar estado, eventos y baseline

**Resultado:** las transiciones inválidas son imposibles de aplicar mediante las
herramientas del harness y los cambios preexistentes quedan identificados.

- Definir una única tabla canónica de estados y eventos. Evitar combinaciones
  independientes de `current_phase`, `status` y `next_action` que puedan
  contradecirse; derivar campos redundantes o eliminarlos.
- Incluir eventos explícitos para `gap_answered`, `implementation_approved`,
  `diff_accepted`, `resume`, `close_uncommitted` y, si se conserva, autorización
  de commit.
- Guardar en cada aprobación actor, timestamp, `head_sha` y un digest del alcance
  aprobado. Invalidar el gate si cambia cualquiera de ellos.
- Capturar un baseline compuesto por `HEAD`, diff del index, diff del worktree y
  lista/hash de archivos no rastreados relevantes, excluyendo artefactos RPI.
- Registrar `resume_state` al abrir una brecha para volver a la fase que la creó.
- Separar la revisión técnica del diff de su aceptación humana. Definir si cerrar
  exige `diff_accepted`; la recomendación es que sí.
- Preservar siempre la revisión de plan antes de escribir la revisión de diff,
  con nombres de artefacto distintos o archivado determinista.

**Archivos previstos:** `skills/rpi/references/state-machine.md`, esquema de
manifest v0.2, `scripts/rpi-state.*`, `scripts/rpi-baseline.*`, migración o lector
read-only para runs v0.1.

**Aceptación:** pruebas de tabla cubren cada estado/evento legal e ilegal; cerrar
una brecha reanuda la fase original; un cambio preexistente no se atribuye a RPI;
un cambio posterior dentro del alcance invalida el gate aplicable.

### Fase 3 — Determinismo y seguridad de artefactos

**Resultado:** el modelo decide contenido, mientras scripts pequeños controlan
integridad y mutaciones mecánicas.

- Añadir comandos para crear runs, validar manifests, aplicar eventos, archivar
  artefactos y generar diffs con exclusiones seguras.
- Escribir manifests y `LATEST` de forma atómica y con locking para evitar
  carreras entre runs.
- Validar rutas canónicas y rechazar traversal o un `project_root` que no coincida
  con el repositorio activo.
- Definir permisos por fase en una allowlist comprobable antes y después de cada
  operación.
- Redactar logs antes de persistirlos: secretos, tokens, cookies y valores de
  variables sensibles nunca deben copiarse al run.
- Mantener cualquier script sin dependencias externas o declarar y comprobar sus
  dependencias en metadata.

**Aceptación:** manifests truncados o transiciones ilegales fallan sin escritura
parcial; dos procesos no corrompen `LATEST`; los tests de path traversal y fuga
de secretos pasan; un diff fuera de alcance queda detectado sin ser revertido.

### Fase 4 — Simplificar prompts y reducir pausas innecesarias

**Resultado:** mismo o mayor control con menos tokens y menos turnos.

- Eliminar duplicación: cada regla normativa tendrá una sola fuente canónica.
- Reescribir instrucciones hacia objetivo, criterios de éxito, invariantes y
  condiciones de parada. Reservar “siempre/nunca/solo” para invariantes reales.
- Permitir que `start` encadene automáticamente Research → Plan → Review plan
  mientras todas las acciones sean de solo lectura y no existan brechas.
- Mantener la pausa obligatoria justo antes de la primera escritura para
  `standard`/`high-risk`, con resumen concreto de baseline y alcance.
- Para `simple`, diseñar y evaluar un loop acotado de corrección dentro del plan.
  Para `standard`, evaluar una sola autocorrección de validación cuando no cambie
  alcance. `high-risk` continúa deteniéndose.
- Hacer Graphify oportunista: consultarlo solo si existe y su cobertura puede
  verificarse con bajo costo; medir si realmente reduce lecturas y tokens.

**Aceptación:** ningún eval de seguridad v0.1 regresa; disminuyen turnos y tokens
del happy path; no aumenta la tasa de cambios fuera de alcance ni de decisiones
materiales inferidas.

### Fase 5 — Evaluación español/inglés y calibración por modelo

**Resultado:** la decisión de idioma y prompting se basa en datos del harness.

- Crear dos variantes semánticamente equivalentes de las instrucciones, español
  e inglés, manteniendo idénticos estados, herramientas, fixtures y solicitudes.
- Probar ambas con los modelos y reasoning efforts que realmente se usarán.
- Comparar: éxito por criterio, decisiones materiales inventadas, pausas falsas,
  mutaciones fuera de alcance, tokens de entrada/salida, duración y número de
  turnos.
- Adoptar inglés total solo si la mejora se repite en la mayoría de casos y
  compensa el costo de mantenimiento. Si la calidad empata, conservar español y
  optimizar únicamente descripciones, identificadores y concisión.
- Guardar la matriz de compatibilidad y volver a ejecutarla cuando cambie el
  modelo principal o una versión mayor de Codex.

**Aceptación:** reporte A/B reproducible con intervalos por repetición y decisión
documentada; no se decide por una sola ejecución.

### Fase 6 — Documentación, migración y rollout controlado

**Resultado:** v0.2 se puede adoptar y revertir sin perder runs v0.1.

- Documentar instalación, actualización, desinstalación, invocación, recuperación
  y ubicación de artefactos.
- Tratar runs v0.1 como read-only o migrarlos mediante dry-run y backup; nunca
  reescribirlos implícitamente.
- Ejecutar un piloto en repositorios desechables, luego en un cambio `simple`, uno
  `standard` y uno `high-risk` con aprobación humana.
- Mantener el lanzador v0.1 disponible hasta que v0.2 pase la matriz completa.
- Publicar criterios de rollback a v0.1 y cerrar el rollout solo después de
  revisar los resultados del piloto.

**Aceptación:** instalación limpia y desinstalación dejan intactos los proyectos;
runs v0.1 siguen legibles; los tres pilotos cumplen alcance, gates y validación.

## Orden y gates de implementación

1. Aprobar D1–D4.
2. Implementar y revisar Fase 0.
3. Implementar Fases 1–3; ejecutar toda la línea base después de cada fase.
4. Revisar métricas antes de autorizar los cambios de autonomía de Fase 4.
5. Ejecutar Fase 5 antes de cualquier traducción completa.
6. Autorizar Fase 6 únicamente con la suite en verde.

Cada fase debe llegar como un diff separado y revisable. Ninguna fase debe hacer
commit, instalar el plugin, modificar `~/.aliases` ni migrar runs reales sin una
solicitud explícita adicional.

## Métricas de éxito de v0.2

- 100 % de transiciones cubiertas por pruebas de tabla.
- 0 mutaciones fuera del alcance en la suite y pilotos.
- 0 decisiones materiales inferidas en casos que exigen una brecha.
- 0 corrupción o mezcla de cambios preexistentes en worktrees sucios.
- Activación explícita e implícita reproducible desde un repositorio ajeno.
- Menos turnos y menor consumo total de tokens en el happy path que v0.1, sin
  reducir la tasa de éxito ni los gates aprobados.
- Resultados de eval ligados a versión de harness, Codex, modelo y configuración.
