# Reviews

**Location**: `docs/reviews/`

Point-in-time assessments: review briefs, audits, batch conformance passes. Each one records what was true on the day it was written and what it asked somebody to decide.

## Naming

`<subject>.md`. No date in the filename. **The date lives inside the document, in a status line near the top**, giving created, updated, and where the work stands. Add a date to a filename only when a second review of the same subject exists and the two must be told apart.

## These are records, not live documents

A review states findings as of its date. When the code moves on, the review is not updated to match.

**Broken references are the exception, and get fixed.** A path that no longer resolves is rot, not history: repoint it, or mark it `(lost)`.

If a review's findings need tracking to a conclusion, that belongs in a work package or a GitHub issue, not in edits to the review.

## Not here

Ceremony records live in `docs/ceremonies/`.
