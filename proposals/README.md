This directory stores AI-assisted coding proposals created by
`scripts/ai_assisted_coding.py` or `src/utils/ai_coding.py`.

Each proposal is a JSON file with the following keys:
- title
- description
- created_at
- status (proposed | reviewed | applied)
- patch (optional unified diff text)
- test_output (captured stdout/stderr from running tests after creating the proposal)

Workflow suggestion:
1. Use the script to create a proposal and run tests.
2. Open the proposal JSON, add or paste the proposed unified diff into `patch`.
3. Review the patch locally, run tests, and apply manually when ready (e.g., via `git apply`).
