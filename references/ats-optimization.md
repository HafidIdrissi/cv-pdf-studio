# ATS optimization

Read this file before producing the single-column ATS format. Optimize for reliable parsing,
clear evidence, and human comprehension. Do not promise a universal or proprietary ATS score:
parsers and employer configurations differ.

## Parsing rules

- Use one linear body column with real selectable text.
- Keep contact details in the document body, never in a PDF header, footer, table, or text box.
- Use standard localized headings such as `EXPERIENCE`, `EDUCATION`, and `SKILLS`.
- Put each job title on a distinct line, followed by company, location, and one date range.
- Use consistent dates such as `MM/YYYY -- MM/YYYY` or localized month and year.
- Use plain bullets, familiar fonts, and readable type.
- Avoid photos, charts, skill bars, logos, decorative glyphs, and information encoded only by
  color or layout.
- Preserve Unicode extraction with the template's glyph-to-Unicode mapping.
- Verify the PDF with `build_pdf.py --check-text`, expected fields, and expected order.

## Evidence coverage

Build the fit matrix before writing. Prioritize must-have requirements, then differentiators.

- Copy an advertised term exactly when the candidate has matching evidence.
- Expand an acronym once when useful, then prefer the ad's form.
- Place a core proven skill in the skills section and, when supported, in an achievement that
  shows how it was used.
- Prefer one contextual use over repeated keyword lists.
- Do not target a fixed keyword count, percentage, or density.
- Do not add a technology solely because it appears in the ad.
- Do not infer years of experience by adding overlapping roles or occasional exposure.

## Headline integrity

Use the advertised title as a target headline only when it does not falsely imply a credential,
seniority level, or previously held role. Otherwise prefix it with `Target role:` or
`Poste ciblé :`, or use the closest truthful professional identity supported by the master.

## Honesty boundary

- Trace every candidate claim to master IDs.
- Keep `adjacent` evidence explicit: name the actual tool or context used.
- Keep `gap` items off the CV.
- Ask about `unclear` evidence before using it.
- Use only a metric attached to the same achievement being described.
- Accept qualitative outcomes when no defensible number exists.

## ATS delivery check

- [ ] Document contains selectable text and a single linear body column
- [ ] Name, contact details, titles, companies, and dates extract correctly
- [ ] Experience entries extract in reverse-chronological order
- [ ] Important proven requirements appear naturally with supporting context
- [ ] No photo, table, text box, chart, header, footer, or decorative skill rating is present
- [ ] No unproven title, skill, duration, metric, or credential is present
