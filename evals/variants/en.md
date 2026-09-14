---
name: rpi
description: Run code changes through research, planning, controlled implementation, and diff review.
---

Complete the requested change end to end with evidence and the smallest scope.
Inspect the code before designing, create an executable plan, and review the plan.
In simple mode you may implement without a second gate, but you must validate the
behavior and review only the delta since the baseline. Do not commit, push, open a
PR, deploy, or roll back. Stop after showing the validated diff and requesting
human acceptance. Use the available scripts to create the run, apply transitions,
and calculate the delta; never edit the manifest manually.
