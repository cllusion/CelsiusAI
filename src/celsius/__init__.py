"""
Celsius AI — main application package.

This package is the canonical home for all Celsius AI source code.
Modules currently living at ``src.<module>`` are being migrated here
incrementally; re-exports from those legacy paths are maintained for
backward compatibility during the transition.

Package layout (target state)
------------------------------
src/celsius/
  hub/          — central orchestrator (CelsiusUltimateHub)
  core/         — AI core, config, assistant (to be migrated from src/core/)
  security/     — auth, guardian, threat analysis (to be migrated from src/security/)
  learning/     — web learning, self-improvement (to be migrated from src/learning/)
  monitoring/   — hourly reporter, health data (to be migrated from src/monitoring/)
  utils/        — shared utilities, db_migrations, code_safety_gate
"""
