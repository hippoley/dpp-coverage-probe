# DPP Coverage Probe

Public, reproducible observations of pinned upstream Digital Product Passport validators.

## Current scope

The initial GitHub Actions bootstrap executes a pinned OpenDPP AAS structural validator against a baseline and a deliberately mutated sample, then repeats the same observations in a separately cloned checkout. Artifacts include actual process outputs, exit codes and SHA-256 digests. A structural validator accepting a semantic mutation **does not establish a security vulnerability or a violation of the validator's stated scope**.

Gate B is considered **unverified** unless a real Actions run and its evidence are inspected. See `.github/workflows/gate-b.yml` for the executable observation workflow. Earlier extended local implementations and 17-story audits remain in the previous project deliverables and have not yet been imported wholesale into this GitHub repository.

## First public execution (2026-10-09)

- [Run #1 — diagnostic failure](https://github.com/hippoley/dpp-coverage-probe/actions/runs/37903800065): both upstream clones and npm installs succeeded; acceptance codes were 0/0. Replay was incorrectly requiring identical raw output bytes across different input filenames.
- [Run #2 — successful real upstream observation](https://github.com/hippoley/dpp-coverage-probe/actions/runs/37904023732): `REPLAY_OUTCOME_MATCH`; both observed validator exit codes were `baseline=0` and `mutant=0`. The Action uploaded `gate-b-real-observation` with independently recorded raw stdout/stderr and SHA-256 hashes.
- Pinned upstream commit: `20211ecc2b63eb7664c571a8d629aeeed364491e`.
- Artifact ID for successful run: `11604095485` (GitHub retains it under its configured retention policy).

**Interpretation:** Two independently cloned and installed copies running on the **same GitHub Runner** agreed on the validator's acceptance/rejection behavior. This is a real public *structural-validation observation*, not an AAS semantic conformance verdict, production interoperability certification, byte-identical output proof, or an independent third-party audit. In particular, the acceptance of a duplicated `idShort` by a JSON Schema validator is not proof of a bug against its declared scope.

**Remaining User Story gap:** The extended 17-story local implementation has not yet been fully committed to this repository; the initial public run exercises a standalone upstream observation bootstrap only. Cross-machine replay, independent reviewer inspection, CIRPASS-2 execution, and external adoption are not yet verified.

## Independent acceptance integrated (2026-10-09)

- [Gate B Run #37907736359](https://github.com/hippoley/dpp-coverage-probe/actions/runs/37907736359) **succeeded** on commit `aaa4eb3101b6ff0dd95a2d2e40e6a543414d75f6`.
- Both pinned OpenDPP checkouts ran; the standalone `product_acceptance.py` checked input hashes, encoded raw output hashes, validator command-to-input binding, fixed upstream commit and outcome-level replay equivalence.
- The CI also ran seven independent acceptance regression tests including tampered input, altered replay outcome, corrupt stdout, missing execution, duplicate JSON keys and symlink input.
- The GitHub Artifact `gate-b-real-observation` (ID `11605890099`, ZIP SHA-256 `b1ae145cd5fbc4b383e4671480f59dfc1f77b7ce44ade9517fad76f1599091af`) contains `report.json`, original primary/replay evidence inputs, and `independent-acceptance.json`.
- The validator accepts both tested inputs (exit code 0 for baseline and mutant). This establishes a reproducible *structural validator observation*, **not a semantic AAS conformance result**. Both checkouts ran on the same GitHub Actions machine; no independent organization has reviewed the result.

The previous failed [Run #37907647029](https://github.com/hippoley/dpp-coverage-probe/actions/runs/37907647029) exposed a positive-test fixture with a wrong directory layout; this was fixed without relaxing the production acceptance policy.
