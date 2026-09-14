# Contrato RPI v0.2

## Resultado esperado

RPI completa un cambio mediante:

```text
Research → Plan → Review plan → Implementation gate → Implement
→ Review diff → Human diff acceptance → close or separately authorized commit
```

Las fases de solo lectura pueden continuar en el mismo turno. La ejecución se
detiene ante una brecha material, evidencia insuficiente, deriva del baseline o
un gate humano pendiente.

## Principios

1. **Evidencia antes de diseño.** Los hechos materiales citan código, comandos o
   documentación autoritativa. Investiga antes de preguntar.
2. **Solución mínima.** No añadas abstracciones, configuración o refactors que el
   objetivo y el repositorio no justifiquen.
3. **Cambios quirúrgicos.** Cada archivo y símbolo modificado se traza a un paso
   aprobado. Preserva trabajo ajeno y estilo existente.
4. **Éxito observable.** Cada paso declara validación y resultado esperado. Las
   pruebas deben demostrar el comportamiento solicitado, no solo finalizar en 0.

## Evidencia y decisiones

Una brecha es material cuando una elección no demostrable cambia producto,
alcance, seguridad, comportamiento público, datos, compatibilidad, despliegue o
una convención incompatible. Registra en `GAPS.md`: ID, fase, pregunta mínima,
impacto, evidencia, opciones, respuesta y estado.

Las preferencias estéticas y elecciones reversibles dentro de convenciones
existentes no son brechas.

## Riesgo

- `simple`: cambio local, reversible y de bajo impacto. Puede omitir el gate de
  implementación solo cuando la persona usuaria declaró este modo.
- `standard`: valor predeterminado. Requiere revisión de plan, gate antes de
  escribir y aceptación humana del diff.
- `high-risk`: autenticación/autorización, multi-tenancy, pagos, migraciones,
  borrado o datos sensibles. Añade validaciones de seguridad y se detiene ante
  cualquier preocupación no resuelta.

El riesgo puede elevarse con evidencia. No se rebaja durante un run sin una
decisión humana explícita.

## Baseline y alcance

El script captura `HEAD`, staged, unstaged y archivos no rastreados relevantes al
inicio. Los snapshots de archivos ya modificados permiten calcular el delta
atribuible al run incluso si RPI toca el mismo archivo.

Antes de conceder un gate, el workspace debe coincidir con el fingerprint del
baseline. La aprobación queda ligada a `HEAD`, fingerprint y digest de alcance.
La aceptación del diff queda ligada al digest del delta observado.
Si el delta cambia después de la revisión técnica, la aceptación humana se
rechaza hasta repetir la revisión.

## Concurrencia

Un solo writer posee cada archivo. Paraleliza escritura únicamente cuando el plan
marca ownership disjunto y no hay dependencia de orden, datos o configuración.
`LATEST` es conveniencia; el `run_id` explícito es autoridad.

## Límites de recuperación

Las fases read-only pueden corregir sus artifacts dentro del mismo alcance. En
`simple`, una validación fallida puede tener un intento de corrección acotado. En
`standard`, solo puede intentarse una corrección que no altere alcance ni riesgo.
`high-risk`, deriva, cambios inesperados o seguridad fallida requieren dirección
humana. Nunca se ejecuta rollback automático.
