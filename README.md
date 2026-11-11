# Emily K. Johnson - Professional Website & CV

Personal academic website for Emily K. Johnson, Assistant Professor at the Danish Centre for Health Economics, University of Southern Denmark.

Live site: [ekjohnson.com](https://ekjohnson.com)

## Where content lives

| To change | Edit |
|---|---|
| Home page text, positions, education | `index.qmd` |
| Research area text and project descriptions | `research.qmd` |
| Research area names, one-line summaries, which papers belong to which area, selected publications | `_assets/data/research.yml` |
| Works in progress, blog posts and other items not in Zotero | `_assets/data/research.yml` |
| Published papers | `_assets/bibliography/references.bib` (Zotero export) |
| CV content, talks, teaching | `cv/_cv-data.yml` |
| Colours, fonts, layout | `site.css` (page colours also in `theme.scss`) |

`build-site.py` runs before every render and generates the publications page, the CV (web page and PDF source), and the fragments in `_generated/` that the home, research and talks pages include.

## Project structure

```
_quarto.yml              # Site config (pre-render runs build-site.py)
build-site.py            # Generator
index.qmd                # Home page
research.qmd             # Research page
talks.qmd                # Talks and teaching (content generated from cv/_cv-data.yml)
publications.qmd         # Auto-generated, do not edit
site.css, theme.scss     # Styles

cv/
  _cv-data.yml           # CV content
  index.qmd              # Auto-generated HTML CV, do not edit
  cv-pdf.qmd             # Auto-generated Typst PDF source, do not edit

_assets/
  bibliography/references.bib   # Published papers (Zotero export)
  data/research.yml             # Research areas, tags, works in progress, commentary
  fonts/                        # Source Serif 4 and Source Sans 3 (SIL Open Font License)
  images/

_generated/              # Auto-generated page fragments (git-ignored)
cv-versions/             # CV snapshots for applications (see cv-versions/README.md)
docs/                    # Rendered site output (GitHub Pages)
```

## Adding a publication

### New peer-reviewed paper

1. Export BibTeX from Zotero into `_assets/bibliography/references.bib`.
2. In `_assets/data/research.yml`, add the citation key under the `pubs:` list of each research area it belongs to. A paper with no area still appears on the publications page and CV, without a tag.
3. Run `quarto render`.

### New work in progress

Add an entry under `in_progress:` in `_assets/data/research.yml`. When the paper is published and in Zotero, delete the entry; keep the same citation key in Zotero or update the key in the area lists.

### Commentary or blog post

- If the item is in Zotero: add its key under `commentary_keys:` in `research.yml`, with a label such as `"Commentary"`.
- If it is not in Zotero: add a full entry under `commentary:`.

These records are kept outside `references.bib` because a Zotero export overwrites that file and drops hand-added entries and keywords. `@unpublished` entries and `cv:other-media` keywords in the `.bib` are still recognised if present.

## How author lists are shown

Lists of up to 8 authors are shown in full. Longer lists show the first three authors, Johnson EK, and the last author. The standalone publication list generated for application snapshots shows up to 30 authors in full.

## Build commands

```bash
quarto render            # full site build (runs build-site.py first)
quarto preview           # preview with live reload
python3 build-site.py --snapshot cv-versions/YYYY-MM-purpose/   # CV + publication list snapshot
```

## License

Content &copy; Emily K. Johnson. All rights reserved. Fonts in `_assets/fonts/` are licensed under the SIL Open Font License.
