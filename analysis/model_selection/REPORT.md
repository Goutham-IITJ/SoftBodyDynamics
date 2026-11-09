# Phase 3: mathematical model selection

## Recommendation

Use **Model C, a one-parameter nonlinear elastic compression backbone**, provisionally:

\[
x_{\rm eq}=qF_b^2,\qquad q=0.097527\ {\rm mm/N^2}
=9.7527\times10^{-5}\ {\rm m/N^2}.
\]

This is the simplest tested law that represents both fitting-load measurements within their practical allowances. It describes the effective sponge–platen–support assembly over the measured force range. It is not an intrinsic material law or a validated dynamic recovery model. Its held-out prediction has a remaining discrepancy, described below. Do not assign a fitted damping constant from these recordings.

This recommendation chooses the static backbone for later implementation. Reproducing finite-time recovery still requires an independently justified temporal law. An arbitrary animation speed must not be described as identified damping. No simulation was built in this phase.

## Data provenance and fitting protocol

Run `python analysis/model_selection.py` from the repository root. Dependencies are the existing NumPy, pandas, SciPy and Matplotlib installations. Outputs are confined to `analysis/model_selection/`; the Phase 2 report, measurements and recordings are unchanged. `provenance.json` records input hashes and verifies that the script did not modify its inputs.

The script reads the complete measurement CSVs, uses the reviewed hold windows in `analysis/config.json`, recomputes median compression, and checks agreement with `outputs/cycle_summary.csv`. `observations.csv` records the source video, time window, frame range and sample count. No video extraction is repeated. Prior quality reports, CSVs and all 19 generated Phase 2 plots were reviewed.

Each cycle contributes one aggregate observation. Adjacent frames are not treated as independent specimens. Parameters use only cycle 1 at 500 and 1000 ml. Both 750 ml cycles remain held out, and cycle 2 at the fitting loads remains a repeatability evaluation. These observations are candidate late-hold states, not independently established equilibrium points. Static model selection is conditional on their representing comparable near-equilibrium responses under full bottle support.

Incremental forces are 5.64075, 8.09325 and 10.54575 N, using water mass plus nominal 75 g tare and g = 9.81 m/s². The shared tare range 50–100 g gives ±0.24525 N. Card weight is already in the reference state and is not added. Nominal pressures on 0.00365 m² are 1.545, 2.217 and 2.889 kPa; uniform pressure is an idealization.

The fitting objective is weighted displacement error:

\[
J=\sum_{i\in\mathrm{fit}}\left[\frac{\hat x(F_i)-x_i}{u_i}\right]^2,
\qquad u_i=0.3+0.1|x_i|\quad\text{in mm}.
\]

The weights reflect the previous engineering allowances, not Gaussian standard deviations. There are no statistically valid confidence intervals derived from this loss. An inverse force residual is also reported, but it is a transformed model residual, not an independent force measurement.

## Candidate equations and numerical fits

**A. Linear elastic:**

\[
x=F_b/k,\qquad k>0.
\]

The weighted displacement fit gives **k = 1.363764 N/mm = 1363.764 N/m**. It predicts 4.136 mm and 7.733 mm at the fitting loads, against 3.012 mm and 10.987 mm observed. Its training residuals are +1.124 and −3.254 mm. The inverse force residuals are −1.533 and +4.438 N.

The two fitting-point secant stiffnesses are 1.873 and 0.960 N/mm. Their disagreement is substantial. Interval feasibility checks show that no single positive compliance fits both observations even with separate ±10% scale stress tests, ±0.3 mm localization allowances and a common tare anywhere at the tested range endpoints and midpoint. This is evidence against a single static linear assembly stiffness under these assumptions. It does not prove intrinsic material nonlinearity: input/support conditions and finite hold history remain possible confounds.

**B. Kelvin–Voigt:**

\[
F_b=kx+c\dot x,\qquad k>0,\ c\ge0.
\]

At equilibrium it reduces exactly to A, so its static conditional estimate is the same k, with the same static errors. The equilibrium measurements contain no information about c. A joint numerical k,c estimate is therefore not reported. This is an identifiability result, not a failed optimizer.

If the selected states are not equilibrium, KV cannot be ranked from these static aggregates alone. Its transient predictions would require the preceding force history and initial state; those are not sufficiently known here. Assuming a step force at first contact would introduce information that the videos do not establish.

**C. Positive monotone nonlinear compliance:**

\[
x=a(F_b/F_*)^n,\qquad F_*=8\ {\rm N},\quad a>0,\ n>0.
\]

Two training observations give **a = 6.204782 mm, n = 2.068225**. Exact interpolation is expected with two parameters and two observations; it provides no independent validation or residual degrees of freedom.

The exponent is close to 2. Fixing n = 2 reduces the model to the recommended one-parameter law, with a = 6.241721 mm at 8 N and q = a/64 = 0.097527 mm/N². The restriction is motivated by the fitting endpoint ratio; it was not optimized against the 750 ml data. Its endpoint residuals are only +0.091 and −0.141 mm, below image resolution. The extra exponent parameter is consequently not justified by the fitting precision.

For compression x ≥ 0 the equivalent restoring law is

\[
F_e(x)=\sqrt{x/q},\qquad
\frac{dF_e}{dx}=\frac{1}{2\sqrt{qx}}>0\quad(x>0).
\]

It is monotone and has a nonnegative convex stored energy
\(U(x)=2x^{3/2}/(3\sqrt q)\), with consistent SI units when used as energy. Incremental stiffness decreases with compression, representing effective softening in the observed interval. No negative-stiffness branch is introduced.

Near zero compression its tangent stiffness is singular, and at high load it predicts unbounded compression. This makes it a restricted operating-range surrogate, not a general foam law. Its inverse force-to-state evaluation is well behaved at zero, but using its restoring law in a later numerical solver would need separate treatment of the origin. Densification and bottoming-out are not identified. Do not extrapolate beyond approximately 5.4–10.8 N or the observed compression range. A new regularization parameter must not be presented as measured.

## Prediction results

Full displacement and force residuals are in `predictions.csv`; errors below mean prediction minus observation.

| Model | Training RMSE, mm | 750 ml RMSE, mm | Repeatability RMSE, mm |
|---|---:|---:|---:|
| A linear; B equilibrium limit | 2.435 | 1.366 | 2.541 |
| C, fitted exponent | 0.000* | 0.976 | 0.302 |
| C, exponent fixed at 2 | 0.119 | 0.947 | 0.378 |

*Interpolation of two fitting points, not evidence of perfect physical accuracy.

| Evaluation observation | Measured x, mm | Linear prediction/error, mm | Fixed-square prediction/error, mm |
|---|---:|---:|---:|
| 750 ml cycle 1 | 7.662 | 5.934 / −1.728 | 6.388 / −1.274 |
| 750 ml cycle 2 | 6.798 | 5.934 / −0.863 | 6.388 / −0.410 |
| 500 ml cycle 2 | 2.585 | 4.136 / +1.551 | 3.103 / +0.518 |
| 1000 ml cycle 2 | 10.974 | 7.733 / −3.241 | 10.846 / −0.128 |

For the fixed-square law, inverse force residuals on the two 750 ml cycles are **+0.771 and +0.256 N**; repeatability residuals are −0.493 and +0.062 N. These exceed tare uncertainty in some cases, but displacement and model uncertainty also contribute.

The held-out displacement allowances are 1.066 and 0.980 mm. Thus the nominal square-law prediction **fails the first 750 ml cycle's measurement-only allowance by about 0.208 mm**, and passes the second. Both repeatability observations pass their measurement-only allowances, although the 500 ml repeat is close to its 0.558 mm allowance. The fitted-exponent model likewise fails the first intermediate cycle. Neither nonlinear model has fully passed intermediate-load validation.

Repeated late-hold states differ by −0.427, −0.865 and −0.013 mm at 500, 750 and 1000 ml. Load ordering is monotone in both repetitions. Unequal hold durations, changed card tilt and pre-cycle residual deformation limit any claim of identical repeated conditions. These differences are retained, not corrected away by fitting offsets to the evaluation cycles.

## Uncertainty, sensitivity and confidence

`tare_sensitivity.csv` varies a shared tare from 50 to 100 g in 1-g increments, refitting only the training cycles each time. The square-law coefficient ranges approximately **0.09195–0.10353 mm/N²**. Yet its intermediate prediction changes only from **6.377 to 6.394 mm** because fitting and query forces move together. The fitted power exponent varies from 2.001 to 2.135 and its intermediate prediction from 6.336 to 6.376 mm. Tare uncertainty alone does not explain the first held-out discrepancy.

`calibration_sensitivity.csv` applies ±10% shared or differential training scale changes, ±0.3 mm endpoint shifts and tare endpoints/midpoint. Across these deterministic corners, square-law q ranges **0.07821–0.11888 mm/N²**, with 750 ml predictions **5.431–7.349 mm**. The flexible exponent ranges 1.509–2.700 under differential scale changes. These are scenario ranges, not confidence intervals. Large uncertainty in exponent is another reason to avoid retaining it as an independently established physical parameter.

The training-prediction envelope overlaps both intermediate measurement bands, but this is **not proof of validation**. In the shared-scale case, the same scale error also changes the held-out measured displacement: common scale cannot be varied only on training data to erase validation bias. Under a pure common scale s, q and all measured/predicted displacements scale by s, while relative residuals and fitted n are unchanged. Differential video calibration is more consequential and remains unresolved. The sensitivity CSV deliberately describes training-parameter perturbations; it does not assert joint probabilistic coverage of the evaluation observations.

No independent specimen repeats or calibrated error distribution are available. Hundreds of correlated video frames cannot substitute for them. A bootstrap over those frames would understate uncertainty. The fitted values are conditional effective assembly parameters, not Young's modulus, intrinsic viscosity, or separately identified yellow/green material constants.

## Damping identifiability

Force during placement and lifting is unknown; nominal weight is assigned only to the candidate hold windows. Most visible recovery occurs before complete bottle separation. The genuinely free windows contain only 0.114–0.368 mm further recovery, comparable to the 0.3 mm practical image resolution, with residual baseline offsets.

For KV at known zero incremental force, x(t) = A exp(−t/τ), τ = c/k. A constant measurement offset can produce y(t) = b + A exp(−t/τ). To test robustness, `recovery_profile.csv` profiles τ from 0.005 to 30 s using only the first 500/1000 ml recovery windows, fitting nonnegative amplitude and a bounded nuisance baseline offset separately per clip. The offset is a measurement sensitivity term, not a new constitutive state. Samples are weighted by elapsed time, avoiding a uniform-FPS assumption.

Every tested τ fits each training recovery within 0.3 mm time-weighted RMSE: the ranges are about 0.034–0.067 mm for 500 ml and 0.043–0.102 mm for 1000 ml. The practical criterion therefore supplies no useful timescale interval within this grid. This is not a claim that every positive τ is mathematically equivalent or that 30 s is an upper bound. It demonstrates lack of robust practical identifiability once realistic baseline uncertainty is allowed. An apparent minimum must not be converted into a precise c.

Zero-offset, exactly-known-force assumptions would make the inference more restrictive, but neither is established at sufficient precision. A fitted c across the hand-controlled transitions could simply absorb unloading speed, transient contact, card movement or camera drift. Keep it unspecified. The chosen nonlinear backbone also has no unique global conversion c = kτ because its tangent stiffness depends on state.

## Proposed layered 3D mapping

Use the nominal geometry 73 × 50 × 27 mm, with green layer height Hg = 7 mm and yellow layer Hy = 20 mm. Geometry dimensions are declared inputs, not recovered layer calibration. Let scalar x come from the model under an independently specified compressive force. Keep horizontal coordinates unchanged; this is an assumption of zero modeled lateral expansion, not a fitted Poisson ratio or an incompressibility constraint.

For a declared layer-allocation fraction β, let ΔHy = βx and ΔHg = (1−β)x. With the base at z = 0:

\[
z' = z(1-\Delta H_g/H_g),\quad 0\le z\le H_g,
\]
\[
z'=H_g-\Delta H_g+(z-H_g)(1-\Delta H_y/H_y),\quad H_g<z\le H_g+H_y.
\]

The interface stays continuous, the base fixed, and the upper face moves down by x. Separate colors preserve layer identity. A minimal geometric prior is β = 20/27, giving uniform axial strain. It is **not identified layer mechanics**, and the observed apparent layer changes suggest that it may be inadequate for layer-resolved agreement. Do not fit β or separate layer stiffness from the present inconsistent absolute dimensions. Reject states that collapse a layer; clipping must be labeled a domain guard, not a learned densification response.

This proposes mesh deformation only; no mesh or simulator is implemented. A fresh independently known bottle mass gives F = mg and a new x = qF² without reading target marker positions. For a prescribed time-dependent force, the static law gives an instantaneous quasi-static sequence and immediate return at zero force. It cannot claim to predict the observed delayed recovery. A future temporal extension requires a measured/controlled input and sufficient recovery signal before that claim is justified.

## Remaining limits and next decision

The card is treated as approximately rigid, but tilt and partial visibility are present. The baseline contains card preload; nonlinear incremental coefficients apply about that baseline and are not total force-free material properties. Uniform pressure, full footprint and hands-off support remain assumptions. Lateral measurements cannot identify lateral coupling. Single-view calibration, inconsistent layer thicknesses, finite hold duration and incomplete recovery between cycles remain material uncertainties.

Implement **the one-parameter nonlinear elastic law as the provisional equilibrium backbone**, because it captures the measured nonlinearity with one coefficient and offers no worse held-out performance than a fitted exponent. Retain its explicit first-cycle 750 ml validation shortfall and operating limits. Do not implement a fitted Kelvin–Voigt damping parameter from these data. The highest-value next evidence for a dynamic extension is a characterized force removal with a larger, resolved free-recovery trajectory, alongside calibration in the specimen-face plane.

Outputs include observation provenance, parameter tables, displacement/force residuals, grouped errors, shared-tare and calibration scenarios, linear feasibility checks, recovery profiles and four comparison plots. The original training/validation split is preserved throughout.
