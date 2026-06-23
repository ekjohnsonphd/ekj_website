# CV Versions

Each subdirectory contains a static snapshot of the CV and publication list for a specific
application. Snapshots are generated from the master CV data (`cv/_cv-data.yml`) and
bibliography (`_assets/bibliography/references.bib`) at the time of application, then committed
to preserve an exact record of what was submitted.

## Directory naming convention

```
cv-versions/YYYY-MM-purpose/
```

Examples:
- `2026-02-sdu-postdoc/`
- `2026-06-nih-r01/`
- `2027-03-oxford-lecturer/`

## Files in each snapshot

| File | Contents |
|------|----------|
| `cv.qmd` | Full CV (Typst source, renders to PDF) |
| `publist.qmd` | Numbered publication list (Typst source, renders to PDF) |

## Workflow: creating a new application snapshot

**1. Update master CV data and bibliography as needed:**
```bash
# Edit cv/_cv-data.yml for non-publication content
# Edit _assets/bibliography/references.bib for new publications
```

**2. Generate the snapshot:**
```bash
python3 build-site.py --snapshot cv-versions/YYYY-MM-purpose/
```
This writes `cv.qmd` and `publist.qmd` into the new directory. It does NOT touch the
main website files (`publications.qmd`, `cv/index.qmd`, `cv/cv-pdf.qmd`).

**3. Render to PDF:**
```bash
quarto render cv-versions/YYYY-MM-purpose/cv.qmd
quarto render cv-versions/YYYY-MM-purpose/publist.qmd
```

**PDF output location (convention): rendered PDFs live in this same
`cv-versions/YYYY-MM-purpose/` folder, alongside their `.qmd` sources — NOT in
`docs/cv-versions/`.** `docs/` is the rendered *website* output; application snapshots
are standalone documents and belong next to their source. Keep each snapshot self-contained
in one folder. PDF filenames may be whatever reads well for submission (e.g.
`Emily Johnson CV.pdf`); only the location is fixed.

> Gotcha: running `quarto render` inside the repo triggers the project pre-render hook
> (`build-site.py`, needs PyYAML). If that errors, render from a scratch directory outside
> the repo and copy the PDFs back, or install `pyyaml`.

**4. Commit the snapshot:**
```bash
git add cv-versions/YYYY-MM-purpose/
git commit -m "Add CV snapshot for YYYY-MM purpose"
```
Commit only the `.qmd` source files. **PDFs are git-ignored repo-wide** (`**/*.pdf` in
`.gitignore`, with exceptions only for `cv/` and `docs/cv/`), so the rendered snapshot PDFs
stay local and won't appear in `git status` or on GitHub — that's expected.

## Editing snapshots after generation

The generated `.qmd` files are plain Typst-flavored Quarto documents. You can edit them
directly if you need application-specific tweaks (different summary statement, reordered
sections, etc.) without affecting the master CV. Re-render with `quarto render` after edits.

## Updating h-index

The h-index in the publication list header comes from `cv/_cv-data.yml`:
```yaml
pub_stats:
  h_index: 9   # update manually
```
Update this before generating a new snapshot.
