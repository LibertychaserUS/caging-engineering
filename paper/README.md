# Caging Engineering: Reachability-Shaped Agent Systems (workshop paper)

Source for the paper. The theory documents under `docs/`, the formal core under `formal/`, and the frozen `experiments/PREREGISTRATION.md` are the source of every claim; the paper compresses them and adds nothing they do not state.

## Build

    cd paper
    tectonic main.tex            # or: tectonic -X compile main.tex

`tectonic` (0.16 or later, at `/opt/homebrew/bin/tectonic` on the authoring machine) fetches packages on first use and runs BibTeX itself. A clean build produces `main.pdf` next to `main.tex`; PDFs are git-ignored.

## Layout

    VERSION              current version (semantic; see rule below)
    main.tex             preamble and section order
    macros.tex           symbols (defined once), the `\results` placeholder, theorem environments, Lean listing style
    sections/*.tex       one file per section and appendix
    figures/*.tex        TikZ figures
    references.bib       bibliography; entries whose details are unconfirmed carry `note = {verify}`
    CHECKLIST.md         review-response table, one row per reviewer comment per revision

## Versioning rule

- `VERSION` is bumped by 0.0.1 **before** any change to the body text. One version number corresponds to exactly one body text.
- A delivered PDF is named `caging-engineering-v<version>-<YYYY-MM-DD>.pdf` (for example `caging-engineering-v0.1.0-2026-10-26.pdf`). Before delivery, confirm that the PDF was built from the `VERSION` it is named after.
- Every revision round is delivered together with an updated `CHECKLIST.md`.

## Placeholders

Experimental results that are not yet available are typeset by `\results{<hypothesis>}{pending}` as a grey box. Searching the PDF for "Result pending" lists everything still open. When a result comes in, the box is replaced by the sentence the preregistration specifies for that outcome, with the numbers filled in.
