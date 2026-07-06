# Example: Project-specific CLAUDE.md

*This is an example of a CLAUDE.md that lives at the root of a project directory. Claude Code reads it automatically when I open that project, so it has project-specific context (data locations, conventions, collaborators) without me having to re-explain every session.*


----


# CLAUDE.md — Hospital Closures × DEX

------------------------------------------------------------------------

## Communication Guidelines

-   Collaborators:
    -   **JD** — PI of DEX at IHME, health economist, advisor on this project.
    -   **HP** — causal-inference biostatistician, assistant professor at Yale University. Expert on matching methods and event studies.
    -   **BA** — RA, \~15 hr/week, CS background, new to research.
    -   **Emily** - primary on the project. Former IHME researcher on DEX, current phd student in health economics.

------------------------------------------------------------------------

## Estimation Philosophy

**Design before results.** During estimation and analysis:

-   Do NOT express concern or excitement about point estimates.
-   Do NOT interpret results as "good" or "bad" until the design is intentional.
-   Focus entirely on whether the specification is correct.
-   Results are meaningless until we're confident the "experiment" is designed on purpose.
-   Objectivity means being attached to getting the design right, not to any particular finding.

------------------------------------------------------------------------

## Project Overview

This is an early-stage project using DEX county-year expenditure data to investigate hospital closures across the US. Prior literature and media coverage have flagged labor and cost pressure on rural hospitals where patient volume is low. This project investigates (1) what characterizes locations where hospitals close, and (2) how closure affects subsequent healthcare consumption patterns in the same and neighboring counties.

### Research Question

How does hospital closure affect subsequent healthcare consumption? Does it shift consumption within a given county across types of care or across age groups? Do costs move downward in closure counties and upward in neighboring counties?

### Data Sources

-   **Exposure (hospital closures):** UNC Sheps Center hospital closures data, publicly available.
-   **Outcome (expenditure, volume, cost per encounter):** IHME's DEX 2025 county-level disease expenditure estimates. **Currently on disk at `data/raw/dex/scaled_version_102/`** (5 payer partitions: `all/`, `mdcd/`, `mdcr/`, `oop/`, `priv/`). v102 covers 2010–2019. A 2023-extended version is expected later; v102 is the working dataset until then.
-   **Covariates:** ACS, USDA RUCC, AHRF, CMS POS, CMS HCRIS. See `README.md` for the full data dictionary.

### Identification Strategy

Event-study difference-in-differences using **Callaway/Sant'Anna** (`did` package in R) to handle staggered closure timing. Treatment is defined at the county-year level. Paired with propensity-score matching or weighting at treatment onset to address selection on observables. Final design TBD.

------------------------------------------------------------------------

## Key Decisions Made

| Date       | Decision | Rationale |
|------------|----------|-----------|
| (none yet) |          |           |

------------------------------------------------------------------------

## Dropped Analyses

(none yet)

------------------------------------------------------------------------

## Key Files

| Purpose | File |
|-------------------------------------------|-----------------------------|
| Data pipeline (panel build) | `code/R/closures_data_processing.R` |
| Descriptives | `code/R/descriptives.R` → `output/figures/descriptives.pdf` |
| Baseline (2010) summary table | `code/R/table1_2010.R` → `output/tables/table1_2010.pdf` |
| Pre/post closure means table | `code/R/table_prepost_closure.R` → `output/tables/table_prepost_closure.pdf` |
| Propensity-score matching (skeletal) | `code/R/psm.R` |
| Outcomes estimation | **not yet started** — beginning now that DEX v102 is on disk |
| Paper draft | TO BE ADDED |
| Presentation | `decks/` |

------------------------------------------------------------------------

## Variable Definitions

See `README.md` for the full data dictionary (panel identifiers, closure outcomes, ACS covariates, RUCC, AHRF, temporal vars).

Key constructed variables:

| Variable | Definition | Source |
|------------------------|-----------------------------|--------------------|
| `treatment` | binary; county had any hospital closure between 2011 and 2019 | UNC Sheps |
| `outcome` | DEX county-year expenditure (per payer partition) | IHME DEX v102 |

------------------------------------------------------------------------

## Sample Restrictions

Excluding counties with no hospitals, counties with a closure in 2010 (baseline year), and counties with NAs for covariates.

------------------------------------------------------------------------

## Current Status

**Phase:** Outcomes analysis starting.

-   Panel built (`data/clean/county_year_panel.csv`; 31,650 county-years × 3,165 counties, 2010–2019).
-   Descriptives + Table 1 (2010) + pre/post closure means table all complete (see `output/`).
-   PSM is a diagnostic skeleton (logit + balance plots only; no downstream use yet).
-   **DEX v102 received** — outcomes analysis script(s) to be written next.
-   2023-extended DEX expected later; analysis on v102 in the meantime.
-   **HCRIS payer-mix (Section 6.6 of the pipeline) parked.** Files in `data/raw/hcris/` are the cost-charges summary format, not the `hosp10_RPT/NMRC` alpha-numeric format the pipeline expects. Decide whether payer-mix is needed before fixing.

See `progress_logs/` for session notes.

------------------------------------------------------------------------

## Tooling

Project-level skills installed in `.claude/skills/`:

-   **`referee2`** — Cunningham's econometrics audit (identification, SEs, FEs, parallel trends, first stage). Run against estimation scripts before trusting results.
-   **`blindspot`** — Adversarial Shklovsky-style read of results. Run against figures/tables before interpretation.
-   **`bibcheck`** — Many-agent .bib verifier (DOI + journal landing pages). Used standalone before paper submission, and as the verification gate inside `discover_lit`.
-   **`beautiful_deck`** — End-to-end Beamer creation with anti-runaway gates (Step 0 triage, Step 2 outline-approval checkpoint, 3-attempt circuit breaker). Prefer over `compiledeck` for new decks; use `compiledeck` for editing existing `.tex`.
-   **`discover_lit`** — Zotero-aware literature discovery. Searches PubMed + WebSearch, resolves DOIs via Crossref, dedupes against `references.bib`, verifies via `bibcheck`, outputs a Zotero-paste-ready DOI list.

User-level skills (in `~/.claude/skills/`) also available globally: `compiledeck`, `split-pdf`, `newproject`, `academic-paper-writer`, `cite_check`, `lit-review-assistant`, `research-ideation`, `emily-style-coach`, `emily-style-emulate`, `organize-repo`, `deploy`, `review-plan`.

HSA `clo-author` worker/critic pattern is under evaluation as a reference model but not adopted.

------------------------------------------------------------------------

## Notes for Claude

-   Keep code as succinct as possible so it's easy to parse and check.
-   After edits to Quarto (.qmd) or R Markdown files, re-render the document before reporting completion.
-   When editing a hardcoded value (year, name, path), grep the entire project for all occurrences before reporting the fix is complete.
-   Before any methodological implementation, confirm the approach with Emily (denominator definitions, weighting schemes, censoring strategies, etc.) — especially for PSM, DiD, event studies, IPCW, bootstrap CIs.
-   Any time Emily asks you to complete some work, do a git commit of the final changes.
