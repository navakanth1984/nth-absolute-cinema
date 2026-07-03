# NAC Architecture Fingerprint — v1.0

**Freeze date:** 2026-07-03
**Purpose:** Pin exactly which frozen architecture any given piece of Sprint 1+ code
was built against — the architectural equivalent of a lockfile. If this fingerprint
doesn't match the `docs/specs/v1/` tree a change is being reviewed against, the specs
moved out from under the code and this document (or the code) needs updating first.

## Document versions

| Document | Version |
|---|---|
| MANIFESTO.md | v1.0 |
| CREATIVE_GRAPH_SPEC.md | v1.0 |
| COMPILER_ABI.md | v1.0 |
| PACK_ABI.md | v1.0 |
| NAC_PACKAGE_SPEC.md | v1.0 |
| EVENT_SPEC.md | v1.0 |
| PLUGIN_ABI.md | v1.0 |
| WORKSPACE_SPEC.md | v1.0 |
| COMPUTE_MANAGER_SPEC.md | v1.0 |
| MODULE_BOUNDARIES.md | v1.0 |
| REPOSITORY_INTERFACES.md | v1.0 |
| EXTENSIBILITY.md | v1.0 |
| VERSIONING_POLICY.md | v1.0 |
| SPRINT0.5-VALIDATION.md | v1.0 |
| SPRINT0_FREEZE.md | v1.0 |

## Per-file SHA-256 (content hash of each frozen document)

```
81a2a0692bcfb86261b37104a6feb2c79b0f61458561bf184b184fa7662f6739  COMPILER_ABI.md
8d9abf6ae62123ba892ccd61785660125b509d1ceb48976b111d5c5e2f083e16  COMPUTE_MANAGER_SPEC.md
6b24f0de4b7ab372ede0218c01d9c0a029f4995dcaf806c591a0140e9d561508  CREATIVE_GRAPH_SPEC.md
8040dc9b857639fe1b1ce7e1fcdaed656172b8e691ffcd599a6771bc100f0297  EVENT_SPEC.md
790fc3e75cdca74931e27913bf95d82247d9efa5c3eef0e56a827f03442170fe  EXTENSIBILITY.md
6e5ca3bc51672735e8729d521376756c07cc9ba5b9025fca0e9412fa7c0919c6  MANIFESTO.md
6dd88b8b1a327fb222f5b0bae7cd3806fc69a7c2fdc4218272b24f82262878a8  MODULE_BOUNDARIES.md
75bdb10229a46aa3c50dd58e36b27a4a71f769c2089388e22dac651e923d75d8  NAC_PACKAGE_SPEC.md
67795913e00382eac562c43b9be24d60d72339b4fe29ab3bea86c53693b8b2e9  PACK_ABI.md
95dc769fe0fc9e2349764d7f6dfea6abe882b069d9663339cd53e8c5416c990b  PLUGIN_ABI.md
5f5713fac5145c1514e28b8a2323dd84784f78dadb0561201767a21f3665ceee  REPOSITORY_INTERFACES.md
abbb0cc00de8ca797636d6a3ba8943bffcf9ac9b0e844642e2ee37b364888f6d  SPRINT0.5-VALIDATION.md
93c779e7c3e8847a0f03f72eab1479025e152825c1cb1390672ff2fda9158c48  SPRINT0_FREEZE.md
56217ab1b64847d43fe0ebe88fa3195f515a5b889d82bcf2b312751def8bf243  VERSIONING_POLICY.md
c55bf5863af12559d2c7f08b895fa687b9fba7b396a020cd3f5de65bdf440aa6  WORKSPACE_SPEC.md
```

(Computed via `sha256sum *.md` over the 15 files in `docs/specs/v1/` at freeze time.
`ARCHITECTURE_FINGERPRINT.md` itself is excluded from its own hash set — it's the
manifest, not a governed spec.)

## Combined architecture hash

Concatenation of the 15 files above, in the alphabetical `git ls-files` order shown,
piped through SHA-256:

```
30637b9993a94dd48c0058d53f57e30013a671a126b20d0a489bd3e37290e0c0
```

Regenerate with:
```bash
cd E:\nth-absolute-cinema\docs\specs\v1
cat COMPILER_ABI.md COMPUTE_MANAGER_SPEC.md CREATIVE_GRAPH_SPEC.md EVENT_SPEC.md \
    EXTENSIBILITY.md MANIFESTO.md MODULE_BOUNDARIES.md NAC_PACKAGE_SPEC.md \
    PACK_ABI.md PLUGIN_ABI.md REPOSITORY_INTERFACES.md SPRINT0.5-VALIDATION.md \
    SPRINT0_FREEZE.md VERSIONING_POLICY.md WORKSPACE_SPEC.md | sha256sum
```

## Rule

**Sprint 1 MUST target this fingerprint.** Any Sprint 1 code, test, or commit message
referencing "the frozen architecture" refers to this exact hash. If any file in
`docs/specs/v1/` changes (a MINOR or MAJOR bump per `VERSIONING_POLICY.md`), this
fingerprint document must be regenerated in the same commit — a stale fingerprint is
worse than no fingerprint, since it silently misrepresents what Sprint 1 code was
actually built against.
