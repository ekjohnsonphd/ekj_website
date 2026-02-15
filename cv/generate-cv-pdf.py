#!/usr/bin/env python3
"""
Generate cv/cv-pdf.qmd from cv/_cv-data.yml for Typst PDF rendering.
Run manually: python3 cv/generate-cv-pdf.py && quarto render cv/cv-pdf.qmd
"""

import yaml
from pathlib import Path


def main():
    data_path = Path(__file__).parent / "_cv-data.yml"
    output_path = Path(__file__).parent / "cv-pdf.qmd"

    with open(data_path, "r", encoding="utf-8") as f:
        cv = yaml.safe_load(f)

    lines = []

    # YAML front matter for Typst PDF
    lines.append("---")
    lines.append(f'title: "{cv["name"]}"')
    lines.append("format:")
    lines.append("  typst:")
    lines.append("    margin:")
    lines.append('      x: "1in"')
    lines.append('      y: "0.75in"')
    lines.append("    fontsize: 10pt")
    lines.append("    mainfont: \"Libertinus Serif\"")
    lines.append("    sansfont: \"Libertinus Sans\"")
    lines.append("bibliography: []")
    lines.append('citeproc: false')
    lines.append("---")
    lines.append("")

    # Custom Typst header block for name and links
    lines.append("```{=typst}")
    lines.append("#set page(numbering: \"1\")")
    lines.append("#set par(justify: true)")
    lines.append("#set text(size: 10pt)")
    lines.append("")
    lines.append("// Section heading style")
    lines.append('#show heading.where(level: 1): it => {')
    lines.append("  set text(size: 11pt, weight: \"bold\")")
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
                # Convert markdown bold to Typst bold
                d_typst = d.replace("**", "*")
                lines.append(f"- {d_typst}")
        lines.append("")

    # Publications
    lines.append("# Publications")
    lines.append("")
    lines.append("## Peer reviewed publications")
    lines.append("")
    lines.append("*All authors listed from first to last*")
    lines.append("")
    for pub in cv["publications"]["peer_reviewed"]:
        note = f" ({pub['note']})" if "note" in pub else ""
        # Convert **bold** to markdown bold for Typst
        authors = pub["authors"]
        lines.append(f'{authors} {pub["title"]} *{pub["journal"]}*. {pub["year"]}{note}.')
        lines.append("")

    lines.append("## Works in progress")
    lines.append("")
    for pub in cv["publications"]["in_progress"]:
        authors = pub["authors"]
        lines.append(f'{authors} {pub["title"]} {pub["status"]}.')
        lines.append("")

    lines.append("## Other Media")
    lines.append("")
    for pub in cv["publications"]["other_media"]:
        authors = pub["authors"]
        lines.append(f'{authors} {pub["title"]} *{pub["journal"]}* ({pub["type"]}). {pub["year"]}.')
        lines.append("")

    # Research Experience
    lines.append("# Research Experience")
    lines.append("")
    for inst in cv["research_experience"]:
        for pos in inst["positions"]:
            lines.append("```{=typst}")
            lines.append(f'#grid(columns: (1fr, auto), align: (left, right),')
            lines.append(f'  [*{inst["institution"]}*], [{inst["location"]}]')
            lines.append(f')')
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
        for role in inst["roles"]:
            lines.append("```{=typst}")
            lines.append(f'#grid(columns: (1fr, auto), align: (left, right),')
            lines.append(f'  [*{inst["institution"]}*], [{inst["location"]}]')
            lines.append(f')')
            lines.append(f'#grid(columns: (1fr, auto), align: (left, right),')
            lines.append(f'  [_{role["title"]}_], [{role["date"]}]')
            lines.append(f')')
            lines.append("```")
            lines.append("")

    # Other Professional Experience
    lines.append("# Other Professional Experience")
    lines.append("")
    for org in cv["other_experience"]:
        for pos in org["positions"]:
            lines.append("```{=typst}")
            lines.append(f'#grid(columns: (1fr, auto), align: (left, right),')
            lines.append(f'  [*{org["organization"]}*], [{org["location"]}]')
            lines.append(f')')
            lines.append(f'#grid(columns: (1fr, auto), align: (left, right),')
            lines.append(f'  [_{pos["title"]}_], [{pos["dates"]}]')
            lines.append(f')')
            lines.append("```")
            if "details" in pos:
                lines.append("")
                for d in pos["details"]:
                    lines.append(f"- {d}")
            lines.append("")

    # Skills
    lines.append("# Skills")
    lines.append("")
    for skill in cv["skills"]:
        lines.append(f"- {skill}")
    lines.append("")

    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    print(f"Generated {output_path}")


if __name__ == "__main__":
    main()
