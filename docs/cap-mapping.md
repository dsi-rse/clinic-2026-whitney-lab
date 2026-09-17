# CAP protocol to task contract

How the CAP Endometrium protocol becomes oncotrace configuration, and what to
watch for when reading these labels later.

## Version anchor

Values are anchored to **CAP Endometrium, protocol posting date June 2022**
(`CAP Endometrium June 2022.pdf`, version 4.3.0.0), standards AJCC-UICC 8 and the
FIGO Cancer Report 2018. The myometrial invasion note is **Note E**.

**This changed on 2026-09-15**; it was previously December 2024 (v5.1.0.0,
Note F). The reason is not that June 2022 is better clinically — it is older — but
that the human hand-read template
(`/net/spaces/annawoodard/annawoodard/endometrial-project/data/cap2022jun_extraction_template.csv`) is June 2022. The
reference standard and the extraction contract must sit on the **same** protocol
version, or a disagreement between a human read and a model label cannot be
distinguished from a version artifact. If the template moves, move this with it.

Filename trap in `/net/spaces/annawoodard/annawoodard/endometrial-project/data/cap-docs/`: the December 2024 protocol is the
file called **`CAP Endometrium UP TO DATE 2026.docx`** (its template page reads
"Protocol Posting Date: December 2024", version 5.1.0.0). No file is named 2024.

### What differs between June 2022 and December 2024

Not only wording. The parent value set, the adenomyosis direction, and the
measurement rules all change answers:

| | June 2022 (v4.3.0.0) | December 2024 (v5.1.0.0) |
| --- | --- | --- |
| myometrial invasion note | **Note E** | Note F |
| parent response options | Not identified / **Present** / CBD / Not applicable | Not identified / **Present, inner half** / **Present, outer half** / CBD / Not applicable |
| inner vs outer half | separate *Percentage of Myometrial Invasion* sub-element | folded into the parent options, with `+Specify Percentage` |
| adenomyosis | carcinoma involving adenomyosis is **not** invasion; invasion within a focus is measured **from that focus** | ICCR / ISGyP: report **pT1b** where the deepest point is in the outer half |
| cornu / leiomyoma / LUS depth rules | **absent** from the note prose | present |
| exophytic component excluded from thickness | in the note's schematic only | stated in prose |
| FIGO staging | 2018 report (FIGO 2009 stages) | FIGO 2009 **and** 2023 |

The adenomyosis row is the one to watch. The two versions point in **opposite
directions** on the same report text: June 2022's worked example — a 2 mm focus of
myoinvasion extending from adenomyosis deep in the myometrium — is explicitly
*less than 50%, FIGO IA*, whereas December 2024 would read the deepest point and
report pT1b. A label extracted under one version is not comparable to a label
extracted under the other on such a case.

For completeness, December 2023 (v5.0.0.0) sits between them and is the version
the hand-read template originally used: it added FIGO 2023 staging, the
International System for Reporting Serous Fluid Cytopathology, and the LVSI
terminology update (which also moved the LVI vessel thresholds from <3 / >=3 to
<5 / >=5).

## Why one task file per field

An oncotrace task declares exactly one categorical `label`, plus `extra_fields`
the label depends on, and rules that make a value defensible. CAP mandates about
ten required fields. Mapping them onto a single task would mean one label and
nine `extra_fields`, which collapses nine independent clinical judgements into
one confidence value and one citation set. So each CAP field gets its own task
file and its own run.

## Myometrial invasion

CAP response options map one-to-one onto the contract. No value is invented and
none is dropped — but on this protocol version the answer is **two fields**,
because CAP asks in two parts.

The label is the parent element, "Myometrial Invasion (Note E)":

| CAP response option | task value |
| --- | --- |
| Not applicable | `not_applicable` |
| Not identified | `not_identified` |
| Present | `present` |
| Cannot be determined (explain) | `cannot_be_determined` |

`myometrial_invasion_percent` is the "Percentage of Myometrial Invasion"
sub-element, and is where the FIGO boundary actually lives:

| CAP response option | task value | stage |
| --- | --- | --- |
| Estimated to be less than 50% | `less_than_50` | pT1a / FIGO 2009 IA |
| Estimated to be 50% or greater | `fifty_or_greater` | pT1b / IB |
| Cannot be determined (explain) | `cannot_be_determined` | — |
| *(CAP omits the sub-element)* | `not_applicable` | label is not `present` |

CAP also offers "Specify Percentage: ___%" here. A task field cannot hold a free
number, so an explicitly stated percentage is recorded as the half it falls in,
and the fact that a number was given is recorded in `depth_basis`
(`explicit_fraction_or_percentage`, as against `estimated_without_number`). The
two fields together reconstruct the CAP response.

CAP marks the whole field **"required only if applicable"**. That conditional is
what the rules encode, because "applicable" means *myometrium was resected*:

- a definite value (`not_identified`, `present`) requires
  `specimen_type: hysterectomy` **and** non-empty `depth_evidence`;
- `present` additionally requires `myometrial_invasion_percent` to be a half or an
  explicit `cannot_be_determined` — the rule `invasion_percent_unresolved`. This
  rule exists because `present` alone is a strictly weaker answer than the old
  flattened `present_outer_half` was, and without it the model could answer the
  easy half of the question and skip the half ultrasound cares about;
- a stated half requires a hysterectomy (`invasion_percent_requires_hysterectomy`),
  which is the closest expressible inverse: oncotrace rules cannot require a
  *label* value from a field condition, only another field;
- `not_applicable` requires a specimen that is *not* a hysterectomy, plus
  `specimen_evidence` showing what was resected;
- an `explicit_fraction_or_percentage` basis requires `quantified_depth`
  citations, which must themselves be a subset of `depth_evidence`;
- an adenomyosis finding that bears on depth requires `depth_evidence`.

### Adenomyosis on this version

`adenomyosis_relation` reproduces CAP's own "+Adenomyosis" element and adds one
value the note requires but the element does not name:

| CAP response option | task value |
| --- | --- |
| *(not mentioned in the report)* | `not_mentioned` |
| Present, uninvolved by carcinoma | `present_uninvolved_by_carcinoma` |
| Present, involved by carcinoma | `present_involved_by_carcinoma` |
| *(Note E's hard case, no response option)* | `invasion_within_adenomyosis` |
| Cannot be determined | `cannot_be_determined` |

`invasion_within_adenomyosis` is carried as a field value because Note E gives it
a distinct measurement rule — measure from the adenomyotic focus to the deepest
area of invasion — and a reviewer needs to see which cases were decided that way.

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
