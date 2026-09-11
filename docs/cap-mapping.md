# CAP protocol to task contract

How the CAP Endometrium protocol becomes oncotrace configuration, and what to
watch for when reading these labels later.

## Version anchor

Values are anchored to **CAP Endometrium, protocol posting date December 2024**
(`CAP Endometrium UP TO DATE 2026.docx`), standards AJCC 8 with both FIGO 2009
and FIGO 2023 staging. Two drifts matter when comparing against the older PDFs
in the same folder:

| | Dec 2023 | Dec 2024 ("2026" file) |
| --- | --- | --- |
| myometrial invasion note | Note E | **Note F** |
| depth sub-field | `Myometrial Thickness` | `+Specify Percentage` |
| FIGO staging | 2023 only | 2009 **and** 2023 |

The 2024 revision also updated Procedure, Tumor Size, Histologic Type,
Histologic Grade, Molecular Type, Cervical Involvement, LVI, Margin Status and
pN Category — so any later task file should be re-checked against this version
rather than the 2023 PDF.

## Why one task file per field

An oncotrace task declares exactly one categorical `label`, plus `extra_fields`
the label depends on, and rules that make a value defensible. CAP mandates about
ten required fields. Mapping them onto a single task would mean one label and
nine `extra_fields`, which collapses nine independent clinical judgements into
one confidence value and one citation set. So each CAP field gets its own task
file and its own run.

## Myometrial invasion

CAP response options map one-to-one onto `label.values`. No value is invented
and none is dropped:

| CAP response option | task value |
| --- | --- |
| Not applicable | `not_applicable` |
| Not identified | `not_identified` |
| Present, inner half (less than 50%) | `present_inner_half` |
| Present, outer half (greater than or equal to 50%) | `present_outer_half` |
| Cannot be determined (explain) | `cannot_be_determined` |

`present_inner_half` is pT1a / FIGO 2009 IA; `present_outer_half` is pT1b / IB.

CAP marks the whole field **"required only if applicable"**. That conditional is
what the rules encode, because "applicable" means *myometrium was resected*:

- a definite value (`not_identified`, `present_inner_half`, `present_outer_half`)
  requires `specimen_type: hysterectomy` **and** non-empty `depth_evidence`;
- `not_applicable` requires a specimen that is *not* a hysterectomy, plus
  `specimen_evidence` showing what was resected;
- an `explicit_fraction_or_percentage` basis requires `quantified_depth`
  citations, which must themselves be a subset of `depth_evidence`.

### Known tuning knob

`depth_requires_hysterectomy` is strict: it refuses a definite depth unless the
model also classified the specimen as a hysterectomy. That is clinically correct
— depth is unmeasurable without myometrium — but it means an OCR failure on the
specimen line forces `cannot_be_determined` even when the depth sentence is
legible. If that turns out to dominate the failure modes, widen the rule's
allowed values to include `other_or_not_stated`. It is a one-line change to the
task file, which is the point of keeping the contract out of the code.

## Cohort and source choice

The delivered data is pan-cancer. `TCGA_Reports.csv` holds 9,523 reports across
686 tissue source sites; `aws_response_txt` holds OCR pages for all of them.
`prep/build_ucec_sources.py` narrows both to the 560 barcodes in the UCEC case
manifest, of which **546 have usable pages** (1,922 pages, ~3.5 per patient).
The 14 with none are listed by the script when it runs.

Two text versions were available and the noisier one was chosen deliberately:

| | `TCGA_Reports.csv` | `aws_response_txt` |
| --- | --- | --- |
| granularity | one flattened row per patient | one file per page |
| text quality | cleaned, whitespace normalised | raw OCR, includes artifacts |
| citations | point at the whole report | point at a page |

oncotrace requires every answer to cite the rows that justify it, so row
granularity *is* citation granularity. A single row per patient makes every
citation vacuous. The OCR noise is real — `"Adeno ,carcinoma, endometriord"` —
but the clinically decisive sentences survive it, and the task instructions tell
the model to prefer `cannot_be_determined` over guessing at a garbled number.

To switch to the cleaned text instead, add a second entry under `sources:`
pointing at a table built from the CSV. Nothing in the contract changes.

## Reports predate every protocol here

TCGA pathology reports were written roughly **2000–2013**, so none of them were
authored against these templates. The task instructions therefore include a
mapping for historical wording — "full thickness", "transmural", "invades to
serosa" all read as outer half — rather than assuming CAP phrasing appears
verbatim. Expect `not_stated`-shaped outcomes to be more common than they would
be on modern synoptic reports.
