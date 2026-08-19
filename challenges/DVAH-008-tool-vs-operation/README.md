# DVAH-008 — Same Tool, Different Operation

**Broken invariant:** INV-13 / tool-vs-operation — authorize the specific operation,
not the tool name.

## The bug
`vulnerable/policy.py` authorizes on the operation **namespace**: if the agent holds
any `github` capability at all, every `github` operation is allowed. An agent with only
`github:issue.read` can therefore delete a repository.

## Your job
Authorize the specific operation against the exact capability held. The reference fix is
in `solution/`.

## Prove it
```
dvah test DVAH-008
```
Passes only when `repository.delete` is denied for an agent that holds only
`issue.read`, and the repository survives.
