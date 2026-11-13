# Getting the endometrial data on your own machine

The roster and report store you normally read live on the DSI cluster. When the
cluster is unavailable, you can rebuild both on your laptop from public data. The
result is byte-for-byte the same file every earlier run read, and a check at the
end proves it.

## The short version

From the repository root, with your OncoTrace clone at `~/oncotrace`:

```bash
bash scripts/endometrial_data/download.sh
```

If OncoTrace lives somewhere else, put `ONCOTRACE_REPO=/path/to/oncotrace` in
front of the command. The script uses `DATA_DIR` from your `.env` (default
`./data`, which Git ignores) and takes a few minutes, most of it the download.

It finishes with three checks. All three should say `ok`:

```text
[ok] patients: roster 546, store 546, expected 546
[ok] annotation quotes at their saved positions: 323 of 323
[ok] store SHA-256 matches the shared copy
```

Then copy `config/endometrial.yaml` to a personal config and change the two input
paths to the ones the script prints:

```yaml
roster: <DATA_DIR>/endometrial/roster_ucec.csv
sources:
  - name: pathology_report
    path: <DATA_DIR>/endometrial/documents/ucec_pathology_report.jsonl
```

## What you need

- Python 3.12, the same environment you use for the OncoTrace client. The scripts
  use only the standard library, plus OncoTrace's own reader for a final check.
- About 1 GB of free disk: 775 MB for the download, a few MB for the result.
- Internet access to `api.gdc.cancer.gov` and to Amazon S3.

## Where the data comes from

TCGA pathology reports are open-access scanned PDFs at the NCI's Genomic Data
Commons (GDC). Kefeli and Tatonetti ran every page through Amazon's OCR service,
Textract, and published the results ([TCGA-Reports, *Patterns* 2024](https://doi.org/10.1016/j.patter.2024.100933);
[code](https://github.com/tatonetti-lab/tcga-path-reports)). The shared store was
built from that OCR text with Mariam Hassan's preparation scripts, which are now in
this repository under `scripts/endometrial_data/`.

The script runs five steps. Each writes into `$DATA_DIR/endometrial/`.

| Step | Script | What it does | Writes |
| --- | --- | --- | --- |
| 1 | `fetch_ucec_cohort.py` | Asks the GDC which patients are in the endometrial project, TCGA-UCEC | `ucec_cohort.tsv` (560 patients) |
| 2 | `curl` | Downloads the public OCR archive, one file per scanned page | `downloads/aws_response.tar.gz` |
| 3 | `extract_ocr_pages.py` | Keeps the endometrial patients' pages and writes each page's text | `aws_response_txt/` (1,922 pages) |
| 4 | `build_ucec_sources.py`, then `build_ucec_document_store.py` | Builds the roster, then stitches each patient's pages into one report | `roster_ucec.csv`, `documents/ucec_pathology_report.jsonl` |
| 5 | `verify_store.py` | Checks the result against the shared copy | nothing |

546 of the 560 patients have a report. The other 14 were never scanned, including
all 12 patients from one contributing site (TCGA-FL). Step 4 prints them.

## If a check fails

- **The SHA-256 differs but the other two pass.** The GDC may have added or
  removed patients since the shared copy was made (it was built against GDC data
  release 46.0). Your store still works, but your results are no longer on exactly
  the same patients. Ask your mentor before running on it.
- **Annotation quotes do not line up.** The report text differs from the shared
  copy. Do not use the store for anything you compare against the annotations; ask
  your mentor.
- **The download stops partway.** Run the script again. It keeps the archive once
  it is complete and starts over if it is not.

## Rules that still apply

- Reports and run outputs stay out of Git. `data/` is already ignored; if you set
  `DATA_DIR` elsewhere, keep it outside the repository.
- Keep the data on an encrypted disk, as the [clinic data policy](../DataPolicy.md)
  requires, and delete your copy when the project ends.
- Do not edit the store after building it. Citations point at character positions
  in this exact text, so a single changed character breaks them.

## Notes for an agent doing this

- Run `download.sh` from the repository root; it is safe to rerun.
- Success is exit status 0 and three `[ok]` lines. Anything else is a failure to
  report, not to work around: do not rebuild from `TCGA_Reports.csv` or re-run OCR,
  because that text differs from the store the annotations cite.
- The OCR archive holds Python pickles. `extract_ocr_pages.py` loads them with a
  loader that refuses any class or function reference, so it can only read plain
  data. Do not replace it with `pickle.load`.
