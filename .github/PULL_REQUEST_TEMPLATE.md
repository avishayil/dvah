## Summary

<!-- What does this PR change and why? -->

## Type

- [ ] feat
- [ ] fix
- [ ] docs
- [ ] test
- [ ] refactor
- [ ] new lab

## Checklist

- [ ] `uv run pytest tests/ -m "unit or integration"` passes (80% coverage gate holds)
- [ ] `make labs` passes (every lab's reference solution is green)
- [ ] `cd web && npm test && npm run build` passes (if frontend touched)
- [ ] e2e / live-model paths stay out of CI
- [ ] New behavior has tests; models remain immutable; files stay small and cohesive
- [ ] (new lab) red-vulnerable / green-solution incl. adversarial; `walkthrough.yaml` added

## Test plan

<!-- How you verified this. -->
