# Issue #42 contract comparison: 2026-11-17_221246_compare

Made 2026-11-17_221246 by `experiments/issue42_depth_rules/analyze_runs.py --runs-dir /Users/kadenhyatt/Desktop/Data_Clinic/clinic-2026-whitney-lab/runs --date 2026-11-17 --scan experiments/issue42_depth_rules/results/2026-11-17_165707_extent_scan`.

Temperature-0 arms: `old_t0ann_a`, `old_t0ann_b` (the same old contract twice,
to measure run-to-run noise) and `new_t0ann`, each on the 66
annotated patients, 18 of them flagged by the extent-wording scan. An
earlier arm, `old_t0_a` (106 patients), hung after 26 when the laptop slept;
its folder is kept as a record and not used.
A0GR repeats: 20 per contract at temperature 1.0. Model and provider are
in `provenance.json` (`runs.*.served_models`, `runs.*.providers`).

## Agreement with the annotations (annotated patients)

One row per arm; columns count patients out of `patients`. `over_committed`
means a definite value where the annotator said `cannot_be_determined` or
`not_applicable`; `abstained` means no accepted answer. `always_*` is the
baseline that always answers the field's commonest annotated value.

| field | subset | arm | patients | correct | wrong | over_committed | abstained |
|---|---|---|---|---|---|---|---|
| myometrial_invasion | annotated_all | old_t0ann_a | 66 | 63 | 0 | 3 | 0 |
| myometrial_invasion | annotated_all | old_t0ann_b | 66 | 63 | 0 | 3 | 0 |
| myometrial_invasion | annotated_all | new_t0ann | 66 | 64 | 0 | 2 | 0 |
| myometrial_invasion | annotated_all | always_present | 66 | 60 | 3 | 3 | 0 |
| myometrial_invasion_percent | annotated_all | old_t0ann_a | 66 | 52 | 2 | 12 | 0 |
| myometrial_invasion_percent | annotated_all | old_t0ann_b | 66 | 51 | 3 | 12 | 0 |
| myometrial_invasion_percent | annotated_all | new_t0ann | 66 | 54 | 1 | 11 | 0 |
| myometrial_invasion_percent | annotated_all | always_less_than_50 | 66 | 31 | 20 | 15 | 0 |
| depth_basis | annotated_all | old_t0ann_a | 66 | 37 | 29 | 0 | 0 |
| depth_basis | annotated_all | old_t0ann_b | 66 | 37 | 29 | 0 | 0 |
| depth_basis | annotated_all | new_t0ann | 66 | 39 | 27 | 0 | 0 |
| depth_basis | annotated_all | always_explicit_fraction_or_percentage | 66 | 32 | 34 | 0 | 0 |

## Held-out AJ patients only

Annotated after the contract was written (#27, #29, #37, #40), so the only
subset here that is not optimistic by construction.

| field | subset | arm | patients | correct | wrong | over_committed | abstained |
|---|---|---|---|---|---|---|---|
| myometrial_invasion | held_out_aj | old_t0ann_a | 17 | 17 | 0 | 0 | 0 |
| myometrial_invasion | held_out_aj | old_t0ann_b | 17 | 17 | 0 | 0 | 0 |
| myometrial_invasion | held_out_aj | new_t0ann | 17 | 17 | 0 | 0 | 0 |
| myometrial_invasion | held_out_aj | always_present | 17 | 16 | 1 | 0 | 0 |
| myometrial_invasion_percent | held_out_aj | old_t0ann_a | 17 | 16 | 1 | 0 | 0 |
| myometrial_invasion_percent | held_out_aj | old_t0ann_b | 17 | 16 | 1 | 0 | 0 |
| myometrial_invasion_percent | held_out_aj | new_t0ann | 17 | 16 | 1 | 0 | 0 |
| myometrial_invasion_percent | held_out_aj | always_less_than_50 | 17 | 8 | 8 | 1 | 0 |
| depth_basis | held_out_aj | old_t0ann_a | 17 | 15 | 2 | 0 | 0 |
| depth_basis | held_out_aj | old_t0ann_b | 17 | 15 | 2 | 0 | 0 |
| depth_basis | held_out_aj | new_t0ann | 17 | 15 | 2 | 0 | 0 |
| depth_basis | held_out_aj | always_explicit_fraction_or_percentage | 17 | 14 | 3 | 0 | 0 |

## Patients whose invasion or depth answer changed

`old_t0ann_a vs old_t0ann_b` is the noise floor: the same contract run twice.
`unambiguous_annotated` = annotated with a definite half and not flagged by
the scan.

| comparison | subset | patients | changed |
|---|---|---|---|
| old_t0ann_a vs old_t0ann_b | annotated | 66 | 2 |
| old_t0ann_a vs old_t0ann_b | unambiguous_annotated | 37 | 2 |
| old_t0ann_a vs old_t0ann_b | scan_touched_annotated | 18 | 0 |
| old_t0ann_a vs old_t0ann_b | held_out_aj | 17 | 0 |
| old_t0ann_a vs new_t0ann | annotated | 66 | 2 |
| old_t0ann_a vs new_t0ann | unambiguous_annotated | 37 | 1 |
| old_t0ann_a vs new_t0ann | scan_touched_annotated | 18 | 1 |
| old_t0ann_a vs new_t0ann | held_out_aj | 17 | 0 |
| old_t0ann_b vs new_t0ann | annotated | 66 | 3 |
| old_t0ann_b vs new_t0ann | unambiguous_annotated | 37 | 2 |
| old_t0ann_b vs new_t0ann | scan_touched_annotated | 18 | 1 |
| old_t0ann_b vs new_t0ann | held_out_aj | 17 | 0 |

## TCGA-A5-A0GJ

| field | value |
|---|---|
| patient | TCGA-A5-A0GJ |
| ann_myometrial_invasion | cannot_be_determined |
| ann_myometrial_invasion_percent | not_applicable |
| old_t0ann_a_myometrial_invasion | present |
| old_t0ann_a_myometrial_invasion_percent | less_than_50 |
| old_t0ann_a_depth_basis | estimated_without_number |
| old_t0ann_b_myometrial_invasion | present |
| old_t0ann_b_myometrial_invasion_percent | less_than_50 |
| old_t0ann_b_depth_basis | estimated_without_number |
| new_t0ann_myometrial_invasion | cannot_be_determined |
| new_t0ann_myometrial_invasion_percent | not_applicable |
| new_t0ann_depth_basis | none_stated |

## TCGA-A5-A0GR, 20 repeats per contract at temperature 1.0

`quotes_gross_thickness` counts repeats that quoted the gross myometrial
thickness statement (offsets 2093-2128). `explicit_fraction_with_one_quote`
counts repeats that claimed a fraction but quoted only one passage for it.

| contract | repeats | answered | fifty_or_greater | less_than_50 | percent_other | basis_explicit_fraction | explicit_fraction_with_one_quote | quotes_gross_thickness | depth_basis_values |
|---|---|---|---|---|---|---|---|---|---|
| old | 20 | 20 | 8 | 10 | 2 | 12 | 3 | 17 | explicit_fraction_or_percentage=12 estimated_without_number=5 descriptive_other=3 |
| new | 20 | 20 | 0 | 19 | 1 | 2 | 1 | 8 | estimated_without_number=17 explicit_fraction_or_percentage=2 descriptive_other=1 |

## Patients with a computable fraction (PR #18)

`same_section`: the depth_basis quotes sit on one page within
300 characters of each other (a proximity heuristic, not a parse of
the report's sections).

| patient | arm | ann_percent | myometrial_invasion_percent | depth_basis | depth_basis_quotes | quote_pages | same_section |
|---|---|---|---|---|---|---|---|
| TCGA-A5-A0GA | old_t0ann_a | cannot_be_determined | less_than_50 | explicit_fraction_or_percentage | 595-635 | 1 | True |
| TCGA-A5-A0GA | old_t0ann_b | cannot_be_determined | less_than_50 | explicit_fraction_or_percentage | 548-632 | 1 | True |
| TCGA-A5-A0GA | new_t0ann | cannot_be_determined | less_than_50 | explicit_fraction_or_percentage | 548-632 | 1 | True |
| TCGA-2E-A9G8 | old_t0ann_a | cannot_be_determined | less_than_50 | explicit_fraction_or_percentage | 2531-2556 2557-2585 | 2 | True |
| TCGA-2E-A9G8 | old_t0ann_b | cannot_be_determined | less_than_50 | explicit_fraction_or_percentage | 2531-2585 | 2 | True |
| TCGA-2E-A9G8 | new_t0ann | cannot_be_determined | less_than_50 | explicit_fraction_or_percentage | 2510-2585 | 2 | True |
| TCGA-5B-A90C | old_t0ann_a | cannot_be_determined | less_than_50 | explicit_fraction_or_percentage | 2415-2448 2449-2485 3247-3333 | 3 | False |
| TCGA-5B-A90C | old_t0ann_b | cannot_be_determined | less_than_50 | explicit_fraction_or_percentage | 2415-2485 3247-3333 | 3 | False |
| TCGA-5B-A90C | new_t0ann | cannot_be_determined | less_than_50 | explicit_fraction_or_percentage | 2415-2485 | 3 | True |
| TCGA-A5-A0GW | old_t0ann_a | cannot_be_determined | less_than_50 | explicit_fraction_or_percentage | 651-693 | 1 | True |
| TCGA-A5-A0GW | old_t0ann_b | cannot_be_determined | less_than_50 | explicit_fraction_or_percentage | 591-693 | 1 | True |
| TCGA-A5-A0GW | new_t0ann | cannot_be_determined | less_than_50 | explicit_fraction_or_percentage | 591-693 | 1 | True |

## Rerun

From the repo root, with the run folders in `<runs folder>`:

    PYTHONPATH=src python experiments/issue42_depth_rules/analyze_runs.py --runs-dir <runs folder> --date 2026-11-17 \
        --scan experiments/issue42_depth_rules/results/2026-11-17_165707_extent_scan

Takes under a minute and reproduces every CSV here exactly. The runs
themselves are model outputs and will not reproduce bit for bit.
