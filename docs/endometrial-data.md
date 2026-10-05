# Endometrial data and attribution

## Source

The task, CAP mapping, and 50 annotation JSON files come from
[Mariam Hassan's endometrial adaptation](https://github.com/marihassan/oncotrace-endometrial-adaptation),
source checkout `36f9ab8760dd785617f04753c4b16f7b5d603f34`.
Six path-filtered patches were replayed with `git am`, retaining Mariam's author
name/email and adding Claude's sign-off. Imported files match that checkout exactly.

| Source commit | Clinic commit |
|---|---|
| `9243b9a` | `981423d` |
| `1117373` | `4899ee1` |
| `e2ebffb` | `fa9d059` |
| `2a4a5ef` | `d1186c1` |
| `6728aaf` | `1822749` |
| `97cacd3` | `1be5862` |

Only the task, mapping, and patient annotations were imported. Historical viewer
settings and empty development-list metadata were excluded: they contain
account-specific paths or cannot establish that a case was never used in development.
The source checkout remains available as historical context.

## Inputs

The [run config](../config/endometrial.yaml) points at these existing read-only inputs:

```text
/net/spaces/annawoodard/annawoodard/endometrial-project/oncotrace-endometrial-adaptation/data/roster_ucec.csv
/net/spaces/annawoodard/annawoodard/endometrial-project/oncotrace-endometrial-adaptation/data/documents/ucec_pathology_report.jsonl
```

The store contains 546 documents for 546 patients across 31 tissue source sites.
Mariam's recorded GDC cohort has 560 cases; missing report delivery accounts for
the smaller usable set according to her notebook. Preserve the roster and store
for reproduction instead of silently replacing them with a new API query or OCR.
The prep scripts and full run outputs remain in the original adaptation/project.

Source text is exactly what offsets index. Do not normalize it after extraction
or overwrite a completed run's records. Put new outputs in a student-owned run root.

## Reference limitations

All 50 imported annotations are marked complete and use `traceview_annotation_v2`.
On October 5, 2026, all 255 saved evidence ranges were checked against the shared
store: 255/255 slices matched their saved text. Coordinate consistency does not
establish clinical support or completeness.

- 45 of the 50 annotated patients come from site A5.
- Invasion values: 45 `present`, 2 `not_identified`, 3 `cannot_be_determined`,
  and no `not_applicable` cases.
- Depth values: 23 `less_than_50`, 13 `fifty_or_greater`,
  11 `cannot_be_determined`, and 3 `not_applicable` cases.

A constant `present` prediction agrees with 45/50 invasion labels in this sample.
Report class supports and depth results alongside accuracy. Treat inherited cases
as development data until historical exposure is audited. Future confirmation
requires patient-disjoint reference collection and a documented clinical reviewer;
undergraduate interpretations do not become clinical gold labels.
