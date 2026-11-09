# Review of the equilibrium model

## Revised recommendation

Use **local monotone piecewise-linear force-to-compression interpolation** for the first limited-range 3D demonstration. Treat it as an empirical equilibrium response of the current assembly. My previous quadratic recommendation was premature because it omitted this important baseline. Fixing the exponent at 2 was an empirical simplification of a two-point power fit, not a mechanics-derived result.

This recommendation does not resolve dynamic recovery. No existing candidate has an identified recovery timescale. A first quasi-static demonstration can predict compression at a new independently specified load; it cannot yet claim validated transient recovery or fully satisfy a dynamic recovery objective.

No extraction, measurement changes, mesh or simulation were performed. `analysis/model_review.py` reproduces this review. `provenance.json` verifies preservation of all prior measurement and model-selection CSV inputs. Official predictions retain the original first 500/1000 ml cycles as endpoints. Neither 750 ml cycle nor either repeat cycle is added to the official fit.

## 1. What the quadratic actually assumes

For x = qF², q = 0.09752689 mm/N² and F ≥ 0,

\[
F(x)=\sqrt{x/q},\qquad
k_t=\frac{dF}{dx}=\frac{1}{2\sqrt{qx}}=\frac{1}{2qF}.
\]

At the nominal 500, 750 and 1000 ml forces, the implied tangent stiffnesses are **0.909, 0.633 and 0.486 N/mm**, respectively. These are model-derived values, not independently measured tangent stiffnesses. The model's secant stiffness F/x is twice its tangent stiffness.

Stiffness decreases as compression increases. This is positive-stiffness softening, not negative stiffness. The restoring force still increases monotonically, and the stored energy U = 2x^(3/2)/(3√q) is convex for x > 0. Thus the response is mechanically admissible over a finite compression interval. Its decreasing stiffness is qualitatively consistent with the measured decrease in effective secant stiffness between fitting loads. That observation does not establish the particular square-root force law or its derivative: two endpoint measurements do not measure local tangent stiffness.

Possible microstructural or contact explanations cannot be distinguished from these recordings. No assumption that all foams obey this law is warranted. In particular, the model has infinite tangent stiffness as x approaches zero and no high-compression densification limit. The card-only reference is also preloaded, so its origin is not a natural force-free material state. Neither limiting behavior is established experimentally.

The fitted two-point power exponent was 2.068, and rounding it to 2 reduced the fitted coefficient count. That was a curve-family and simplicity decision. Calling it a physical law would overstate the evidence. Its one fitted coefficient also understates the model-selection freedom already spent choosing the exponent family.

## 2. Local interpolation baseline

Let (F1,x1) = (5.64075 N, 3.012083 mm), and (F2,x2) = (10.54575 N, 10.987214 mm). Within this force interval,

\[
\hat x(F)=x_1+\frac{F-F_1}{F_2-F_1}(x_2-x_1).
\]

The nominal 750 ml force is exactly midway between the endpoints because the same bottle tare is added to all three water masses. Therefore

\[
\hat x_{750}=\tfrac12(x_1+x_2)=\mathbf{6.999649\ mm}.
\]

The local compliance is 1.625918 mm/N, corresponding to a local inverse slope of approximately **0.6150 N/mm**. This is an endpoint chord slope, not an identified intrinsic modulus. The affine segment must not be extrapolated to zero force: doing so would predict negative compression. A global linear elastic law x = F/k and this local affine interpolation are different models.

Both endpoints are reproduced exactly by construction. This zero training error supplies no residual degrees of freedom and is not evidence of perfect mechanics. The method assumes only a monotone straight connection between the two sampled loaded states; curvature within that interval remains unresolved.

## 3. Comparison using every cycle

Source observations are read from `analysis/model_selection/observations.csv` and cross-checked against `analysis/outputs/cycle_summary.csv`. All residuals below are prediction minus measurement, in mm. Linear and quadratic coefficients are retained from the previous weighted fitting protocol; interpolation uses the original endpoints.

| Load/cycle | Measured | Linear residual | Quadratic residual | Local interpolation residual | Fitted-power residual |
|---|---:|---:|---:|---:|---:|
| 500/1, fitting | 3.012 | +1.124 | +0.091 | 0.000 | 0.000 |
| 500/2, repeat | 2.585 | +1.551 | +0.518 | +0.427 | +0.427 |
| 750/1, held out | 7.662 | −1.728 | −1.274 | −0.663 | −1.307 |
| 750/2, held out | 6.798 | −0.863 | −0.410 | +0.202 | −0.443 |
| 1000/1, fitting | 10.987 | −3.254 | −0.141 | 0.000 | 0.000 |
| 1000/2, repeat | 10.974 | −3.241 | −0.128 | +0.013 | +0.013 |

| Model | Training RMSE | Held-out RMSE | Repeat evaluation RMSE |
|---|---:|---:|---:|
| A: global linear elasticity | 2.435 | 1.366 | 2.541 |
| B: fixed quadratic | 0.119 | 0.947 | 0.378 |
| C: local interpolation | 0.000 | **0.490** | 0.302 |
| D: fitted power exponent | 0.000 | 0.976 | 0.302 |

Interpolation errors at 750 ml, −0.663 and +0.202 mm, are within the respective engineering allowances of 1.066 and 0.980 mm. Quadratic and fitted-power predictions exceed the first cycle's allowance. These allowances are sensitivity estimates, not statistical confidence intervals. This supports interpolation for the present interval, without proving a unique constitutive form.

The fitted power model adds no compelling predictive advantage. A monotone cubic would introduce unsupported curvature or an arbitrary smoothing rule. No additional fitted parameters are justified.

Because model choice has now been revised after examining the 750 ml results, those cycles remain excluded from parameter fitting but are no longer a pristine test set for this revised selection decision. A fresh prospective interaction is needed for a strong independent validation claim.

## 4. Repeatability

| Load | Mean compression, mm | Cycle 2 − cycle 1, mm | Half-range, mm | Sample SD, mm | Sample CV |
|---|---:|---:|---:|---:|---:|
| 500 ml | 2.798 | −0.427 | 0.214 | 0.302 | 10.80% |
| 750 ml | 7.230 | −0.865 | 0.432 | 0.611 | 8.46% |
| 1000 ml | 10.981 | −0.013 | 0.0065 | 0.0093 | 0.084% |

With only two cycles, sample SD = |x2−x1|/√2. These are descriptive pair statistics, not reliable population repeatability estimates. The very small 1000 ml difference is below practical image resolution; it does not establish 0.009 mm accuracy. Means are descriptive and are not substituted into the fitting dataset. Averaging the intermediate cycles would hide their 0.865 mm spread: interpolation lies 0.231 mm below their mean, while quadratic lies 0.842 mm below it.

Several causes remain plausible, with no causal attribution from two repetitions:

- **Load placement/contact:** changing footprint or load eccentricity can change the effective response. Depthwise centering is unobserved.
- **Plate tilt:** late-hold relative angles change from −1.27° to +0.16°, +0.45° to −1.09°, and −1.03° to +0.80° across the three load pairs. This can change local deformation; it is not automatically human error.
- **History/preconditioning:** previous compression and different dwell times can alter response. Preconditioning is a hypothesis, not established by the direction of two observations.
- **Initial state:** pre-cycle-2 residual compression is about 0.22, 0.72 and 0.17 mm. The original card-only reference is retained; no reset is applied. Subtracting these offsets would not establish comparable internal states or eliminate viscoelastic memory.
- **Measurement/setup uncertainty:** registration, plane mismatch and boundary detection can shift apparent compression. The practical 0.3 mm resolution is smaller than the 750 ml pair difference, but shared/systematic effects prevent a significance claim from that fact alone.

## 5. Sensitivity and robustness

**Tare.** Varying the same bottle tare from 50 to 100 g shifts all forces equally. The interpolation fraction (F750−F500)/(F1000−F500) remains exactly 1/2, so the 6.999649 mm prediction and chord slope are unchanged. The force-coordinate location of the segment changes; an independently weighed new object's query force must still be expressed consistently. Quadratic's prediction varies only 6.377–6.394 mm. This cannot explain its first-cycle discrepancy or recover an advantage over interpolation.

**Endpoint localization.** Independently shifting each fitting compression by ±0.3 mm gives interpolation predictions 6.700–7.300 mm; quadratic gives 6.067–6.698 mm. These are deterministic scenario ranges, not confidence intervals. Interpolation propagates endpoint errors with weights 1/2 each, making its uncertainty easy to explain.

**Correlated calibration.** A common scale factor s changes all measured and predicted displacements together. Interpolation prediction and errors scale by s, its chord stiffness scales by 1/s, and q scales by s. It cannot be applied only to training measurements to erase evaluation error. At shared factors 0.9, 1 and 1.1, interpolation held-out RMSE is 0.441–0.539 mm versus quadratic 0.849–1.044 mm; its advantage survives this test.

Independent factors 0.9, 1 and 1.1 for the low, high and intermediate videos give 27 differential-scale scenarios. Interpolation outperforms quadratic in 20 of them, but not all. Across this stress test, interpolation RMSE ranges 0.393–1.721 mm and quadratic 0.393–2.252 mm. Counts are not probabilities. Differential calibration can change the ranking, so no statistically decisive selection is claimed.

**Individual repeated endpoints.** As a diagnostic only, substituting the four possible 500/1000 ml endpoint-cycle pairs gives nominal-tare interpolation predictions 6.779–7.000 mm and quadratic predictions 6.076–6.388 mm. Using cycle 2 at both endpoints gives 6.779 mm for interpolation, close to the separately observed 750 ml cycle-2 value 6.798 mm. That is suggestive of history/setup effects but is not a new official fit or independent validation. Original fitting endpoints remain fixed in the reported residual table. The quadratic's advantage over global linear elasticity remains; an advantage over local interpolation is not supported.

## 6. Recovery and the smallest useful additional trial

The six free windows last 1.29–3.69 s, but additional measured recovery is only 0.114–0.368 mm. Most motion occurs while transmitted force is unknown during lifting. The previous training-only recovery sensitivity profile admitted every tested timescale from 0.005 to 30 s within practical image resolution when uncertain amplitude and baseline offset were allowed. This indicates poor practical identifiability; it is not a timescale estimate or a proof of an upper/lower bound.

A minimal improvement is **one additional rapid-release trial of the same specimen, card and load**, with a fixed camera and calibration in the face plane. Hold until height is approximately stationary, lift the bottle vertically without pressing or dragging, film at the available high frame rate, and continue observing the card-only state for roughly 10–15 s or until stable. Timestamp release and the first definite separation; exclude the uncertain transition. This duration is a capture plan, not an assumed material time constant.

The trial is useful only if appreciable recovery remains at definite separation. Aim for post-separation amplitude several times the practical resolution, for example at least about 1.5 mm, across multiple frames. If a manual lift cannot achieve that, improve the release mechanism before collecting more equivalent slow lifts; a measured release input or a simple fast disengagement is more informative than adding indentation. A scalar recovery timescale needs a well-resolved free trajectory and baseline. Converting it into a damping coefficient additionally requires a stated dynamic law and corresponding stiffness scale. No damping value is inferred here.

## 7. Model boundary for the first 3D demonstration

Use an empirical monotone table with anchors **(0 N, 0 mm), (F1,x1), (F2,x2)** relative to the card-only baseline. The zero anchor is the reference convention. The lower segment is an explicit interpolation assumption, not validated low-load behavior. In the measured loaded interval use the formula above. Its two segment stiffnesses are approximately 1.873 and 0.615 N/mm; the kink is a table approximation, not an identified physical transition.

Restrict demonstrations to independently specified compressive loads within the sampled maximum and clearly mark the low-load segment as unvalidated. Do not extrapolate the upper segment or silently clamp a higher load and call it a prediction. A new mass m supplies F = mg under stationary full support, and the table produces a new compression without reading target marker positions. Keep both layers visible; layer allocation and zero modeled lateral expansion remain declared geometric approximations because the data do not identify them.

**Explicit physical relationships:** gravity for a supported known mass, the incremental baseline convention, unilateral compressive contact assumptions, and geometric consistency. If a later force solver uses the table's inverse as a restoring force, identify it as an empirical assembly closure; it can be integrated into a positive-stiffness elastic energy but that construction does not establish its material origin.

**Empirical approximations:** the force–compression table, unmeasured curvature, the below-first-load segment, layer deformation allocation and any lateral assumption. No time history, hysteresis or rate dependence follows from a static table. A visually smooth recovery animation would add an unsupported temporal rule. A dynamic extension must wait for informative recovery evidence or carry an explicitly uncalibrated status.

**Final choice: C, local monotone interpolation for equilibrium prediction.** It is transparent, inexpensive, uses the observed endpoints directly, avoids an unsupported global exponent and improves intermediate-load agreement. Treat its remaining limitations as model boundaries rather than inventing more fitted parameters. Stop at this review; no 3D implementation is included.
