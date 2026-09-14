# Evaluación de RPI

## Suite determinista

Desde la raíz del plugin:

```bash
python3 evals/run_evals.py
```

La suite prueba esquema, tabla de estados, reanudación de brechas, binding de
aprobaciones, baseline sucio, diff atribuible, redacción de logs y seguridad de
rutas. Debe pasar antes y después de cualquier cambio al skill.

## Evaluación live y A/B de idioma

`evals/run_live_ab.py` prepara repositorios temporales, expone el skill mediante
`.agents/skills/rpi`, ejecuta casos con `codex exec --json` y guarda resultados
fuera de los fixtures. Es opt-in porque consume uso del modelo:

```bash
python3 evals/run_live_ab.py --model <model> --repetitions 3
```

Compara variantes `es` y `en` con fixtures, modelo y reasoning effort idénticos.
Mide éxito por criterio, pausas falsas, mutaciones fuera de alcance, duración,
turnos y usage reportado. `summary.json` agrega tasa de éxito, medias e intervalos
de confianza aproximados del 95 % por variante. No concluyas a partir de una sola
ejecución.

Los resultados incluyen versión de Codex, modelo, configuración y commit del
harness. No incluyas secretos ni código de repositorios reales.
