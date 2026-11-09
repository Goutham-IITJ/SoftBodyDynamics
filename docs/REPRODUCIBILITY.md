# Reproducibility without disturbing the freeze

All paths below are relative to the repository root. Existing media, measurements and verification artifacts are bundled. Viewing and verification do not require regeneration.

## Installed and supported environment

The audit used Python **3.10.7** on Windows with NumPy 2.2.6, SciPy 1.14.1, Matplotlib 3.9.0, Pillow 10.3.0, OpenCV module 5.0.0 (installed distribution `opencv-python` 5.0.0.93), and pandas 2.2.2. The [existing requirements](../requirements.txt) were inspected and retained unchanged: their pins match installed evidence, and OpenCV's existing range includes this installation. No dependency was installed or upgraded.

Use Python 3.10 for the recorded baseline. NumPy/SciPy package metadata requires ≥3.10. That lower bound does not certify every newer interpreter or a clean install; no clean-environment installation or Python 3.11 run was performed. The frozen demo/evaluation and unit tests require the existing requirements only. Historical extraction, aggregation and model-review scripts additionally import pandas; if reproducing them in a separate environment, the observed version can be installed with `python -m pip install pandas==2.2.2` after the existing requirements.

## Safe commands in this working tree

```sh
python -B demo/check.py
python -B docs/check_baseline.py
python -B demo/evaluate.py --help
python -B demo/evaluate.py predict --help
python -B demo/evaluate.py score --help
```

The first runs the 36 existing unit methods without invoking report-generating drivers. The second hashes frozen files and checks documentation/media targets. The evaluator help commands only describe its CLI. `-B` prevents new Python bytecode caches. Tests may use temporary fixtures, which are not new experimental data.

The [root README's 6.5 N query](../README.md#run-a-new-full-face-force-query) uses the existing `demo.model` API and prints a solved equilibrium without writing outputs. The [fresh protocol](../demo/FRESH_VALIDATION.md) writes exclusively to new user-chosen prediction/score files; it will not overwrite a record. Validation inputs must be actual observations when making a scientific claim.

## Output-generating commands: separate working copy only

The entry points below were confirmed by source inspection/in-memory compilation. The demo and calibration modules were also safely imported and their callable `run()` functions/signatures inspected. **They were not executed in this task.** They expose neither a temporary-output CLI override nor a dry-run option. In particular, `python demo/run_demo.py --help` is NOT safe help: the script does not parse arguments and would regenerate outputs.

To regenerate, use a separate user-owned checkout/working copy containing the inputs. No repository copy, refit, extraction or rerender was created during this audit. Do not redirect only stdout and assume file outputs have moved; all scripts retain their fixed destinations.

| Command in a separate working copy | Writes / meaning |
|---|---|
| `python -B demo/run_demo.py` | `demo/outputs/`; solves/renders 51 equilibria, selected real frames, MP4/GIF/HTML; about one minute in recorded run |
| `python -B analysis/calibration/run_calibration.py` | `analysis/calibration/outputs/`; official endpoint-only fits, evaluation and sensitivity |
| `python -B analysis/material/test_hyperfoam.py --report` | `analysis/material/verification/`; tests plus material diagnostic report artifacts |
| `python -B analysis/fem/patch_test.py` | `analysis/fem/verification/`; synthetic element/patch report artifacts |
| `python -B analysis/fem_solver/verify_solver.py` | `analysis/fem_solver/verification/`; synthetic solver report artifacts |
| `python -B analysis/sponge/verify_sponge.py` | `analysis/sponge/verification/`; synthetic nominal-geometry report artifacts |

Historical measurement regeneration, also in a separate working copy:

```sh
python -B analysis/extract.py
python -B analysis/annotate.py
python -B analysis/review_frames.py
python -B analysis/validate.py
python -B analysis/summarize.py
```

These write under `analysis/outputs/`. Validation also writes audit/sensitivity CSVs and decodes video; it is not a read-only substitute for `docs/check_baseline.py`. The extraction script supports `--video 500ml`, but still writes that experiment's existing output location. Some historical scripts execute their pipeline at import time; do not import them to probe help. The [preserved extraction guide](../analysis/README.md) describes the full dataset-specific procedure. Empirical comparison regeneration is available through `analysis/model_selection.py` and `analysis/model_review.py`, which also write their stage output directories and are not imported/run by this audit.

## Viewing and publication

Open [the local HTML presentation](../demo/outputs/index.html), or run `python -m http.server 8000 --bind 127.0.0.1` and browse to `/demo/outputs/index.html`. Stop the server when finished. GitHub's ordinary HTML file view is source, not a hosted viewer; the linked GIF/MP4 remains available as an asset. A GitHub Pages/release/other hosted result could be arranged by the user later; no hosting is configured here.

The current `.gitattributes` preserves byte-level research provenance across checkouts. Do not normalize source/configuration/CSV line endings to repair a hash failure; investigate against the baseline instead. Existing frozen configuration checks deliberately reject changed parameters/core bytes.

## Historical manifests

The original [Stage 6 package manifest](../demo/outputs/package_manifest.json) is retained unchanged, including its pre-organization root README hash. The root README is the single authorized pre-existing file edited by this task, so that historical README hash no longer matches. All its other files must still match. [BASELINE_MANIFEST.json](BASELINE_MANIFEST.json) records the complete pre-edit inventory; `check_baseline.py` explicitly permits that README edit and no scientific-file edit. `SUBMISSION_MANIFEST.json` records the organized package's current bytes without replacing the historical manifest.
