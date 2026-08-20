# Contributing to DVAH

Thanks for your interest! Contributions — especially **new labs and invariants** — are
very welcome.

## Getting set up

```bash
uv venv && uv pip install -e ".[dev,services,web]"
uv run pytest tests/ -m "unit or integration"
cd web && npm install && npm test
```

Read [`CLAUDE.md`](./CLAUDE.md) for the architecture, conventions, and command reference,
and [`docs/ARCHITECTURE.md`](./docs/ARCHITECTURE.md) for the harness design.

## Ground rules

- **Immutability**: data models are frozen; never mutate — return copies.
- **Small, cohesive files**; keep the `harness/` (plumbing) vs `guardrails/` (controls)
  split intact.
- Every change ships with tests. Markers: `unit`/`integration` run in CI; `e2e` is manual
  and must stay out of CI. Keep the 80% coverage gate on `dvah` green.
- Model adapters must import without their SDK installed (lazy imports).

## Adding a lab

Follow the DVAH-001/002 pattern (see [`CLAUDE.md`](./CLAUDE.md) → "Adding a lab"):
a `scenario.yaml` overriding exactly one guardrail slot, `guardrails/vulnerable/` + hidden
`guardrails/solution/`, an `environment/`, `workflows/plans.yaml`, `evals/`
(functional/exploit/invariant/adversarial), and a
`walkthrough.yaml`. Tag invariant tests with `@pytest.mark.invariant("INV-0X")`. Verify the
lab is **red vulnerable / green solution**, including the adversarial suite.

## Pull requests

1. Branch from `main` and open a PR — `main` is protected, so you can't push to it directly
   (no force-pushes or deletions).
2. Keep the CI set green (`pytest -m "unit or integration"`, `npm test`, `npm run build`)
   and every lab's reference solution passing (`make labs`).
3. Use conventional commit messages (`feat:`, `fix:`, `docs:`, `test:`, `refactor:`).
4. Describe the change and its test plan in the PR.

To merge, a PR must: pass the required checks (**`test`**, **`web`**, and the
**dependency-review** check), get **one approving review from a code owner**, have all
conversations resolved, and keep **linear history** (rebase, don't merge-commit).

### Contribution safety

CI for pull requests from forks runs with a **read-only token and no repository secrets**,
so the untrusted lab code a PR might add can't exfiltrate anything or write back to the
repo. CodeQL and dependency review run on every PR.

## Reporting security issues

See [`SECURITY.md`](./SECURITY.md). Note DVAH intentionally contains vulnerable *lab* code
— those are features, not bugs. Report issues in the **harness/runtime/web app** itself.
