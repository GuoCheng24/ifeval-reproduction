# Redaction of a machine name from the sealed pre-registrations

**2026-09-23.** One machine name was removed from the pre-registration(s) below,
after they were published. This file exists because the alternative — changing a
sealed document quietly — would destroy the only thing a seal is for.

## What was changed

A single six-character token naming a compute node was replaced by a
six-character neutral label. **Nothing else.** The replacement is the same length
as what it replaced, so every other byte in each file is at the byte offset it
was at before, and the number of differing bytes is exactly the token length
times the number of occurrences:

| file | occurrences | bytes changed | expected | length before = after |
|---|---|---|---|---|
| `prereg/PREREG_run3.md` | 6 | 36 | 6 × 6 = 36 | yes |
| `prereg/PREREG_run3_addendum_3d.md` | 1 | 6 | 1 × 6 = 6 | yes |

## Hashes

| file | sealed as | now |
|---|---|---|
| `prereg/PREREG_run3.md` | `f414c8665a2d5a6c945a2a000ff9de219a9166c9919a7a46c1c3ae7439a38992` | `56a2b22e39b7741d14fb1817ba7395cb99305b94b291411f0dd6322afa5bff97` |
| `prereg/PREREG_run3_addendum_3d.md` | `f364b429304ec1064e28c25c058901c7a0a88093026e8b9a4b51dd582b319148` | `9d860e6013fad43a04401470f35facead864130447f0d616e7c687e16276e8be` |

Anyone holding the original bytes can confirm the first column. The analysis
scripts assert the second.

## What was not changed

No sentence, number, threshold, stopping rule, pre-stated interpretation or
date. The scientific content of a pre-registration is what makes it worth
sealing, and none of it is a machine name.

## The history was rewritten too

**2026-09-23.** The pre-redaction bytes are no longer in this
repository's git history either. Every commit was rewritten to remove the same
token class and the result was force-pushed, after a full backup and after
verifying two things:

- **the working tree is unchanged.** Every tracked file at `HEAD` hashes to
  exactly what it hashed to before the rewrite, so the seals above still hold —
  the rewrite touched only historical versions;
- **nothing remains.** A fresh clone from the remote finds no occurrence of the
  token class anywhere in the full history, and the sealed pre-registration
  still verifies against its recorded hash.

Every commit identifier changed, as it must. Anything that referred to an old
one — a fork, a bookmark, a link to a specific commit — needs to be re-fetched.

One caveat worth stating rather than hiding: a hosting platform can keep
unreachable objects addressable by their identifier for some time after a force
push, until its own collection runs. The identifiers in question were never
published anywhere.
