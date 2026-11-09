# Reviewer documentation index

[Project overview and quick start](../README.md) · [Demo video](../demo/outputs/demonstration.mp4) · [GIF](../demo/outputs/demonstration.gif) · [Local comparison viewer](../demo/outputs/index.html)

## Current submission

| Read | Purpose |
|---|---|
| [Baseline identity](BASELINE.md) | Exact official parameters, canonical sources, hashes and Git/tag status |
| [Submission checklist](SUBMISSION_CHECKLIST.md) | Assignment coverage and explicit remaining gaps |
| [Reproducibility](REPRODUCIBILITY.md) | Safe verification versus output-generating historical commands |
| [Repository audit](REPOSITORY_AUDIT.md) | Files changed/preserved, tests, links, size and hygiene |
| [Technical summary](../demo/TECHNICAL_SUMMARY.md) | Mechanical and experimental interpretation for discussion |
| [Fresh validation protocol](../demo/FRESH_VALIDATION.md) | Predict first, observe later, score without refitting |
| [Dataset guide](../experiments/README.md) | Existing full-face data separated from proposed recordings |
| [Future simulator roadmap](SIMULATOR_ROADMAP.md) | Planned patch/indenter work; no new implementation |

## Preserved research history

Historical reports describe their own milestone, not necessarily the final model. In particular, the original empirical recommendation and Stage 1's homogeneous 27 mm illustration are not the official Stage 6 geometry/calibration.

| Topic / original stage directory | Report |
|---|---|
| Experimental extraction and consistency | [analysis/REPORT.md](../analysis/REPORT.md), [measurement methods/run guide](../analysis/README.md) |
| Initial reduced-order model selection | [analysis/model_selection/REPORT.md](../analysis/model_selection/REPORT.md) |
| Revised empirical interpolation baseline/repeatability | [analysis/model_review/REPORT.md](../analysis/model_review/REPORT.md) |
| Stage 1: verified constitutive kernel | [analysis/material/REPORT.md](../analysis/material/REPORT.md) |
| Stage 2: Tet4 elements and assembly | [analysis/fem/REPORT.md](../analysis/fem/REPORT.md) |
| Stage 3: global nonlinear equilibrium | [analysis/fem_solver/REPORT.md](../analysis/fem_solver/REPORT.md) |
| Stage 4: actual nominal geometry integration | [analysis/sponge/REPORT.md](../analysis/sponge/REPORT.md) |
| Stage 5: experimental inverse FEM and prediction | [analysis/calibration/REPORT.md](../analysis/calibration/REPORT.md) |
| Stage 6: demonstration and submission preparation | [demo/TECHNICAL_SUMMARY.md](../demo/TECHNICAL_SUMMARY.md) |

The user's six-workstream summary combines some earlier stages; the directory labels above retain their historical numbering. No stage report was renamed or rewritten.
