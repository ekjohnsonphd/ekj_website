# Emily K. Johnson - Professional Website

Personal academic website for Emily K. Johnson, PhD student in Health Economics at the University of Southern Denmark.

🔗 **Live site**: [https://ekjohnsonphd.github.io/quarto-professional-website-emily/](https://ekjohnsonphd.github.io/quarto-professional-website-emily/)

## About

This website showcases my research in population health metrics, health spending, and administrative health data. The site includes:

- **Home**: Overview of my background, research interests, education, and experience
- **Research**: Current and past research projects
- **Publications**: Academic publications with automated bibliography management
- **CV**: Downloadable curriculum vitae

## Technical Details

This site is built with [Quarto](https://quarto.org/) and deployed via GitHub Pages. Key features include:

- Custom CSS styling
- Automated publication list generation from BibTeX using `organize-bibliography.py`
- Responsive design for mobile and desktop viewing
- Academic icons integration for ORCID, Google Scholar, etc.

### Site Structure

- `index.qmd` - Home page with sidebar layout
- `research.qmd` - Research interests and projects
- `cv.qmd` - CV download page
- `references.bib` - Master bibliography file
- `organize-bibliography.py` - Script to generate publications page from bibliography
- `styles.css` - Custom styling
- `_quarto.yml` - Site configuration
- `files/` - Static files (images, PDFs)
- `docs/` - Rendered site (published to GitHub Pages)

## Building Locally

```bash
quarto render
```

The site is configured to render to the `docs/` directory for GitHub Pages deployment.

## Credits

This website was built using a [Quarto academic website template](https://drganghe.github.io/quarto-academic-site-examples.html) and customized for my personal branding and research focus.

## License

Content © 2025 Emily K. Johnson. All rights reserved.