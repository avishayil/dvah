# DVAH-005 — Who Told You That?

**Broken invariant:** INV-05 — provenance (source/trust/tenant/timestamp) is preserved
through every hop.

## The bug
`vulnerable/provenance.py` drops the tag on `merge`, so after a tool call the agent no
longer knows where the data came from — any later policy decision that depends on
provenance is now blind.

## Your job
Preserve every provenance tag. The reference fix is in `solution/`.

## Prove it
```
dvah test DVAH-005
```
Passes only when a tool result's source is still recorded after it flows back.
