#!/usr/bin/env python3
"""
Generate cv/index.qmd from cv/_cv-data.yml
Run as a Quarto pre-render script.
"""

import yaml
from pathlib import Path

def main():
    data_path = Path(__file__).parent / "_cv-data.yml"
    output_path = Path(__file__).parent / "index.qmd"

    with open(data_path, "r", encoding="utf-8") as f:
        cv = yaml.safe_load(f)

    lines = []

    # YAML front matter
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
    lines.append(f'# {cv["name"]}')
    lines.append("::: {.cv-links}")
    lines.append(f'[LinkedIn]({cv["links"]["linkedin"]}) | [ResearchGate]({cv["links"]["researchgate"]})')
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
        honors = f' | {edu["honors"]}' if "honors" in edu else ""
        lines.append("::: {.cv-entry}")
        lines.append("::: {.cv-entry-header}")
        lines.append(f'[**{edu["institution"]}**]{{.cv-institution}}')
        lines.append(f'[{edu["location"]}{honors}]{{.cv-location}}')
        lines.append(":::")
        lines.append("::: {.cv-position}")
        lines.append(f'[*{edu["degree"]}*]{{.cv-title}}')
        lines.append(f'[{edu["date"]}]{{.cv-dates}}')
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
    lines.append("### Peer reviewed publications")
    lines.append("")
    lines.append("*All authors listed from first to last*")
    lines.append("")
    for pub in cv["publications"]["peer_reviewed"]:
        note = f' ({pub["note"]})' if "note" in pub else ""
        lines.append("::: {.cv-publication}")
        lines.append(f'{pub["authors"]} {pub["title"]} *{pub["journal"]}*. {pub["year"]}{note}.')
        lines.append(":::")
        lines.append("")

    lines.append("### Works in progress")
    lines.append("")
    for pub in cv["publications"]["in_progress"]:
        lines.append("::: {.cv-publication}")
        lines.append(f'{pub["authors"]} {pub["title"]} {pub["status"]}.')
        lines.append(":::")
        lines.append("")

    lines.append("### Other Media")
    lines.append("")
    for pub in cv["publications"]["other_media"]:
        lines.append("::: {.cv-publication}")
        lines.append(f'{pub["authors"]} {pub["title"]} *{pub["journal"]}* ({pub["type"]}). {pub["year"]}.')
        lines.append(":::")
        lines.append("")

    # Research Experience
    lines.append("## Research Experience {.cv-section}")
    lines.append("")
    for inst in cv["research_experience"]:
        for pos in inst["positions"]:
            lines.append("::: {.cv-entry}")
            lines.append("::: {.cv-entry-header}")
            lines.append(f'[**{inst["institution"]}**]{{.cv-institution}}')
            lines.append(f'[{inst["location"]}]{{.cv-location}}')
            lines.append(":::")
            lines.append("::: {.cv-position}")
            lines.append(f'[*{pos["title"]}*]{{.cv-title}}')
            lines.append(f'[{pos["dates"]}]{{.cv-dates}}')
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
        lines.append(f'{pres["authors"]}. *{pres["title"]}*')
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
        lines.append(f'[**{inst["institution"]}**]{{.cv-institution}}')
        lines.append(f'[{inst["location"]}]{{.cv-location}}')
        lines.append(":::")
        for role in inst["roles"]:
            lines.append("::: {.cv-position}")
            lines.append(f'[*{role["title"]}*]{{.cv-title}}')
            lines.append(f'[{role["date"]}]{{.cv-dates}}')
            lines.append(":::")
        lines.append(":::")
        lines.append("")

    # Other Professional Experience
    lines.append("## Other Professional Experience {.cv-section}")
    lines.append("")
    for org in cv["other_experience"]:
        for pos in org["positions"]:
            lines.append("::: {.cv-entry}")
            lines.append("::: {.cv-entry-header}")
            lines.append(f'[**{org["organization"]}**]{{.cv-institution}}')
            lines.append(f'[{org["location"]}]{{.cv-location}}')
            lines.append(":::")
            lines.append("::: {.cv-position}")
            lines.append(f'[*{pos["title"]}*]{{.cv-title}}')
            lines.append(f'[{pos["dates"]}]{{.cv-dates}}')
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

    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    print(f"Generated {output_path}")


if __name__ == "__main__":
    main()
