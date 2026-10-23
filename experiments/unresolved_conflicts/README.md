# Unresolved conflicts

Investigation for issue #15: how the annotations (and later OncoTrace) handle
multiple or conflicting reports of myometrial invasion.

## Files

| File | What it is |
|---|---|
| `annotation_tables.py` | Reads `annotations/endo_myometrial_invasion` and writes the tables below to `results/` |
| `audit_14_patients.csv` | Hand-made audit of the 14 patients with an `unresolved_conflicts` note. The OncoTrace columns are still to fill in |
| `results/annotation_overview.csv` | One row per patient: her values, whether she wrote a note, and any percents found in her evidence |
| `results/percent_check.csv` | Patients with a number in the evidence, and whether her percent matches the worst case |
| `results/presence_vs_percent.csv` | Patients whose presence and percent labels do not fit together |
| `results/cannot_be_determined_breakdown.csv` | The `cannot_be_determined` percents, split by `depth_basis` and numbers found |

No report text is written; only values, counts and computed percents.

## Run it

```bash
make unresolved-conflicts
```

## Caveat

Percents are found by pattern matching on her evidence spans, so every row in
`percent_check.csv` with `matches_worst_case` False must be checked by hand. A
span that is cut off in the middle can give a wrong number.
