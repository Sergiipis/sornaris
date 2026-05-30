# Security Policy

## Supported versions

`sornaris` is pre-1.0. Security fixes are made on the latest released
version (`0.x`). Please upgrade to the newest release before reporting.

## Reporting a vulnerability

Please report security issues **privately**, not in public issues:

1. Open a GitHub private security advisory at
   `https://github.com/Sergiipis/sornaris/security/advisories/new`, or
2. Contact the maintainer via the email on their GitHub profile.

You'll get an acknowledgement as soon as the report is reviewed, and a fix or
mitigation plan once the issue is confirmed.

## Scope

`sornaris` is a local developer tool with no runtime dependencies. The most
relevant security considerations:

- **Provider credentials.** The real providers read API keys from environment
  variables (`OPENAI_API_KEY`, `ANTHROPIC_API_KEY`). Keys are sent only to the
  configured `base_url` over HTTPS and are never written to the cache, reports,
  or logs. Reports contain version ids, scores, and probe steps — not prompts,
  outputs, or keys.
- **Untrusted input files.** `prompts` / `models` / `evals` JSONL files and the
  sqlite cache file are read from paths you provide; treat them as you would any
  local input.
- **Outbound requests.** Only the provider you select makes network calls, to
  its `base_url`. The offline `fake` provider makes none.

## What is not in scope

- The behaviour or safety of the LLMs you point the tool at.
- Third-party endpoints reachable via a custom `base_url`.
