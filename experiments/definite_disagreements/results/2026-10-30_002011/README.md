# Issue #26: the two disagreements where the annotation is definite

Two rows, both the depth field. Every number below comes from a CSV or
`summary.txt` in this folder; where a judgement is mine rather than a
computation, it says so. Patients are TCGA IDs and passages are character
offsets into the patient's one stitched document. No report text appears here
([`leak_check.csv`](leak_check.csv): 9 of 9 files clean on a 7-word check
against the report store).

**Setup** ([`provenance.json`](provenance.json)): the four PR #21 runs, oncotrace
`fc3dadc`, contract `ba27b6ce50ad657b…`, GLM-5.3-Flash, agentic, temperature
0.0 / 1.0. 53 annotation files read. Nothing was re-run. Built from clinic-repo
commit `eaa9093` with no uncommitted files, and two consecutive runs produce
byte-identical tables.

## The table

| | `TCGA-A5-A0GJ` | `TCGA-A5-A0GR` |
|---|---|---|
| Field | `myometrial_invasion_percent` | `myometrial_invasion_percent` |
| Annotation | `not_applicable` | `less_than_50` |
| T0 / T1 r1 / r2 / r3 | `less_than_50` ×4 | `less_than_50` / **`fifty_or_greater`** / `less_than_50` / `less_than_50` |
| Confidence | high / medium / high / high | medium / medium / high / high |
| `depth_basis` claimed | `estimated_without_number` ×4 | `estimated_without_number` / `explicit_fraction_or_percentage` / `explicit_fraction_or_percentage` / `descriptive_other` |
| Runs agreeing with the annotation | 0 of 4 | 3 of 4 |
| Earlier reading | #15: vague depth wording, no number. PR #22: overconfident | #15: the report's pages conflict on whether there is invasion; the only answer that changed between runs |
| Earlier reading source | #15 comment; PR #18 `audit_14_patients.csv` group `vague_depth`; PR #22 `results/2026-10-27_182156_issue13/README.md` | #15 comment; PR #18 `audit_14_patients.csv` group `conflicting_depths`; issue #26 body |
| **Verdict** | **task contract doesn't say** | **model wrong** (`t1_r1` only) |
| Deciding offsets | `1801-1868`, `2060-2083` | `552-593`, `2093-2128`, `7196-7247` |
| Failure mode | — (not blamed; see below) | **fraction arithmetic wrong** |
| Proposed annotation label | none — the annotation is right | none — the annotation is right |
| Agree with the earlier reading? | **Yes, both**, and now with offsets behind them | **Partly** — the conflicting pages are real but are *not* what flipped the answer |

The same table with the full reasoning and mentor questions is
[`verdicts.csv`](verdicts.csv). The judgements come from
[`../../inputs/verdicts.csv`](../../inputs/verdicts.csv), which the script
validates: a verdict outside issue #26's four values, or a deciding offset
nobody actually cited, stops the run.

## Scope check

[`scope_check.csv`](scope_check.csv) groups **every** disagreement in PR #21's
200 patient-runs (50 patients × 4 runs × 2 fields) by annotation value:

| Field | Annotation | Run answer | Run rows | Owner |
|---|---|---|---|---|
| invasion | `cannot_be_determined` | `present` | 12 | issue #13 / PR #22 |
| depth | `cannot_be_determined` | `fifty_or_greater` | 20 | issue #13 / PR #22 |
| depth | `cannot_be_determined` | `less_than_50` | 24 | issue #13 / PR #22 |
| depth | `less_than_50` | `fifty_or_greater` | 1 | **issue #26** |
| depth | `not_applicable` | `less_than_50` | 4 | **issue #26** |

**There is no third row.** Issue #26's two rows are the complete set of
disagreements whose annotation is not `cannot_be_determined`.

Worth saying plainly: under the strictest reading of "definite" — a value that
asserts a clinical fact — only `TCGA-A5-A0GR` qualifies. `TCGA-A5-A0GJ`'s
`not_applicable` is a *field-does-not-apply* value, set because its invasion
label is `cannot_be_determined`. That is exactly why its verdict is about the
contract and not about who is right.

---

## `TCGA-A5-A0GJ` — task contract doesn't say

**What the report contains.** [`report_vocabulary.csv`](report_vocabulary.csv),
over the whole 12,974-character document:

| Wording class | Occurrences | Where |
|---|---|---|
| `invasion_word` | **0** | — |
| `half_word` | **0** | — |
| `full_thickness_word` | **0** | — |
| `depth_statement` | **0** | — |
| `thickness_statement` | **0** | — |
| `myometrium_token` | **2** | `1858`, `2073` — both page 1 |
| `confined_statement` | 1 | `1807` |
| `unquantified_extent` | 8 | one of them at `1846` |
| `fraction_or_percent` | 6 | `64`, `75`, `4463`, `7873`, `10844`, `12903` |

The word for invasion never appears in this report. Nothing states a half, a
fraction of thickness, a depth or a thickness. The myometrium is mentioned
exactly twice, and **both mentions are the two passages the model cited.** The
six `fraction_or_percent` hits sit at the top of the document and beside page
breaks (page 4 starts at `7881`, page 5 at `10852`), and none of them falls
inside any span the annotator or any run cited as depth evidence — check that
against [`evidence_spans.csv`](evidence_spans.csv), where every cited range for
this patient is listed.

**What the runs did** ([`evidence_spans.csv`](evidence_spans.csv),
[`run_answers.csv`](run_answers.csv)):

- All four runs read **100%** of the document. Nothing was missed.
- All four cite `1801-1868` as `depth_evidence`. That range is **byte-identical
  to the annotator's own `myometrial_invasion` span** — the model and the
  annotator read the same 67 characters and drew opposite conclusions.
- Its wording classes are `confined_statement`, `unquantified_extent`,
  `myometrium_token`, `endometrium_token`, and it holds **no measurement**. It
  carries a confinement claim and an unquantified-extent claim at once, which is
  PR #22's "one diagnosis line contradicts itself ~1800", now pinned exactly.
- All four cite `2060-2083` as `counterevidence` (23 characters,
  `myometrium_token`, no measurement) and all four recorded at least one
  `unresolved_conflicts` entry (`t1_r1` recorded three) — then answered a
  definite half anyway, three of them at `high`.
- `quantified_depth` is empty in all four, and `depth_basis` is
  `estimated_without_number` in all four. **The model itself says there is no
  number.**

**Why not "model wrong".** The contract
([`tasks/endo_myometrial_invasion.yaml`](../../../../tasks/endo_myometrial_invasion.yaml))
licenses `estimated_without_number` for *"unquantified wording that still
commits to a half (`superficial half`, `inner half`)"*. This report's wording
does not commit to a half — `half_word` is zero. The contract therefore has **no
rule that reaches this report**, in either direction: it neither licenses
`less_than_50` nor forces `cannot_be_determined`. Whether unquantified-extent
wording means `less_than_50` is the open clinical question from #15, and issue
#26 says not to count this as a model error until the mentor answers it. So the
verdict is that the contract doesn't say.

The report does **not** support a definite depth answer. But I am not proposing
`cannot_be_determined` as the model's correct answer either, because that too
depends on the mentor's ruling.

**New, and it matters for #23:** PR #22's contract C — the copy *with* an
explicit abstention rule and a high/medium/low rubric, digest `c3348a5b` — still
answered `present` / `less_than_50` on this patient, just at `medium` instead of
`high` (PR #22's `contract_comparison.csv`, its two rows for this patient, and
its README table). **A confidence rubric does not fix this row.** Only a rule
about unquantified extent wording would.

**Agree with the earlier reading: yes, both.** #15's "vague depth wording, no
number" and PR #22's "overconfident, the report contradicts itself" are both
right. What is added here is that the vagueness is total — not just the cited
passage but the entire document contains no number, no half, and no invasion
word — and that the deciding span is the annotator's own span.

**Question for the mentor:**

> Does unquantified-extent wording about the myometrium, with no number and no
> half anywhere in the report, establish (a) that invasion is present at all and
> (b) that it is `less_than_50`? If yes, the contract needs a rule saying so. If
> no, it needs a rule forcing `cannot_be_determined`. Either way the contract
> currently has neither, and a confidence rubric alone does not change the
> answer.

---

## `TCGA-A5-A0GR` — model wrong (`t1_r1`), fraction arithmetic wrong

**What flipped.** One citation, and only one.
[`evidence_spans.csv`](evidence_spans.csv), page column included:

| Range | Page | Classes | Measurement | `t0` | `t1_r1` | `t1_r2` | `t1_r3` |
|---|---|---|---|---|---|---|---|
| `552-593` | 1 | `depth_statement` `invasion_word` `myometrium_token` | 1.0 mm | — | `quantified_depth` | — | — |
| `2093-2128` | 2 | `myometrium_token` `thickness_statement` | 2.0 mm | — | `depth_evidence` + `quantified_depth` | `counterevidence` | — |
| `1390-1431` | 1 | `negation` `staging_line` | — | `counterevidence` | `depth_evidence` | `counterevidence` | — |
| `7196-7247` | 4 | `gross_examination` `invasion_word` `myometrium_token` `negation` | — | `counterevidence` | `counterevidence` | (`7146-7247`) | — |

Read the first row as exact ranges, not as "only `t1_r1` found the depth
figure": `t0` cited `579-607` and `t1_r2` cited `532-593`, which hold the same
1.0 mm. What is unique to `t1_r1` is the second row.

`t1_r1` is the **only** run that treated `2093-2128` as depth evidence. `t1_r2`
cited the identical range as *counterevidence*. `t0` and `t1_r3` never cited it
at all.

**The arithmetic** ([`arithmetic.csv`](arithmetic.csv)):

| Numerator | Denominator | Percent | Label |
|---|---|---|---|
| depth of invasion, 1.0 mm, offset `586-592`, page 1 (microscopic) | gross myometrial thickness, 2.0 mm, offset `2121-2127`, page 2 | **50.0** | `fifty_or_greater` |
| same 1.0 mm | gross **endometrial** thickness, 17.0 mm, offset `2085-2091`, page 2 | 5.9 | `less_than_50` |

1.0 / 2.0 is exactly 50.0%, and the bucket is "50% **or greater**", so the
boundary is inclusive and the answer tips. `t1_r1` set `depth_basis` to
`explicit_fraction_or_percentage` and cited both numbers as `quantified_depth` —
the contract's own comment on that value reads *"CAP 'Specify Percentage', or
depth+thickness in mm"*, so combining a depth and a thickness is sanctioned.
Nothing in the contract says they must come from the same section or the same
examination.

**Why this is the model's error and not the annotation's** — this part is my
judgement, not a computation:

1. The report states **no** fraction or percentage of myometrial thickness
   anywhere: `half_word` 0, `full_thickness_word` 0, and the five
   `fraction_or_percent` hits (`138`, `3462`, `4841`, `7037`, `8378`) fall
   outside every cited depth span (page 3 starts at `4849`, page 4 at `7045`).
   So `t1_r1`'s `explicit_fraction_or_percentage` describes a fraction **it
   constructed**, not one the pathologist wrote.
2. The denominator is implausible. The same gross list gives endometrial
   thickness 17.0 mm at `2085-2091` and myometrial thickness 2.0 mm at
   `2121-2127` — a myometrium thinner than the endometrium beside it, the
   reverse of normal uterine anatomy. Taken at face value it means 1.0 mm of
   invasion into a 2.0 mm wall, which no pathologist would describe with the
   unquantified-extent wording this same report uses at `532-560`. I cannot
   prove the pair is transposed or mislabelled, but it is not a safe
   denominator, and the second row of `arithmetic.csv` shows what the other
   reading gives (5.9%).
3. It mixes examinations. The 1.0 mm is a page-1 microscopic figure; the 2.0 mm
   is a page-2 gross figure, from the same gross examination that says on page 4
   there was no myometrial invasion at all (`7196-7247`). Dividing one by the
   other treats two incompatible readings as one measurement.

So the annotation's `less_than_50` stands, and `t1_r1` is wrong. Failure mode
from issue #26's list: **fraction arithmetic wrong** — specifically the choice
of denominator, with no plausibility check.

**Did the other three cite the conflicting page?** Yes — and so did the flip
run. `t0`, `t1_r1` and `t1_r2` all cite the page-4 passage as counterevidence
(`t1_r2` as the wider `7146-7247`). The one run that cited **no**
counterevidence at all is `t1_r3` — which nevertheless answered `less_than_50`
at `high`, and put `610-683` into `depth_evidence`, a range overlapping the
annotator's *adenomyosis* span (`610-670`), with `depth_basis`
`descriptive_other`.

**Agree with the earlier reading: partly — I overturn half of it.** #15 and the
issue body attribute the instability to the pages conflicting on whether there
is invasion. The conflict is real and the annotator recorded it at `7196-7247`.
But it is **not what flipped the answer**: three of the four runs cited that
conflict, including the one that flipped, and the run that ignored it answered
the same as the majority. The flip is explained entirely by one page-2 gross
thickness citation that only `t1_r1` made. The right story is a denominator
problem, not a page-conflict problem.

**Corroboration from PR #24 (open, `yuxuang/issue17-determinism`).** Issue #17
independently flagged this patient as unstable over five identical repeats:
`present/less_than_50` ×4 and `present/fifty_or_greater` ×1
(`experiments/endometrial_determinism/results/default_5x_cpu32/unstable_patients.csv`
on that branch). Together with the four temperature runs that is **9
observations, 7 `less_than_50` and 2 `fifty_or_greater`** — the same minority
flip in the same direction. Two caveats, so treat it as corroborating rather
than comparable: PR #24 ran a different oncotrace commit (`f99cefd`) and its
provenance does not record a contract digest; and its run folders
(`/net/spaces/scratch/yuxuang-oncotrace/runs/determinism_cpu32/rep{1..5}`) are
permission-denied from here (issue #32), so only its committed tables and trace
cards were readable, not the raw records. That means **I could not check whether
PR #24's flip repeat cited the same `2093-2128` range.** It is the obvious next
check if those permissions are fixed.

**Question for the mentor:**

> May a gross myometrial-thickness measurement from a later page be the
> denominator for a depth measured microscopically on page 1? And should a
> thickness figure be rejected as implausible when it is smaller than the
> endometrial thickness listed beside it?

---

## Other things the traces show

Not part of the two verdicts, but they came out of the same tables and bear on
#23 and on the contract.

1. **`depth_basis` is unstable on an identical report.** Four runs of
   `TCGA-A5-A0GR` claimed three different bases: `estimated_without_number`,
   `explicit_fraction_or_percentage` (twice) and `descriptive_other`
   ([`run_answers.csv`](run_answers.csv)). `t1_r2` claimed
   `explicit_fraction_or_percentage` while citing **only a numerator** — one
   `quantified_depth` span, no thickness. `t0` claimed
   `estimated_without_number` while citing a `quantified_depth` span that holds
   a measurement. The field is not being used consistently, so it cannot
   currently be trusted as a filter for "the model had a real number".
2. **`descriptive_other` is undefined.** It is an allowed `depth_basis` value
   with no comment in the contract and no instruction saying when to use it.
   `t1_r3` used it.
3. **Citing a conflict does not stop an answer.** On `TCGA-A5-A0GJ` all four
   runs filed counterevidence *and* an `unresolved_conflicts` entry and still
   answered a definite half, three at `high`. `t1_r1` on `TCGA-A5-A0GR` filed
   the page-4 conflict as counterevidence and recorded **zero**
   `unresolved_conflicts` entries. The two signals are not kept in step.
4. **Truncation is everywhere on `TCGA-A5-A0GR`:** 3, 2, 2 and 1 replies cut off
   at the token cap in `t0`, `t1_r1`, `t1_r2`, `t1_r3`. Three of the four also
   hit a recoverable error (`quantified_depth_not_classified` twice,
   `answer_exists` once). This is a long, fragile trajectory, and it is the
   patient that flips.
5. **"Missed passage" is ruled out for both rows.** Every run read 100% of both
   documents ([`run_answers.csv`](run_answers.csv), `doc_fraction_read`).

## What this does not settle

- Two rows, hand-read. Nothing here is a rate.
- One annotator, not adjudicated, 45 of 50 patients from one tissue source
  site. A disagreement is not evidence that the annotation is the truth.
- `TCGA-A5-A0GR`'s verdict rests on a clinical judgement about a measurement's
  plausibility, written out above as a question. If the mentor says the gross
  figure is usable as-is, the verdict becomes **task contract doesn't say** and
  `t1_r1` becomes arguably correct.
- The `TCGA-A5-A0GJ` row cannot be closed without the #15 ruling.
- PR #24's raw records were unreadable, so its flip was not traced to a span.
