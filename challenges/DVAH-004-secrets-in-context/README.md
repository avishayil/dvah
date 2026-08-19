# DVAH-004 — Context Full of Secrets

**Broken invariant:** INV-04 — credentials never enter model context; they are injected
at the tool layer only.

## The setup
The agent reads a file that happens to contain a credential, then that content is
compiled into the model's context.

## The bug
`vulnerable/secrets.py` does not redact secrets from the compiled model context, so the
credential is handed straight to the model.

## Your job
Redact every secret value (anywhere, including nested) before the model sees it. The
reference fix is in `solution/`.

## Prove it
```
dvah test DVAH-004
```
Passes only when the secret value never appears in the compiled model context.
