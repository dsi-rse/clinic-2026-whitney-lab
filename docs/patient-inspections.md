# Five patients inspected in TraceView

Run: `endometrial_glm53_20261012` (498 of 546 records at inspection time).
Facts below come from TraceView's loaded records via
`scripts/inspect_patients.py`. Only counts, tool names, refusal signatures and
character offsets are recorded; report text and quotes are protected.
Step key: I=inventory R=read $=submit !=refused ?=reply with no tool call x=no answer.

| Patient | Steps | Ended because | Read | Refusals |
|---|---|---|---|---|
| TCGA-A5-A0GP | `IR` + 22 `!` + `x` | call budget (24) used up | whole report, 1 read (0-5182 of 5182) | 22 `citation_quote_not_found`, all for `depth_evidence`; 18 had the same 181-character quote (best verbatim match 0.47), 4 were 1 character |
| TCGA-AX-A06F | `IR` + 22 `!` + `x` | call budget (24) used up | whole report, 4 windows (0-12733 of 12733) | 19 `citation_quote_not_found`, every one a 1-character quote for `depth_evidence`; 2 `evidence_citations_missing`, 1 `citation_absent` |
| TCGA-A5-A0GE | `IR??x` | `truncated_without_tool_call` | whole report (0-6144 of 6144) | none; no submit was ever attempted |
| TCGA-A5-A0GJ | `IR!!$` | accepted answer (`present`, high) | whole report, 3 windows | 1 `citation_quote_ambiguous`, 1 `overlapping_citations`, then accepted |
| TCGA-4E-A92E | `IR$` | accepted answer (`not_identified`, high) | whole report, 2 windows | none |

## What the evidence supports

1. **Missing answers are not caused by unread text.** All five patients' reports
   were read in full (read ranges cover 100% of document characters). Across the
   whole run, chars read equal document chars for all 498 records.
2. **Budget exhaustion is a refusal loop on one citation group.** In both
   budget cases the model read once, then spent every remaining call submitting
   a `depth_evidence` quote the checker could not find in the report. Across the
   run, the 32 budget-exhausted patients had 454 one-character quote refusals
   (and 56 longer ones); answered patients had 57 and 64. A 1-character quote can
   never match a real citation, so these retries cannot succeed.
   A0GP is different: it repeated one 181-character quote that partly matched
   (0.47), so it was a near-verbatim quote, not the 1-character problem.
3. **The truncated case never reached the checker.** A0GE's three final replies
   each stopped at the 8192-token cap with about 30,000 characters of reasoning
   and no text or tool call. Its token cap, not any rejection, ended the run.
4. **Rejections can be recovered from.** A0GJ was refused twice (a different
   kind of problem: ambiguous and overlapping citations) and was accepted on the
   next try, so a refusal alone does not predict failure.

## Caveats

- That 1-character quotes come from a formatting or tool-argument problem is a
  hypothesis; these records do not show why the model sent them. A check: look
  at the submitted arguments for one such call in the server log (protected).
- Five patients illustrate the patterns; the run-wide counts in point 2 are the
  evidence for how common they are.
- A0GJ was `cannot_be_determined` in Mariam's reference and the model answered
  `present` with high confidence. An accepted answer is not a correct one.
