# Agentic vs one_shot: baseline

Patients both modes ran: 546. Only agentic: 0. Only one_shot: 0. Every table below is over the patients both modes ran, so neither mode is flattered by having run more.

## Who answered

| group | patients |
|---|---|
| both answered | 466 |
| only agentic answered | 37 |
| only one_shot answered | 30 |
| neither answered | 13 |

## Why a patient got no answer

| reason | agentic | one_shot |
|---|---|---|
| model_call_budget_exhausted | 26 | 19 |
| truncated_without_tool_call | 17 | 31 |

## What each mode spent (token counts are the server's own)

| arm | units | answered | model_calls | prompt_tokens | completion_tokens | refusals |
|---|---|---|---|---|---|---|
| agentic | 546 | 503 | 2790 | 18741654 | 4824155 | 1220 |
| one_shot | 546 | 496 | 1711 | 13732783 | 5891937 | 1277 |

## What each mode was refused on

| refusal | agentic refusals | agentic patients | one_shot refusals | one_shot patients |
|---|---|---|---|---|
| citation_quote_not_found | 554 | 87 | 480 | 86 |
| quantified_depth_not_classified | 358 | 286 | 299 | 286 |
| evidence_citations_missing | 79 | 18 | 130 | 37 |
| answer_exists | 61 | 14 | 61 | 19 |
| citation_absent | 2 | 2 | 94 | 49 |
| empty_unresolved_conflicts | 8 | 2 | 67 | 6 |
| citation_quote_ambiguous | 39 | 12 | 30 | 8 |
| citation_document_ambiguous | 35 | 18 | 28 | 22 |
| quantified_basis_uncited | 19 | 11 | 39 | 14 |
| empty_rationale | 16 | 12 | 23 | 22 |
| specimen_type_not_allowed | 26 | 6 | 12 | 5 |
| overlapping_citations | 6 | 5 | 11 | 11 |
| citation_malformed | 6 | 4 | 0 | 0 |
| depth_evidence_missing | 4 | 4 | 1 | 1 |
| adenomyosis_relation_not_allowed | 4 | 2 | 0 | 0 |
| myometrial_invasion_percent_not_allowed | 2 | 2 | 1 | 1 |
| depth_basis_not_allowed | 0 | 0 | 1 | 1 |
| search_batch_size | 1 | 1 | 0 | 0 |

## Agreement with annotations: invasion

| arm | scored | correct | wrong | over_committed | abstained | coverage | accuracy | accuracy_if_answered |
|---|---|---|---|---|---|---|---|---|
| agentic | 50 | 46 | 0 | 3 | 1 | 0.980 | 0.920 | 0.939 |
| one_shot | 50 | 43 | 0 | 3 | 4 | 0.920 | 0.860 | 0.935 |
| always 'present' | 50 | 45 | 5 | 0 | 0 | 1.000 | 0.900 | 0.900 |
| only agentic correct / only one_shot correct | 4 | 1 |  |  |  |  |  | McNemar exact p=0.375 |

## Agreement with annotations: depth

| arm | scored | correct | wrong | over_committed | abstained | coverage | accuracy | accuracy_if_answered |
|---|---|---|---|---|---|---|---|---|
| agentic | 50 | 37 | 0 | 12 | 1 | 0.980 | 0.740 | 0.755 |
| one_shot | 50 | 34 | 0 | 12 | 4 | 0.920 | 0.680 | 0.739 |
| always 'less_than_50' | 50 | 23 | 27 | 0 | 0 | 1.000 | 0.460 | 0.460 |
| only agentic correct / only one_shot correct | 4 | 1 |  |  |  |  |  | McNemar exact p=0.375 |

Unanswered patients count as wrong in `accuracy`; `over_committed` means the model gave a definite answer where the annotation says not applicable or cannot be determined. The annotations are a development reference, not an independently adjudicated test set. Patients where the modes differ are listed in `disagreements.csv`.
