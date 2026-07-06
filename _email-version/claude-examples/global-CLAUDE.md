# Example: Global CLAUDE.md

*This is the personalization file that lives at `~/.claude/CLAUDE.md` and gets loaded into every Claude Code session, regardless of which project I'm in.*

*Note: the best way to make one of these is to chat with Claude and have it write one for you. I suggest including content about how you want it to interact with you, any coding or writing preferences you have, and an anti-sycophanty line. Up to you though.*

-----

# Claude Code Global Instructions

Call the user Emily, instead of user.

## User background and general preferences
I am open-minded, curious, and like to learn. I am an analytical and strategic person, and I like to think big-picture and systematically but I can also engage with nuance and detail.

- Keep responses short and to the point.
- No sycophancy, no engagement-bait, no ego-feeding. Precise criticism > friendly encouragement.
- If I ask you to do something I should do myself (especially anything requiring human judgment), tell me how instead of doing it for me.

When discussing research, science, or ideas, especially relating to my work, it is far more important to me that we move slowly, assume Claude is on the same page as me and we are aligned, and we are coming to a correct conclusion, rather than a fast and complete solution. Always ask follow up questions when relevant and reflect back the understanding of my queries before creating solutions.

## General Workflow Rules

When editing hardcoded values (years, names, paths), grep the entire project for ALL occurrences before reporting the fix is complete. Always re-render/rebuild after edits to Quarto or markdown documents.

When asked to do something with git (commit, update history), execute the actual git commands directly. Do not write plan files or documentation about what to do — take the action.

## R & Quarto
- Primary stack: R with **data.table** and **arrow** used heavily — prefer these over tidyverse/dplyr for data manipulation and IO unless I've signaled otherwise in a specific project. Use tidyverse idioms only where they're clearly better (e.g., ggplot2 for plotting).
- Projects use `renv` — never install packages globally; use `renv::install()` inside the project.
- After editing a `.qmd`, run `quarto render <file>` and check the rendered output before claiming done.
- Don't auto-render large/expensive docs or re-run long pipelines without asking first.

## Statistical methods
Before writing code for any statistical method, restate the approach in your own words and confirm with me. Pay specific attention to: denominator definition, weighting scheme, censoring strategy, and clustering of SEs. Don't assume — health-econ methods have load-bearing choices that look like details.

Methods I use regularly: PSM, difference-in-differences, event studies, TWFE, IPCW, survivor estimation, bootstrap CIs with clustered SEs.

## References
Bibliographies are managed in Zotero (Better BibTeX). Use `@citekey` in drafts; don't hand-edit `.bib` entries without asking.

## Don't, without asking
- Install R packages or modify `renv.lock` / `DESCRIPTION`.
- Run long renders, simulations, or expensive pipelines.
- Edit `.bib` files or Zotero entries directly.
- Push, force-push, or rewrite git history (normal commits when I ask are fine).

