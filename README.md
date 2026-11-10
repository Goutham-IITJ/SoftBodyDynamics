# SoftBodyDynamics

An observation-calibrated **3D FEM sponge simulator**. The primary model predicts full-face quasi-static compression; video-derived measurements fit its effective stiffness. The separate localized-loading extension is experimental.

**Review without installing:** [Watch the demo GIF](demo/outputs/demonstration.gif) | [View real-versus-simulation comparisons on GitHub](demo/COMPARISON.md)

> **Download the 45.2-second video to watch it.** GitHub may say “too large to preview”; this does not mean the video is broken. [Download the MP4](https://github.com/Goutham-IITJ/SoftBodyDynamics/raw/refs/heads/main/demo/outputs/demonstration.mp4), then open the downloaded file. If your player does not support its codec, use the GIF above. No Python is needed to view these results.

## 1. Get the project and install dependencies

Install **Python 3.10** and **Git** first. These examples use Windows PowerShell. If you already cloned the project, skip `git clone` and open a terminal inside your existing `SoftBodyDynamics` folder.

```powershell
git clone https://github.com/Goutham-IITJ/SoftBodyDynamics.git
cd SoftBodyDynamics
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Using the virtual environment's Python directly avoids PowerShell activation-policy problems. On macOS/Linux, create it with `python3 -m venv .venv`, then use `.venv/bin/python` instead of `.\.venv\Scripts\python.exe` in the install/run commands. Dependencies are NumPy, SciPy, Matplotlib, Pillow and OpenCV. No GPU or external physics engine is required. [Environment and reproduction details](docs/REPRODUCIBILITY.md).

## 2. Run the simulator and open the model

Run these **after setup, from the repository folder**. The launcher runs the existing FEM solver, saves results, prints their location and opens a local browser viewer. Use new output folder names; existing results are never overwritten.

**Primary full-face model** — about 5.10 mm compression at 6.5 N:

```powershell
.\.venv\Scripts\python.exe -B -m analysis.localized_fem.launch full-face --force 6.5 --sequence --open --output runs/review_fullface
```

**Experimental localized patch** — a deliberately modest 0.3 N load, so true-scale motion is below 1 mm:

```powershell
.\.venv\Scripts\python.exe -B -m analysis.localized_fem.launch localized --force 0.3 --patch-length-mm 20 --patch-width-mm 30 --center-x-mm 18.25 --center-y-mm 25 --mesh 2 2 1 --sequence --open --output runs/review_localized
```

The browser displays **actual solved vertices**, not a replay of the experiment. Drag to rotate, play/step through saved equilibria, and inspect the red force arrow and displacement colors. True scale is the default; optional **5x/10x display magnification is labeled visualization-only** and does not alter the model or numeric results. The force arrow is an input indicator, not a physical bottle/card model. This is a viewer of saved results; change CLI inputs and rerun to simulate a different case.

If no browser window opens, double-click `viewer.html` inside the printed output folder. To view an **existing run without solving again**, for example the original `runs/fullface` or `runs/localized`:

```powershell
.\.venv\Scripts\python.exe -B -m analysis.localized_fem.view_results runs/fullface --open
.\.venv\Scripts\python.exe -B -m analysis.localized_fem.view_results runs/localized --open
```

| File inside your chosen output folder | How to use it |
|---|---|
| `viewer.html` | Double-click to open the rotatable 3D result in a browser; no server/CDN needed |
| `deformed.png` | Final solved 3D image |
| `sequence/loading_unloading.gif` | Animation when `--sequence` was requested; open in a browser/image viewer |
| `diagnostics.json` | Force, compression, convergence and support diagnostics |
| `nodes.csv`, `tetrahedra.csv` | Reference/solved vertices, applied nodal loads and element connectivity |

The older `analysis.localized_fem.simulator` command remains available but **does not open a window automatically**. The new `launch` command adds viewing and clear output messages; it uses the same solver. Run `--help` for options.

## 3. Understand what worked and what did not

| Case | Outcome |
|---|---|
| Frozen full-face model | Primary submission; numerically verified and calibrated/evaluated retrospectively. The 500 ml mismatch remains. |
| Small 0.3 N localized run | **Converged**, with admissible support. The 2/2/1 quick example has about 0.289 mm peak motion; the 4/4/2 example has about 0.464 mm. Both look subtle at true scale, and the difference shows mesh sensitivity. Not a failed solve, but not experimentally validated. |
| Nominal 10.54575 N half-area run | **Failed at its final load step.** No valid nominal prediction or experimental error score is claimed. |

Localized mesh dependence, unknown fingertip force, lack of independent prospective validation and unidentified damping/physical recovery time remain disclosed. Increasing visual magnification does not resolve those limitations. Playback traverses reversible equilibria; playback time is not physical recovery time.

## What is verified, fitted, and experimental?

| Part | Evidence and scope |
|---|---|
| Numerical mechanics | Verified hyperfoam energy/stress, Tet4 assembly and nonlinear equilibrium; 36 frozen regression tests |
| Experimental calibration | First 500/1000 ml cycles fit only mu; alpha/beta and nominal geometry are assumed |
| Retrospective evaluation | Both 750 ml cycles excluded from FEM fitting, but already inspected during earlier model selection; not untouched prospective validation |
| Localized extension | Exact clipped reference traction and verified small-load unilateral bottom support; 18 localized/support/CLI tests; experimental spatial accuracy |
| Recovery and fresh validation | Reversible equilibria shown in the demo; no identified damping or physical recovery timing, and no independent prediction-first experiment |

The primary model is **mu = 6999.814990181902 Pa, alpha = 10, beta = 0**, with **73 × 50 × 20 mm yellow deformable foam** above **7 mm rigid green backing**. Full-face loading uses a horizontal frictionless normal platen constraint. The frozen baseline tag is `baseline-v1-fullface-fem`; Phase 7 does not replace it or change its calibration.

| Nominal water load | Measured cycle 1 / 2 compression, mm | Primary full-face FEM, mm |
|---|---:|---:|
| 500 ml | 3.012 / 2.585 | 3.923 |
| 750 ml | 7.662 / 6.798 | 7.488 |
| 1000 ml | 10.987 / 10.974 | 10.316 |

The **500 ml mismatch is unresolved**. Calibration RMSE is 0.800 mm; intermediate-load RMSE is 0.504 mm, versus 0.490 mm for empirical interpolation. Forces assume water density 1 g/ml, unmeasured 75 g bottle tare, g = 9.81 m/s² and stationary full support. Mu is an effective specimen coefficient conditional on these assumptions, not a uniquely identified intrinsic property. See the [calibration report](analysis/calibration/REPORT.md) and [parameter CSV](analysis/calibration/outputs/parameters.csv).

## Verify and reproduce

```powershell
.\.venv\Scripts\python.exe -B demo/check.py
.\.venv\Scripts\python.exe -B -m unittest analysis.localized_fem.test_localized analysis.localized_fem.test_support analysis.localized_fem.test_cli analysis.localized_fem.test_view_results -v
.\.venv\Scripts\python.exe -B -m analysis.localized_fem.check_package
```

The authorized-delta checker preserves historical manifests while explicitly accounting for requested README revisions. Existing demo/calibration generators write fixed historical output directories; use a separate working copy for regeneration, as described in the reproduction guide. The original demonstration and measurements remain unchanged.

### Run a new full-face force query

Use the primary command in section 2 with a different `--force` and a new output directory. It calls the unchanged frozen Stage 6 API. Its full-face compression search limit remains 13 mm.

The [GitHub comparison page](demo/COMPARISON.md) requires no local setup. The older `demo/outputs/index.html` is **local HTML, not a hosted website**: after cloning, open it with `Start-Process .\demo\outputs\index.html` on Windows. Clicking its GitHub file page displays source code rather than rendering the presentation.

## Experimental localized loading

The separate CLI uses downward **reference-area dead traction**, free top nodes and a unilateral frictionless bottom plane. It does not enforce a rigid card's planarity, tilt, evolving footprint or pressure redistribution. Its packaged 4/4/2 default is an affordable exploratory mesh; the quick command above deliberately uses the verified 2/2/1 modest-load example.

The final synthetic refinement changed peak displacement by **6.8%** and loaded-area mean by **11.4%**. The single frozen half-area attempt at **10.54575 N failed** at its final step; no admissible nominal prediction or experimental error score was exported. Unknown supported force, hidden depth contact, optical scale and backing behavior also limit comparison. Fingertip force is unknown: no validated force-depth law is claimed. See the [Phase 7C report](analysis/localized_fem/PHASE7C_REPORT.md), [Phase 7A observations](analysis/localized_experiments/REPORT.md), and existing [localized GIF](analysis/localized_fem/phase7c/cli_localized/sequence/loading_unloading.gif).

## Research evidence and submission notes

- [Original assignment](Assignment/Dirac-Research-TakeHome.pdf), [original input videos](Videos/), [experiment guide](experiments/README.md)
- [Sequential extraction report](analysis/REPORT.md): 5,169 full-face frames, six settled-hold observations, calibration/quality records
- [Technical summary](demo/TECHNICAL_SUMMARY.md), [report index](docs/README.md), [baseline identity](docs/BASELINE.md)
- [Prediction-first protocol](demo/FRESH_VALIDATION.md): available, but no independent prospective result completed
- [Historical submission checklist](docs/SUBMISSION_CHECKLIST.md), [final handoff](docs/FINAL_HANDOFF.md), [draft email](docs/SUBMISSION_EMAIL_DRAFT.md)

Original videos, measurement CSVs, fitted parameters, prior verification outputs, comparison artifacts and demonstration media are preserved. The private ID-card photograph previously deleted by the user is excluded; its historical removal is documented in the [publication note](docs/PUBLICATION_CHECKPOINT.md). No paper reproduction is claimed; the two supplied papers remain interview reading.

Prepared with **OpenAI Codex assistance**, reusing this project's verified material, Tet4 and solver modules. Numerical and visual tools: NumPy, SciPy, Matplotlib, OpenCV and Pillow; historical data analysis also uses pandas. The preserved material report documents the [Abaqus hyperfoam convention](https://docs.software.vt.edu/abaqusv2026/English/SIMACAEMATRefMap/simamat-c-hyperfoam.htm). Experimental footage and FEM outputs are not AI-generated imagery.
