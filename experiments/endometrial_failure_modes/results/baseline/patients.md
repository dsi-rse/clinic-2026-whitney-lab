# Patient trajectories

Step key: I=inventory R=read S=search $=submit !=refused ?=other x=no answer

## TCGA-A5-A0GP

- unit: TCGA-A5-A0GP
- outcome: model_call_budget_exhausted
- label: None
- confidence: 
- steps: IR!!!!!!!!!!!!!!!!!!!!!!x
- model_calls: 24
- document_chars: 5182
- read_windows: [(0, 5182)]
- chars_read: 5182
- refusals: {'citation_quote_not_found': 22}
- single_char_quotes: 4
- not_found_quotes: 22
- truncated_replies: 0
- max_completion_tokens: 5912
- last_event: no_answer

## TCGA-AX-A06F

- unit: TCGA-AX-A06F
- outcome: model_call_budget_exhausted
- label: None
- confidence: 
- steps: IR!!!!!!!!!!!!!!!!!!!!!!x
- model_calls: 24
- document_chars: 12733
- read_windows: [(0, 4000), (4000, 8000), (8000, 12000), (12000, 12733)]
- chars_read: 12733
- refusals: {'citation_quote_not_found': 19, 'evidence_citations_missing': 2, 'citation_absent': 1}
- single_char_quotes: 19
- not_found_quotes: 19
- truncated_replies: 2
- max_completion_tokens: 8192
- last_event: no_answer

## TCGA-A5-A0GE

- unit: TCGA-A5-A0GE
- outcome: truncated_without_tool_call
- label: None
- confidence: 
- steps: IR??x
- model_calls: 5
- document_chars: 6144
- read_windows: [(0, 6144)]
- chars_read: 6144
- refusals: {}
- single_char_quotes: 0
- not_found_quotes: 0
- truncated_replies: 3
- max_completion_tokens: 8192
- last_event: no_answer

## TCGA-A5-A0GJ

- unit: TCGA-A5-A0GJ
- outcome: answered
- label: present
- confidence: high
- steps: IR!!$
- model_calls: 5
- document_chars: 12974
- read_windows: [(0, 5000), (5000, 10000), (10000, 12974)]
- chars_read: 12974
- refusals: {'citation_quote_ambiguous': 1, 'overlapping_citations': 1}
- single_char_quotes: 0
- not_found_quotes: 0
- truncated_replies: 0
- max_completion_tokens: 4457
- last_event: submit

## TCGA-4E-A92E

- unit: TCGA-4E-A92E
- outcome: answered
- label: not_identified
- confidence: high
- steps: IR$
- model_calls: 3
- document_chars: 9607
- read_windows: [(0, 5000), (5000, 9607)]
- chars_read: 9607
- refusals: {}
- single_char_quotes: 0
- not_found_quotes: 0
- truncated_replies: 0
- max_completion_tokens: 2857
- last_event: submit
