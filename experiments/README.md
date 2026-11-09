# Experimental datasets

## Existing full-face compression baseline

The original full-face videos stay in [Videos/](../Videos/): [500 ml](../Videos/500ml.mp4), [750 ml](../Videos/750ml.mp4) and [1000 ml](../Videos/1000ml.mp4). The user deleted the separate specimen photograph before publication because it exposed personal ID-card details; its historical hash remains in the original inventory. See the [publication note](../docs/PUBLICATION_CHECKPOINT.md). Two additional recordings appeared later, as cataloged below. No video was moved, re-encoded or re-extracted for publication.

The same bottle and approximately rigid 85 × 50 mm card load the 73 × 50 mm nominal specimen footprint. [The extraction configuration](../analysis/config.json) identifies reviewed hold/separation windows. [Measurement tables](../analysis/outputs/) retain the actual decoded timestamps, missing detections, quality flags and card-only reference. [cycle_summary.csv](../analysis/outputs/cycle_summary.csv) contains the six settled compression observations; [the extraction report](../analysis/REPORT.md) explains geometry/calibration uncertainty and recovery limits.

**Calibration separation:** first 500/1000 ml cycles fit the official scale; second endpoint cycles assess repeated loads; both 750 ml cycles are excluded from FEM fitting but already inspected retrospectively. A genuinely new prediction-first observation is not present. Preserve this split and all raw values.

## New full-face validation

Use the existing [prediction-first protocol](../demo/FRESH_VALIDATION.md). Save the actual measured total mass, condition, initial-state notes and frozen prediction before measuring compression; then retain observation and score together. Do not relabel existing videos or synthetic test fixtures as fresh experiments, or automatically refit after scoring.

## Future localized-loading recordings

[localized_loading/](localized_loading/) is a documentation-only catalog/destination for the proposed half-area card and finger-indentation work. During the audit, [Videos/fingertip.mp4](../Videos/fingertip.mp4) and [Videos/half area.mp4](<../Videos/half area.mp4>) appeared outside this task's edits. They remain at those paths. Their contents, loading conditions and force/measurement interpretation have not been reviewed or analyzed here; their names alone do not establish validation. No video was copied into the new directory. Keep separate identifiers, metadata and future analysis outputs; neither recording enters the existing full-face calibration CSV or parameter fit.
