<!-- IWALLET PR checklist (per readiness report + project-context NFR29). -->

## Story / FR reference

- Story: <!-- e.g. 1.2 -->
- FRs / NFRs covered: <!-- e.g. FR7, NFR12 -->

## Summary

<!-- 2-3 sentences: what & why. Skip "what" if diff is obvious; lean on "why". -->

## Acceptance criteria

- [ ] All ACs from the story spec are satisfied
- [ ] Tests added / updated (≥ 80% on services & selectors)
- [ ] `ruff check` + `ruff format --check` + `djlint --check` green locally
- [ ] No `print()`, no `float` for money, no `import *`
- [ ] Migration reviewed (if any model change)
- [ ] Manual smoke test on Telegram WebApp iOS + Android (if UI change)

## Notes / trade-offs

<!-- Anything reviewer should know — deliberate divergences, deferred work, etc. -->
