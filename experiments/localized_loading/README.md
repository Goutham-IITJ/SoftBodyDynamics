# Localized-loading dataset catalog — not analyzed

This directory's only current content is this guide. Two recordings arrived during the audit: [Videos/fingertip.mp4](../../Videos/fingertip.mp4) (45,712,866 bytes) and [Videos/half area.mp4](<../../Videos/half area.mp4>) (47,762,345 bytes). They remain outside this directory at their actual arrival paths. Names suggest the intended categories, but their contents/conditions were not reviewed, and no measurements, forces or validation conclusions were extracted. Current hashes are recorded in the submission inventory.

The Stage 6 simulator does **not** implement the mechanics of either proposed category. The following describes proposed metadata/validation needs, not completed analysis:

| Proposed category | What a future record should establish | What is not currently known |
|---|---|---|
| Half-area ID-card platen loading | Actual supported area, card position/orientation, known supported mass or measured force, baseline/history, observed settled deformation | Actual pressure distribution, finite-contact evolution and whether loading stays centered/horizontal |
| Localized finger indentation | Finger/indenter geometry and position, indentation trajectory, camera/face calibration, specimen baseline/history; independently measured force if force identification is intended | Finger force from video alone, pressure distribution, friction, changing contact area and validated material parameters for this mode |

Record actual conditions and uncertainty; a geometric half-area label does not prove uniform pressure. Future filenames/identifiers should distinguish category and trial. Keep original media unchanged and future annotations/results separate from them. No placeholder masses, force values or displacement measurements are provided.

Any new recording belongs to a new research dataset, not an extra row in the [frozen full-face dataset](../README.md). See the [simulator roadmap](../../docs/SIMULATOR_ROADMAP.md) before treating such recordings as supported simulator inputs.
