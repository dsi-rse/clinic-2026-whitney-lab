# Issue #42: close two gaps in the task contract's depth rules

Issue #26 traced two disagreements to gaps in
`tasks/endo_myometrial_invasion.yaml`:

- **TCGA-A5-A0GJ.** The only depth statement in the report places the
  carcinoma in the endometrium and in the superficial myometrium at once, with
  no number, half or invasion word. The contract has no rule for it. The model
  answers `present` / `less_than_50`; the annotator answered
  `cannot_be_determined`.
- **TCGA-A5-A0GR.** One run divided a microscopic depth (page 1) by a gross
  wall thickness (page 2), got exactly 50%, and flipped to `fifty_or_greater`.
  The contract allows a fraction from any depth and any thickness.

Plus `descriptive_other`, an allowed `depth_basis` value with no definition.

## Rulings (Claude's judgement, not the mentor's)

Issue #42 asked for mentor rulings. The student (kh) asked Claude to decide
after reviewing the case instead. These are those decisions and the reasons.

**A0GJ: the annotation stands (`cannot_be_determined`).** The statement both
confines the carcinoma to the endometrium and says it involves the superficial
myometrium. Those are the two label values `not_identified` and `present`.
Tumour at an irregular endomyometrial junction is often described this way
without being true invasion (CAP's own note on irregular junctions), so neither
reading is the definitive one. The report's other myometrium statement is a
separate bullet about background myometrium and settles nothing (offsets
`2060-2083`). Where invasion *is* stated, wording that limits it to the
superficial myometrium is read as `less_than_50`. The annotator did so on 6 of
the 7 annotated patients with a "superficial" statement that has an invasion
word and no number; the seventh, TCGA-A5-A1OG, has a stated fraction elsewhere
(`annotator_labels.csv` in the scan folder below). SEER registry practice reads "superficial" the same way.

**A0GR: a fraction needs a depth and a thickness from the same section.** The
microscopic depth and the gross thickness come from different examinations, and
the gross examination itself reports no invasion. The gross thickness is also
smaller than the endometrial thickness beside it, which is implausible. So the
fraction should not be built. Without a usable pair, the answer comes from the
descriptive wording (`less_than_50`, `estimated_without_number`), which matches
the annotation. A constructed fraction must quote both numbers.

**`descriptive_other` is defined**, not removed: words that describe invasion
of the myometrium but settle neither a half nor full thickness. It goes with
`myometrial_invasion_percent` `cannot_be_determined`. The annotations use it
twice, both times with depth `cannot_be_determined`.

## Which patients A0GJ's wording touches

From `results/2026-11-17_165707_extent_scan/scan_summary.csv`, over all 546
reports:

- **A0GJ is the only report with its whole-report pattern** (a myometrium
  statement with extent wording, and nothing about the myometrium anywhere that
  has an invasion word, half, number, depth or thickness).
- 22 more reports (9 annotated) have an A0GJ-type statement, but another
  statement in the report may settle depth.
- 38 reports (10 annotated) have extent wording with an invasion word and no
  number ("superficial invasion"-type statements).

`extent_patients.csv` lists all 58 with offsets. The 18 annotated ones are in
the comparison. The 40 unannotated ones were in the first run's roster but were
dropped to save time: with no annotation they could only show whether answers
moved, not whether they were right.

## What changed in the contract

`contracts/new.yaml` is `contracts/old.yaml` (= `tasks/endo_myometrial_invasion.yaml`
at `ad531ff`) with:

1. comments defining each `depth_basis` value, including `descriptive_other`;
2. in the instructions: superficial-limited wording counts as
   `estimated_without_number`; `descriptive_other` goes with percent
   `cannot_be_determined`;
3. a paragraph allowing a worked-out fraction only from a same-section depth
   and thickness, ruling out an implausible thickness, and requiring both to be
   quoted under `depth_basis`;
4. a paragraph sending a statement that both confines the carcinoma to the
   endometrium and places it in the myometrium, with nothing else to settle it,
   to label `cannot_be_determined`;
5. checklist item 3 now checks the fraction's two numbers come from one section.

`diff contracts/old.yaml contracts/new.yaml` shows all of it. No rule changed.
OncoTrace rules can only test field values and list lengths, so neither "quote
the thickness too" nor "this wording means cannot_be_determined" can be a rule.
Enforcing the first needs an OncoTrace change (a minimum quote count per answer
value, or separate depth and thickness fields).

Neither report's wording is used as an example, but items 3 and 4 describe
each report's situation closely. The scan below found no other report with
A0GJ's pattern, so item 4 cannot be shown to generalise here.

## Pass bars (written before the runs)

- **A0GJ:** the new contract answers label `cannot_be_determined` at
  temperature 0; the old one answers `present`.
- **A0GR:** over 20 repeats at temperature 1.0, the new contract gives no
  `fifty_or_greater` and no quote of the gross thickness (`2093-2128`). If the
  old contract also gives none, the result is inconclusive for the flip (the
  earlier rate was 2 in 9 on the cluster setup).
- **No collateral change:** on annotated patients with a definite half and no
  extent wording (`unambiguous_annotated`), the number whose invasion or depth
  answer changes from old to new is no larger than the old-vs-old noise floor.
- **Legitimate fractions:** TCGA-A5-A0GA, 2E-A9G8, 5B-A90C, A5-A0GW keep their
  old answer, and the quotes behind the fraction come from one section.
- **Agreement:** reported per field for all annotated, development and
  held-out AJ patients, against the always-commonest baseline. No pass bar:
  the contract is not expected to move overall agreement much.

## Results against the pass bars

All numbers are from `results/2026-11-17_221246_compare/` (file named in
brackets). Model, provider and run folders are in its `provenance.json`.

- **A0GJ: met** (`answers.csv`). New contract: `cannot_be_determined`,
  percent `not_applicable`, as annotated. Old contract, both runs: `present`,
  `less_than_50`.
- **A0GR flip: met** (`a0gr_repeats.csv`). `fifty_or_greater` in 8 of 20
  old-contract repeats, 0 of 20 new. The new contract answered `less_than_50`
  (the annotation) in 19 of 20. At temperature 0 the flip also showed up once:
  `old_t0ann_b` answered `fifty_or_greater`, `old_t0ann_a`
  `cannot_be_determined`, `new_t0ann` `less_than_50` (`answers.csv`).
- **A0GR gross-thickness quote: not met** (`a0gr_repeats.csv`). The new
  contract still quoted the gross thickness in 8 of 20 repeats (old: 17 of 20).
  It built a fraction in 2 of 20 (old: 12 of 20), one of them with only one
  quote, but never reached `fifty_or_greater`. The table does not say which
  field the gross quote sat under, so whether it was cited as the rejected
  thickness is unchecked.
- **No collateral change: met** (`changes.csv`). On the 37
  `unambiguous_annotated` patients, old-vs-old changed 2 (A0GR, A0GU) and
  old-vs-new changed 1 or 2 (A0GR, and A0GU against `old_t0ann_b`). A0GU
  flipped to `fifty_or_greater` in `old_t0ann_b` only (annotated
  `less_than_50`); that may be the same depth/thickness mistake but has not
  been checked.
- **Legitimate fractions: met** (`fraction_patients.csv`). All four keep
  `less_than_50` in all three arms. Under the new contract all four quote one
  section by the proximity heuristic; under the old one, TCGA-5B-A90C also
  quoted a page-3 passage in both runs. All four are annotated
  `cannot_be_determined` (#18), so they count as `over_committed` in the
  agreement table under every contract.
- **Agreement** (`agreement.csv`, 66 annotated). Correct out of 66, old a /
  old b / new / always-commonest: invasion 63 / 63 / 64 / 60; percent
  52 / 51 / 54 / 31; depth basis 37 / 37 / 39 / 32. On the 17 held-out AJ
  patients all three arms are identical (17, 16 and 15 correct).

**Limits.** One model and provider; one new-contract run at temperature 0, so
there is no new-vs-new noise floor; 20 repeats per contract. The contract
edits were written with A0GJ and A0GR in view, so their improvement on those
two is expected, and A0GJ's instruction cannot be shown to generalise (no other
report has its pattern). The rulings are Claude's, not the mentor's. The
same-section check is a proximity heuristic.

## Files

| File | What it is |
|---|---|
| `scan_extent_wording.py` | Scans all 546 reports for A0GJ-type wording |
| `make_rosters.py` | Builds the run rosters from the scan |
| `contracts/old.yaml`, `contracts/new.yaml` | The two contracts compared |
| `configs/*.yaml` | OpenRouter run configs, one per contract and temperature |
| `rosters/roster_compare.csv` | 66 annotated + 40 scan patients; used only by the abandoned arm `old_t0_a` |
| `rosters/roster_a0gr.csv` | TCGA-A5-A0GR alone (temperature-1.0 repeats) |
| `run_arms.sh` | Runs the extractions, one new run folder per arm |
| `analyze_runs.py` | Builds the comparison tables and results README |
| `results/` | Timestamped results folders |

## How to rerun

From a fresh clone, with the data built by `scripts/endometrial_data/download.sh`
(see `docs/local-data.md`), Python with `pandas`, `pyyaml` and `python-dotenv`,
and an OncoTrace checkout at `d4b7fd3` or later:

```bash
export PYTHONPATH=src
python experiments/issue42_depth_rules/scan_extent_wording.py \
  --reports data/endometrial/documents/ucec_pathology_report.jsonl
python experiments/issue42_depth_rules/make_rosters.py \
  --scan experiments/issue42_depth_rules/results/<scan folder>
```

The scan takes seconds and reproduces the committed scan tables exactly. The
model runs need an OpenRouter key, cost under $1, and take about 3 hours at 3
workers. Run them under `caffeinate -i` on a Mac: a first attempt, `old_t0_a`
on the 106-patient roster, hung after 26 patients when the laptop slept. Its
folder is kept as a record and is not used.

```bash
set -a; source .env; set +a
export ONCOTRACE=<oncotrace checkout> PYTHON=python
WORKERS=3 caffeinate -i bash experiments/issue42_depth_rules/run_arms.sh runs <date> old_t0ann_a new_t0ann old_t0ann_b
for i in $(seq -w 1 20); do echo old_t1_rep$i; echo new_t1_rep$i; done |
  WORKERS=1 xargs -P 3 -I{} bash experiments/issue42_depth_rules/run_arms.sh runs <date> {}
python experiments/issue42_depth_rules/analyze_runs.py --runs-dir runs --date <date> \
  --scan experiments/issue42_depth_rules/results/<scan folder>
```

Model outputs do not reproduce bit for bit. The analysis of a given set of run
folders does, in under a minute.

The run folders (`2026-11-17_issue42_*`, with their `.log` files, including
the unused `old_t0_a`) were made on a laptop and copied on 2026-11-20 to
`/net/spaces/annawoodard/oncotrace/workspaces/khyatt/runs/`, group
`__oncotrace`, group-readable. File counts and checksums matched the laptop
copies. To rerun the analysis from them, pass that folder as `--runs-dir` with
`--date 2026-11-17`. The `not_shared` acknowledgements in the committed
`provenance.json` files name this folder. No teammate has yet confirmed they
can open it.
