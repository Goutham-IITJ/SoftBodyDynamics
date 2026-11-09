# Experimental data extraction report

Phase 2, 9 November 2026. No physical parameters or simulations were fitted. The original videos are preserved, with SHA-256 verification. The existing geometry measurements were retained during the final sequential-frame review.

## Decision

The data support choosing a reduced-order **effective axial-compression** representation and beginning a conditional assessment of its load-dependent static response. They do **not yet support a defensible joint identification of Kelvin–Voigt stiffness and damping**. Unknown force during lifting and placement, limited free-recovery amplitude, and unresolved geometric calibration systematics prevent that stronger conclusion. A single linear response across all loads should be tested, not presumed.

Full-surface compression remains appropriate. Localized indentation is unnecessary for resolving the present uncertainties.

## Completed work and verification

The existing seven files were inspected before further changes: `config.json`, `extract.py`, `annotate.py`, `review_frames.py`, `validate.py`, `summarize.py`, and `README.md`. Existing measurement tables, quality summaries, plots, overlays, and sequential contact sheets were inspected. Full extraction and summary generation were already complete. The interrupted sequential jobs had also completed successfully. Remaining work was to strengthen the timestamp check from sampled frames to every frame, expose contact-sheet frame identities in a manifest, and write this report.

The final checks cover all 5,169 decoded frames and 46,521 attempted marker observations. Every sequentially decoded timestamp is compared with its measurement row; marker frame/time joins, force masks, data splits, frame counts and original hashes are checked. `outputs/validation_checks.csv` records results. `outputs/manual_review/frame_manifest.csv` lists each contact-sheet tile's zero-based frame index and timestamp. Individual `frame_XXXXX_*` image names refer to measurement CSV row XXXXX. Labels round timestamps to three decimals; CSVs retain precision. Phase boundary frame fields use the first frame at or after the annotated boundary, so rounded boundary labels can differ by one frame from a visually selected neighboring frame.

Random seeking had produced misleading frame counters. Final review sheets and validation decode sequentially. Earlier geometry extraction was already sequential and did not require repeating. Measurement CSVs were not rescaled or interpolated to conceal uncertainty. Numerical integrity checks verify the pipeline, not independent physical accuracy.

## Timing

Source: `outputs/video_metadata.csv` and each experiment's `timestamp_gaps.csv`.

| Video | Frames | Average reported FPS | Last frame time, s | Largest interval, ms | Intervals over 25 ms |
|---|---:|---:|---:|---:|---:|
| 500 ml | 1,238 | 59.9634 | 20.6293 | 33.333 | 1 |
| 750 ml | 1,883 | 59.9481 | 31.3938 | 33.322 | 2 |
| 1000 ml | 2,048 | 59.6911 | 34.2933 | 66.633 | 8 |

All videos are 1920 × 1080. Timestamps increase strictly. No uniform-60-FPS reconstruction is used. Timing gaps can affect fast transients, especially in the 1000 ml trial.

## Calibration and dimensional inconsistencies

Source: `outputs/measurement_quality.csv`, per-video `ruler_ticks.csv`, `calibration.json`, and calibration images.

| Video | Baseline total height, mm | Yellow color-region thickness, mm | Green color-region thickness, mm | Ruler-equivalent visible length, mm |
|---|---:|---:|---:|---:|
| 500 ml | 27.86 | 17.79 | 10.12 | 67.81 |
| 750 ml | 28.31 | 17.96 | 10.25 | 68.59 |
| 1000 ml | 27.56 | 17.52 | 9.99 | 67.38 |
| Stated specimen dimensions | 27 | 20 | 7 | 73 |

Ruler spacing varies with image height. A quadratic vertical coordinate-to-mm map fits detected 1-mm ticks with residual RMS 0.017–0.021 mm. This small residual describes agreement with ruler ticks only. It does not establish coplanarity, lens calibration or dimensional accuracy at the sponge. Bottom silhouette points extend below the last fitted tick and require extrapolation.

The visible length is about 6–8% smaller than the stated length, while the apparent backing is roughly 3 mm thicker than stated. Possible contributors include perspective, a different visible plane, irregular fibres and the relationship between a color boundary and the physical layer interface. The current evidence does not isolate their contributions. A common scale correction cannot simultaneously reconcile the layer dimensions. No dimensions were forced to agree.

Absolute layer thicknesses and strains should therefore remain provisional. Their time-dependent visible-boundary changes are useful observations but do not independently identify each layer's constitutive response.

## Measurement accuracy and registration

Card-only baseline height standard deviations are 0.060, 0.036 and 0.036 mm for 500, 750 and 1000 ml. Sampled occupancy-threshold sensitivity changes total height by at most about 0.224 mm; yellow thickness by at most about 0.318 mm. These numbers support sub-millimetre image repeatability, not corresponding absolute accuracy.

Use approximately **0.3 mm practical resolution plus a separate assumed 10% geometric sensitivity allowance** when assessing compression. At 3, 7.7 and 11 mm this gives illustrative allowances of about 0.6, 1.1 and 1.4 mm. These are engineering sensitivity allowances, not statistical confidence intervals or guaranteed error bounds. The layer-dimension discrepancy can exceed them.

Median registration inlier RMS is 0.68–0.89 original pixels, with no frames rejected by the current registration criteria. A known synthetic image warp is recovered within 0.49 original pixels at the tested positions. Real registration features concentrate on the ruler, however. The transform cannot independently separate camera motion from ruler motion, parallax or perspective. Its scale varies by roughly 1.9–3.0 percentage points over each clip. This especially limits small lateral-strain claims.

## Loads and selected compression measurements

The baseline is the sponge with card already present. The following incremental loads use water mass plus the assumed 50–100 g tare, with nominal tare 75 g and g = 9.81 m/s². The same bottle makes tare uncertainty correlated across experiments.

| Video | Nominal force [range], N | Nominal pressure [range], kPa | Cycle 1 late-hold compression, mm | Cycle 2 late-hold compression, mm |
|---|---:|---:|---:|---:|
| 500 ml | 5.641 [5.396–5.886] | 1.545 [1.478–1.613] | 3.01 | 2.58 |
| 750 ml | 8.093 [7.848–8.339] | 2.217 [2.150–2.285] | 7.66 | 6.80 |
| 1000 ml | 10.546 [10.301–10.791] | 2.889 [2.822–2.956] | 10.99 | 10.97 |

Pressure uses 0.00365 m². Full-footprint contact and uniform pressure are idealizations; card overhang is excluded. These forces are assumptions, not force measurements. Card mass is not added again.

Source: `outputs/force_pressure_table.csv` and `outputs/cycle_summary.csv`. Selected hold windows are respectively 11.3–12.0 and 16.5–18.0 s; 13.2–14.2 and 25.0–27.5 s; 12.0–14.0 and 27.0–30.0 s. Nominal force is conditional on full support and absence of hand force. Neither is independently measured. Earlier loaded motion, placement, lifting and separation brackets retain unknown force. They should not automatically be interpreted as creep under constant load.

Loading levels are clearly distinct relative to the extraction resolution. Their displacement increments are not proportional to the assumed force increments. This could reflect nonlinearity, loading history or setup/input errors; it does not establish any particular constitutive law.

## Card movement and marker confidence

Card translation, apparent rotation and line-fit residuals are recorded separately. Whole-object compression is obtained from top-to-bottom thickness, so bottom motion is not automatically counted as compression. The left-tip horizontal trace is a partial edge measurement, not full 3D platen pose.

Late-hold rotation relative to baseline changes from −1.27° to +0.16° between 500 ml cycles, +0.45° to −1.09° at 750 ml, and −1.03° to +0.80° at 1000 ml. Tilt is consequential. The late-hold 90th-percentile deviation from the fitted card line is about 0.14–0.16 mm at the lower loads and 0.35 mm at 1000 ml. Residuals include occlusion and detection error; they suggest inspecting the rigid-platen approximation but do not prove bending. Apparent angles are image-plane angles.

Detected-marker coverage averages 88–89%, but coverage is not tracking accuracy. Marker 8 near the interface is detected in only 0.4%, 1.1% and 45.5% of frames respectively. The middle interior marker is detected throughout, but fragmented edge ink can shift centroids while retaining a high contrast score. Scores are heuristic, not calibrated probabilities. Missing measurements remain NaN.

Middle-row pair width changes during late holds are +0.22/+1.54 mm, +1.08/+0.08 mm and +0.93/−0.33 mm across the two repetitions. Differences and sign changes, together with other row disagreement, prevent a reliable common lateral-expansion law. Retain these tracks as exploratory diagnostics. Do not fit Poisson ratio or a depthwise expansion law from them.

## Free recovery and repeatability

Source: `outputs/cycle_summary.csv`, `outputs/free_recovery.png`, per-video phase tables and sequential separation sheets. Availability runs from the latest separation bound until the next possible contact or final timestamp.

| Video/cycle | Separation bracket, s | Free window, s | Frames in window | Further recovered height*, mm |
|---|---:|---:|---:|---:|
| 500/1 | 13.098–13.214 | 1.286 | 77 | 0.153 |
| 500/2 | 18.730–18.813 | 1.816 | 109 | 0.114 |
| 750/1 | 16.280–16.380 | 2.120 | 128 | 0.272 |
| 750/2 | 29.328–29.444 | 1.950 | 117 | 0.216 |
| 1000/1 | 17.163–17.313 | 3.687 | 222 | 0.368 |
| 1000/2 | 31.744–31.877 | 2.416 | 139 | 0.259 |

*Difference between the median residual compression in the first 0.15 s after the latest separation bound and the last 0.3 s of the window. This is a descriptive measurement, not an exponential fit.

Most recovery occurs while the bottle is being lifted. Remaining free-recovery amplitudes are comparable to the practical measurement allowance, even though many frames exist. The 1000 ml first cycle has the most promising tail, but its final equilibrium is unmeasured and drift/calibration effects are unresolved. A unique effective recovery timescale is not established.

Cycle-2 late-hold compression differs from cycle 1 by −0.43 mm (500 ml), −0.86 mm (750 ml), and −0.01 mm (1000 ml). Similar gross responses are evident, but these are different hold durations and platen orientations. Before cycle 2, residual compression is approximately 0.22, 0.72 and 0.17 mm respectively. Do not silently reset internal material memory or declare identical repeated initial conditions. Agreement of 1000 ml late values does not establish trajectory repeatability or model validation.

## Readiness and prioritized recommendations

1. **Vertical compression:** useful for global response and separating loads; practical image resolution around 0.3 mm, with larger unresolved scale/plane systematics. Absolute layer strains remain uncertain.
2. **Lateral expansion:** not reliable enough for parameter identification. Preserve exploratory tracks and their flags.
3. **Card movement:** visible translation and rotation can be distinguished in image space; complete contact geometry, out-of-plane pose and bending remain uncertain.
4. **Free recovery:** 1.29–3.69 s is available per cycle, but only 0.11–0.37 mm further recovery is measured after conservative separation.
5. **Loading levels:** clearly distinct in both assumed force and observed compression.
6. **Repetitions:** broadly consistent qualitatively, with measurable differences and incomplete recovery between cycles. Their histories are not interchangeable.
7. **Reduced-order model readiness:** sufficient to select axial effective compression as the first representation and to assess a static load-response baseline after approval. Insufficient for a confident joint Kelvin–Voigt stiffness/damping fit or choosing SLS complexity. Any later fit must respect force masks, retained baseline history and measurement uncertainty.
8. **Additional measurements with material value:** verify layer dimensions and place a calibration target in the visible face plane; obtain a cleaner, independently characterized unloading input and a longer card-only recovery; weigh the filled bottle if available. Input timing/force and geometric calibration matter more than adding indentation. Preserve platen geometry if collecting another trial so comparisons remain meaningful.

The proposed split remains unchanged: first 500/1000 ml cycles for initial fitting, second cycles for repeatability, both 750 ml cycles held out for intermediate-load evaluation. No physical fitting or simulation was performed during this milestone.
