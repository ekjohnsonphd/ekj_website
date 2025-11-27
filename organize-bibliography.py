#!/usr/bin/env python3
"""
Extract journal articles from references.bib and sort by year (most recent first)
"""

import re

def parse_bib_file(bib_file):
    """Parse .bib file and extract article entries with year and author info"""
    with open(bib_file, 'r', encoding='utf-8') as f:
        content = f.read()

    # Pattern to match complete bib entries
    pattern = r'(@\w+\{[^@]+?\n\})'
    entries = re.findall(pattern, content, re.DOTALL)

    articles = []

    for entry in entries:
        # Only keep @article entries
        type_match = re.search(r'@(\w+)\{', entry)
        if not type_match or type_match.group(1).lower() != 'article':
            continue

        # Extract year from date field
        year_match = re.search(r'date\s*=\s*\{(\d{4})', entry)
        year = int(year_match.group(1)) if year_match else 0

        # Check if first author (look for author field)
        # First author is the one listed first in the author field
        author_match = re.search(r'author\s*=\s*\{([^}]+)\}', entry)
        is_first_author = False
        if author_match:
            authors = author_match.group(1)
            # First author is before the first " and "
            first_author = authors.split(' and ')[0].strip()
            if 'Johnson, Emily' in first_author or 'Johnson, E. K.' in first_author:
                is_first_author = True

        articles.append((year, entry, is_first_author))

    return articles

def main():
    print("Extracting journal articles...")

    # Parse and extract articles
    articles = parse_bib_file('references.bib')

    # Sort by year (most recent first)
    articles.sort(key=lambda x: x[0], reverse=True)

    # Calculate statistics
    total_pubs = len(articles)
    first_author_pubs = sum(1 for _, _, is_first in articles if is_first)

    # Write articles.bib
    with open('articles.bib', 'w', encoding='utf-8') as f:
        for _, entry, _ in articles:
            f.write(entry)
            f.write('\n\n')

    # Generate simple publications.qmd with statistics and enhanced CSS
    with open('publications.qmd', 'w') as f:
        f.write(f"""---
title: "Publications"
bibliography: articles.bib
csl: apa.csl
nocite: '@*'
---

```{{=html}}
<style>
/* Publication statistics styling - compact version */
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

/* Enhanced publication list styling */
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

/* Make journal names stand out */
.references .csl-entry em {{
  font-style: italic;
  color: #2c5282;
  font-weight: 500;
}}

/* Bold author name - will be done via JavaScript */
.references .csl-entry strong {{
  color: #000;
  font-weight: 700;
}}

/* Year and volume styling */
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
  // Bold author name (Johnson, E. K.) in bibliography
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

    print(f"Complete! Extracted {len(articles)} journal articles (sorted by year, most recent first)")

if __name__ == '__main__':
    main()
