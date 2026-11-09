# SoftBodyDynamics

Observation-calibrated 3D sponge mechanics for the Dirac Robotics research take-home. A hyperfoam tetrahedral FEM predicts equilibrium compression from applied force; measured trajectories do not drive the mesh.

**[View the comparison presentation](demo/outputs/index.html)** · **[Demo video](demo/outputs/demonstration.mp4)** · **[GIF animation](demo/outputs/demonstration.gif)** · **[Technical summary](demo/TECHNICAL_SUMMARY.md)**

Download/clone the repository to open the HTML locally. GitHub's source view does not execute HTML; use the GIF/video links there. The MP4 uses MPEG-4 Part 2; the GIF works when a browser lacks that codec. No external service or network is needed to view the local package.

![Real specimen compared with frozen FEM at 750 ml](demo/outputs/comparison_750ml.png)

## Run

Tested with Python 3.10.7, NumPy 2.2.6, SciPy 1.14.1, Matplotlib 3.9.0, Pillow 10.3.0 and OpenCV 5.0.0. A clean Python 3.10/3.11 environment can use:

```sh
python -m venv .venv
# Windows PowerShell: .\.venv\Scripts\Activate.ps1
# Linux/macOS: source .venv/bin/activate
python -m pip install -r requirements.txt
python -B demo/run_demo.py
python -B demo/check.py
```

Run commands from the repository root. The demo writes only `demo/outputs/`, takes roughly one minute on the development machine, and uses installed OpenCV/Pillow encoders; FFmpeg CLI, GPU and large 3D libraries are unnecessary. Actual runtime varies. Its 51 equilibrium states use 27 nodes/48 tetrahedra. Existing outputs are bundled, so viewing does not require regeneration. Unit tests include saved-output integrity checks; generate the demo first if removing bundled outputs.

For an optional local HTTP viewer:

```sh
python -m http.server 8000 --bind 127.0.0.1
# Open http://127.0.0.1:8000/demo/outputs/index.html
```

The extraction, model reviews and calibration remain separately reproducible using their reports. The frozen demo does not run or repeat calibration. Older extraction/review entry points additionally require pandas, and are not necessary for viewing/evaluation.

## Approach and results

Videos at three nominal water volumes provide six settled compression measurements. First 500/1000 ml cycles fit **one effective scale**, mu = **6999.814990181902 Pa**, at assumed alpha = 10, beta = 0. The yellow volume is 73 × 50 × **20 mm**, above rigid 7 mm green backing. A rigid massless 85 × 50 mm card imposes full-face frictionless normal constraints; foam contact area is 0.00365 m². The original card-on-sponge state is the incremental reference.

The verified constitutive kernel supplies energy and stress, Tet4 elements assemble nodal forces, and a nonlinear minimizer relaxes free degrees of freedom. An outer root solve matches the platen reaction to the applied force. The demo renders those solved positions directly, including intermediate loading/unloading equilibria and the final zero-load state.

| Load | Assumed force, N | Measured cycles 1 / 2, mm | Frozen FEM, mm |
|---|---:|---:|---:|
| 500 ml | 5.64075 | 3.012 / 2.585 | 3.923 |
| 750 ml | 8.09325 | 7.662 / 6.798 | 7.488 |
| 1000 ml | 10.54575 | 10.987 / 10.974 | 10.316 |

These forces assume water density 1 g/ml, shared **unmeasured 75 g bottle tare**, g = 9.81 m/s² and stationary full support. Calibration RMSE is 0.800 mm. The primary low-load mismatch exceeds its nominal engineering allowance. Intermediate-load RMSE is 0.504 mm versus 0.490 mm for empirical interpolation: no demonstrated FEM accuracy advantage.

The 750 ml observations are **held out from this FEM fitting**, but were inspected during earlier model selection. They are not prospective validation. Alpha = 20 remains a separately labeled sensitivity: calibration RMSE 0.224 mm, intermediate RMSE 0.838 mm. It does not replace the official primary model. Source data and full residuals: [Stage 5 report](analysis/calibration/REPORT.md).

## What this does and does not establish

- Numerical verification covers energies/gradients, assembly, positive Jacobians, force balance, coordinate translation and homogeneous mesh consistency. The test runner includes all 36 unit methods.
- The model is quasi-static and reversible. **Animation duration is presentation time, not physical recovery time.** No damping or time integrator is identified. Zero modeled lateral expansion follows assumed beta = 0, not measured lateral behavior.
- Mu is an effective coefficient conditional on geometry, reference, constitutive shape and contact. It is not a uniquely identified intrinsic material property. Rigid backing neglects real compliance/interlayer shear. Full-face plane constraints are not finite-footprint collision/contact; there is no tilt, friction or indentation validation.
- Optical scale/plane uncertainty, apparent layer dimensions, platen movement and differing cycle histories remain consequential. Two meshes agreeing on a homogeneous affine state does not establish accuracy for arbitrary spatial interactions.
- **Assignment gaps:** no new prospective interaction has been recorded, and measured recovery timing is not reproduced. A fresh-test protocol is provided; new data are not fabricated. Repository publication/hiring-team access, a hosted result link, email submission and interview preparation remain user actions, not performed by this package.

## Fresh validation without refitting

[Follow the prediction-first protocol](demo/FRESH_VALIDATION.md). `demo/evaluate.py predict` accepts actual measured **total bottle mass**, loading condition and initial-state notes; it does not accept observed compression. It saves the frozen prediction first. A later `score` command accepts the real settled measurement, verifies the receipt/model and reports the residual. Neither command fits parameters, and neither overwrites an existing record.

## Files and provenance

- `Videos/`: original input clips and specimen photograph, unchanged; no synthetic replacement inputs.
- `analysis/`: preserved extraction, model review and five verified stages, with reports and CSVs.
- `demo/`: entry points, frozen model snapshot, validation protocol, tests and technical summary.
- `demo/outputs/`: MP4/GIF, local HTML presentation, real/FEM comparisons, solved nodes/connectivity, force-compression graph, numerical summary and preservation hashes.

Real comparison frames are sequentially decoded within the selected hold windows and retain original zero-based frame indices/timestamps in `real_frame_manifest.csv`. Displayed measurements are hold medians, not single-frame estimates. `solved_fem_states.npz` contains all rendered equilibrium positions. The demo verifies hashes of **401 prior analysis, video, assignment and paper files** before/after generation. Previous results are not overwritten.

## Credits

Prepared with OpenAI Codex assistance. The project reuses its verified Stage 1–4 modules rather than a third-party simulator. Numerical/visual tools: NumPy, SciPy, Matplotlib, OpenCV and Pillow. The hyperfoam convention is credited in the [material report](analysis/material/REPORT.md); structured Tet4 assembly and solver derivations are documented in their stage reports. Paper PDFs are included as assignment reading, not as code claimed to be reproduced. No AI-generated imagery replaces experimental frames or FEM results.
