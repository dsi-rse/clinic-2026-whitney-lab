# Prompt given to each revising agent

Both agents get this text word for word. `{WORKSPACE}` is the arm's own folder
and `{ONCOTRACE}` the OncoTrace clone. The guided agent's prompt also includes
the line marked GUIDED ONLY; the unguided agent's prompt leaves it out. Nothing
else differs.

---

You are revising a task contract for OncoTrace. In OncoTrace, a language model
reads one patient's pathology report and submits answers whose fields, allowed
values, rules and instructions are defined by the contract, a YAML file. Your
goal is to make this contract as good and as clear as you can, so the model
gives correct, consistent answers.

Work only with the files in `{WORKSPACE}`. Do not open any other file or
folder, do not run git, gh or any web request, and do not look for other
versions of this contract.

Files:
- `contract.yaml`: the current contract.
- `task-contract.md`: OncoTrace's reference for what a contract can declare.
- `reports/`: 20 example reports of the kind the contract will run on. The
  contract will be evaluated on different reports.
- `guidelines.md`: guidelines for writing a task contract. Follow them. (GUIDED ONLY)

Facts you need:
- The human annotations used for evaluation hold the current field names and
  values.
- Report text must not be copied into the contract.

Deliver:
1. `{WORKSPACE}/revised.yaml`: the revised contract.
2. `{WORKSPACE}/changes.md`: a short list of what you changed and why. No
   report text.

Check that the revised contract loads, using only this command:

    PYTHONPATH={ONCOTRACE} {PYTHON} -c "import yaml; from oncotrace.task import load_task; load_task(yaml.safe_load(open('{WORKSPACE}/revised.yaml'))); print('loads')"

When you finish, reply with one paragraph summarising your changes.
