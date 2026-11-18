# Changes from contract.yaml to revised.yaml

Field names and values are unchanged, because the evaluation annotations use them (guideline 14).

## Values (guidelines 1–4)
- Every value of every field now has a comment saying what in a report leads to it. The instructions repeat the definitions so the model sees them.
- The two half values now have a stated boundary: exactly 50% is `fifty_or_greater`.
- `depth_basis` now has an order of precedence for when several bases apply. `descriptive_other`, which was previously undefined, is now defined: wording that names no half and no inner or outer third, or a depth with no thickness it can be combined with.
- Label `cannot_be_determined` is separated from `not_applicable`. A report that says nothing about the specimen, or gives only a stage, is `cannot_be_determined`, never `not_applicable`.
- `adenomyosis_relation`: `present_uninvolved_by_carcinoma` (adenomyosis listed as a separate finding) and `cannot_be_determined` (relation left open) are now told apart.
- Confidence values `high` / `medium` / `low` are now defined.
- Known limits, kept because the annotations use these values: `other_or_not_stated` and `none_stated` each merge two meanings, and `not_mentioned` covers both "not mentioned" and "stated absent". The comments say so.

## Instructions (guidelines 5–9)
- I mapped the kinds of wording found in the 20 sample reports to values: checklist half choices, older "half or less" categories, thirds, depth with thickness, depth alone, descriptive words, stage codes, cassette lists that mention full-thickness sections, and cervical or lower-segment invasion.
- Removed example phrases that also appear in the sample reports, and replaced them with made-up ones. I checked the new ones against the reports.
- Stage codes may no longer decide depth: IB means under half in older editions and half or more from 2009. A stage line that states depth in words is a last resort.
- Added rules for combining numbers: only from the same statement or synoptic block, convert units, use the largest value of a range, never pair a gross number with a microscopic one, and a computed fraction is not a stated one.
- Added an order of precedence for conflicting statements (amendment > final diagnosis/synoptic > microscopic comment > gross > frozen section/original/prior biopsy). `unresolved_conflicts` now records only statements that would change the label or the percent value.
- Quoting: say what each field quotes, copy OCR errors verbatim, and make each quote unique, because some reports repeat a page and an ambiguous quote is refused. Quote the value line, not the heading. Explicit bases quote both numbers.
- Made the reading instructions work in both modes, by removing the reference to an `inventory` tool. Kept the CAP Note E measurement rules, including MELF/desmoplasia and the junction guidance, in shorter form.

## Rules (guidelines 10–13)
- Added `invasion_percent_without_invasion`: any label other than `present` requires percent `not_applicable`.
- Added `committed_basis_requires_half`: explicit or estimated basis requires `less_than_50` or `fifty_or_greater`.
- Added `full_thickness_requires_outer_half`: `descriptive_full_thickness` requires `fifty_or_greater`.
- Added `uncommitted_basis_has_no_half`: `descriptive_other` or `none_stated` requires `cannot_be_determined` or `not_applicable`.
- Removed `invasion_percent_requires_hysterectomy`. It became redundant, because a half now requires `present`, and `present` requires a hysterectomy.
- Every combination the instructions allow passes all the rules. The new rules are not yet tested with `check_answer` (one passing and one failing submission each). Do that before a run, and count refusals by signature afterwards, since in one_shot mode a refusal abstains the patient.

## Note on guideline 15
This version changes definitions, instructions and rules together, so a change in answers cannot be traced to one of them. Rerun the baseline on the new digest, and repeat runs before judging the change (guideline 16).
