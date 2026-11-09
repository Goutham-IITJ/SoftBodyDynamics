# Final Dirac Robotics submission handoff

Published repository: [Goutham-IITJ/SoftBodyDynamics](https://github.com/Goutham-IITJ/SoftBodyDynamics)

Branch: `main`. Exact verified submission payload commit: [`14a9baa49be0b71701a3df6655a74dfb28758829`](https://github.com/Goutham-IITJ/SoftBodyDynamics/commit/14a9baa49be0b71701a3df6655a74dfb28758829). Normal push to `origin/main` succeeded. This publication receipt is recorded in a subsequent documentation-only commit; run `git rev-parse HEAD` for the final checkout revision. The baseline tag `baseline-v1-fullface-fem` remains unchanged.

## Project summary

SoftBodyDynamics is an observation-calibrated 3D tetrahedral FEM model of full-face sponge compression. First-cycle 500/1000 ml measurements fit mu = 6999.814990181902 Pa; alpha = 10, beta = 0, nominal yellow foam 73 x 50 x 20 mm, rigid green backing 7 mm. The primary submission is frozen Stage 6, with numerical verification and retrospective real/simulation comparison. Phase 7 adds a clearly experimental finite-area traction CLI; it is not a validated replacement.

## View the result

- Existing 45.2-second demonstration: [demo/outputs/demonstration.mp4](../demo/outputs/demonstration.mp4)
- [GIF fallback](../demo/outputs/demonstration.gif), [real/FEM comparison](../demo/outputs/comparison_750ml.png), [local HTML viewer](../demo/outputs/index.html)
- [Final release checklist](final_release/CHECKLIST.md), [technical reports](README.md), [reproduction instructions](REPRODUCIBILITY.md)

GitHub displays HTML source rather than deploying the viewer. Clone/download and open locally. MPEG-4 Part 2 playback support varies; use the GIF if necessary. No existing demonstration was regenerated.

## Run

From the repository root, using Python 3.10 and dependencies in requirements.txt, with new output directories:

```powershell
python -B -m analysis.localized_fem.simulator full-face --force 6.5 --output runs/fullface
python -B -m analysis.localized_fem.simulator localized --force 0.3 --patch-length-mm 20 --patch-width-mm 30 --center-x-mm 18.25 --center-y-mm 25 --mesh 2 2 1 --output runs/localized
```

The full-face example gives 5.10350445 mm compression. The inexpensive localized example gives approximately 0.289484 mm peak downward motion with admissible unilateral support. The latter is a coarse numerical demonstration, not an experimentally validated shape. Both export solved vertices, connectivity, loads, reactions, diagnostics and static 3D images. Release examples were run without requesting new animations.

## Final verification

- All 36 frozen regression tests passed.
- All 18 localized/support/CLI tests passed.
- Current authorized-delta package integrity check passed: 460 baseline-tag files excluding README unchanged; original videos, measurements, parameters and demonstration bytes preserved.
- Existing demo verified as 452 frames at 10 FPS, duration 45.2 seconds; required media and local links resolve.
- Both inexpensive CLI examples passed; [test results](final_release/test_results.json), [integrity result](final_release/package_integrity.json), [publication audit](final_release/publication_audit.json).
- All regular files are below 100,000,000 bytes; no required asset is ignored. Originals were neither recompressed nor omitted, and LFS/history were not rewritten.
- Deleted private ID-card photograph remains absent/ignored. High-confidence secret/private-file scans found no hits; representative new video frames had no legible ID details. This is not a claim of exhaustive frame-by-frame OCR.

The historical README hashes are preserved. The documented checker now accepts a separately recorded, user-authorized final README delta; historical manifests are not edited to conceal changes. Historical whole-snapshot checks still report the README mismatch. The release changes documentation, integrity bookkeeping and includes the completed experimental extension; no physics development was performed.

## Known limitations and remaining submission requirements

- Primary 500 ml calibration mismatch remains: measured 3.012 mm (first cycle), predicted 3.923 mm. Full-face calibration RMSE is 0.800 mm.
- No independent prospective prediction-first validation. Both 750 ml observations were already inspected before final FEM evaluation; retrospective intermediate RMSE is 0.504 mm.
- No identified damping, dynamics or physical recovery time. Equilibrium playback does not validate recovery speed.
- No validated fingertip force or force-depth law.
- The single nominal 10.54575 N localized half-area prediction failed; no valid nominal state/error score was published or retried.
- Localized mesh dependence remains: last synthetic peak change 6.8%, area mean 11.4%. Unknown real pressure, supported bottle force, footprint, card tilt and backing behavior remain unresolved.
- A traction patch is not rigid-card contact. The primary baseline does not claim general fingertip/contact prediction.
- A clean installation on other platforms, hiring-team access and hosted browser playback have not been independently tested. No visibility/access settings were changed.
- The user must confirm the hiring team can access repository/result links, optionally provide a separately hosted result, and send the [draft reply](SUBMISSION_EMAIL_DRAFT.md). No email was sent. Paper-discussion preparation remains the user's responsibility.

Physics development has stopped. This release does not close the disclosed prospective-validation/recovery gaps.
