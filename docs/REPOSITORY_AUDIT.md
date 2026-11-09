# Repository organization and freeze audit

Audit date: 9 November 2026. Scope is documentation/navigation, byte-level baseline identification and conservative ignore rules. No scientific/computational baseline change was made.

## Changes

**Modified pre-existing file:** root [README.md](../README.md) only. It now routes reviewers from demonstration/comparison through mechanics, a working full-face query, tests, reports and submission gaps; it distinguishes safe verification from fixed-directory regeneration.

**Added:** `.gitignore`; `docs/README.md`, `BASELINE.md`, `BASELINE_MANIFEST.json`, `REPRODUCIBILITY.md`, `SIMULATOR_ROADMAP.md`, `SUBMISSION_CHECKLIST.md`, this `REPOSITORY_AUDIT.md`, `check_baseline.py`, `SUBMISSION_MANIFEST.json`, `FREEZE_AUDIT.json`; `experiments/README.md` and `experiments/localized_loading/README.md`. The experimental extension directory contains documentation only. New audit code reads/hashes files; it implements no physics or model fitting.

All other **445 pre-existing non-cache files** remain byte-identical to the [start-of-task inventory](BASELINE_MANIFEST.json). This includes material/FEM/solver/sponge/calibration/demo source and tests, canonical parameters/configuration, measurements, every earlier report, generated verification output, original videos, papers/assignment, final MP4/GIF/HTML and visualization assets. `.gitattributes` and `requirements.txt` were not changed. No source/output/video was moved, deleted, re-extracted, refitted, rerendered or converted.

**Concurrent additions outside this task:** `Videos/fingertip.mp4` (45,712,866 bytes) and `Videos/half area.mp4` (47,762,345 bytes) appeared after the original inventory, and local Git commits/tracking appeared during work. These additions were preserved without staging, moving or analyzing them. The new recordings are cataloged separately, not added to the full-face calibration or described as prediction-first validation. Their current hashes are included in the organized submission inventory.

The [old Stage 6 package manifest](../demo/outputs/package_manifest.json) remains a historical artifact. Its root README hash intentionally refers to the earlier README; that is the only expected old-package mismatch. All other hashes still agree. The new [submission manifest](SUBMISSION_MANIFEST.json) identifies current documentation without overwriting the old manifest.

## Git before and after

At the initial snapshot, local `main` was unborn: **no commits, no tracked files**. An `origin` remote name existed. During the audit, local commits/tracked files appeared outside this task's actions; latest observed short HEAD was `5d56d8e` (`material report`), and 18 files were tracked. Root README is now a modified tracked file; many source/data/media/documentation files remain untracked. The status below and final machine-readable audit record these observations, not actions performed by the agent. No reset/discard, staging, commit, tag, branch, push or email was performed by this task. Remote publication/history/access were not checked.

Before:

```text
?? .gitattributes
?? Assignment/
?? Papers/
?? README.md
?? Videos/
?? analysis/
?? demo/
?? requirements.txt
```

After (captured final-audit status):

```text
 M README.md
?? .gitattributes
?? .gitignore
?? Assignment/
?? Papers/
?? Videos/
?? analysis/README.md
?? analysis/REPORT.md
?? analysis/calibration/REPORT.md
?? analysis/calibration/outputs/
?? analysis/calibration/run_calibration.py
?? analysis/calibration/test_calibration.py
?? analysis/fem/verification/
?? analysis/fem_solver/verification/
?? analysis/fem_solver/verify_solver.py
?? analysis/material/hyperfoam.py
?? analysis/material/test_hyperfoam.py
?? analysis/material/verification/
?? analysis/model_review.py
?? analysis/model_review/
?? analysis/model_selection.py
?? analysis/model_selection/
?? analysis/outputs/
?? analysis/review_frames.py
?? analysis/sponge/
?? analysis/summarize.py
?? analysis/validate.py
?? demo/FRESH_VALIDATION.md
?? demo/check.py
?? demo/evaluate.py
?? demo/fresh_observation.template.json
?? demo/frozen_models.json
?? demo/model.py
?? demo/outputs/
?? docs/BASELINE.md
?? docs/FREEZE_AUDIT.json
?? docs/README.md
?? docs/REPOSITORY_AUDIT.md
?? docs/REPRODUCIBILITY.md
?? docs/SIMULATOR_ROADMAP.md
?? docs/SUBMISSION_CHECKLIST.md
?? docs/SUBMISSION_MANIFEST.json
?? docs/check_baseline.py
?? experiments/
?? requirements.txt
```

Suggested user-created baseline tag after review and a user-created complete-baseline commit: **`baseline-v1-fullface-fem`**. The documentation-only freeze is not a Git tag or independent archival guarantee. Existing external commits are preserved; their appearance does not mean all submission artifacts are committed.

## Reproducibility checks

- `python -B demo/check.py`: **36 tests pass**, 85.194 s in this audit's installed environment. These test mathematical/numerical behavior and saved artifact integrity, not new physical validation.
- The exact 6.5 N command in the revised README runs successfully and prints **5.103504445816268 mm**, min J **0.7448247777091859**, free residual **5.4401eâˆ’15 N**. It writes no baseline output.
- `demo/evaluate.py --help`, `predict --help` and `score --help` execute successfully. The existing unit tests exercise prediction-first receipt integrity, scoring without refitting and refusal to overwrite records; no fresh experimental claim is made.
- Demo/calibration `run()` entry points were safely imported, inspected and compiled in memory. Both have fixed output destinations, no output override and no dry-run flag. They were **not executed**, as required to protect frozen results. All historical regeneration commands are documented separately in [REPRODUCIBILITY.md](REPRODUCIBILITY.md).
- The read-only [baseline checker](check_baseline.py) validates preserved byte hashes, the canonical configuration and local Markdown/HTML targets. The final machine-readable check is in [FREEZE_AUDIT.json](FREEZE_AUDIT.json).
- All local presentation references exist; no presentation links required editing. The HTML, media and render code are unchanged. GitHub ordinary HTML file view is not hosting; README/viewer guidance explicitly requires local viewing or future user-arranged hosting. External link availability beyond the consulted GitHub documentation is not asserted by the local-link checker.
- Existing dependency pins match the installed environment; no dependency file edit/install was justified. Pandas 2.2.2 is documented as an additional observed historical-analysis dependency. Python 3.10.7 was used; newer-interpreter and clean-install support are not claimed as tested.

## Size, duplicates and hygiene

Before organization, project payload excluding `.git` was **345,609,863 bytes (345.61 MB / 329.60 MiB)** over 447 files, including one Python cache. Excluding that cache gives the 446-file, 345,581,283-byte baseline inventory. The current exact count/size including new documentation is recorded in [FREEZE_AUDIT.json](FREEZE_AUDIT.json); this is working-tree payload, not compressed Git history size.

| Large input | Bytes | Approximate MiB |
|---|---:|---:|
| `Videos/1000ml.mp4` | 86,245,302 | 82.25 |
| `Videos/750ml.mp4` | 78,948,991 | 75.29 |
| `Videos/500ml.mp4` | 51,964,252 | 49.56 |
| `Papers/3D Gaussian splatting.pdf` | 35,829,709 | 34.17 |
| `Papers/2611.04492v1.pdf` | 16,066,422 | 15.32 |
| New `Videos/half area.mp4` (unreviewed) | 47,762,345 | 45.55 |
| New `Videos/fingertip.mp4` (unreviewed) | 45,712,866 | 43.60 |

The two incoming recordings add 93,475,211 bytes, bringing the organized payload to approximately **439 MB / 419 MiB** before Git history. All files are below GitHub's documented 100 MiB regular-Git file limit. The 750/1000 ml clips exceed its 50 MiB warning threshold. All five clips and the larger paper exceed its 25 MiB browser-upload limit; use reviewed Git transport or an explicitly chosen large-asset strategy rather than relying on web uploads. These limits and the recommendation to keep repositories ideally below 1 GB are from [GitHub's large-file guidance](https://docs.github.com/en/repositories/working-with-files/managing-large-files/about-large-files-on-github), consulted during this audit. The present payload alone does not exceed those regular-Git hard limits; future binary revision history could grow quickly.

No Git LFS conversion, release upload, asset deletion or history rewrite was performed. If future recordings materially increase size, the user can choose LFS or a release/object-storage arrangement while preserving original bytes, access and stable links. Any such storage change needs its own review because frozen byte/provenance checks assume locally available original files.

Twelve identical-file groups were found and retained. They include deliberate per-scenario mesh/reference/reversible-state exports, the calibration plot copied into the demo, and source/output frozen configuration snapshots. Deduplicating them would break provenance or expected paths. No destructive cleanup was attempted.

The sole existing cache is `analysis/__pycache__/extract.cpython-310.pyc` (28,580 bytes); it remains on disk but is now ignored. No virtual environments or `.tmp`/`.bak`/`.log` scratch files were found in the inspected project. `.gitignore` adds only disposable caches, local environments, editor/OS scratch and temporary patterns. It does not ignore original videos, papers, measurements, necessary parameters/meshes, fresh prediction receipts or the demonstration. Existing `.gitattributes` preserves research file bytes and remains unchanged.

## Submission blockers and scope boundary

See the assignment-cross-checked [submission checklist](SUBMISSION_CHECKLIST.md). A genuine new prediction-first experimental interaction, identified recovery timing, paper-discussion readiness, a reviewed local commit/publication/access arrangement, a viewable hosted result URL and the required user-sent email remain pending or unverified. The existing 750 ml comparison is retrospective; no data were fabricated to close those gaps.

The [localized-loading catalog/location](../experiments/localized_loading/README.md) documents the two incoming recordings without analysis; the [simulator roadmap](SIMULATOR_ROADMAP.md) describes planned capabilities only. No video was copied/moved or analyzed. There is no implemented general fingertip/contact simulator, damping, new constitutive law or MuJoCo/Gazebo port. Work stops at documentation organization and reproducibility verification.
