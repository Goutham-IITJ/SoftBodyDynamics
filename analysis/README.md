# Phase 2: experimental video measurements

This directory contains image-analysis code and measurements only. It does not fit stiffness, damping, a constitutive law, or a simulation. The training/evaluation split is retained in every experiment CSV.

## Reproduce

From the repository root, using an environment that already has NumPy, OpenCV, SciPy, pandas and Matplotlib:

```powershell
python analysis/extract.py
python analysis/annotate.py
python analysis/review_frames.py
python analysis/validate.py
python analysis/summarize.py
```

No installation or environment change is performed. Paths are resolved relative to the script, so these scripts also work when invoked by absolute path. `extract.py --video 500ml` processes one experiment. Full extraction processes every frame; it can take several minutes. `annotate.py` permits event-window revisions without repeating image processing. Human review is still required when applying this dataset-specific configuration to new videos.

Original videos are opened read-only. SHA-256 is computed before and after extraction and independently checked by validation. All generated artifacts stay in `analysis/outputs/`. Dependency versions and extraction/configuration hashes are recorded in `environment.json`; later annotation hashes are in `annotation_provenance.json`.

## Main outputs

- `REPORT.md`: technical findings and answers to the eight milestone questions.
- `outputs/video_metadata.csv`: decoded timing and dimensions.
- `outputs/force_pressure_table.csv`: assumed forces, pressures, and tare bounds.
- `outputs/cycle_summary.csv`: exact aggregation windows, frame references, per-cycle measurements and free-recovery availability.
- `outputs/measurement_quality.csv`: calibration checks, noise, registration and marker coverage.
- `outputs/load_comparison.png`, `outputs/free_recovery.png`: comparison and recovery plots.
- `outputs/<video>/measurements.csv`: one row for every decoded frame.
- `outputs/<video>/markers.csv`: nine attempted marker measurements per frame; missing values remain NaN.
- `outputs/<video>/phases.csv`: reviewed event brackets and candidate hold windows.
- `outputs/<video>/ruler_ticks.csv`, `calibration.json`, `calibration.png`: calibration evidence.
- `outputs/<video>/registration.png`, `trajectories.png`, `lateral.png`: time series.
- `outputs/<video>/frame_*`: representative originals, overlays and background features.
- `outputs/manual_review/`: contact/separation sheets labeled with actual decoded timestamps and zero-based frame indices.
- `outputs/validation_checks.csv`, `segmentation_sensitivity.csv`: integrity and measurement-method checks. These are not physical-model validation.
- `outputs/manual_review/frame_manifest.csv`: sequential frame/time identity for every contact-sheet tile.
- `outputs/representative_frame_manifest.csv`, `final_consistency.json`: representative-image identities and final consistency/provenance record.

## Methods and conventions

Images are analyzed at half resolution, but reported image coordinates are in original-resolution pixels. Every frame retains its decoder presentation timestamp; no constant-FPS resampling is performed. Positive image y and positive plate translation point downwards. Compression is a reduction in thickness, positive when compressed. Positive marker dx points right. All displacements reference the median card-only interval 0.2–2.0 s, not a hypothetical force-free specimen.

Background registration uses forward/backward-checked Lucas–Kanade features and a RANSAC similarity transform from the first frame. Features are requested only outside the specimen/bottle region. In these clips most available features are on the ruler: this is effectively **ruler-anchored image registration**, not an independently measured camera trajectory. Camera motion cannot be separated from ruler motion or all perspective/parallax effects. The reported translation, rotation and scale describe the image transform. Feature overlays expose this spatial concentration.

Calibration detects 1-mm ruler ticks. A quadratic map from vertical image coordinate to relative ruler millimetres handles the observed nonuniform spacing; its origin is arbitrary and cancels in differences. This is an image-coordinate calibration fit, not a physical-parameter fit. The lowest specimen pixels are below the last fitted tick and require a small extrapolation, whose bounds are recorded. Coplanarity of ruler and specimen is unverified. A single vertical ruler cannot establish a full camera calibration or a horizontal homography. Horizontal measurements use mean ruler pixels/mm and are explicitly ruler-equivalent. Known dimensions are independent checks, never constraints used to force agreement.

Yellow/green color occupancy is measured in narrow columns. Top, layer interface and bottom boundaries are retained separately. Total and layer thicknesses are medians across columns; medians of component thicknesses need not sum exactly to the median total thickness. Left/center/right thicknesses expose spatial variation. These are visible color/silhouette boundaries with irregular fibres, not exact constitutive interfaces.

The card's visible lower edge is fitted with a robust straight line. Mean vertical motion, left-tip horizontal motion, apparent image-plane rotation, and residual departures from the line are separate columns. Hidden edge regions remain missing. Residuals can arise from edge detection/occlusion as well as bending and are not proof of plate flexibility. The rigid-platen approximation remains the user's stated initial assumption. Sponge thickness is measured relative to its bottom boundary, rather than treating all card displacement as compression.

Marker IDs are row-major: 1–3 upper row, 4–6 middle row, 7–9 near the interface; within each row left, center, right. Seeds in `config.json` are manually selected from the current videos, not inherited marker spacing. Geometry predicts a small search region, but coordinates are emitted only when a dark-ink component is detected. Predictions are never emitted as measured positions. Threshold-sensitive centroids and fragmented/edge-clipped ink are a substantial limitation. Confidence scores are heuristic image-quality scores, not probabilities. Missing detections are not interpolated.

Overlay colors: yellow = upper foam boundary; blue = yellow/green interface; green = bottom silhouette; magenta = detected card edge; red numbered circles = detected marker centroids; cyan horizontal segment = bottle-bottom proxy. Background-feature images use green dots for accepted tracks. `bottle_motion.png` displays the bottle/plate trajectories and reviewed separation intervals.

Bottle-bottom position is a grayscale contour proxy and becomes unavailable when outside the frame or visually ambiguous. Its median bottom is not the lowest 3D point and its apparent gap is not itself a contact detector. Complete-separation brackets are manually reviewed using visible clearance, conservatively acknowledging the single-view limitation. Force is NaN during placement, unverified loading, lifting and separation brackets. Candidate late-hold windows use the assumed gravitational force, explicitly conditional on full support and no hand force; hands-off status is not independently visible. After the latest separation bound, incremental bottle force is zero. Earlier loaded motion is not automatically called creep.

The force range uses the same shared bottle tare of 50–100 g in all trials. Its uncertainty is correlated across loads; do not treat the three tare errors as independent. The card's mass is not added to incremental force. Pressure uses 0.00365 m², with uniform pressure and full footprint contact explicitly assumed. Card overhang is excluded.

## Uncertainty and interpretation

CSV uncertainty columns distinguish baseline image noise, a boundary-localization floor, a practical 0.3-mm resolution allowance, and a separate assumed 10% calibration/plane sensitivity. The 10% is motivated by dimensional mismatch but is **not a statistically established bound**. It does not resolve the larger disagreement in the green layer's absolute thickness. Marker uncertainty floors are 0.4 mm at clipped side markers and 0.2 mm at interior markers; these are engineering allowances, not confidence intervals. Pair uncertainty combines localization terms only; image-scale, shape-change and identity ambiguity remain additional systematic effects.

`validate.py` checks all frame counts, timestamps, force masks, missing-data semantics, splits and source hashes. It tests registration using a known synthetic image warp, and reports segmentation sensitivity to occupancy thresholds at sampled actual frames. These checks establish internal consistency and numerical behavior, not independently calibrated physical accuracy.

The 750 ml experiment is processed for measurement quality as requested but remains excluded from future physical-parameter fitting. No physical parameters have been fitted to any video.
