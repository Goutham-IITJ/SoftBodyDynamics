# SoftBodyDynamics

A reusable **quasi-static 3D physics simulator for full-face sponge compression**, calibrated from video observations. Applied force drives a hyperfoam tetrahedral FEM equilibrium solve; recorded marker trajectories do not drive its vertices. General fingertip, finite-patch and rigid-indenter contact are future work.

## Review in six steps

1. **Watch:** [45.2-second demo video](demo/outputs/demonstration.mp4) or [GIF fallback](demo/outputs/demonstration.gif).
2. **Compare:** [real-versus-FEM presentation](demo/outputs/index.html) and [force-compression plot](demo/outputs/force_compression.png).
3. **Understand:** [technical summary](demo/TECHNICAL_SUMMARY.md) and [mathematical/stage report index](docs/README.md).
4. **Query:** [run a new full-face force](#run-a-new-full-face-force-query) with the frozen model.
5. **Reproduce:** [tests and provenance checks](#verify-without-regenerating-results), then [regeneration instructions](docs/REPRODUCIBILITY.md) for a separate working copy.
6. **Assess:** [submission checklist](docs/SUBMISSION_CHECKLIST.md), [baseline identity](docs/BASELINE.md) and [repository audit](docs/REPOSITORY_AUDIT.md).

Download/clone before opening HTML locally: GitHub's file view displays its source rather than running the presentation. The MP4 uses MPEG-4 Part 2; use the GIF if your browser lacks that codec. A hosted result link has not been published.

![Real specimen and frozen FEM at 750 ml](demo/outputs/comparison_750ml.png)

## Assignment and experimental contribution

The [original assignment](Assignment/Dirac-Research-TakeHome.pdf) asks for a soft object filmed during deformation/release, an observation-informed 3D model, a fresh interaction and real/simulated comparison. It requests code/model, input videos, run instructions, a short demo or viewer, assumptions/limitations and tool credits. Two supplied papers are interview reading; no paper reproduction or written paper submission is required.

This project contributes three original full-face bottle-loading videos, **5,169 sequentially decoded frames**, six settled-hold compression observations, and a traceable image-analysis pipeline. Ruler ticks calibrate image coordinates; background registration, visible top/bottom boundaries, plate pose and ink markers are recorded with quality flags and actual timestamps. Thickness change is measured relative to the card-on-sponge baseline. Measurements were not rescaled to force agreement with nominal dimensions. See the [extraction report](analysis/REPORT.md) and [dataset guide](experiments/README.md).

Mechanics-based FEM was selected to obtain force-driven spatial equilibrium, material energy/stress and reactions, rather than a geometric replay. It has not demonstrated better intermediate-load accuracy than the empirical interpolation baseline.

## Frozen baseline and results

The official configuration comes from the [Stage 5 parameter CSV](analysis/calibration/outputs/parameters.csv) and [existing frozen model snapshot](demo/frozen_models.json):

| Property | Baseline |
|---|---|
| Constitutive law | One-term compressible hyperfoam |
| Fitted scale mu | **6999.814990181902 Pa** |
| Assumed alpha / beta | **10 / 0** |
| Deformable yellow foam | 73 Ã— 50 Ã— **20 mm**, z = 7â€“27 mm |
| Green backing | Rigid 7 mm; no invented stiffness |
| Card/platen | Massless, horizontal, full-face frictionless normal constraint |
| Response | Quasi-static force-controlled equilibrium; no identified damping |

Only first cycles at 500/1000 ml fit mu, minimizing equal-weight squared FEM displacement errors. Both 750 ml cycles are held out **from this FEM fitting**, but earlier model selection already inspected them. They are not untouched prospective validation. Alpha = 20 remains separately labeled sensitivity, not the official model.

| Load | Assumed force, N | Measured cycles 1 / 2, mm | Primary FEM, mm |
|---|---:|---:|---:|
| 500 ml | 5.64075 | 3.012 / 2.585 | 3.923 |
| 750 ml | 8.09325 | 7.662 / 6.798 | 7.488 |
| 1000 ml | 10.54575 | 10.987 / 10.974 | 10.316 |

Forces assume water density 1 g/ml, shared **unmeasured 75 g bottle tare**, g = 9.81 m/sÂ² and stationary full support. Calibration RMSE is **0.800 mm**; the low-load mismatch exceeds its engineering allowance. Intermediate RMSE is **0.504 mm**, versus **0.490 mm** for empirical interpolation. Full uncertainty, repeatability and sensitivity results are in the [calibration report](analysis/calibration/REPORT.md).

The model predicts equilibrium compression and a solved nodal/stress field conditional on this loading geometry. Global compression has been compared with observations; local stresses, lateral expansion and arbitrary contact have not been experimentally validated. The [baseline record](docs/BASELINE.md) identifies source/configuration/data/media hashes. Suggested future tag: `baseline-v1-fullface-fem`; no commit, tag, branch or push was created by this documentation task.

## Install and view

Tested environment: **Python 3.10.7**, NumPy 2.2.6, SciPy 1.14.1, Matplotlib 3.9.0, Pillow 10.3.0 and OpenCV 5.0.0 (distribution 5.0.0.93). Use Python 3.10 for the recorded baseline. Dependency metadata requires Python â‰¥3.10; other Python versions/clean installations have not been verified in this audit.

```sh
python -m venv .venv
# Windows PowerShell: .\.venv\Scripts\Activate.ps1
# Linux/macOS: source .venv/bin/activate
python -m pip install -r requirements.txt
```

No installation is needed in the existing environment. [requirements.txt](requirements.txt) is the unchanged demo/evaluation/test dependency file. Historical extraction/model-review scripts additionally use pandas; the installed audited version is 2.2.2. See [reproducibility notes](docs/REPRODUCIBILITY.md) before regenerating any results.

The bundled media need no Python to view. Open [demo/outputs/index.html](demo/outputs/index.html), or serve locally:

```sh
python -m http.server 8000 --bind 127.0.0.1
```

Then visit `http://127.0.0.1:8000/demo/outputs/index.html`. No external services, GPU, FFmpeg CLI or large 3D library are required by the demo.

## Run a new full-face force query

From the repository root, this existing API solves a **6.5 N computational query**, printing compression and numerical diagnostics without writing frozen outputs:

```sh
python -B -c "from demo.model import configuration, new_sponge, solve; s = solve(new_sponge(configuration()), 6.5); print(dict(force_N=6.5, compression_mm=1000*s.displacement, min_J=s.min_J, free_residual_N=s.free_residual))"
```

Expected compression is approximately **5.10350 mm**. This is an unmeasured example query, not a new validation experiment. Change the force argument and printed force together. Use stationary centered full-face loading; the unchanged search limit is 13 mm yellow compression. No force clamping or general contact is provided.

For a real fresh experiment, [save a prediction before measuring](demo/FRESH_VALIDATION.md). The existing CLI accepts actual measured **total bottle mass**, condition and initial-state notes, then scores an observation separately:

```sh
python -B demo/evaluate.py --help
```

The protocol supplies `predict`/`score` commands and the observation template. Do not add assumed bottle tare to a directly measured total mass. Prediction records are exclusive-create and the evaluator never automatically refits.

## Verify without regenerating results

```sh
python -B demo/check.py
python -B docs/check_baseline.py
```

The first runs all **36 existing unit methods**, including verification of the saved solved nodes and real-frame labels. The second checks the documented byte-level baseline, unchanged model snapshot and local presentation/documentation targets. Neither regenerates media, calibration or experimental measurements.

The existing generation commands are `python -B demo/run_demo.py` and `python -B analysis/calibration/run_calibration.py`. **They write fixed output directories and have no output override/dry-run option.** They were checked by safe import/source inspection, not executed during this freeze. Use only a separate working copy for regeneration; [the reproducibility guide](docs/REPRODUCIBILITY.md) lists exact entry points and write locations. The recorded demo runtime was about one minute, not a performance guarantee.

## Assumptions, limits and remaining work

- Mu is an effective specimen coefficient conditional on nominal geometry, reference, shape and support; it is not a uniquely identified intrinsic material property.
- Green compliance and interlayer shear are neglected. Full-face bilateral planes are not finite-footprint collision/contact; there is no finger, tilted platen, friction or localized indentation capability.
- Optical plane/scale uncertainty, differing apparent layer thicknesses, card motion and material history remain unresolved. All measured total compression is allocated to yellow under the rigid-backing assumption.
- The animation traverses reversible equilibria. **Playback duration is not physical recovery time.** Damping, creep, hysteresis and time-accurate recovery are not identified. Beta = 0's zero homogeneous lateral expansion is an assumption, not a validated lateral observation.
- Small residuals and affine mesh consistency establish numerical behavior, not arbitrary-load experimental accuracy. The primary low-load mismatch remains visible.
- A genuinely fresh prediction-first trial, resolved recovery timing, paper-discussion preparation, publication/access arrangements and submission communication remain pending or unverified. See the [submission checklist](docs/SUBMISSION_CHECKLIST.md).

## Project structure

| Location | Purpose |
|---|---|
| [Videos/](Videos/) | Original full-face clips and new unanalysed half-area/fingertip recordings |
| [analysis/](analysis/) | Extraction, model review, material/FEM/solver/sponge/calibration reports and results |
| [demo/](demo/) | Existing frozen-model solve/evaluation/rendering entry points and tests |
| [demo/outputs/](demo/outputs/) | Preserved final MP4/GIF, HTML, real/FEM comparisons and solved coordinates |
| [docs/](docs/) | Navigation, freeze identity, reproducibility and submission audits, roadmap |
| [experiments/](experiments/) | Dataset separation and **planned-only** localized-loading recording location |
| [Assignment/](Assignment/) / [Papers/](Papers/) | Original assignment and supplied reading |

No existing source, data or results were relocated. Two recordings appeared during this audit at [Videos/fingertip.mp4](Videos/fingertip.mp4) and [Videos/half area.mp4](<Videos/half area.mp4>). They remain in their arrival locations, are unreviewed/unanalysed, and are excluded from the full-face calibration. [experiments/localized_loading/](experiments/localized_loading/) catalogs these paths and reserves a separate destination for future recordings/results. The [roadmap](docs/SIMULATOR_ROADMAP.md) describes future simulator capabilities only.

## Credits and references

Prepared with OpenAI Codex assistance. Numerical/visual dependencies are NumPy, SciPy, Matplotlib, OpenCV and Pillow; historical measurement analysis also uses pandas. The implementation reuses this project's verified material, Tet4 and solver modules, with derivations credited in the [report index](docs/README.md). No AI imagery replaces experimental frames or FEM results.

- [Abaqus hyperfoam convention](https://docs.software.vt.edu/abaqusv2026/English/SIMACAEMATRefMap/simamat-c-hyperfoam.htm), as documented in the preserved material report.
- [3D Gaussian Splatting for Real-Time Radiance Field Rendering](https://arxiv.org/abs/2308.04079) and [Hybrid Particle-Voxel Dynamics for Multimodal 3D World Simulation](https://arxiv.org/abs/2611.04492): assignment reading; neither is claimed as code reproduced here.

The current project payload is approximately 439 MB before Git history, including the two newly arrived recordings. [The repository audit](docs/REPOSITORY_AUDIT.md) records size, publication considerations and the Git changes observed during work. No video was deleted or converted to external storage. The user-authorized removal of a private ID-card photograph is documented in [the publication note](docs/PUBLICATION_CHECKPOINT.md).
