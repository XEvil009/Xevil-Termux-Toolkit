# Contributing

1. Open an issue describing the defect or proposed change before broad refactoring.
2. Work on a descriptive feature branch; do not commit directly to `main`.
3. Keep changes focused and preserve existing command names and Termux paths unless a change is explicitly approved.
4. Add or update automated tests and documentation.
5. Run `python -m unittest discover -s tests -v` and `python -m compileall -q tools tests`.
6. Inspect the final diff for secrets, local paths, generated documents, and unrelated changes.
7. Open a pull request with scope, test evidence, risks, and deployment impact. Governance and release-policy changes remain proposals until formally approved.
