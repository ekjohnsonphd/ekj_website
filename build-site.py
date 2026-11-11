#!/usr/bin/env python3
"""
Unified pre-render script. Reads references.bib, cv/_cv-data.yml and
_assets/data/research.yml and generates the publications page, the CV (HTML
and Typst PDF source), and the fragments in _generated/ that the hand-written
pages include.

Run automatically via quarto render (configured in _quarto.yml pre-render).

Usage:
  python3 build-site.py                              # normal site build
  python3 build-site.py --snapshot PATH/             # generate CV + publist snapshot
"""

import argparse
import html
import json
import os
import re
import unicodedata
import yaml
from pathlib import Path

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

BIB_PATH = Path("_assets/bibliography/references.bib")
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

LATEX_ACCENT_MARKS = {"'": "\u0301", '"': "\u0308", "~": "\u0303", "`": "\u0300", "^": "\u0302",
                      "v": "\u030c", "c": "\u0327"}


def _accent(match):
    mark = LATEX_ACCENT_MARKS.get(match.group(1))
    return unicodedata.normalize("NFC", match.group(2) + mark) if mark else match.group(2)


def convert_accents(text):
    """LaTeX accents to Unicode: {\\"o} -> ö, \\'e -> é, \\v{c} -> č."""
    text = re.sub(r"""\{?\\(['"~`^])\{?([A-Za-z])\}?\}?""", _accent, text)
    text = re.sub(r"\{?\\([vc])\{([A-Za-z])\}\}?", _accent, text)
    return text


def clean_latex(text):
    """Remove LaTeX formatting from text."""
    # Remove BibTeX title-casing markers: {{...}} → ...
    text = re.sub(r'\{\{(.+?)\}\}', r'\1', text)
    # Handle LaTeX accents: {\'e} or {\"{o}} etc.
    text = convert_accents(text)
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
    text = convert_accents(text)
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
# Research areas and publication records (from _assets/data/research.yml)
# ---------------------------------------------------------------------------

RESEARCH_DATA_PATH = Path("_assets/data/research.yml")
GENERATED_DIR = Path("_generated")
FONT_DIR = Path("_assets/fonts")
TALKS_INCLUDE = "talks.md"

ABBREV_THRESHOLD = 8   # author lists longer than this are abbreviated around Johnson EK
ABBREV_LEAD = 3

MONTHS = {m: i for i, m in enumerate(
    ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"], start=1)}

JOURNAL_FIX = {"PLoS medicine": "PLOS Medicine"}


def load_research():
    with open(RESEARCH_DATA_PATH, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def _yaml_entry(item, etype):
    """Turn a YAML publication record into the same shape as a parsed bib entry."""
    entry = {k: str(v) for k, v in item.items() if k != "key"}
    entry["_type"] = etype
    entry["_key"] = item["key"]
    return entry


def sort_key(entry):
    return (get_year(entry), MONTHS.get(str(entry.get("month", "")).lower()[:3], 0))


def build_pub_groups(entries, research):
    """Group publications into peer-reviewed / in-progress / other-media.

    Sources, in order: references.bib, then the in_progress and commentary
    lists in research.yml (skipped if the key is already in the bib).
    """
    commentary_keys = research.get("commentary_keys") or {}
    groups = {"peer-reviewed": [], "in-progress": [], "other-media": []}
    seen = set()

    for entry in entries:
        key = entry["_key"]
        if key in commentary_keys:
            entry["_kind"] = commentary_keys[key]
            groups["other-media"].append(entry)
            seen.add(key)
            continue
        cat = categorize(entry)
        if cat is None:
            continue
        if cat == "other-media":
            entry["_kind"] = get_media_type(entry).replace("-", " ").capitalize()
        groups[cat].append(entry)
        seen.add(key)

    for item in research.get("in_progress") or []:
        if item["key"] not in seen:
            groups["in-progress"].append(_yaml_entry(item, "unpublished"))
    for item in research.get("commentary") or []:
        if item["key"] not in seen:
            entry = _yaml_entry(item, "article")
            entry["_kind"] = item.get("kind", "Commentary")
            groups["other-media"].append(entry)

    for group in groups.values():
        group.sort(key=sort_key, reverse=True)
    return groups


def areas_by_key(research):
    """Map citation key -> list of area ids, in site order."""
    out = {}
    for area in research["areas"]:
        for key in area.get("pubs") or []:
            out.setdefault(key, []).append(area["id"])
    return out


def check_area_keys(research, groups):
    known = {e["_key"] for g in groups.values() for e in g}
    for area in research["areas"]:
        for key in area.get("pubs") or []:
            if key not in known:
                print(f"Warning: research.yml area '{area['id']}' lists unknown key '{key}'")
    for key in research.get("selected") or []:
        if key not in known:
            print(f"Warning: research.yml 'selected' lists unknown key '{key}'")


# ---------------------------------------------------------------------------
# Shared publication formatting
# ---------------------------------------------------------------------------

def author_tokens(entry):
    """Author list as tokens: (text, is_me) tuples, with '…' / 'et al.' strings
    where a long list is abbreviated. Long lists keep the first three authors,
    Johnson EK, and the last author."""
    raw = entry.get("author", "")
    authors = [a.strip() for a in re.split(r'\s+and\s+', raw) if a.strip()]
    toks = [(abbreviate_author(a), AUTHOR_BOLD_SURNAME + ", E" in a and not is_consortium_author(a))
            for a in authors]
    n = len(toks)
    if n <= ABBREV_THRESHOLD:
        return toks
    me = next((i for i, t in enumerate(toks) if t[1]), None)
    out = toks[:ABBREV_LEAD]
    if me is None or me < ABBREV_LEAD:
        return out + ["et al."]
    out.append("…")
    out.append(toks[me])
    if me < n - 1:
        if me < n - 2:
            out.append("…")
        out.append(toks[-1])
    return out


def authors_md(entry):
    return ", ".join(t if isinstance(t, str) else (f"**{t[0]}**" if t[1] else t[0])
                     for t in author_tokens(entry))


def authors_html(entry):
    return ", ".join(t if isinstance(t, str) else
                     (f"<strong>{html.escape(t[0])}</strong>" if t[1] else html.escape(t[0]))
                     for t in author_tokens(entry))


def pub_title(entry):
    return clean_title_for_cv(entry.get("title", "")).replace("--", "–")


def pub_journal(entry):
    journal = clean_latex(entry.get("journal", ""))
    return JOURNAL_FIX.get(journal, journal)


def pub_url(entry):
    if entry.get("doi"):
        return "https://doi.org/" + entry["doi"]
    return entry.get("url", "")


def pub_item_html(entry, key_areas, area_titles, tags=True, year_gutter=True):
    """One publication as an <li>. Used on the home, research and publications pages."""
    key = entry["_key"]
    ids = key_areas.get(key, [])
    title = html.escape(pub_title(entry))
    url = pub_url(entry)
    title_html = f'<a href="{html.escape(url)}">{title}</a>' if url else title

    meta = []
    journal = pub_journal(entry)
    if journal:
        meta.append(f"<em>{html.escape(journal)}</em>")
    if entry["_type"] == "unpublished":
        meta.append(html.escape(entry.get("note", "In preparation")))
    elif not year_gutter:
        meta.append(str(get_year(entry)))
    if entry.get("_kind"):
        meta.append(html.escape(entry["_kind"]))
    meta_html = ", ".join(meta)

    tag_html = ""
    if tags and ids:
        links = " ".join(
            f'<a class="pub-tag" href="research.html#{i}">{html.escape(area_titles[i])}</a>' for i in ids)
        tag_html = f'<div class="pub-tags">{links}</div>'

    year_html = ""
    if year_gutter:
        year = "" if entry["_type"] == "unpublished" else get_year(entry)
        year_html = f'<div class="pub-year">{year}</div>'

    return (
        f'<li class="pub" data-areas="{" ".join(ids)}">{year_html}'
        f'<div class="pub-body"><div class="pub-title">{title_html}</div>'
        f'<div class="pub-authors">{authors_html(entry)}</div>'
        f'<div class="pub-meta">{meta_html}</div>{tag_html}</div></li>'
    )


def pub_list_html(items, key_areas, area_titles, **kw):
    cls = "pub-list" + ("" if kw.get("year_gutter", True) else " pub-list-plain")
    rows = "\n".join(pub_item_html(e, key_areas, area_titles, **kw) for e in items)
    return f'<ul class="{cls}">\n{rows}\n</ul>'


def raw_html(block):
    return "```{=html}\n" + block + "\n```\n"


def md_inline(text):
    """Minimal inline markdown -> HTML (bold only), for CV detail lines."""
    return re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', html.escape(text))


def plural(n, word):
    return f"{n} {word}" + ("" if n == 1 else "s")


# ---------------------------------------------------------------------------
# Publications page (publications.qmd)
# ---------------------------------------------------------------------------

def generate_publications_page(cv, research, groups):
    key_areas = areas_by_key(research)
    area_titles = {a["id"]: a["title"] for a in research["areas"]}
    peer = groups["peer-reviewed"]
    first_author = sum(1 for e in peer if is_first_author(e))
    scholar = cv["links"]["scholar"]

    used = {i for ids in key_areas.values() for i in ids}
    buttons = ['<button type="button" class="pub-filter is-active" data-area="">All</button>']
    for area in research["areas"]:
        if area["id"] in used:
            buttons.append(
                f'<button type="button" class="pub-filter" data-area="{area["id"]}">'
                f'{html.escape(area["title"])}</button>')

    parts = [
        "---",
        'pagetitle: "Publications"',
        "---",
        "",
        "<!-- AUTO-GENERATED by build-site.py. Do not edit. -->",
        "",
        "# Publications",
        "",
        f"[{plural(len(peer), 'peer-reviewed article')}, {first_author} as first author. "
        f"Citation counts are on [Google Scholar]({scholar}).]{{.page-lede}}",
        "",
        raw_html('<div class="pub-filters" role="group" aria-label="Filter by research area">\n'
                 + "\n".join(buttons) + "\n</div>"),
        "## Peer-reviewed articles {.pub-section}",
        "",
        raw_html(pub_list_html(peer, key_areas, area_titles)),
    ]
    if groups["in-progress"]:
        parts += ["## Works in progress {.pub-section}", "",
                  raw_html(pub_list_html(groups["in-progress"], key_areas, area_titles))]
    if groups["other-media"]:
        parts += ["## Commentary {.pub-section}", "",
                  raw_html(pub_list_html(groups["other-media"], key_areas, area_titles))]

    parts.append(raw_html("""<script>
(function () {
  var buttons = document.querySelectorAll('.pub-filter');
  var items = document.querySelectorAll('.pub-list .pub');
  var sections = document.querySelectorAll('.pub-section');
  function apply(area) {
    items.forEach(function (li) {
      var areas = (li.getAttribute('data-areas') || '').split(' ');
      li.hidden = !!area && areas.indexOf(area) === -1;
    });
    sections.forEach(function (sec) {
      sec.hidden = !sec.querySelector('.pub:not([hidden])');
    });
    buttons.forEach(function (b) {
      var on = b.getAttribute('data-area') === area;
      b.classList.toggle('is-active', on);
      b.setAttribute('aria-pressed', on ? 'true' : 'false');
    });
  }
  buttons.forEach(function (b) {
    b.addEventListener('click', function () {
      var area = b.getAttribute('data-area');
      history.replaceState(null, '', area ? '#' + area : location.pathname);
      apply(area);
    });
  });
  var initial = location.hash.slice(1);
  if (initial && document.querySelector('.pub-filter[data-area="' + initial + '"]')) apply(initial);
})();
</script>"""))

    PUBLICATIONS_QMD_PATH.write_text("\n".join(parts), encoding="utf-8")
    print(f"Generated {PUBLICATIONS_QMD_PATH}: {len(peer)} articles ({first_author} first-author)")


# ---------------------------------------------------------------------------
# Includes for hand-written pages (_generated/*.md)
# ---------------------------------------------------------------------------

def generate_includes(cv, research, groups):
    """Write the fragments that index.qmd, research.qmd and talks.qmd include."""
    GENERATED_DIR.mkdir(exist_ok=True)
    key_areas = areas_by_key(research)
    area_titles = {a["id"]: a["title"] for a in research["areas"]}
    by_key = {e["_key"]: e for g in groups.values() for e in g}
    published = {e["_key"] for e in groups["peer-reviewed"] + groups["other-media"]}

    # Home page: research areas
    rows = []
    for area in research["areas"]:
        keys = [k for k in area.get("pubs") or [] if k in by_key]
        n_pub = sum(1 for k in keys if k in published)
        n_wip = len(keys) - n_pub
        evidence = []
        if n_pub:
            evidence.append(plural(n_pub, "publication"))
        if n_wip:
            evidence.append(f"{n_wip} in preparation")
        if area.get("note"):
            evidence.append(area["note"])
        rows.append(
            f'<a class="area-row" href="research.html#{area["id"]}">'
            f'<span class="area-title">{html.escape(area["title"])}</span>'
            f'<span class="area-summary">{html.escape(area["summary"].strip())}</span>'
            f'<span class="area-meta">{html.escape(", ".join(evidence))}</span></a>')
    (GENERATED_DIR / "home-areas.md").write_text(
        raw_html('<div class="area-list">\n' + "\n".join(rows) + "\n</div>"), encoding="utf-8")

    # Home page: selected publications
    selected = [by_key[k] for k in research.get("selected") or [] if k in by_key]
    (GENERATED_DIR / "home-selected.md").write_text(
        raw_html(pub_list_html(selected, key_areas, area_titles, tags=False)), encoding="utf-8")

    # Research page: publications per area, newest first
    for area in research["areas"]:
        items = [by_key[k] for k in area.get("pubs") or [] if k in by_key]
        items.sort(key=lambda e: (e["_type"] == "unpublished", sort_key(e)), reverse=True)
        body = raw_html(pub_list_html(items, key_areas, area_titles, tags=False)) if items else ""
        (GENERATED_DIR / f"area-{area['id']}.md").write_text(body, encoding="utf-8")

    # Talks page
    (GENERATED_DIR / TALKS_INCLUDE).write_text(raw_html(talks_html(cv)), encoding="utf-8")
    print(f"Generated includes in {GENERATED_DIR}/")


def invited_venue_text(venue):
    bits = [venue["host"]]
    if venue.get("date"):
        bits.append(str(venue["date"]))
    if venue.get("status"):
        bits.append(venue["status"])
    return ", ".join(bits)


def talks_html(cv):
    out = []
    if cv.get("invited_talks"):
        out.append('<h2>Invited seminars</h2>')
        for talk in cv["invited_talks"]:
            venues = "".join(f"<li>{html.escape(invited_venue_text(v))}</li>" for v in talk["venues"])
            out.append(f'<div class="talk"><div class="talk-title">{html.escape(talk["title"])}</div>'
                       f'<ul class="talk-venues">{venues}</ul></div>')
    out.append('<h2>Conference presentations</h2>')
    for pres in cv["conference_presentations"]:
        venues = "".join(f"<li>{html.escape(v)}</li>" for v in pres["venues"])
        authors = html.escape(pres["authors"]).replace("Johnson EK", "<strong>Johnson EK</strong>")
        out.append(f'<div class="talk"><div class="talk-title">{html.escape(pres["title"].rstrip("."))}</div>'
                   f'<div class="talk-authors">{authors}</div>'
                   f'<ul class="talk-venues">{venues}</ul></div>')
    out.append('<h2>Teaching</h2>')
    for inst in cv["teaching_experience"]:
        out.append(cv_entry_html(inst["institution"], inst["location"],
                                 [(r["title"], r["date"], []) for r in inst["roles"]]))
    return "\n".join(out)


# ---------------------------------------------------------------------------
# CV, HTML version (cv/index.qmd)
# ---------------------------------------------------------------------------

def cv_entry_html(name, where, positions):
    """positions: list of (title, dates, [detail lines])."""
    rows = [f'<div class="cv-row cv-inst"><span>{html.escape(name)}</span>'
            f'<span class="cv-right">{html.escape(where)}</span></div>']
    for title, dates, details in positions:
        rows.append(f'<div class="cv-row cv-pos"><span>{md_inline(title)}</span>'
                    f'<span class="cv-right">{html.escape(str(dates))}</span></div>')
        if details:
            rows.append("<ul>" + "".join(f"<li>{md_inline(d)}</li>" for d in details) + "</ul>")
    return '<div class="cv-entry">' + "".join(rows) + "</div>"


def cv_pub_html(entry, numbered=None):
    journal = pub_journal(entry)
    bits = [authors_html(entry).rstrip(".") + ".", html.escape(pub_title(entry)).rstrip(".?") + (
        "?" if pub_title(entry).endswith("?") else ".")]
    if entry["_type"] == "unpublished":
        bits.append(html.escape(entry.get("note", "In preparation")) + ".")
    else:
        kind = f" ({html.escape(entry['_kind'].lower())})" if entry.get("_kind") else ""
        bits.append(f"<em>{html.escape(journal)}</em>{kind}. {get_year(entry)}.")
    text = " ".join(bits)
    url = pub_url(entry)
    if url:
        text += f' <a class="cv-doi" href="{html.escape(url)}">Link</a>'
    return f"<li>{text}</li>"


def cv_contact_links(cv):
    links = cv["links"]
    return [("ORCID", links.get("orcid")), ("Google Scholar", links.get("scholar")),
            ("GitHub", links.get("github")), ("LinkedIn", links.get("linkedin"))]


def generate_cv_html(cv, pub_groups):
    def section(title, body):
        return f'<section class="cv-section"><h2>{title}</h2><div class="cv-content">{body}</div></section>'

    contact = [f'<a href="mailto:{cv["email"]}">{cv["email"]}</a>',
               f'<a href="https://{cv["website"]}">{cv["website"]}</a>']
    contact += [f'<a href="{url}">{label}</a>' for label, url in cv_contact_links(cv) if url]

    out = ['<div class="cv">',
           '<header class="cv-head"><div>',
           f'<h1>{html.escape(cv["name"])}</h1>',
           f'<p class="cv-role">{html.escape(cv["title"])}<br>{html.escape(cv["affiliation"])}</p>',
           f'<p class="cv-contact">{" · ".join(contact)}</p>',
           '</div><a class="button" href="cv-pdf.pdf">Download PDF</a></header>']

    out.append(section("Profile", f"<p>{md_inline(cv['summary'].strip())}</p>"))

    out.append(section("Appointments", "".join(
        cv_entry_html(a["institution"], a["location"],
                      [(p["title"], p["dates"], p.get("details", [])) for p in a["positions"]])
        for a in cv.get("appointments", []))))

    edu = []
    for e in cv["education"]:
        degree = e["degree"] + (f" ({e['honors']})" if e.get("honors") else "")
        edu.append(cv_entry_html(e["institution"], e["location"], [(degree, e["date"], e.get("details", []))]))
    out.append(section("Education", "".join(edu)))

    pubs = []
    if pub_groups["peer-reviewed"]:
        pubs.append('<h3>Peer-reviewed articles</h3><p class="cv-note">Author lists longer than '
                    f'{ABBREV_THRESHOLD} names are abbreviated.</p>')
        pubs.append('<ol class="cv-pubs">' + "".join(cv_pub_html(e) for e in pub_groups["peer-reviewed"]) + "</ol>")
    if pub_groups["in-progress"]:
        pubs.append("<h3>Works in progress</h3>")
        pubs.append('<ul class="cv-pubs">' + "".join(cv_pub_html(e) for e in pub_groups["in-progress"]) + "</ul>")
    if pub_groups["other-media"]:
        pubs.append("<h3>Commentary</h3>")
        pubs.append('<ul class="cv-pubs">' + "".join(cv_pub_html(e) for e in pub_groups["other-media"]) + "</ul>")
    out.append(section("Publications", "".join(pubs)))

    out.append(section("Research experience", "".join(
        cv_entry_html(i["institution"], i["location"],
                      [(p["title"], p["dates"], p.get("details", [])) for p in i["positions"]])
        for i in cv["research_experience"])))

    talks = []
    if cv.get("invited_talks"):
        talks.append("<h3>Invited seminars</h3>")
        for talk in cv["invited_talks"]:
            venues = "".join(f"<li>{html.escape(invited_venue_text(v))}</li>" for v in talk["venues"])
            talks.append(f'<div class="cv-entry"><div class="cv-talk">{html.escape(talk["title"])}</div><ul>{venues}</ul></div>')
    talks.append("<h3>Conference presentations</h3>")
    for pres in cv["conference_presentations"]:
        venues = "".join(f"<li>{html.escape(v)}</li>" for v in pres["venues"])
        talks.append(f'<div class="cv-entry"><div class="cv-talk">{html.escape(pres["authors"])}. '
                     f'<em>{html.escape(pres["title"])}</em></div><ul>{venues}</ul></div>')
    out.append(section("Presentations", "".join(talks)))

    out.append(section("Teaching", "".join(
        cv_entry_html(i["institution"], i["location"], [(r["title"], r["date"], []) for r in i["roles"]])
        for i in cv["teaching_experience"])))

    out.append(section("Other professional experience", "".join(
        cv_entry_html(o["organization"], o["location"],
                      [(p["title"], p["dates"], p.get("details", [])) for p in o["positions"]])
        for o in cv["other_experience"])))

    out.append(section("Skills", "<ul>" + "".join(f"<li>{md_inline(s)}</li>" for s in cv["skills"]) + "</ul>"))
    out.append("</div>")

    page = "\n".join([
        "---",
        'pagetitle: "Curriculum Vitae"',
        "body-classes: cv-page",
        "---",
        "",
        "<!-- AUTO-GENERATED by build-site.py. Do not edit. -->",
        "",
        raw_html("\n".join(out)),
    ])
    CV_HTML_PATH.write_text(page, encoding="utf-8")
    print(f"Generated {CV_HTML_PATH}")


# ---------------------------------------------------------------------------
# CV and publication list, PDF versions (Typst)
# ---------------------------------------------------------------------------

def ty(text):
    """Escape text for use inside Typst content brackets."""
    return re.sub(r'([\\#$*_@<>\[\]`~])', r'\\\1', str(text))


def ty_md(text):
    """Escape for Typst, keeping **bold** from the YAML."""
    parts = re.split(r'\*\*(.+?)\*\*', str(text))
    return "".join(f"#strong[{ty(p)}]" if i % 2 else ty(p) for i, p in enumerate(parts))


def typst_front_matter(out_file, margin_x="0.9in", margin_y="0.8in"):
    fonts = os.path.relpath(FONT_DIR, Path(out_file).parent)
    return [
        "---",
        'title: ""',
        "format:",
        "  typst:",
        "    margin:",
        f'      x: "{margin_x}"',
        f'      y: "{margin_y}"',
        "    fontsize: 10pt",
        '    mainfont: "Source Serif 4"',
        f"    font-paths: [\"{fonts}\"]",
        "bibliography: []",
        "citeproc: false",
        "---",
        "",
    ]


def typst_preamble(cv, doc_label):
    """Shared Typst styling and the name/contact header."""
    contact = [f'#link("mailto:{cv["email"]}")[{ty(cv["email"])}]',
               f'#link("https://{cv["website"]}")[{ty(cv["website"])}]']
    contact += [f'#link("{url}")[{label}]' for label, url in cv_contact_links(cv) if url]
    return [
        "```{=typst}",
        '#let ink = rgb("#1c211e")',
        '#let muted = rgb("#5d665f")',
        '#let accent = rgb("#1B4332")',
        '#let rule = rgb("#c9d1c9")',
        '#let sans = "Source Sans 3"',
        "",
        "#set page(numbering: \"1\", footer: context {",
        "  set text(font: sans, size: 8pt, fill: muted)",
        f"  [{ty(cv['name'])}, {doc_label} #h(1fr) #counter(page).display() of #counter(page).final().first()]",
        "})",
        '#set text(font: "Source Serif 4", size: 10pt, fill: ink)',
        "#set par(justify: false, leading: 0.58em, spacing: 0.8em)",
        "#set list(spacing: 0.55em, indent: 0.1em, body-indent: 0.6em, marker: text(fill: muted)[–])",
        "#set enum(spacing: 0.75em, body-indent: 0.6em)",
        "#show link: set text(fill: accent)",
        "",
        "#show heading.where(level: 1): it => block(above: 1.5em, below: 0.8em, sticky: true)[",
        "  #text(font: sans, size: 8.5pt, weight: \"semibold\", tracking: 0.09em, fill: accent, upper(it.body))",
        "  #v(-0.6em)",
        "  #line(length: 100%, stroke: 0.4pt + rule)",
        "]",
        "#show heading.where(level: 2): it => block(above: 1.1em, below: 0.6em, sticky: true,",
        "  text(font: sans, size: 9.5pt, weight: \"semibold\", fill: ink, it.body))",
        "",
        "#let side(body) = text(font: sans, size: 9pt, fill: muted, body)",
        "#let inst(name, where) = block(above: 0.95em, below: 0.5em, sticky: true,",
        "  grid(columns: (1fr, auto), column-gutter: 1.5em, text(weight: \"semibold\", name), side(where)))",
        "#let role(title, when) = block(above: 0.5em, below: 0.45em, sticky: true,",
        "  grid(columns: (1fr, auto), column-gutter: 1.5em, emph(title), side(when)))",
        "",
        f'#text(size: 22pt, weight: "semibold")[{ty(cv["name"])}]',
        "#v(-0.75em)",
        f'#text(font: sans, size: 10pt)[{ty(cv["title"])}, {ty(cv["affiliation"])}]',
        "#v(-0.4em)",
        f'#text(font: sans, size: 9pt, fill: muted)[{" #h(0.4em)·#h(0.4em) ".join(contact)}]',
        "#v(0.2em)",
        "```",
        "",
    ]


def typst_entry(name, where, positions):
    lines = ["```{=typst}", f"#inst[{ty(name)}][{ty(where)}]"]
    open_block = True
    for title, dates, details in positions:
        if not open_block:
            lines.append("```{=typst}")
        lines.append(f"#role[{ty_md(title)}][{ty(dates)}]")
        lines.append("```")
        open_block = False
        if details:
            lines.append("")
            lines += [f"- {d}" for d in details]
            lines.append("")
    if open_block:
        lines.append("```")
    lines.append("")
    return lines


def cv_pub_md(entry):
    bits = [authors_md(entry).rstrip(".") + ".", pub_title(entry) + "."]
    if entry["_type"] == "unpublished":
        bits.append(entry.get("note", "In preparation") + ".")
    else:
        kind = f" ({entry['_kind'].lower()})" if entry.get("_kind") else ""
        bits.append(f"*{pub_journal(entry)}*{kind}. {get_year(entry)}.")
    return " ".join(bits)


def generate_cv_pdf(cv, pub_groups, output_path=None):
    """Generate the Typst CV source. output_path overrides cv/cv-pdf.qmd (used for snapshots)."""
    out = Path(output_path) if output_path else CV_PDF_PATH
    lines = typst_front_matter(out) + typst_preamble(cv, "Curriculum Vitae")

    lines += ["# Profile", "", cv["summary"].strip(), ""]

    if cv.get("appointments"):
        lines += ["# Appointments", ""]
        for a in cv["appointments"]:
            lines += typst_entry(a["institution"], a["location"],
                                 [(p["title"], p["dates"], p.get("details", [])) for p in a["positions"]])

    lines += ["# Education", ""]
    for e in cv["education"]:
        degree = e["degree"] + (f" ({e['honors']})" if e.get("honors") else "")
        lines += typst_entry(e["institution"], e["location"], [(degree, e["date"], e.get("details", []))])

    lines += ["# Publications", ""]
    if pub_groups["peer-reviewed"]:
        lines += ["## Peer-reviewed articles", "",
                  f"*Author lists longer than {ABBREV_THRESHOLD} names are abbreviated.*", ""]
        for i, entry in enumerate(pub_groups["peer-reviewed"], start=1):
            lines += [f"{i}. {cv_pub_md(entry)}", ""]
    if pub_groups["in-progress"]:
        lines += ["## Works in progress", ""]
        lines += [f"- {cv_pub_md(e)}" for e in pub_groups["in-progress"]] + [""]
    if pub_groups["other-media"]:
        lines += ["## Commentary", ""]
        lines += [f"- {cv_pub_md(e)}" for e in pub_groups["other-media"]] + [""]

    lines += ["# Research Experience", ""]
    for inst in cv["research_experience"]:
        lines += typst_entry(inst["institution"], inst["location"],
                             [(p["title"], p["dates"], p.get("details", [])) for p in inst["positions"]])

    lines += ["# Presentations", ""]
    if cv.get("invited_talks"):
        lines += ["## Invited seminars", ""]
        for talk in cv["invited_talks"]:
            lines += [talk["title"], ""]
            lines += [f"- {invited_venue_text(v)}" for v in talk["venues"]] + [""]
    lines += ["## Conference presentations", ""]
    for pres in cv["conference_presentations"]:
        lines += [f'{pres["authors"]}. *{pres["title"]}*', ""]
        lines += [f"- {v}" for v in pres["venues"]] + [""]

    lines += ["# Teaching", ""]
    for inst in cv["teaching_experience"]:
        lines += typst_entry(inst["institution"], inst["location"],
                             [(r["title"], r["date"], []) for r in inst["roles"]])

    lines += ["# Other Professional Experience", ""]
    for org in cv["other_experience"]:
        lines += typst_entry(org["organization"], org["location"],
                             [(p["title"], p["dates"], p.get("details", [])) for p in org["positions"]])

    lines += ["# Skills", ""]
    lines += [f"- {s}" for s in cv["skills"]] + [""]

    out.write_text("\n".join(lines), encoding="utf-8")
    print(f"Generated {out}")


def generate_publist_typst(cv, pub_groups, output_path):
    """Generate a standalone numbered publication list (full author lists up to 30 names)."""
    output_path = Path(output_path)
    output_path.mkdir(parents=True, exist_ok=True)
    out_file = output_path / "publist.qmd"

    peer = pub_groups["peer-reviewed"]
    stats = [plural(len(peer), "peer-reviewed article"),
             f"{sum(1 for e in peer if is_first_author(e))} as first author"]
    h_index = cv.get("pub_stats", {}).get("h_index")
    if h_index is not None:
        stats.append(f"h-index {h_index}")

    lines = typst_front_matter(out_file) + typst_preamble(cv, "Publications")
    lines += ["# Peer-Reviewed Articles", "", f"*{', '.join(stats)}. All authors listed from first to last.*", ""]
    for i, entry in enumerate(peer, start=1):
        lines += [f'{i}. {format_authors_publist(entry)}. {pub_title(entry)}. '
                  f'*{pub_journal(entry)}*. {get_year(entry)}.', ""]
    if pub_groups["in-progress"]:
        lines += ["# Works in Progress", ""]
        for i, entry in enumerate(pub_groups["in-progress"], start=1):
            lines += [f'{i}. {format_authors_publist(entry)}. {pub_title(entry)}. '
                      f'{entry.get("note", "In preparation")}.', ""]
    if pub_groups["other-media"]:
        lines += ["# Commentary", ""]
        for i, entry in enumerate(pub_groups["other-media"], start=1):
            lines += [f'{i}. {format_authors_publist(entry)}. {pub_title(entry)}. '
                      f'*{pub_journal(entry)}* ({entry.get("_kind", "commentary").lower()}). {get_year(entry)}.', ""]

    out_file.write_text("\n".join(lines), encoding="utf-8")
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

    # Load CV data (non-publication sections) and research areas
    with open(CV_DATA_PATH, "r", encoding="utf-8") as f:
        cv = yaml.safe_load(f)
    research = load_research()

    # Group publications (bib + research.yml), newest first
    pub_groups = build_pub_groups(entries, research)
    check_area_keys(research, pub_groups)

    # Optional cv_publications allowlist in _cv-data.yml (publist always gets everything)
    cv_pub_groups = filter_pub_groups_for_cv(cv, pub_groups)

    if args.snapshot:
        # Snapshot mode: write cv.qmd and publist.qmd to the given directory
        generate_snapshot_cv(cv, cv_pub_groups, args.snapshot)
        generate_publist_typst(cv, pub_groups, args.snapshot)
    else:
        # Normal site build
        generate_publications_page(cv, research, pub_groups)
        generate_includes(cv, research, pub_groups)
        generate_cv_html(cv, cv_pub_groups)
        generate_cv_pdf(cv, cv_pub_groups)
        submissions = parse_submission_tracker(OBSIDIAN_TRACKER_PATH)
        generate_submission_data(submissions)


if __name__ == "__main__":
    main()
