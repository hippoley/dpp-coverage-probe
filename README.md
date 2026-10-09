# DPP Coverage Probe

Public, reproducible observations of pinned upstream Digital Product Passport validators.

## Current scope

The initial GitHub Actions bootstrap executes a pinned OpenDPP AAS structural validator against a baseline and a deliberately mutated sample, then repeats the same observations in a separately cloned checkout. Artifacts include actual process outputs, exit codes and SHA-256 digests. A structural validator accepting a semantic mutation **does not establish a security vulnerability or a violation of the validator's stated scope**.

Gate B is considered **unverified** unless a real Actions run and its evidence are inspected. See `.github/workflows/gate-b.yml` for the executable observation workflow. Earlier extended local implementations and 17-story audits remain in the previous project deliverables and have not yet been imported wholesale into this GitHub repository.
