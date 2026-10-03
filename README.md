# CV PDF Studio

[![Python Tests](https://github.com/HafidIdrissi/cv-pdf-studio/actions/workflows/tests.yml/badge.svg)](https://github.com/HafidIdrissi/cv-pdf-studio/actions/workflows/tests.yml)

CV PDF Studio is an agent skill that turns verified career evidence and a target role into a
tailored CV PDF and, optionally, a matching cover letter.

It provides two renderings:

| Format | Layout | Default photo policy | Best use |
|---|---|---|---|
| ATS | Single-column, linear text | No photo | Portals and unknown parsing pipelines |
| Design | Two columns | Optional, with consent | Direct human review where locally appropriate |

The skill does not promise an opaque ATS score. It validates the things it can actually test:
source provenance, page count, unresolved placeholders, selectable text, required fields, and
reading order.

## Core workflow

1. Validate `assets/cv_master.json` in strict provenance mode.
2. Map every meaningful job requirement to proven, adjacent, missing, or unclear evidence.
3. Select and write only claims linked to master IDs.
4. Choose one or two pages from the candidate's experience and target market.
5. Compile the PDF and fail closed when page or text checks cannot be verified.
6. Deliver an honest gap report with the finished files.

## Install

### Codex

Codex discovers repository skills under `.agents/skills` and personal skills under
`$HOME/.agents/skills`. Clone or copy this directory to:

```text
$HOME/.agents/skills/cv-pdf-studio
```

Then invoke it explicitly with `$cv-pdf-studio`, or describe a matching CV task. See the
[official OpenAI skill documentation](https://learn.chatgpt.com/docs/build-skills).

### Other compatible agent hosts

Install the directory in the host's supported skills location. The runtime workflow avoids
host-specific absolute paths and file-presentation tool names.

## Requirements

- Python 3.9+
- A LaTeX engine, with `pdflatex` recommended
- Pillow for non-JPEG photo conversion: `pip install pillow`
- `pypdf`, `pdfinfo`, or a LaTeX log that exposes page count
- `pdftotext` or `pypdf` for ATS text QA

The build fails with an actionable error when a required check cannot run.

## Create the private master

Copy `assets/cv_master.example.json` to `assets/cv_master.json` and replace every fictional
value with verified candidate facts. Keep the IDs: they connect skills and generated claims to
specific achievements.

```text
python scripts/validate_master.py assets/cv_master.json --strict-provenance
```

The repository ignores the private master, photos, claim ledgers, fit matrices, and generated
PDFs by default.

Validate an application matrix and claim ledger before compiling:

```text
python scripts/validate_master.py assets/cv_master.json --strict-provenance \
  --fit-matrix work/fit_matrix_company.json \
  --claim-ledger work/claim_ledger_company.json
```

## Build and verify a PDF

```text
python scripts/build_pdf.py --tex work/cv_example_role.tex --out outputs \
  --max-pages 1 --check-text \
  --expect-text "Candidate Name" --expect-text "Target Role" \
  --expect-order "Most Recent Company" --expect-order "Older Company"
```

For an opted-in photo in the design format, add `--photo path/to/image`. The ATS template is
intentionally photo-free. The design template automatically expands its header when no photo is
provided.

Exit codes:

- `0`: PDF and requested checks passed
- `2`: LaTeX compilation failed
- `3`: selected page limit exceeded; an inspection PDF is retained
- `4`: invalid input, dependency, placeholder, photo, or page-count failure
- `5`: extracted-text QA failed; an inspection PDF is retained

## Project layout

```text
cv-pdf-studio/
├── SKILL.md
├── agents/openai.yaml
├── assets/
│   ├── cv_master.example.json
│   ├── claim_ledger.example.json
│   ├── fit_matrix.example.json
│   └── templates/
├── references/
├── scripts/
│   ├── build_pdf.py
│   └── validate_master.py
└── tests/
```

## Design principles

- Evidence before keywords
- A labelled target role instead of unearned seniority
- One page by default, two when meaningful experience justifies it
- Photo policy based on market, channel, and explicit consent
- Reverse chronology with relevance-based selection
- Qualitative outcomes accepted when no defensible metric exists
- No delivery without verified PDF, page, and requested ATS checks

## Tests

Run the existing unit tests from the repository root:

```sh
python -m unittest discover -s tests -v
```

GitHub Actions runs this suite on Python 3.9 and 3.14. The LaTeX integration
test is skipped when `pdflatex` is unavailable; a green core run does not
verify PDF compilation in that environment.

## License

MIT — see [LICENSE](LICENSE).
