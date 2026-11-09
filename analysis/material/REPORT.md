# Stage 1: constitutive kernel verification

## Decision and scope

**The one-term hyperfoam energy/stress kernel is verified for the tested states and suitable for a limited next FEM development stage. Its sponge parameters are not uniquely identified.** Use one fitted scale at a declared fixed shape/compressibility scenario; retain alternative scenarios. Do not use the two-point exact fit as a unique material calibration.

Only the material module, unit tests/verification driver and this report were added, with generated verification CSVs/plots. No geometry, element assembly, contact, damping or indentation was implemented. Prior measurements are unchanged, checked by hashes in `verification/summary.json`.

The requested `analysis/architecture/REPORT.md` does not exist. The architecture review was delivered in the conversation. Its proposed one-term energy is the starting formulation below; existing extraction and model-selection files provide the experimental evidence.

## Reference, convention and derivation

The convention follows the [Abaqus 2026 hyperfoam strain-energy definition](https://docs.software.vt.edu/abaqusv2026/English/SIMACAEMATRefMap/simamat-c-hyperfoam.htm), one term, no thermal expansion. Principal stretches are **total mechanical stretches, not isochoric stretches**. The reference energy is zero at the identity. The parameter mu is the initial shear modulus, with initial bulk modulus K = 2 mu (1/3 + beta), and nu = beta/(1+2 beta). These describe the selected model, not independently measured properties of the sponge.

For a deformation x(X),

\[
F=\frac{\partial x}{\partial X},\quad J=\det F>0,\quad
F=U\operatorname{diag}(\lambda_1,\lambda_2,\lambda_3)V^T.
\]

The singular values lambda_i are positive principal stretches. With no thermal strain,

\[
W(F)=\frac{2\mu}{\alpha^2}\left[\sum_{i=1}^3\lambda_i^\alpha-3+
\frac{J^{-\alpha\beta}-1}{\beta}\right].
\]

Units: F, J, alpha, beta and stretches are dimensionless; mu, W, P and Cauchy stress have units Pa, with W equivalently J/m³ of reference volume. The kernel accepts mu > 0, alpha != 0, beta >= 0. This deliberately restricts compressibility to 0 <= nu < 0.5 rather than implementing every possible hyperfoam parameter regime.

For beta = 0 the volumetric expression has the exact limit −alpha log J. Define B = J^(−alpha beta), with B = 1 when beta = 0. Since dJ/dlambda_i = J/lambda_i,

\[
p_i=\frac{\partial W}{\partial\lambda_i}
=\frac{2\mu}{\alpha\lambda_i}(\lambda_i^\alpha-B),
\qquad P=U\operatorname{diag}(p_i)V^T.
\]

This P is first Piola stress, conjugate to F per reference volume. Cauchy stress is

\[
\sigma=\frac{1}{J}PF^T.
\]

At F = I, W = 0 and P = 0. Left rotation leaves singular values unchanged, so W(RF) = W(F), P(RF) = RP(F), and sigma rotates as R sigma R^T. SVD is used only to evaluate spectral functions, without differentiating singular vectors. Repeated stretches therefore require no eigenvector-derivative division.

For stable near-reference evaluation let t_i = alpha log lambda_i, v = −alpha beta log J, and r(t) = exp(t)−1−t. Cancellation of the linear terms gives

\[
W=\frac{2\mu}{\alpha^2}\left[\sum_i r(t_i)+r(v)/\beta\right],
\]

where the second term is zero for beta = 0. The implementation uses a short series for r near zero, `expm1` elsewhere, and exp(v) expm1(t_i−v) for the stress difference. Nonpositive determinants, malformed/nonfinite/complex F and numerically unrepresentable responses raise ValueError. No clamping or silent element inversion repair is used. A mathematically admissible extreme state can still exceed floating-point range and is rejected.

## Traction-free uniaxial verification

Let axial stretch be lambda along z and equal lateral stretches be t. Solving Pxx = Pyy = 0 gives

\[
t^\alpha=J^{-\alpha\beta},\quad
t=\lambda^{-\nu},\quad J=\lambda^{1-2\nu}.
\]

Thus lateral deformation is allowed; t = 1 occurs only in the explicit beta = 0 scenario. Unit tests independently solve the lateral traction equation numerically and compare against this expression.

\[
P_{zz}=\frac{2\mu}{\alpha}\left(\lambda^{\alpha-1}-\lambda^{-1-\alpha\nu}\right),
\]
\[
\frac{dP_{zz}}{d\lambda}=\frac{2\mu}{\alpha}
\left[(\alpha-1)\lambda^{\alpha-2}+(1+\alpha\nu)\lambda^{-2-\alpha\nu}\right].
\]

Compression force is −A0 Pzz, x = H0(1−lambda), and positive axial force/compression tangent is (A0/H0) dPzz/dlambda. Compression stress is negative in the tensile-positive stress convention. Nominal reaction uses reference area; Cauchy stress accounts for the changing current area.

The ideal comparison assumes a **homogeneous 27 mm reference height** and reference area 0.00365 m². The measured card-only state is treated as an effective stress-free reference for this test. These are incremental approximations, not a reconstruction of natural geometry or card prestress. The test does not represent two different layers, platen friction, card tilt or the tabletop.

## Reproduction and verification results

From the repository root:

```powershell
python -B -m unittest discover -s analysis/material -p test_hyperfoam.py -v
python -B analysis/material/test_hyperfoam.py --report
```

The second command runs tests before generating diagnostics. It uses the existing Python 3.10.7, NumPy 2.2.6, SciPy, pandas and Matplotlib environment. No installation is needed.

All **7 test methods pass**, including many states within each method:

| Check | Result |
|---|---|
| Identity energy and stress | Exactly zero in tested parameter cases |
| Rigid rotations/objectivity | Pass; maximum relative energy discrepancy 1.50e−14 |
| Rotated stress covariance | Pass; maximum relative discrepancy 1.10e−14 |
| Positive J and invalid input rejection | Pass |
| Central energy differences versus analytical P | Maximum relative error 8.28e−10 at h = 1e−6 in report sweep |
| Zero lateral traction and independently solved lateral stretch | Pass |
| Uniaxial tangent versus numerical derivative | Relative error below 1e−7 in unit-test sweep |
| Small-strain shear/bulk convention and beta→0 continuity | Pass |
| Energy positivity, scale proportionality, symmetric Cauchy stress | Pass |

`gradient_checks.csv` contains 60 valid states at four step sizes, including shear, rotations and repeated stretches. Separate unit tests cover 100 energy-gradient cases at h = 1e−6, plus near-reference and invalid states. Relative errors use max(norm(P),1 Pa) in the denominator; they are not ill-defined at zero stress. Pure rotations are tested separately.

The generated compression curves cover axial stretch 0.45–1 (up to 55% ideal total-height compression), with all fitted compressibility scenarios having positive axial tangent. Minimum sampled tangent is **0.510 N/mm**. Unit tests additionally check traction-free states through lambda = 1.1 in tension. Positive uniaxial tangent does not establish strong ellipticity or stability under every 3D loading mode. No material Hessian or global FEM robustness claim is made.

## Experimental comparison and parameter strategy

Fitting uses only cycle 1 at 500 and 1000 ml. Observations are recomputed from the existing measurement CSV hold windows and recorded with frame provenance in `verification/observations.csv`. Repeats and both 750 ml cycles are evaluated only after fitting.

At each fixed alpha and beta, the scale is found by minimizing sum[((mu g_i − F_i)/F_i)²], where g_i is the ideal compression force per unit mu at measured stretch. Alpha is searched within 0.2–60 for the two-parameter diagnostic. This is a **relative force-error objective**, different from the previous empirical displacement-error objective. No likelihood interpretation is attached to it.

| Assumed nu | beta | Two-parameter mu, Pa | alpha | Relative force loss |
|---|---:|---:|---:|---:|
| 0.00 | 0 | 11,689.7 | 13.633 | approximately zero |
| 0.10 | 0.125 | 6,214.3 | 10.909 | 0.111 |
| 0.25 | 0.5 | 2,843.0 | 5.409 | 0.298 |

The zero-nu fit exactly interpolates two training observations with two parameters. Its intermediate-load prediction is **6.581 mm**, compared with 7.662 and 6.798 mm observed: errors −1.081 and −0.217 mm. The first error slightly exceeds the previous measurement-only allowance of 1.066 mm. This is not a fully validated material calibration.

A conditional shape profile at beta = 0 admits alpha approximately **8.65–23.61** within the engineering displacement allowances after refitting scale. The tested nonzero-nu scenarios do not achieve both nominal training allowances in that profile. This does not independently measure nu or rule out those values for the actual layered/contact system.

Given this ambiguity, **reduce the fitted parameter count to one scale mu**, with alpha and beta specified as scenario assumptions. For illustration, at beta = 0:

| Fixed assumed alpha | Fitted mu, Pa | Training x errors, mm | Predicted 750 ml x, mm |
|---:|---:|---:|---:|
| 2 | 3,190.4 | See predictions.csv; poor training agreement | See predictions.csv |
| 10 | 9,167.2 | +0.367, −0.956 | 6.266 |
| 20 | 16,022.8 | −0.387, +1.040 | 7.518 |

Both alpha 10 and 20 fit the training displacements within their engineering allowances but predict different intermediate responses. Alpha 20 agrees better with the already inspected intermediate data; selecting it for that reason would spend the validation set on model selection. Neither shape is established as a measured property. Alpha 2 is tested within the same hyperfoam formula, not silently substituted as a different constitutive kernel.

For initial FEM verification, alpha 10, beta 0 with one fitted scale is a declared test scenario; alpha 20 is a necessary sensitivity companion, not another fitted parameter. Do not promote either to a uniquely calibrated two-layer sponge material. A fresh test and improved geometric/contact characterization remain needed before doing so.

## Sensitivity and limitations

The beta/nu scenarios produce markedly different lateral stretches and volume ratios. Around 11 mm compression, refitted scenarios predict lateral stretches about **1.000, 1.054 and 1.139**, with J about **0.594, 0.659 and 0.771**. These are predictions of assumptions, not measurements.

`parameter_sensitivity.csv` combines shared tare 50/75/100 g, common/differential ±10% endpoint scales and ±0.3 mm endpoint shifts. At beta = 0 the two-parameter diagnostic spans mu approximately **7.49–21.37 kPa**, alpha **7.98–26.71**, and predicted intermediate compression **5.18–8.19 mm**. These are deterministic sensitivity corners, not confidence intervals. They perturb training inputs; they must not be treated as joint probabilistic bounds for held-out observations with correlated calibration errors.

The scale is called mu because that is the model convention. Its fitted numerical value here is an **effective coefficient conditional on homogeneous geometry, compressibility, reference state and traction-free boundaries**. It is not an independently measured shear modulus of either layer. The same applies to model-implied Young's and bulk moduli. No damping, density or layer-specific property was fitted.

## Deliverables and next-stage gate

- `hyperfoam.py`: energy, analytical first Piola stress, Cauchy stress and analytic traction-free response.
- `test_hyperfoam.py`: mathematical tests and reproducible material-point comparison driver.
- `verification/`: gradient/objectivity tables, compression curves, fits, residuals, sensitivity profiles, provenance and two plots.

The formulation is mathematically implementable and its first derivatives are verified. Proceeding to a small FEM verification problem is reasonable, subject to separate element-gradient, contact, reaction-balance and mesh-convergence checks. It is not yet reasonable to claim a validated full-sponge response or arbitrary-contact prediction. The material-point test is spatially homogeneous and is not a substitute for the next FEM stage.
