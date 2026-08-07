---
name: cv-pdf-studio
description: >
  Create, tailor, rewrite, validate, and compile truthful CVs/resumes and cover letters as
  application-ready PDFs from a cv_master.json source of truth. Use when the user asks to
  make or adapt a CV, resume, curriculum vitae, cover letter, or lettre de motivation for a
  role; provides a job ad or job-ad URL with an intent to apply; requests an ATS-friendly
  version; or wants a previously produced application document reviewed or re-rendered.
  Support a linear ATS format and a two-column design format, choose length and photo policy
  for the candidate's experience, target market, and application channel, and never invent
  candidate evidence.
---

# CV PDF Studio

Produce a truthful, targeted CV PDF and, when requested, a matching cover-letter PDF. Treat
the master file as candidate evidence, the job ad as targeting context, and the fit matrix as
the bridge between them.

## Non-negotiables

1. Deliver a compiled PDF when the user requests a finished document; do not stop at `.tex`.
2. Trace every candidate claim to one or more IDs in `cv_master.json`. Never invent or inflate
   a skill, date, scope, metric, credential, title, or level of seniority.
3. Keep experiences and projects reverse-chronological within their sections. Let relevance
   decide inclusion and emphasis, not chronology.
4. Preserve honest gaps. Do not turn an adjacent skill into direct experience.
5. Treat ATS compatibility as parsing and evidence coverage, not as a guaranteed score.
6. Minimize personal data and never commit the private master file, photos, or generated CVs.

## Step 0 — Gather the inputs

1. Locate `assets/cv_master.json`. If it is absent, read
   `assets/cv_master.example.json`, explain that the private master is missing, and offer to
   build it from a CV or LinkedIn export supplied by the user. Do not generate from guesses.
2. Run `python scripts/validate_master.py assets/cv_master.json --strict-provenance`.
   Migrate legacy string bullets, metrics, or skills into evidence-bearing objects before
   drafting. Fix errors; discuss factual ambiguities with the user.
3. Read the job ad directly when pasted. Fetch a supplied URL. If no ad exists, ask for the
   target role, market, and seniority; produce a baseline CV only when that is what the user
   wants.
4. Locate an attached photo only if the chosen policy permits one. Never require a photo.
5. Determine the target country and application channel. If either is uncertain and affects
   photo, length, language, or personal-data conventions, ask one short question or verify
   current market guidance with authoritative sources.

## Step 1 — Choose the output policy

Use the user's explicit choices. Otherwise offer:

- **ATS** — single column, linear text, standard headings, no photo by default. Prefer this
  for portals and any unknown parsing pipeline.
- **Design** — two columns and optional photo. Prefer this for direct, human-first review
  when local conventions and the user support it.
- **Both** — identical evidence and targeting, rendered in both formats.

Ask in the same short prompt whether to include a cover letter.

Choose the CV length from the evidence:

- Default to one page for early-career and most mid-career candidates.
- Allow two pages when roughly 10+ years, leadership scope, technical depth, publications,
  or several directly relevant roles make the second page useful.
- Put decisive evidence on page one. Never shrink type below readable size just to preserve
  a one-page rule.
- Keep the cover letter to one page.

Apply this photo policy:

- ATS format: omit the photo by default.
- US, UK, and Canada: omit it unless the user has a specific, informed reason.
- France and other markets where photos may be accepted: make it opt-in, not automatic.
- Design format: include it only with the user's consent and a suitable image.

## Step 2 — Build the fit matrix

Extract the exact advertised title, responsibilities, hard skills, methodologies,
credentials, languages, seniority, must-haves, preferences, register, and ad language.

Create a working `fit_matrix_<company>.json` with one record per meaningful requirement:

```json
{
  "requirement": "Kubernetes",
  "priority": "must",
  "status": "proven",
  "master_refs": ["skill-kubernetes", "ach-aks-release"],
  "cv_action": "show_in_skills_and_experience",
  "notes": "Direct production evidence"
}
```

Use only these statuses:

- `proven` — direct evidence exists; include when important.
- `adjacent` — transferable evidence exists; describe only the true adjacent experience.
- `gap` — no evidence exists; keep it off the CV and report it.
- `unclear` — the master is ambiguous; ask before claiming it.

Do not target a fixed number or density of keywords. Cover the important proven requirements
in natural language, and place core terms both in skills and in evidence-bearing context when
truthful. Treat the advertised title as a target headline, not as a title the candidate
already holds. Add `Target role:` / `Poste ciblé :` when an exact title could otherwise
misrepresent seniority, licensing, or past experience.

Validate the matrix after drafting it:

```text
python scripts/validate_master.py assets/cv_master.json --strict-provenance \
  --fit-matrix <fit_matrix_company.json>
```

## Step 3 — Select and write

Read `references/writing-playbook.md` before drafting. For ATS output, also read
`references/ats-optimization.md`.

- Prioritize evidence that answers must-have requirements and differentiators.
- Keep enough career continuity for a recruiter to understand the timeline.
- Use the number of experiences and projects that the page strategy supports; do not enforce
  arbitrary quotas.
- Use metrics only when a matching achievement ID supports the number. A precise qualitative
  outcome is preferable to a weak or invented metric.
- Preserve the ad's language unless the user or target market requires another language.
- Honor exclusions and conditional-inclusion rules by their referenced IDs.
- Escape LaTeX content according to `references/latex-pitfalls.md`.

## Step 4 — Prepare the source

Copy the selected template into an environment-appropriate temporary working directory. Do
not edit templates in place and do not assume `/home/claude`, `/mnt/user-data`, or a specific
operating system.

Use:

- `assets/templates/cv_ats.tex` for ATS output. Keep it photo-free.
- `assets/templates/cv_twocolumn.tex` for design output. It automatically expands the header
  when `photo.jpg` is absent.
- `assets/templates/cover_letter.tex` for the letter.

Replace every `{{PLACEHOLDER}}`. Name final files with lowercase ASCII words and underscores:
`cv_<lastname>_<company>_<role>.pdf` and `letter_<lastname>_<company>.pdf`.

Maintain an application claim ledger alongside the working source. For each summary sentence
and bullet, record the supporting achievement, skill, experience, project, education, or
credential IDs. Resolve any claim without a source before compiling.

Validate it together with the fit matrix before building:

```text
python scripts/validate_master.py assets/cv_master.json --strict-provenance \
  --fit-matrix <fit_matrix_company.json> --claim-ledger <claim_ledger_company.json>
```

## Step 5 — Build and verify

Choose `--max-pages 1` or `--max-pages 2` from Step 1. Build an ATS CV with text checks:

```text
python scripts/build_pdf.py --tex <working-cv.tex> --out <output-dir> \
  --max-pages <1-or-2> --check-text \
  --expect-text "<candidate name>" --expect-text "<target title>" \
  --expect-order "<most recent company>" --expect-order "<older company>"
```

For an opted-in design photo, add `--photo <attached-image>`. Build a cover letter without
`--photo` and with `--max-pages 1`.

Interpret exit codes:

- `0` — compilation and requested checks passed.
- `2` — LaTeX compilation failed; fix the reported source error.
- `3` — page limit exceeded; apply the compression ladder in
  `references/latex-pitfalls.md`, or reconsider a justified two-page policy.
- `4` — input, dependency, placeholder, photo, or page-count validation failed.
- `5` — extracted-text QA failed; do not deliver the PDF.

After an exit `0`, inspect the rendered pages visually. Confirm readable type, balanced
spacing, unbroken links, no clipping, and a strong first-page hierarchy. For ATS output,
also inspect extracted text and confirm that contact details, titles, companies, and dates
remain in linear reading order.

## Step 6 — Deliver

Present PDFs through the environment's available file-delivery mechanism. Include editable
`.tex` files only when requested. Give a concise debrief containing:

- the target role, chosen format, page count, photo policy, and language;
- the strongest evidence-based adaptations;
- the important proven requirements now visible;
- the honest `gap` and `adjacent` items from the fit matrix;
- any claim that still requires the user's confirmation.

Never claim a proprietary ATS score. Say which parsing, evidence, page, and text-order checks
actually passed.

## Quality gate

- [ ] Master validation passed with strict provenance
- [ ] Every candidate claim has a master ID in the claim ledger
- [ ] Fit matrix distinguishes `proven`, `adjacent`, `gap`, and `unclear`
- [ ] Experience and project sections are reverse-chronological
- [ ] Headline cannot be mistaken for an unearned title or seniority level
- [ ] Length and photo follow the declared target-market policy
- [ ] No placeholder remains and LaTeX escaping is valid
- [ ] Build returned exit `0` with the intended page count
- [ ] ATS text extraction and expected order checks passed when requested
- [ ] Rendered pages passed visual inspection
- [ ] Debrief includes an honest gap report
