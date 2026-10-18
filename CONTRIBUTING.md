# Contributing

Report bugs with a minimal `.puml` example, include URL or source commit, renderer versions, expected output, and the actual diagnostic or SVG. Use the issue forms for reproducible bugs and feature proposals.

Keep Level 0 and Level 1 published signatures compatible. Use one shared core and sibling profile includes; official files must not import the experimental testing repository. Propose alternate notations and Level 2 in `ArmanAvanesyan/test` first.

Run `python3 scripts/check.py` with Python 3.10+ and Docker. The pinned image makes the local run equivalent to CI. Add behavioral fixtures when changing rendering, validation, or compatibility. Update the executable examples and matching README blocks together. Include representative SVG evidence in the PR.

After pushing, run `python3 scripts/check.py --remote-ref FULL_COMMIT_SHA` to exercise actual raw GitHub includes. No secret is required. CI performs this check for branches in the official repository; fork contributors can run it after maintainers make their commit available in that repository.

PRs should explain the diagram behavior before and after the change, identify any source migration, and report verification. Maintainers review and merge separately. Tags/releases are deliberate follow-up actions; submitting a PR never publishes a release. There is no automatic stale-issue closure policy.

Adapted from the contribution-guidance branch inspected during consolidation; its unimplemented automation policy was omitted.
