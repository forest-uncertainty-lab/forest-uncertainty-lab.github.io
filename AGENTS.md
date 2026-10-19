# Notes for coding agents

## Secrets

`.env` holds API keys (`FIRMS_MAP_KEY`). Never open, print, search, copy or summarize it, and never run a command that would show its contents. Variable names are in `.env.example`. To use the key, run `make refresh`; uv loads `.env` itself.

The ignore files (`.cursorignore`, `.geminiignore`, `.aiderignore`, `.codeiumignore`, `.aiignore`) and the Claude Code and Codex settings described in the README enforce this rule where the tool allows.

## Working here

- `make test` runs the unit tests. They use no network and no key.
- The design, plan and open items are linked from `README.md`. `docs/backlog.md` is the list of what is left to do.
