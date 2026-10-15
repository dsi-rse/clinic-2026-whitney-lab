# Does the model's confidence track agreement with the annotations?

Run `endometrial_glm53_20261012`, label `myometrial_invasion`, matched by patient
ID to Mariam Hassan's 50 annotations (`scripts/confidence_table.py`). All 50
have a record in the run.

| Confidence | Patients | Correct | Wrong | Over-committed | No answer |
|---|---|---|---|---|---|
| high | 46 | 44 | 0 | 2 | 0 |
| medium | 1 | 1 | 0 | 0 | 0 |
| low | 0 | 0 | 0 | 0 | 0 |
| none (no answer) | 3 | 0 | 0 | 0 | 3 |
| **Total** | **50** | **45** | **0** | **2** | **3** |

Over-committed: the model gave a definite label where the human said
`cannot_be_determined`. No answer: the run ended without an accepted submission
(`model_call_budget_exhausted` for 2, `truncated_without_tool_call` for 1).

## What this does and does not show

- Confidence did not separate good from bad here: 46 of 47 answers are `high`,
  and both disagreements are `high`. Only one answer is `medium` and none are
  `low`, so there is nothing to compare against.
- The sample is small and uneven (45 of 50 from site A5, 45 `present`), and
  these annotations may have shaped the prompt, so this is not a test set.
  TraceView scores all 50 as "prospective" only because the annotation
  project declares no development units.
- Missing answers sit outside the confidence groups: an unanswered patient has
  no confidence to rate.

## High-confidence disagreement inspected: TCGA-A5-A0GJ

Human: `cannot_be_determined`. Model: `present`, `high`, depth
`less_than_50` with `estimated_without_number`.

- The model's depth citation and the annotator's evidence are the same
  character range (1801-1868). They read the same sentence differently.
- The sentence says the cancer is confined to the endometrium with only
  superficial myometrial involvement. The annotator's note says they were
  unsure whether "superficial" counts as invasion.
- The run read the whole report and made 5 model calls with no problems other
  than two corrected citation refusals. Nothing in the trajectory points to a
  pipeline fault.

The other disagreement, TCGA-A5-A2K4 (model `present`, `fifty_or_greater`,
`high`; human `cannot_be_determined`), is a different kind. The model cites a
passage stating a depth fraction, while the annotator cites a different
passage that hedges ("possible" invasion). The report contains both.

## Question for the mentor

For A5-A0GJ, is this a model error or an annotation question? The model and the
annotator cite the identical sentence. Does the task's definition of `present`
cover "only superficial myometrium", or should that wording be
`cannot_be_determined` (or something else)? The answer decides whether this is
counted as a model mistake, an annotation to revise, or a gap in the protocol
that needs a clinical reviewer.
