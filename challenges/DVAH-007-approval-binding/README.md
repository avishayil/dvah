# DVAH-007 — You Approved What?

**Broken invariant:** INV-03 — approval binds to the resolved `action_hash`, not the
plan.

## The bug
`vulnerable/approvals.py` issues a grant bound to a constant "plan id" and validates
any grant regardless of the action. An approval obtained for deleting `/tmp/old.log`
is then reused to authorize deleting `/prod/customer.db`.

## Your job
Bind each approval to the exact resolved action. The reference fix is in `solution/`.

## Prove it
```
dvah test DVAH-007
```
Passes only when the approval that authorizes each action is bound to that action's own
hash — a stale, mismatched approval must never authorize a different action.
