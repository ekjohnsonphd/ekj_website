#!/usr/bin/env python3
"""
Unified pre-render script: generates publications page, CV HTML, and CV PDF
from references.bib + cv/_cv-data.yml.

Run automatically via quarto render (configured in _quarto.yml pre-render).

Usage:
  python3 build-site.py                              # normal site build
  python3 build-site.py --snapshot PATH/             # generate CV + publist snapshot
"""

import argparse
import json
import re
import yaml
from pathlib import Path

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

BIB_PATH = Path("_assets/bibliography/references.bib")
ARTICLES_BIB_PATH = Path("_assets/bibliography/articles.bib")
CV_DATA_PATH = Path("cv/_cv-data.yml")
PUBLICATIONS_QMD_PATH = Path("publications.qmd")
CV_HTML_PATH = Path("cv/index.qmd")
CV_PDF_PATH = Path("cv/cv-pdf.qmd")

# Submission dashboard
OBSIDIAN_TRACKER_PATH = Path("/Users/ejohnson/Documents/obsidian/Emily Obsidian/Project management system/Resources/Paper submission tracker.md")
SUBMISSION_DATA_PATH = Path("data/submissions.json")

# Maps old and new column header names → normalized field names
SUBMISSION_COL_MAP = {
    "paper": "paper",
    "authorship": "authorship",
    "journal": "journal",
    "submission date": "submission_date",
    "first submission date": "submission_date",
    "decision date": "decision_date",
    "final decision date": "decision_date",
    "status": "status",
    "final status": "status",
    "decision": "status",       # tracker uses "Decision" as the column name
    "notes": "notes",
}

AUTHOR_BOLD_SURNAME = "Johnson"
ET_AL_THRESHOLD = 20   # If >20 authors, show first 5 + et al. (CV / publications page)
ET_AL_SHOW = 5
PUBLIST_ET_AL_THRESHOLD = 30  # For publication list: ≤30 authors shown in full
PUBLIST_ET_AL_SHOW = 10       # For publication list: show first 10 if over threshold

# ---------------------------------------------------------------------------
# LaTeX / BibTeX cleaning
# ---------------------------------------------------------------------------

LATEX_ACCENTS = {
    r"\'e": "e", r"\'a": "a", r"\'i": "i", r"\'o": "o", r"\'u": "u",
    r"\"e": "e", r"\"a": "a", r"\"i": "i", r"\"o": "o", r"\"u": "u",
    r"\~n": "n", r"\~a": "a",
    r"\v{c}": "c", r"\v{s}": "s", r"\v{z}": "z",
}


def clean_latex(text):
    """Remove LaTeX formatting from text."""
    # Remove BibTeX title-casing markers: {{...}} → ...
    text = re.sub(r'\{\{(.+?)\}\}', r'\1', text)
    # Handle LaTeX accents: {\'e} or {\"{o}} etc.
    for pattern, replacement in LATEX_ACCENTS.items():
        text = text.replace("{" + pattern + "}", replacement)
        text = text.replace(pattern, replacement)
    # Handle \& → &
    text = text.replace(r"\&", "&")
    # Remove remaining single braces
    text = text.replace("{", "").replace("}", "")
    # Clean up double spaces
    text = re.sub(r'  +', ' ', text)
    return text.strip()


def clean_title_for_cv(text):
    """Clean title for CV display (no LaTeX, proper casing)."""
    # Remove {{...}} markers but keep content
    text = re.sub(r'\{\{(.+?)\}\}', r'\1', text)
    # Handle accents
    for pattern, replacement in LATEX_ACCENTS.items():
        text = text.replace("{" + pattern + "}", replacement)
        text = text.replace(pattern, replacement)
    # Handle \& → &
    text = text.replace(r"\&", "&")
    # Remove remaining braces
    text = text.replace("{", "").replace("}", "")
    # Normalize whitespace
    text = re.sub(r'\s+', ' ', text).strip()
    # Remove trailing period if present (we add our own punctuation)
    if text.endswith('.'):
        text = text[:-1]
    return text


# ---------------------------------------------------------------------------
# BibTeX parsing (regex-based, no external dependencies)
# ---------------------------------------------------------------------------

def parse_bib_file(path):
    """Parse a .bib file and return list of entry dicts."""
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()

    entries = []
    # Match complete bib entries: @type{key, ... }
    for match in re.finditer(r'@(\w+)\{([^,]*),\s*(.*?)\n\}', content, re.DOTALL):
        entry_type = match.group(1).lower()
        entry_key = match.group(2).strip()
        body = match.group(3)

        fields = {"_type": entry_type, "_key": entry_key, "_raw": match.group(0)}

        # Extract fields using brace-counting for nested values
        for field_match in re.finditer(r'(\w[\w-]*)\s*=\s*', body):
            name = field_match.group(1).lower()
            rest = body[field_match.end():]
            if rest.startswith('{'):
                # Brace-delimited value: count braces to find matching close
                depth = 0
                end = 0
                for i, ch in enumerate(rest):
                    if ch == '{':
                        depth += 1
                    elif ch == '}':
                        depth -= 1
                        if depth == 0:
                            end = i
                            break
                value = rest[1:end]  # Strip outer braces
            else:
                # Bare value (number, etc.)
                m = re.match(r'(\S+)', rest)
                value = m.group(1) if m else ""
            # Strip trailing comma
            if value and value.endswith(","):
                value = value[:-1]
            fields[name] = value

        entries.append(fields)

    return entries


def get_year(entry):
    """Extract year from entry (handles both 'year' and 'date' fields)."""
    if "year" in entry:
        m = re.search(r'(\d{4})', str(entry["year"]))
        return int(m.group(1)) if m else 0
    if "date" in entry:
        m = re.search(r'(\d{4})', entry["date"])
        return int(m.group(1)) if m else 0
    return 0


def get_keywords(entry):
    """Extract keywords as a set of stripped strings."""
    kw = entry.get("keywords", "")
    return {k.strip() for k in kw.split(",") if k.strip()}


def categorize(entry):
    """Return CV category: 'peer-reviewed', 'in-progress', 'other-media', or None."""
    etype = entry["_type"]
    keywords = get_keywords(entry)

    if etype == "unpublished":
        return "in-progress"
    if "cv:other-media" in keywords:
        return "other-media"
    if etype == "article":
        return "peer-reviewed"
    # inproceedings, software, etc. → excluded from CV publications
    return None


def get_media_type(entry):
    """Extract cv:type:xxx from keywords (e.g. 'commentary', 'blog-post')."""
    for kw in get_keywords(entry):
        if kw.startswith("cv:type:"):
            return kw[len("cv:type:"):]
    return ""


def is_for_publications_page(entry):
    """Should this entry appear on the publications page?"""
    etype = entry["_type"]
    keywords = get_keywords(entry)
    if etype != "article":
        return False
    if "cv:other-media" in keywords:
        return False
    return True


# ---------------------------------------------------------------------------
# Author formatting for CV
# ---------------------------------------------------------------------------

def is_consortium_author(author_str):
    """Detect consortium/collaborator group authors."""
    lower = author_str.lower()
    return "collaborator" in lower or "consortium" in lower or "network" in lower


def abbreviate_author(author_str):
    """Convert 'LastName, FirstName MiddleName' → 'LastName FI MI'.
    Handles particles (van, de, etc.) and consortium authors."""
    author_str = author_str.strip()

    # Consortium author (wrapped in braces or detected by name)
    if author_str.startswith("{") and author_str.endswith("}"):
        return clean_latex(author_str[1:-1])
    if is_consortium_author(author_str):
        return clean_latex(author_str)

    # Standard: "LastName, FirstName MiddleName"
    if "," in author_str:
        parts = author_str.split(",", 1)
        last = clean_latex(parts[0].strip())
        givens = clean_latex(parts[1].strip())
        # Get initials from given names
        initials = ""
        for name in givens.split():
            if name and name[0].isalpha():
                # Already an initial (e.g., "K.")
                initials += name[0].upper()
        return f"{last} {initials}" if initials else last
    else:
        # No comma — might be a single name or consortium
        return clean_latex(author_str)


def format_authors_cv(entry, bold=True):
    """Format full author list for CV display."""
    raw = entry.get("author", "")

    # Split on " and " (BibTeX author separator)
    authors = [a.strip() for a in re.split(r'\s+and\s+', raw) if a.strip()]

    # Apply et al. for very long author lists
    use_et_al = len(authors) > ET_AL_THRESHOLD
    if use_et_al:
        authors = authors[:ET_AL_SHOW]

    formatted = []
    for a in authors:
        abbrev = abbreviate_author(a)
        # Bold the target surname
        if bold and AUTHOR_BOLD_SURNAME in a and not is_consortium_author(a):
            formatted.append(f"**{abbrev}**")
        else:
            formatted.append(abbrev)

    result = ", ".join(formatted)
    if use_et_al:
        result += ", et al"

    return result


def format_authors_publist(entry, bold=True):
    """Format full author list for publication list (higher et al. threshold)."""
    raw = entry.get("author", "")

    authors = [a.strip() for a in re.split(r'\s+and\s+', raw) if a.strip()]

    use_et_al = len(authors) > PUBLIST_ET_AL_THRESHOLD
    if use_et_al:
        authors = authors[:PUBLIST_ET_AL_SHOW]

    formatted = []
    for a in authors:
        abbrev = abbreviate_author(a)
        if bold and AUTHOR_BOLD_SURNAME in a and not is_consortium_author(a):
            formatted.append(f"**{abbrev}**")
        else:
            formatted.append(abbrev)

    result = ", ".join(formatted)
    if use_et_al:
        result += ", et al"

    return result


def is_first_author(entry):
    """Check if Johnson is first author."""
    raw = entry.get("author", "")
    first = raw.split(" and ")[0].strip()
    return "Johnson, Emily" in first or "Johnson, E. K." in first


# ---------------------------------------------------------------------------
# Publication group filtering
# ---------------------------------------------------------------------------

def filter_pub_groups_for_cv(cv, pub_groups):
    """Apply cv_publications allowlist from cv-data if present.

    If cv['cv_publications'] is set, only entries whose bib key appears in
    the allowlist for that category are kept. Unlisted categories are unchanged.
    Returns a new dict; does not mutate the original.
    """
    cv_filter = cv.get("cv_publications")
    if not cv_filter:
        return dict(pub_groups)
    filtered = {}
    for cat, entries in pub_groups.items():
        allowed = cv_filter.get(cat)
        if allowed is not None:
            allowed_set = set(allowed)
            filtered[cat] = [e for e in entries if e["_key"] in allowed_set]
        else:
            filtered[cat] = list(entries)
    return filtered


# ---------------------------------------------------------------------------
# Publications page generation (publications.qmd + articles.bib)
# ---------------------------------------------------------------------------

def generate_publications_page(entries):
    """Generate publications.qmd and articles.bib from article entries."""
    # Filter to articles for the publications page
    pub_entries = [e for e in entries if is_for_publications_page(e)]
    pub_entries.sort(key=get_year, reverse=True)

    total_pubs = len(pub_entries)
    first_author_pubs = sum(1 for e in pub_entries if is_first_author(e))

    # Write articles.bib
    with open(ARTICLES_BIB_PATH, "w", encoding="utf-8") as f:
        for e in pub_entries:
            f.write(e["_raw"])
            f.write("\n\n")

    # Generate publications.qmd
    with open(PUBLICATIONS_QMD_PATH, "w", encoding="utf-8") as f:
        f.write(f"""---
title: "Publications"
bibliography: _assets/bibliography/articles.bib
csl: _assets/bibliography/apa.csl
nocite: '@*'
---

```{{=html}}
<style>
.pub-stats {{
  margin-bottom: 2em;
  padding-bottom: 1em;
  border-bottom: 2px solid #e0e0e0;
}}

.stat-grid {{
  display: flex;
  gap: 2em;
  flex-wrap: wrap;
}}

.stat-item {{
  display: inline-flex;
  align-items: baseline;
  gap: 0.5em;
}}

.stat-number {{
  font-size: 1.5em;
  font-weight: 700;
  color: #2c5282;
}}

.stat-label {{
  font-size: 0.9em;
  color: #666;
}}

.references {{
  margin-left: 0;
  padding-left: 0;
}}

.references .csl-entry {{
  margin-bottom: 1em;
  padding-bottom: 0.75em;
  border-bottom: 1px solid #e0e0e0;
  line-height: 1.6;
}}

.references .csl-entry:last-child {{
  border-bottom: none;
}}

.references .csl-entry em {{
  font-style: italic;
  color: #2c5282;
  font-weight: 500;
}}

.references .csl-entry strong {{
  color: #000;
  font-weight: 700;
}}

.references .csl-entry a {{
  color: #2563eb;
  text-decoration: none;
}}

.references .csl-entry a:hover {{
  text-decoration: underline;
}}
</style>
```

::: {{.pub-stats}}
::: {{.stat-grid}}
<div class="stat-item">
<span class="stat-number">{total_pubs}</span>
<span class="stat-label">publications</span>
</div>

<div class="stat-item">
<span class="stat-number">{first_author_pubs}</span>
<span class="stat-label">first author</span>
</div>

<div class="stat-item">
<span class="stat-number">9</span>
<span class="stat-label">h-index</span>
</div>
:::
:::

::: {{#refs}}
:::

```{{=html}}
<script>
document.addEventListener('DOMContentLoaded', function() {{
  const refs = document.getElementById('refs');
  if (refs) {{
    refs.innerHTML = refs.innerHTML
      .replace(/Johnson, E\\. K\\./g, '<strong>Johnson, E. K.</strong>')
      .replace(/Johnson, Emily K\\./g, '<strong>Johnson, Emily K.</strong>')
      .replace(/Johnson, Emily(?!<)/g, '<strong>Johnson, Emily</strong>');
  }}
}});
</script>
```
""")

    print(f"Generated publications page: {total_pubs} articles ({first_author_pubs} first-author)")


# ---------------------------------------------------------------------------
# CV HTML generation (cv/index.qmd)
# ---------------------------------------------------------------------------

def generate_cv_html(cv, pub_groups):
    """Generate cv/index.qmd from CV data + publications."""
    lines = []
    lines.append("<!-- AUTO-GENERATED by build-site.py — do not edit manually -->")
    lines.append("---")
    lines.append('title: "Curriculum Vitae"')
    lines.append("toc: true")
    lines.append("toc-depth: 2")
    lines.append("page-navigation: false")
    lines.append("format:")
    lines.append("  html:")
    lines.append("    css: cv.css")
    lines.append("---")
    lines.append("")

    # Header
    lines.append("::: {.cv-header}")
    lines.append(f"# {cv['name']}")
    lines.append("::: {.cv-links}")
    lines.append(f"[LinkedIn]({cv['links']['linkedin']}) | [ResearchGate]({cv['links']['researchgate']})")
    lines.append(":::")
    lines.append(":::")
    lines.append("")

    # Download button
    lines.append("::: {.cv-download}")
    lines.append("[{{< fa file-pdf >}} Download PDF](cv-pdf.pdf){.btn .btn-primary}")
    lines.append(":::")
    lines.append("")

    # Summary
    lines.append("## Summary {.cv-section}")
    lines.append("")
    lines.append("::: {.cv-summary}")
    lines.append(cv["summary"].strip())
    lines.append(":::")
    lines.append("")

    # Education
    lines.append("## Education {.cv-section}")
    lines.append("")
    for edu in cv["education"]:
        loc = edu["location"]
        if "honors" in edu:
            loc += f" | {edu['honors']}"
        lines.append("::: {.cv-entry}")
        lines.append("::: {.cv-entry-header}")
        lines.append(f"[**{edu['institution']}**]{{.cv-institution}}")
        lines.append(f"[{loc}]{{.cv-location}}")
        lines.append(":::")
        lines.append("::: {.cv-position}")
        lines.append(f"[*{edu['degree']}*]{{.cv-title}}")
        lines.append(f"[{edu['date']}]{{.cv-dates}}")
        lines.append(":::")
        if "details" in edu:
            lines.append("")
            for d in edu["details"]:
                lines.append(f"- {d}")
        lines.append(":::")
        lines.append("")

    # Publications
    lines.append("## Publications {.cv-section}")
    lines.append("")

    if pub_groups["peer-reviewed"]:
        lines.append("### Peer reviewed publications")
        lines.append("")
        lines.append("*All authors listed from first to last*")
        lines.append("")
        for entry in pub_groups["peer-reviewed"]:
            authors = format_authors_cv(entry)
            title = clean_title_for_cv(entry.get("title", ""))
            journal = clean_latex(entry.get("journal", ""))
            year = get_year(entry)
            note = entry.get("note", "")
            note_str = f" ({note})" if note else ""
            lines.append("::: {.cv-publication}")
            lines.append(f"{authors}. {title}. *{journal}*. {year}{note_str}.")
            lines.append(":::")
            lines.append("")

    if pub_groups["in-progress"]:
        lines.append("### Works in progress")
        lines.append("")
        for entry in pub_groups["in-progress"]:
            authors = format_authors_cv(entry)
            title = clean_title_for_cv(entry.get("title", ""))
            status = entry.get("note", "")
            lines.append("::: {.cv-publication}")
            lines.append(f"{authors}. {title}. {status}.")
            lines.append(":::")
            lines.append("")

    if pub_groups["other-media"]:
        lines.append("### Other Media")
        lines.append("")
        for entry in pub_groups["other-media"]:
            authors = format_authors_cv(entry)
            title = clean_title_for_cv(entry.get("title", ""))
            journal = clean_latex(entry.get("journal", ""))
            year = get_year(entry)
            media_type = get_media_type(entry).replace("-", " ")
            lines.append("::: {.cv-publication}")
            lines.append(f"{authors}. {title}. *{journal}* ({media_type}). {year}.")
            lines.append(":::")
            lines.append("")

    # Research Experience
    lines.append("## Research Experience {.cv-section}")
    lines.append("")
    for inst in cv["research_experience"]:
        lines.append("::: {.cv-entry}")
        lines.append("::: {.cv-entry-header}")
        lines.append(f"[**{inst['institution']}**]{{.cv-institution}}")
        lines.append(f"[{inst['location']}]{{.cv-location}}")
        lines.append(":::")
        for pos in inst["positions"]:
            lines.append("::: {.cv-position}")
            lines.append(f"[*{pos['title']}*]{{.cv-title}}")
            lines.append(f"[{pos['dates']}]{{.cv-dates}}")
            lines.append(":::")
            if "details" in pos:
                lines.append("")
                for d in pos["details"]:
                    lines.append(f"- {d}")
        lines.append(":::")
        lines.append("")

    # Conference Presentations
    lines.append("## Conference Presentations {.cv-section}")
    lines.append("")
    for pres in cv["conference_presentations"]:
        lines.append("::: {.cv-entry}")
        lines.append(f"{pres['authors']}. *{pres['title']}*")
        lines.append("")
        lines.append("::: {.cv-venues}")
        for v in pres["venues"]:
            lines.append(f"- {v}")
        lines.append(":::")
        lines.append(":::")
        lines.append("")

    # Teaching Experience
    lines.append("## Teaching Experience {.cv-section}")
    lines.append("")
    for inst in cv["teaching_experience"]:
        lines.append("::: {.cv-entry}")
        lines.append("::: {.cv-entry-header}")
        lines.append(f"[**{inst['institution']}**]{{.cv-institution}}")
        lines.append(f"[{inst['location']}]{{.cv-location}}")
        lines.append(":::")
        for role in inst["roles"]:
            lines.append("::: {.cv-position}")
            lines.append(f"[*{role['title']}*]{{.cv-title}}")
            lines.append(f"[{role['date']}]{{.cv-dates}}")
            lines.append(":::")
        lines.append(":::")
        lines.append("")

    # Other Professional Experience
    lines.append("## Other Professional Experience {.cv-section}")
    lines.append("")
    for org in cv["other_experience"]:
        lines.append("::: {.cv-entry}")
        lines.append("::: {.cv-entry-header}")
        lines.append(f"[**{org['organization']}**]{{.cv-institution}}")
        lines.append(f"[{org['location']}]{{.cv-location}}")
        lines.append(":::")
        for pos in org["positions"]:
            lines.append("::: {.cv-position}")
            lines.append(f"[*{pos['title']}*]{{.cv-title}}")
            lines.append(f"[{pos['dates']}]{{.cv-dates}}")
            lines.append(":::")
            if "details" in pos:
                lines.append("")
                for d in pos["details"]:
                    lines.append(f"- {d}")
        lines.append(":::")
        lines.append("")

    # Skills
    lines.append("## Skills {.cv-section}")
    lines.append("")
    lines.append("::: {.cv-skills}")
    for skill in cv["skills"]:
        lines.append(f"- {skill}")
    lines.append(":::")
    lines.append("")

    with open(CV_HTML_PATH, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    print(f"Generated {CV_HTML_PATH}")


# ---------------------------------------------------------------------------
# CV PDF generation (cv/cv-pdf.qmd, Typst format)
# ---------------------------------------------------------------------------

def generate_cv_pdf(cv, pub_groups, output_path=None):
    """Generate cv/cv-pdf.qmd from CV data + publications.

    output_path: if given, write to that Path instead of CV_PDF_PATH.
    """
    out = Path(output_path) if output_path else CV_PDF_PATH
    lines = []

    # YAML front matter for Typst PDF
    lines.append("---")
    lines.append('title: ""')
    lines.append("format:")
    lines.append("  typst:")
    lines.append("    margin:")
    lines.append('      x: "1in"')
    lines.append('      y: "0.75in"')
    lines.append("    fontsize: 10pt")
    lines.append('    mainfont: "Libertinus Serif"')
    lines.append('    sansfont: "Libertinus Sans"')
    lines.append("bibliography: []")
    lines.append("citeproc: false")
    lines.append("---")
    lines.append("")

    # Custom Typst header block
    lines.append("```{=typst}")
    lines.append('#set page(numbering: "1")')
    lines.append("#set par(justify: true)")
    lines.append("#set text(size: 10pt)")
    lines.append("")
    lines.append("// Section heading style")
    lines.append('#show heading.where(level: 1): it => {')
    lines.append('  set text(size: 11pt, weight: "bold")')
    lines.append("  v(0.6em)")
    lines.append('  upper(text(tracking: 0.1em, it.body))')
    lines.append("  v(-0.2em)")
    lines.append('  line(length: 100%, stroke: 0.5pt)')
    lines.append("  v(0.3em)")
    lines.append("}")
    lines.append("")
    lines.append('#show heading.where(level: 2): it => {')
    lines.append('  set text(size: 10pt, weight: "bold")')
    lines.append("  v(0.3em)")
    lines.append("  it.body")
    lines.append("  v(0.1em)")
    lines.append("}")
    lines.append("")
    # Name header
    lines.append('#align(center)[')
    lines.append(f'  #text(size: 24pt, weight: "bold")[{cv["name"]}]')
    lines.append("  \\")
    lines.append(f'  #link("{cv["links"]["linkedin"]}")[Linkedin]')
    lines.append(f'  | #link("{cv["links"]["researchgate"]}")[ResearchGate]')
    lines.append("]")
    lines.append("```")
    lines.append("")

    # Summary
    lines.append("# Summary")
    lines.append("")
    lines.append(cv["summary"].strip())
    lines.append("")

    # Education
    lines.append("# Education")
    lines.append("")
    for edu in cv["education"]:
        honors = f"  {edu['honors']}" if "honors" in edu else ""
        lines.append("```{=typst}")
        lines.append(f'#grid(columns: (1fr, auto), align: (left, right),')
        lines.append(f'  [*{edu["institution"]}*], [{edu["location"]},{honors}]')
        lines.append(f')')
        lines.append(f'#grid(columns: (1fr, auto), align: (left, right),')
        lines.append(f'  [_{edu["degree"]}_], [{edu["date"]}]')
        lines.append(f')')
        lines.append("```")
        if "details" in edu:
            lines.append("")
            for d in edu["details"]:
                d_typst = d.replace("**", "*")
                lines.append(f"- {d_typst}")
        lines.append("")

    # Publications
    lines.append("# Publications")
    lines.append("")
    if pub_groups["peer-reviewed"]:
        lines.append("## Peer reviewed publications")
        lines.append("")
        lines.append("*All authors listed from first to last*")
        lines.append("")
        for entry in pub_groups["peer-reviewed"]:
            authors = format_authors_cv(entry)
            title = clean_title_for_cv(entry.get("title", ""))
            journal = clean_latex(entry.get("journal", ""))
            year = get_year(entry)
            note = entry.get("note", "")
            note_str = f" ({note})" if note else ""
            lines.append(f'{authors}. {title}. *{journal}*. {year}{note_str}.')
            lines.append("")

    if pub_groups["in-progress"]:
        lines.append("## Works in progress")
        lines.append("")
        for entry in pub_groups["in-progress"]:
            authors = format_authors_cv(entry)
            title = clean_title_for_cv(entry.get("title", ""))
            status = entry.get("note", "")
            lines.append(f'{authors}. {title}. {status}.')
            lines.append("")

    if pub_groups["other-media"]:
        lines.append("## Other Media")
        lines.append("")
        for entry in pub_groups["other-media"]:
            authors = format_authors_cv(entry)
            title = clean_title_for_cv(entry.get("title", ""))
            journal = clean_latex(entry.get("journal", ""))
            year = get_year(entry)
            media_type = get_media_type(entry).replace("-", " ")
            lines.append(f'{authors}. {title}. *{journal}* ({media_type}). {year}.')
            lines.append("")

    # Research Experience
    lines.append("# Research Experience")
    lines.append("")
    for inst in cv["research_experience"]:
        lines.append("```{=typst}")
        lines.append(f'#grid(columns: (1fr, auto), align: (left, right),')
        lines.append(f'  [*{inst["institution"]}*], [{inst["location"]}]')
        lines.append(f')')
        lines.append("```")
        for pos in inst["positions"]:
            lines.append("```{=typst}")
            lines.append(f'#grid(columns: (1fr, auto), align: (left, right),')
            lines.append(f'  [_{pos["title"]}_], [{pos["dates"]}]')
            lines.append(f')')
            lines.append("```")
            if "details" in pos:
                lines.append("")
                for d in pos["details"]:
                    lines.append(f"- {d}")
        lines.append("")

    # Conference Presentations
    lines.append("# Conference Presentations")
    lines.append("")
    for pres in cv["conference_presentations"]:
        lines.append(f'{pres["authors"]}. *{pres["title"]}*')
        lines.append("")
        for v in pres["venues"]:
            lines.append(f"- {v}")
        lines.append("")

    # Teaching Experience
    lines.append("# Teaching Experience")
    lines.append("")
    for inst in cv["teaching_experience"]:
        lines.append("```{=typst}")
        lines.append(f'#grid(columns: (1fr, auto), align: (left, right),')
        lines.append(f'  [*{inst["institution"]}*], [{inst["location"]}]')
        lines.append(f')')
        lines.append("```")
        for role in inst["roles"]:
            lines.append("```{=typst}")
            lines.append(f'#grid(columns: (1fr, auto), align: (left, right),')
            lines.append(f'  [_{role["title"]}_], [{role["date"]}]')
            lines.append(f')')
            lines.append("```")
        lines.append("")

    # Other Professional Experience
    lines.append("# Other Professional Experience")
    lines.append("")
    for org in cv["other_experience"]:
        lines.append("```{=typst}")
        lines.append(f'#grid(columns: (1fr, auto), align: (left, right),')
        lines.append(f'  [*{org["organization"]}*], [{org["location"]}]')
        lines.append(f')')
        lines.append("```")
        for pos in org["positions"]:
            lines.append("```{=typst}")
            lines.append(f'#grid(columns: (1fr, auto), align: (left, right),')
            lines.append(f'  [_{pos["title"]}_], [{pos["dates"]}]')
            lines.append(f')')
            lines.append("```")
        lines.append("")

    # Skills
    lines.append("# Skills")
    lines.append("")
    for skill in cv["skills"]:
        lines.append(f"- {skill}")
    lines.append("")

    with open(out, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    print(f"Generated {out}")


# ---------------------------------------------------------------------------
# Publication list generation (standalone numbered Typst PDF)
# ---------------------------------------------------------------------------

def generate_publist_typst(cv, pub_groups, output_path):
    """Generate a standalone numbered publication list as a Typst .qmd file."""
    output_path = Path(output_path)
    output_path.mkdir(parents=True, exist_ok=True)
    out_file = output_path / "publist.qmd"

    peer = pub_groups["peer-reviewed"]
    inprog = pub_groups["in-progress"]
    other = pub_groups["other-media"]

    total_peer = len(peer)
    first_author = sum(1 for e in peer if is_first_author(e))
    h_index = cv.get("pub_stats", {}).get("h_index")

    lines = []

    # YAML front matter
    lines.append("---")
    lines.append('title: ""')
    lines.append("format:")
    lines.append("  typst:")
    lines.append("    margin:")
    lines.append('      x: "1in"')
    lines.append('      y: "0.75in"')
    lines.append("    fontsize: 10pt")
    lines.append('    mainfont: "Libertinus Serif"')
    lines.append('    sansfont: "Libertinus Sans"')
    lines.append("bibliography: []")
    lines.append("citeproc: false")
    lines.append("---")
    lines.append("")

    # Typst preamble + header
    lines.append("```{=typst}")
    lines.append('#set page(numbering: "1")')
    lines.append("#set par(justify: true)")
    lines.append("#set text(size: 10pt)")
    lines.append("")
    lines.append('#show heading.where(level: 1): it => {')
    lines.append('  set text(size: 11pt, weight: "bold")')
    lines.append("  v(0.6em)")
    lines.append('  upper(text(tracking: 0.1em, it.body))')
    lines.append("  v(-0.2em)")
    lines.append('  line(length: 100%, stroke: 0.5pt)')
    lines.append("  v(0.3em)")
    lines.append("}")
    lines.append("")
    lines.append('#show heading.where(level: 2): it => {')
    lines.append('  set text(size: 10pt, weight: "bold")')
    lines.append("  v(0.3em)")
    lines.append("  it.body")
    lines.append("  v(0.1em)")
    lines.append("}")
    lines.append("")
    lines.append('#align(center)[')
    lines.append(f'  #text(size: 24pt, weight: "bold")[{cv["name"]}]')
    lines.append("  \\")
    lines.append(f'  #link("{cv["links"]["linkedin"]}")[LinkedIn]')
    lines.append(f'  | #link("{cv["links"]["researchgate"]}")[ResearchGate]')
    lines.append("]")
    lines.append("")

    # Publication summary stats
    stats_parts = [f"{total_peer} peer-reviewed publications", f"{first_author} first-author"]
    if h_index is not None:
        stats_parts.append(f"h-index: {h_index}")
    lines.append(f'#align(center)[_{" · ".join(stats_parts)}_]')
    lines.append("```")
    lines.append("")

    # Peer Reviewed
    lines.append("# Peer Reviewed Publications")
    lines.append("")
    lines.append("*All authors listed from first to last*")
    lines.append("")
    for i, entry in enumerate(peer, start=1):
        authors = format_authors_publist(entry)
        title = clean_title_for_cv(entry.get("title", ""))
        journal = clean_latex(entry.get("journal", ""))
        year = get_year(entry)
        note = entry.get("note", "")
        note_str = f" ({note})" if note else ""
        lines.append(f'{i}. {authors}. "{title}." *{journal}*. {year}{note_str}.')
        lines.append("")

    # Works in Progress
    if inprog:
        lines.append("# Works in Progress")
        lines.append("")
        for i, entry in enumerate(inprog, start=1):
            authors = format_authors_publist(entry)
            title = clean_title_for_cv(entry.get("title", ""))
            status = entry.get("note", "")
            lines.append(f'{i}. {authors}. "{title}." {status}.')
            lines.append("")

    # Other Media
    if other:
        lines.append("# Other Media")
        lines.append("")
        for i, entry in enumerate(other, start=1):
            authors = format_authors_publist(entry)
            title = clean_title_for_cv(entry.get("title", ""))
            journal = clean_latex(entry.get("journal", ""))
            year = get_year(entry)
            media_type = get_media_type(entry).replace("-", " ")
            lines.append(f'{i}. {authors}. "{title}." *{journal}* ({media_type}). {year}.')
            lines.append("")

    with open(out_file, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    print(f"Generated {out_file}")


def generate_snapshot_cv(cv, pub_groups, output_path):
    """Generate cv.qmd snapshot into output_path/ using the standard CV PDF template."""
    output_path = Path(output_path)
    output_path.mkdir(parents=True, exist_ok=True)
    generate_cv_pdf(cv, pub_groups, output_path=output_path / "cv.qmd")


# ---------------------------------------------------------------------------
# Submission dashboard data generation
# ---------------------------------------------------------------------------

def parse_submission_tracker(path):
    """Read the Obsidian paper submission tracker markdown file.

    Finds the first markdown table in the file and parses it into a list of
    dicts. Accepts both the old column names (First submission date / Final
    decision date / Final status) and the new ones (Submission date / Decision
    date / Status). Wikilinks ([[Title]]) are stripped to plain text. Blank
    cells are stored as None.
    """
    try:
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
    except FileNotFoundError:
        print(f"Warning: Submission tracker not found at {path}; skipping dashboard data.")
        return []

    # Collect the first contiguous block of pipe-delimited lines
    table_lines = []
    for line in content.splitlines():
        stripped = line.strip()
        if stripped.startswith("|") and stripped.endswith("|"):
            table_lines.append(stripped)
        elif table_lines:
            break  # end of table block

    if len(table_lines) < 3:
        print("Warning: No valid table found in submission tracker (need ≥ header + separator + 1 row).")
        return []

    # Header row → normalized column names
    raw_headers = [h.strip() for h in table_lines[0].split("|")[1:-1]]
    cols = [SUBMISSION_COL_MAP.get(h.lower(), h.lower().replace(" ", "_")) for h in raw_headers]

    # table_lines[1] is the separator row (| --- | --- |); skip it
    rows = []
    for line in table_lines[2:]:
        cells = [c.strip() for c in line.split("|")[1:-1]]
        if len(cells) < len(cols):
            continue
        row = {}
        for col, cell in zip(cols, cells[:len(cols)]):
            cell = re.sub(r'\[\[(.+?)\]\]', r'\1', cell)  # strip Obsidian wikilinks
            val = cell if cell else None
            # Normalize categorical fields to lowercase for consistent JS lookup
            if col in ("authorship", "status") and val:
                val = val.lower()
            row[col] = val
        rows.append(row)

    return rows


def generate_submission_data(rows):
    """Write submission rows to JSON for the dashboard page."""
    SUBMISSION_DATA_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(SUBMISSION_DATA_PATH, "w", encoding="utf-8") as f:
        json.dump(rows, f, indent=2, ensure_ascii=False)
    print(f"Generated {SUBMISSION_DATA_PATH} ({len(rows)} submission rows)")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Build site files from bib + CV data.")
    parser.add_argument(
        "--snapshot", metavar="PATH",
        help="Generate a CV + publication list snapshot into PATH/ instead of the normal site build.",
    )
    args = parser.parse_args()

    # Parse bibliography
    entries = parse_bib_file(BIB_PATH)
    print(f"Parsed {len(entries)} entries from {BIB_PATH}")

    # Load CV data (non-publication sections)
    with open(CV_DATA_PATH, "r", encoding="utf-8") as f:
        cv = yaml.safe_load(f)

    # Group publications for CV
    pub_groups = {"peer-reviewed": [], "in-progress": [], "other-media": []}
    for entry in entries:
        cat = categorize(entry)
        if cat and cat in pub_groups:
            pub_groups[cat].append(entry)

    # Sort each group by year descending
    for group in pub_groups.values():
        group.sort(key=get_year, reverse=True)

    # Apply CV publication filter (publist always gets all publications)
    cv_pub_groups = filter_pub_groups_for_cv(cv, pub_groups)

    if args.snapshot:
        # Snapshot mode: write cv.qmd and publist.qmd to the given directory
        generate_snapshot_cv(cv, cv_pub_groups, args.snapshot)
        generate_publist_typst(cv, pub_groups, args.snapshot)
    else:
        # Normal site build
        generate_publications_page(entries)
        generate_cv_html(cv, cv_pub_groups)
        generate_cv_pdf(cv, cv_pub_groups)
        submissions = parse_submission_tracker(OBSIDIAN_TRACKER_PATH)
        generate_submission_data(submissions)


if __name__ == "__main__":
    main()
