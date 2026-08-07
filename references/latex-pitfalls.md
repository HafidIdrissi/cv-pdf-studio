# LaTeX safety and page strategy

## Encoding and special characters

The templates use UTF-8 input and T1 fonts. Keep source files in UTF-8 and escape LaTeX special
characters consistently.

| Character | Write |
|---|---|
| `%` | `\%` |
| `&` | `\&` |
| `#` | `\#` |
| `_` | `\_` |
| `$` | `\$` |
| `{` `}` | `\{` `\}` |
| `~` | `\textasciitilde{}` |
| `^` | `\textasciicircum{}` |
| `\` | `\textbackslash{}` |

Additional rules:

- Use `--` for a range and `---` for an em dash when the font pipeline makes raw punctuation
  unreliable.
- Use `\og ... \fg{}` for French quotation marks when needed.
- Use `\texteuro{}` or the currency word; do not assume `eurosym`.
- Use `~` only as a LaTeX non-breaking space in source, for example `35~\%`.
- Escape `&` in company names and query strings.
- Never leave a `{{PLACEHOLDER}}`; the build script rejects it.

## Photo handling

Keep the ATS template photo-free. For an opted-in design photo, pass the original image with
`--photo`; `build_pdf.py` converts it to a 3:4 RGB JPEG named `photo.jpg`. Without a photo, the
design template expands its header automatically.

## Page compression ladder

When the selected page limit is exceeded, rebuild after each change:

1. Remove the weakest bullet or redundant skill.
2. Rewrite wrapped bullets without losing evidence.
3. Remove a project or older entry that contributes no unique proof.
4. Shorten the summary or remove it when the headline already positions the candidate.
5. Tighten section and entry spacing slightly.
6. If the candidate genuinely needs more space under the length policy, switch from one to
   two pages and keep page one decisive.
7. Reduce font size only as a last resort, never below comfortable print and screen reading.

Do not pad a sparse page. Improve evidence selection and hierarchy; preserve whitespace when it
supports scanning.

## Supported packages

Rely on the packages already present in the templates. Do not introduce an additional font or
icon dependency without checking that the selected LaTeX engine can load it.
