# Contributing

Issues and focused pull requests are welcome. Before submitting:

1. Keep Procore integration read-only, fixture/mock by default, and live mode explicitly gated.
2. Use synthetic placeholders only; never include credentials, private IDs, URLs, logs, or data.
3. Run `make quality`.
4. Update documentation and tests for behavior or safety-contract changes.

Do not add Procore mutations, external infrastructure, or production claims without an explicitly
reviewed project phase. Contributions follow the [Code of Conduct](CODE_OF_CONDUCT.md).
