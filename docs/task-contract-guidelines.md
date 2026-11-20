# Guidelines for writing a task contract

Read this before you write or edit a task contract. OncoTrace's
[task contract reference](https://github.com/dsi-rse/oncotrace/blob/main/docs/task-contract.md)
says what a contract can declare, and OncoTrace refuses a badly formed contract
when it loads one. These guidelines cover what loading can't check: whether the
contract says clearly what it means.

## Values

1. **Define every value where you declare it.** Add one comment saying what in a
   report leads to that value. Without a definition, the model uses a value
   inconsistently. Catch-all values such as `other` need the most careful
   definition. If you can't define one, remove it.
2. **Make sure each case fits exactly one value.** Every kind of evidence a
   report can hold should fit one value and only one. Say which value takes a
   boundary case, such as exactly 50%.
3. **Keep "not found", "can't tell", "not stated" and "doesn't apply" apart.**
   They mean different things, so give each its own value. Don't put something
   that can be quoted (`other`) in the same value as something that can't
   (`not_stated`).
4. **Make the rules as strict as the definitions.** If a value's definition
   needs two things, such as a size *and* the unit it was measured in, the
   instructions must ask for both. If no rule can check it, say so in a comment.

```yaml
- name: size_basis
  values:
    - measured      # the report gives this tumor's size as a number with a unit
    - estimated     # the report gives a range, or "about" a size
    - not_stated    # no size for this tumor anywhere in the report
```

## Instructions

5. **Map every kind of wording to a value.** Before you finish, read a sample of
   real reports and list the ways they phrase the answer. Include wording that
   hints at an answer without committing to one. Each kind of wording must map
   to a value. Where the contract says nothing, the model guesses.
6. **Describe kinds of wording, not phrases copied from reports.** If example
   phrases also appear in the reports you test on, the test only checks that
   the model can match the examples. Make up your examples, and check that they
   don't appear in the test reports.
7. **Say how numbers may be combined.** If the model may compute a value, such
   as a fraction, say which numbers can go together (for example, only numbers
   from the same section). Say also that a computed number is not a stated one.
8. **Say what to do when a report contradicts itself.** Say which statement wins
   (for example, the final diagnosis over a preliminary one) and where the
   other one is recorded.
9. **Say what each answer should quote.** It should quote the sentence that
   decides the answer, not the heading above it. One passage can be quoted
   under several answers.

## Rules

10. **Rules check values, not quotes.** A rule can require one value when
    another is given. It can't check what a quote says. Put any other
    requirement in the instructions, with a comment that no rule enforces it.
11. **Spell every name and value exactly as declared.** OncoTrace checks that a
    rule's field names exist, but not its values. A misspelled value means the
    rule never fires, and nothing reports it. The same goes for names used in
    the instructions.
12. **Give each no-quote value a name that no other field uses.**
    `no_quote_values` matches by value name across all fields. A shared name
    such as `not_applicable` is exempt everywhere it appears, including in
    fields that should be quoted.
13. **Add a rule only when it's worth the retries.** Each refusal costs a model
    call. A rule that refuses good answers can leave a report with no answer at
    all. Make sure every answer the instructions allow can pass all the rules
    at once. Before a model run, test a new rule on two made-up submissions,
    one it should pass and one it should refuse, using OncoTrace's
    `check_answer`. After a run, count refusals by rule.

## Changing a contract

14. **Keep the annotations in step.** When you add, rename or remove a value,
    check that every annotation still holds an allowed value. An empty value is
    not allowed. Don't rename a value the annotations use unless the
    annotations change with it.
15. **Change one thing per version.** Changing the contract changes its digest,
    so earlier runs no longer compare directly: rerun the baseline. If you
    change the format and the meaning separately, a change in answers can be
    traced to one of them.
16. **Judge a change against run-to-run variation.** Identical runs can give
    different answers. If a patient's answer changed once, one rerun doesn't
    show whether a fix worked. Repeat the run to see how often it changes. Also
    check that the patients who were already right still are.
