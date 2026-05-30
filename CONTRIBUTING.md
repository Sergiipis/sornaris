# Contributing to Sornaris

Thanks for your interest! Bug reports, feature ideas, and pull requests are all
welcome.

## Development setup

```bash
git clone https://github.com/Sergiipis/sornaris
cd sornaris
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
```

## Before you open a PR

```bash
pytest -q                       # all tests pass
ruff check src tests examples   # lint clean
ruff format --check src tests examples  # formatting clean
```

- Keep the package **dependency-free at runtime** — the standard library only
  (sqlite for the cache is fine). Provider HTTP calls use `urllib`, not
  third-party SDKs.
- Add or update tests for any behaviour change; the suite is fast and offline.
- New providers should subclass `BaseProvider` and raise `ProviderError` on
  misconfiguration / transport failure.
- Run the `examples/` after changes that touch the engine — they double as
  end-to-end smoke tests.

## Pull request checklist

- [ ] Tests added/updated and passing
- [ ] `ruff check` and `ruff format --check` clean
- [ ] `CHANGELOG.md` updated under `[Unreleased]`
- [ ] Commits signed off (DCO): `git commit -s`

## Sign-off (DCO)

This project uses the [Developer Certificate of Origin](https://developercertificate.org/).
Add a `Signed-off-by` line to each commit with `git commit -s`, certifying you
wrote the patch or otherwise have the right to submit it under the MIT license.

## Reporting security issues

Please do **not** open a public issue for vulnerabilities — see
[SECURITY.md](SECURITY.md).
