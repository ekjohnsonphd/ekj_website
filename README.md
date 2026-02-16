# Emily K. Johnson - Professional Website & CV

Personal academic website for Emily K. Johnson, PhD student in Health Economics at the University of Southern Denmark.

Live site: [ekjohnson.com](https://ekjohnson.com)

## Project structure

```
_quarto.yml              # Site config (pre-render runs build-site.py)
build-site.py            # Generates publications page + CV from references.bib
index.qmd                # Home page
research.qmd             # Research page
publications.qmd         # Auto-generated — do not edit
styles.css               # Site-wide styles

cv/
  _cv-data.yml           # CV content (education, experience, skills, etc.)
  index.qmd              # Auto-generated HTML CV — do not edit
  cv-pdf.qmd             # Auto-generated Typst PDF source — do not edit
  cv-pdf.pdf             # Rendered PDF (committed to repo)
  cv.css                 # CV page styles

_assets/
  bibliography/
    references.bib       # Single source of truth for all publications
    articles.bib         # Auto-generated filtered articles — do not edit
    apa.csl              # Citation style
  images/                # Profile photo
  includes/              # HTML includes (academic icons, etc.)

docs/                    # Rendered site output (GitHub Pages)
```

## Adding a new publication

All publications live in `_assets/bibliography/references.bib`. The `build-site.py` pre-render script reads this file and generates the publications page and CV automatically.

### New peer-reviewed paper (most common)

1. Export BibTeX from Zotero
2. Paste the entry into `_assets/bibliography/references.bib`
3. Run `quarto render`

That's it. The paper will appear on both the publications page and the CV.

### New GBD / consortium paper

1. Add an `@article` entry with a consortium author in double braces:
   ```bibtex
   @article{key,
     title = {Paper Title},
     author = {{GBD XXX Collaborators}},
     year = 2025,
     journal = {The Lancet},
     doi = {10.xxxx/xxxxx}
   }
   ```
2. Run `quarto render`

The double braces `{{ }}` tell BibTeX it's a corporate author. The build script detects "Collaborators" in the name and displays it as-is (no abbreviation).

### New work in progress

1. Add an `@unpublished` entry with a `note` field for status:
   ```bibtex
   @unpublished{key,
     title = {Paper Title},
     author = {Johnson, Emily K. and Coauthor, Name},
     year = 2025,
     note = {Manuscript under review}
   }
   ```
2. Run `quarto render`

This will appear in the "Works in progress" section of the CV only (not on the publications page). When the paper is published, change `@unpublished` to `@article`, add the `journal` field, and remove the `note`.

### New commentary or blog post

1. Add an `@article` entry with `keywords` to tag it:
   ```bibtex
   @article{key,
     title = {Article Title},
     author = {Johnson, Emily K. and Coauthor, Name},
     year = 2025,
     journal = {Journal Name},
     keywords = {cv:other-media, cv:type:commentary}
   }
   ```
   For a blog post, use `cv:type:blog-post` instead of `cv:type:commentary`.
2. Run `quarto render`

This will appear in the "Other Media" section of the CV only (not on the publications page).

## How categorization works

| Entry type | Keywords | Where it appears |
|---|---|---|
| `@article` | *(none needed)* | Publications page + CV "Peer reviewed" |
| `@article` | `cv:other-media, cv:type:commentary` | CV "Other Media" only |
| `@article` | `cv:other-media, cv:type:blog-post` | CV "Other Media" only |
| `@unpublished` | *(none needed)* | CV "Works in progress" only |
| `@inproceedings` | — | Neither (conference presentations are in `_cv-data.yml`) |
| `@software` | — | Neither |

## Updating non-publication CV content

Education, research experience, conference presentations, teaching, other experience, and skills are in `cv/_cv-data.yml`. Edit that file directly, then run `quarto render`.

## Build commands

```bash
# Full site build (runs build-site.py automatically as pre-render)
quarto render

# Preview with live reload
quarto preview

# Regenerate CV PDF only
python3 build-site.py && quarto render cv/cv-pdf.qmd
```

## Auto-generated files (do not edit)

These files are overwritten by `build-site.py` on every build:
- `publications.qmd`
- `_assets/bibliography/articles.bib`
- `cv/index.qmd`
- `cv/cv-pdf.qmd`

They are listed in `.gitignore` (except the rendered PDF which is committed).

## License

Content &copy; Emily K. Johnson. All rights reserved.
