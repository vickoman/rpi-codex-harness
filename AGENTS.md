# RPI harness maintenance

This repository builds the `rpi-codex-harness` plugin. Keep the runtime workflow
self-contained under `skills/rpi/`; files in that skill may not depend on paths
outside the plugin.

Before completing a change:

- run `python3 evals/run_evals.py`;
- run the skill and plugin validators documented in `README.md`;
- keep state transitions in `rpi_core.py` and `state-machine.md` synchronized;
- preserve v0.1 runs as read-only unless a migration is explicitly requested;
- do not install the plugin, modify personal marketplaces, or change global
  aliases unless the user requests that external mutation.

Use English for machine identifiers and Spanish for the default human-facing
workflow. Evaluate language changes with `evals/run_live_ab.py` instead of
assuming one language performs better.
