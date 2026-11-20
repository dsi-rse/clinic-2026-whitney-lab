# Changes from contract.yaml to revised.yaml

Field names and values are unchanged, so the human annotations still line up.
Only `rules` and `instructions` changed. The header and field comments are
kept as they were.

## Rules
- **Added `invasion_percent_without_invasion`.** If the label is
  `not_applicable`, `not_identified` or `cannot_be_determined`, then
  `myometrial_invasion_percent` must be `not_applicable`. The old contract only
  said this in the instructions. With the existing `invasion_percent_unresolved`
  rule, the label and the depth field now have to agree both ways.
- **Added `depth_basis_requires_half` and `full_thickness_requires_outer_half`.**
  A depth that rests on a number or on half-wording has to commit to a half.
  Full-thickness wording has to give `fifty_or_greater`.
- **Added `present_requires_depth_basis`.** A `present` label cannot have
  `depth_basis: none_stated`.
- **Added `adenomyosis_invasion_requires_depth`.** `invasion_within_adenomyosis`
  needs a depth answer, so the label has to be `present`.
- All the old rules are kept, with the same signatures.

## Instructions
Rewritten into one section per answer, with an explicit order of precedence:
- **Which statement decides.** A ranked order: amendment, then final
  microscopic diagnosis and synoptic, then gross, then frozen section. The
  example reports often disagree between the gross or frozen section and the
  final diagnosis, and between an original diagnosis and its amendment.
- **Each label value is defined.** This includes when to use
  `cannot_be_determined` (for example, a report that gives only a stage
  category).
- **Fixed ways to decide the half.** In order: a stated percentage, then
  depth ÷ thickness, then half-wording, then full-thickness wording, then
  "superficial" or "minimal". Exactly 50% counts as `fifty_or_greater`. Use
  the deepest value when a range is given. Use the thickness at the site of
  deepest invasion.
- **New list of numbers and words that are not depth.** Before, any "full
  thickness" counted as `fifty_or_greater`, and nearly every report uses
  "full-thickness section" for how the tissue was sampled. The list also
  covers percentages of surface involvement, solid growth, differentiation or
  staining, cervical stromal fractions, tumor size, serosal distance, and LVI.
- **New section on stage categories changing meaning.** In AJCC 6th / FIGO
  1988, T1b/IB means less than half. In AJCC 7th / FIGO 2009, it means half or
  more. Several example reports use the older edition. So the model never
  decides depth from a stage letter when the report describes the invasion,
  and does not count an older-edition stage that agrees as a conflict.
- **`depth_basis` now has a precedence order.** Explicit numbers come before
  other wording. It also says which basis to use for `not_identified`, a
  stage-only report, and garbled numbers.
- **Clearer `specimen_type`.** Every kind of hysterectomy counts, including a
  data form that names a surgical resection. A prior D&C in the history does
  not change it.
- **`adenomyosis_relation` values are defined.** Adenomyosis listed only as a
  background finding is `present_uninvolved_by_carcinoma`. Adenomyosis stated
  as absent is `not_mentioned`.
- **A firm rule for `unresolved_conflicts`.** List a passage only if, read on
  its own, it would change the label or the half. Small differences in depth
  within the same half are not listed. This makes the list consistent from one
  report to the next.
- **Guidance on quoting and OCR.** Quote verbatim with the OCR errors left in.
  Make each quote unique. Ignore TCGA review checklists and repeated pages.
- **New guidance on confidence levels**, and the final checklist now includes
  the stage-edition and consistency checks.
- The CAP measurement rules are kept: adenomyosis, MELF, LVI and exophytic
  tumors. "Compression without invasion" was added.
- No report text is copied in. The examples use made-up numbers and generic
  wording.
