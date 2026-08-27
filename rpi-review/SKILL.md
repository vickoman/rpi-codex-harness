---
name: rpi-review
description: "Review an RPI implementation plan or completed diff against research, scope, security, and validation without changing source. Use after rpi-plan or rpi-implement hands off a legal review state."
---

# RPI Review — revisión de plan

Revisa críticamente un plan RPI antes de autorizar implementación. Es una fase de
lectura: encuentra defectos y evidencia, pero nunca corrige el plan ni escribe
código.

## Modos

- `mode: plan`: revisa `PLAN.md` antes de implementación. Parte de
  `READY_FOR_REVIEW` y usa los cuatro pilares de diseño descritos abajo.
- `mode: diff`: revisa el diff real después de `rpi-implement`. Parte de
  `VALIDATED` y comprueba que el resultado ejecutado coincide con el plan,
  validaciones y alcance autorizado.

Si el modo solicitado no coincide con la transición del manifiesto, informa el
estado, no lo alteres y devuelve el control a `rpi-next`.

## Referencias y entradas obligatorias

Antes de revisar, lee:

1. [principios RPI](../references/rpi-principles.md): P1, P2, P3 y P4.
2. [contrato operativo](../references/rpi-contract.md).
3. [esquema de artefactos](../references/artifact-schema.md).
4. `manifest.yaml`, `RESEARCH.md`, `PLAN.md`, `REVIEW.md`,
   `IMPLEMENTATION.md` cuando el modo sea `diff`, `GAPS.md` si existe,
   decisiones explícitas de la persona usuaria y `AGENTS.md` del proyecto
   objetivo.

Además, inspecciona de forma dirigida el código fuente real que sustenta los
pasos y las validaciones del plan. Graphify puede orientar navegación si sigue
vigente, pero no sustituye esa confirmación.

Para `plan`, si no hay un `PLAN.md` válido en estado `READY_FOR_REVIEW`; para
`diff`, si no existe `IMPLEMENTATION.md` completo con estado `VALIDATED` y
manifiesto en transición legal, devuelve el control a `rpi-next`. No recrees
investigación, no derives una decisión implícita y no inicies un run nuevo.

## Permisos y límites

Puedes inspeccionar el proyecto y escribir únicamente dentro del run:
`manifest.yaml`, `REVIEW.md`, `GAPS.md` cuando una decisión externa lo exija,
`history/` y `logs/`. Nunca escribas `PLAN.md`, fuente, configuración del
proyecto, `.gitignore`, Graphify ni sistemas externos.

En `plan`, `REJECTED` devuelve el plan a `rpi-plan revise`; en `diff`,
`DIFF_REJECTED` detiene el handoff y espera dirección humana. Ningún resultado
autoriza a corregir el plan o el código desde este skill. Mantén los cambios
existentes de la persona usuaria intactos.

## Procedimiento de revisión

1. **Revalidar el handoff.** Comprueba `base_ref`, worktree, archivos y símbolos
   citados. Registra cualquier deriva material: el plan no puede aprobarse contra
   una realidad que cambió.
2. **Trazar el objetivo.** Relaciona requisito, decisión, evidencia de
   investigación, paso, archivo/símbolo, validación y criterio de aceptación.
   Señala alcance especulativo, refactors no necesarios o comportamiento público
   no decidido.
3. **Evaluar los cuatro pilares.**

   - **Enfoque y orden:** la solución mínima logra el objetivo y respeta las
     dependencias reales; los pasos tienen precondiciones y orden correcto.
   - **Factibilidad y seguridad:** las rutas, APIs, datos y dependencias existen
     y son compatibles. Para `high-risk`, comprueba explícitamente auth,
     autorización, IDOR/aislamiento de tenant cuando aplique, datos sensibles,
     migraciones/borrados, fallo seguro y rollback.
   - **Validación:** cada cambio relevante tiene un comando realizable, resultado
     esperado y casos de borde/fallo. Confirma que el proyecto puede ejecutar lo
     propuesto; no aceptes comandos inventados ni cobertura que omita el riesgo.
   - **Claridad ejecutable y ownership:** un implementador puede actuar sin
     adivinar. Cada archivo tiene un writer, `Parallel: yes` solo es válido con
     ownership disjunto y sin dependencias, y hay comportamiento ante fallo.
4. **Clasificar hallazgos.** Cada hallazgo cita pilar, severidad, evidencia
   (`archivo:línea` o comando/resultado), impacto y corrección concreta. No
   conviertas preferencias estéticas en bloqueos.
5. **Resolver la salida legal.**

   - `APPROVED`: no hay hallazgos críticos o materiales; el plan puede pasar al
     gate humano previo a implementación.
   - `APPROVED_WITH_WARNINGS`: solo hay advertencias no bloqueantes y se declaran
     sus límites.
   - `REJECTED`: hay una corrección de plan, acotada y realizable, sin nueva
     decisión de la persona usuaria. Conserva el plan, actualiza el manifiesto y
     dirige a `rpi-plan revise`.
   - `AWAITING_GAP_CLOSURE`: una decisión de producto, alcance, seguridad o
     comportamiento sigue siendo necesaria. Investiga primero, registra la
     pregunta mínima, evidencia y opciones en `GAPS.md`, y detente.
   - `BLOCKED`: falta evidencia, hay deriva material o `review_revision_count`
     ya es 2; pide dirección humana en vez de iniciar un tercer ciclo.

No rebajes un `high-risk` por inferencia. Un rechazo solo puede entrar en revisión
nueva después de que `rpi-plan revise` preserve el plan anterior en `history/` y
actualice `review_revision_count`; este skill no incrementa ni reinicia el
contador.

## Revisión del diff (`mode: diff`)

Después de comprobar que el baseline del manifiesto coincide con el punto de
partida de implementación:

1. Inspecciona `git diff <base_ref> --`, `git status --short`, los checkpoints de
   `IMPLEMENTATION.md` y los resultados de validación. Excluye artefactos RPI de
   la evaluación del cambio de producto, pero registra si aparecieron archivos
   de fuente inesperados.
2. Mapea cada hunk a un requisito, decisión y paso del plan. Un archivo,
   símbolo, dependencia o configuración fuera de alcance es un hallazgo
   bloqueante; no lo elimines ni lo corrijas.
3. Comprueba que el cambio observado conserva el comportamiento autorizado,
   que las validaciones declaradas realmente pasaron y que su salida esperada
   cubre el objetivo. Puedes repetir comandos no destructivos del plan, pero no
   inventes pruebas ni cambies el árbol para hacerlas pasar.
4. Para `high-risk`, revisa el diff y la evidencia de seguridad: autorización,
   aislamiento de tenant/IDOR si aplica, datos sensibles, migraciones/borrados,
   fallo seguro y rollback. Una preocupación no resuelta bloquea.
5. Reporta por archivo/hunk la intención, resultado real, evidencia, severidad,
   impacto y decisión humana necesaria. La salida es:

   - `DIFF_APPROVED` si todo el diff está dentro del plan, las validaciones pasan
     y no hay hallazgos materiales.
   - `DIFF_REJECTED` si hay deriva, cambio fuera de alcance, validación fallida o
     riesgo no resuelto. Detente; no inicies `rpi-plan revise` ni un arreglo de
     código automáticamente.
   - `AWAITING_GAP_CLOSURE` si el diff revela una decisión externa no cerrada.
   - `BLOCKED` si el baseline o la evidencia del handoff no son confiables.

En `DIFF_REJECTED`, el manifiesto conserva la evidencia, deja claro que no hay
rollback automático y dirige a revisión humana. Solo una aprobación explícita
de diff permite que otro paso prepare un commit; este skill nunca lo prepara.

## Salidas

Escribe `REVIEW.md` con: modo, run ID, baseline y evidencia inspeccionada,
trazabilidad resumida, resultado de cada pilar o de cada hunk, hallazgos
priorizados, limitaciones, decisión, estado del manifiesto y acción siguiente.
No declares un plan implementable ni un diff aprobado si existe una brecha
material, cambio fuera de alcance o validación no factible.

En la respuesta conversacional, presenta la decisión primero y luego evidencia,
hallazgos, brechas y siguiente acción. No hagas commits, despliegues, PRs ni
escrituras fuera del run.
