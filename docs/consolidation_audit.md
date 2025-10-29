Consolidation Audit: Code Approval & Learning

Date: 2025-10-27

Purpose
- Inventory all files implementing code-approval and learning functionality.
- Map which files are imported/used by the Hub and other core components.
- Recommend canonical modules and a safe consolidation plan.

Findings (high level)
- The repository contains multiple layers:
  - Core engines: src/core/celsius_code_approval_system.py, src/core/celsius_learning_system.py, src/core/self_learning.py
  - Learning integration & launchers: src/learning/*.py (celsius_learning_launcher.py, celsius_web_learning_integration.py, celsius_web_learning_dashboard.py, etc.)
  - Utility/adaptor wrappers: src/utils/celsius_code_approval.py
  - Demo and archived copies: archive_20251024/* and archive_20251025/* contain historical or demo variants (demo_code_approval.py, celsius_web_learning_*.py, etc.)
  - Hub references both utils and core modules in places (mix of imports).

Files of interest (non-exhaustive)
- Core
  - src/core/celsius_code_approval_system.py
  - src/core/celsius_learning_system.py
  - src/core/self_learning.py

- Active learning modules
  - src/learning/celsius_learning_launcher.py
  - src/learning/celsius_web_learning_integration.py
  - src/learning/celsius_web_learning_dashboard.py
  - src/learning/celsius_web_learner.py
  - src/learning/ai_to_ai_training.py
  - src/learning/conversation_ingest.py

- Active utils/adaptors
  - src/utils/celsius_code_approval.py
  - src/utils/enhanced_email_system.py

- Hub UI
  - src/hub/celsius_ultimate_hub.py (imports and calls many of the above)

- CLI / Intelligence
  - src/intelligence/celsius_code_generator.py (reads/writes to code approval DB and learning DB)

- Archive / Demos
  - archive_20251024/ and archive_20251025/ contain many demo and backup copies (demo_code_approval.py, celsius_web_learning_*), safe to keep for history.

Observed Hub import patterns
- Top-level Hub imports utils for code approval: src.utils.celsius_code_approval
- Hub also dynamically imports core implementations (src.core.celsius_code_approval_system and src.core.celsius_learning_system) in specific methods
- Hub sometimes launches learning as an external process using scripts in src/learning/

Recommendation (summary)
1. Canonical modules
   - Code approval: src/core/celsius_code_approval_system.py
   - Learning engine: src/core/celsius_learning_system.py
   - Learning integration: src/learning/celsius_web_learning_integration.py
   - Hub UI should import core modules (not demo/utils) and use wrappers in src/learning for launching processes where appropriate.

2. Consolidation steps (safe)
   - Update Hub imports to prefer core modules. Use try/fallbacks for compatibility.
   - Archive demo/backup files into archive/ (these already exist, but any remaining duplicates in src/ should be moved to archive/)
   - Run test suite and smoke tests (launch Hub in dev) after consolidation.

3. Merge lint-catching utilities
   - Search utils/demo implementations for useful helper functions and merge any missing helpers into core modules before archiving.

Next actions performed
- I'll update the Hub top-level import to import the core code-approval system by default, keeping a fallback to the utils adaptor if necessary.
- After that change I'll run the test suite and report results.

Detailed mapping and call sites are available on request.
