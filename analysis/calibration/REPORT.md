# Stage 5: experimental calibration and FEM prediction

The primary one-scale FEM calibration is **mu = 6999.815 Pa, with assumed alpha = 10 and beta = 0**. It predicts 7.4884 mm compression at the intermediate bottle load. However, its 0.8002 mm calibration RMSE includes a low-load discrepancy larger than the previously stated engineering allowance. Its intermediate-load RMSE, 0.5036 mm, does not improve on empirical interpolation's 0.4899 mm. This is an observation-calibrated **effective specimen model with unresolved model discrepancy**, not an identified intrinsic material or a prospectively validated simulator.

All requested numerical checks pass. Experimental adequacy is a separate question: the primary shape does not reproduce both fitting loads within their nominal allowances. Stage 5 stops here; no final demonstration or video was generated.

## Inputs, reference state and separation

The source is the unchanged `analysis/outputs/cycle_summary.csv`, cross-checked against `analysis/model_selection/observations.csv`. First cycles at 500 and 1000 ml alone enter the official calibration. Second endpoint cycles assess repeated-load consistency. Both 750 ml cycles are **held out from this FEM fitting**, but have already been examined during earlier model selection; they are not untouched prospective validation.

Assume water density 1 g/ml, g = 9.81 m/s², and one shared bottle tare of 75 g:

| Water volume | Incremental supported mass | Force | Force at assumed tare 50–100 g |
|---|---:|---:|---:|
| 500 ml | 0.575 kg | 5.64075 N | 5.39550–5.88600 N |
| 750 ml | 0.825 kg | 8.09325 N | 7.84800–8.33850 N |
| 1000 ml | 1.075 kg | 10.54575 N | 10.30050–10.79100 N |

Bottle tare is not measured. Water volume is also treated as nominal; no unsupported volume precision distribution is assigned. The card is already present in the optical baseline and is assumed massless in the mechanics, so its weight is not added again. The forces apply only under stationary full support without additional hand force; placement/lifting trajectories are not fitting observations.

Stage 4 geometry and constraints are reused unchanged: 73 × 50 × **20 mm yellow foam**, bottom z = 7 mm, top z = 27 mm, and a rigid green backing of 7 mm. Contact area is 0.00365 m². All observed displacement is allocated to yellow deformation under this rigid-backing assumption. In particular, the supplied compression values are the **total top-to-bottom optical changes**, not the separately extracted yellow color-region changes. Apparent green color-region changes of roughly 1.1–1.4 mm and the earlier optical layer-thickness discrepancy remain unresolved. Reassigning them silently would change the experiment being fitted. The fit is conditional on this displacement allocation and the nominal geometry.

The card-only state is treated as an effective stress-free reference. Actual natural dimensions, card prestress and residual material history are not recovered from these data.

`outputs/protocol.json` declares the primary assumptions, equal-weight objective, split and numerical domain. `frozen_fits.json` records all three official scenario fits before the driver's evaluation step. Neither intermediate-load residuals nor repeated cycles select alpha or beta. The primary remains alpha = 10, beta = 0 throughout.

## Inverse FEM method and numerical domain

For each fixed alpha/beta scenario, SciPy's bounded scalar minimizer operates on log(mu) and minimizes

\[
L(\mu)=\sum_{i\in\{500/1,1000/1\}}
\left[d_{\rm FEM}(F_i;\mu,\alpha,\beta)-d_i\right]^2.
\]

Displacements are metres, forces newtons, mu pascals, and loss m². Equal weights avoid treating the previous engineering allowances as known independent Gaussian standard deviations. They also make the displacement-error criterion explicit. A different weighting is a different estimator, not a numerical correction.

Every objective prediction calls the Stage 3 **force-controlled global FEM solver through the Stage 4 sponge**. No material-point formula, fitted polynomial, empirical reaction table or interpolated equilibrium surrogate replaces it. For fixed alpha/beta and displacement, the kernel and assembled energy scale exactly with mu:

\[
U(x;\mu)=(\mu/\mu_r)U(x;\mu_r),\qquad
d_{\rm FEM}(F;\mu)=d_{\rm FEM}(F\mu_r/\mu;\mu_r),\quad\mu_r=2000\ {\rm Pa}.
\]

With homogeneous material, no body loads and the same eliminated constraints, the relaxed positions at prescribed d are independent of this positive scale. The code reuses cached reference-scale FEM equilibria, rescales dimensional energies/forces, and retains their actual nodal positions. This is exact mechanical scaling, not interpolation. Independent direct solves at the fitted mu verify the acceleration on both meshes.

The original maximum force-search compression is retained at **0.65 × 20 = 13 mm**. The observed maximum is 10.9872 mm, or 54.94% yellow compression. Even the largest endpoint engineering perturbation used here, 12.3859 mm, stays below 13 mm. The force at the cap is first solved by FEM to define an admissible lower mu bound; the common upper bound is 1e6 Pa. Optima lie inside their bounds. No failed fit is made successful by increasing the compression limit.

During the initial nonzero-beta sweep, the default 1e−8 N inner tolerance encountered a line-search stagnation at 1.03e−8 N. The calibration now explicitly requests **5e−8 N reference/direct inner tolerance**. This is a run setting; existing equations, solver defaults and previous outputs are unchanged. Scaled reference residuals scale with mu/2000; their recorded maximum is 1.0782e−7 N. Direct fitted-scale solves retain the explicit 5e−8 N tolerance. These errors are many orders smaller than experimental displacement uncertainty and are reported separately.

The previous Stage 1 illustrative coefficients are not reused: that exercise used homogeneous 27 mm height and a relative **force-error** objective. This stage uses the actual Stage 4 20 mm deformable layer and **displacement-error** fitting, so its mu and predictions need not match Stage 1.

## Calibration, intermediate-load evaluation and repeats

All residuals below are prediction minus observation, in mm. Full precision is retained in `predictions.csv`.

| Observation | Role | Measured | Primary FEM | Residual | Engineering allowance |
|---|---|---:|---:|---:|---:|
| 500 ml / 1 | Calibration | 3.012083 | 3.923162 | +0.911078 | 0.601208 |
| 1000 ml / 1 | Calibration | 10.987214 | 10.316013 | −0.671202 | 1.398721 |
| 750 ml / 1 | Intermediate evaluation | 7.662464 | 7.488439 | −0.174025 | 1.066246 |
| 750 ml / 2 | Intermediate evaluation | 6.797866 | 7.488439 | +0.690574 | 0.979787 |
| 500 ml / 2 | Repeated-load evaluation | 2.584746 | 3.923162 | +1.338415 | 0.558475 |
| 1000 ml / 2 | Repeated-load evaluation | 10.974121 | 10.316013 | −0.658109 | 1.397412 |

The primary model misses the nominal low-load allowance on both cycles. Both intermediate residuals are inside their allowances, but the two intermediate observations themselves differ by 0.8646 mm. The allowance is **0.3 mm practical optical resolution plus 10% of measured displacement**, an engineering sensitivity convention, not a statistical interval or a pass/fail material-validation standard.

The scale needed to reproduce each training endpoint individually is 8158.06 Pa at 500 ml and 6512.29 Pa at 1000 ml. Their disagreement demonstrates that changing one scale cannot reproduce both exactly for alpha = 10, beta = 0. The optimized compromise overpredicts low-load compression and underpredicts high-load compression. This systematic sign pattern is a constitutive/setup discrepancy, not optimizer failure.

| Model/scenario | Fixed alpha | Fixed beta | Fitted mu, Pa | Calibration RMSE, mm | 750 ml prediction, mm | 750 ml RMSE, mm | Endpoint-repeat RMSE, mm |
|---|---:|---:|---:|---:|---:|---:|---:|
| Primary FEM | 10 | 0 | 6999.815 | 0.800180 | 7.488439 | 0.503575 | 1.054624 |
| Shape sensitivity | 20 | 0 | 13361.887 | 0.223937 | 7.948242 | 0.838163 | 0.477914 |
| Lateral-coupling sensitivity | 10 | 0.125 | 4530.266 | 2.089972 | 7.260128 | 0.433336 | 2.298881 |
| Existing empirical interpolation | — | — | — | 0 by construction | 6.999649 | 0.489919 | 0.302315 |

Alpha = 20 reduces calibration residuals to +0.2105 and −0.2366 mm, both within nominal allowances. Beta = 0.125 (model-implied nu = 0.1) gives +1.9984 and −2.1777 mm training residuals. Its smaller intermediate RMSE does not rescue its poor endpoint fit and is not a reason to choose it. Neither scenario is promoted to a measured property. Only these individual assumption changes were tested; an alpha–beta interaction is not inferred.

At additional independently specified query forces, the primary fine-mesh model predicts **5.10350 mm at 6.5 N** and **9.26377 mm at 9.5 N**. These are fresh *computational queries*, not newly observed experiments or validated prospective interactions. Their solved node coordinates are exported. The FEM curves cover 0–11.5 N; predictions beyond measured endpoint forces are explicitly unvalidated extrapolations within the numerical domain.

## Sensitivity and identifiability

Twenty-three training-input refits produce 31 evaluation records. Official fits remain unchanged. Each refit still fits only mu at alpha = 10, beta = 0. No intermediate observation enters a sensitivity objective.

| Assumed perturbation | Effective mu range, kPa | 750 ml prediction range, mm |
|---|---:|---:|
| Shared bottle tare 50 and 100 g | 6.781–7.220 | 7.476–7.500 |
| Common displacement scale 0.9 and 1.1 | 6.507–7.596 | 6.556–8.315 |
| Independent endpoint scale corners ±10% | 6.507–7.596 | 6.556–8.315 |
| Independent endpoint localization shifts ±0.3 mm | 6.788–7.217 | 7.139–7.838 |
| Joint tare endpoints and ±(0.3 mm + 10%) endpoint allowances | 6.108–8.061 | 6.184–8.676 |
| Other individual endpoint-cycle pairs | 7.005–7.131 | 7.275–7.480 |

These finite deterministic ranges are not posterior distributions or confidence intervals, and untested intermediate/extreme combinations are not bounded by them. Common-scale scenarios apply the same factor to **evaluation measurements**, too. Differential endpoint corners are evaluated at separate 750-video scale factors 0.9, 1.0 and 1.1. Geometry remains the specified nominal geometry; this test perturbs optical displacement, not all specimen dimensions. Tare shifts all three forces together, never independently.

Changing tare over this interval barely changes the intermediate prediction; it cannot explain away the primary low-load mismatch. Optical systematic uncertainty has a much larger effect. Under common optical scale shifts, primary versus baseline RMSE ordering can change (FEM 0.392–0.598 mm versus baseline 0.441–0.539 mm). Differential scenarios broaden the errors further. The nominal 0.0137 mm RMSE difference between FEM and interpolation does not establish a decisive ranking.

The three diagnostic repeat-endpoint combinations use cycles (1,2), (2,1) and (2,2), without averaging or replacing the official first-cycle fit. Initial states differ: pre-cycle-2 residual compression is approximately 0.22, 0.72 and 0.17 mm in the three videos, with different dwell times and platen angles. Potential contributors include eccentric loading, plate tilt/contact changes, material history/preconditioning, optical uncertainty and initial-state differences. The recordings do not isolate a cause; these variations are not automatically human error. The reversible static model does not represent that history.

Two scalar training observations cannot uniquely determine three material parameters. A finite-difference two-by-three displacement sensitivity matrix has rank 2 with a local null direction; it is recorded in `local_identifiability.csv` and `summary.json`. Its perturbation coordinates are 1% mu, one unit alpha and 0.01 beta; the null vector depends on that scaling and is not a globally valid family of materials. Even fitting just mu and alpha exactly would consume both observations and leave no calibration residual degrees of freedom. Unknown tare, layer thickness, area, baseline and contact assumptions add further confounding. No intrinsic shear modulus, Poisson ratio or backing property is identified.

The alpha = 20 training result shows that constitutive shape can materially affect the discrepancy. It does not establish that shape as correct. Other plausible causes remain: nominal versus optical geometry, allocating the measured total compression to yellow, full-face/frictionless support, finite footprints, card tilt, uncertain supported force, and preconditioning. The marker data were previously found insufficient for lateral-parameter identification; they are not used to fit beta here.

## Numerical evidence

Both 1 × 1 × 1 and 2 × 2 × 2 structured-cell meshes are exercised (6 and 48 tetrahedra). Each scenario has direct fitted-scale force solves on both meshes at all three bottle forces and at 6.5/9.5 N. Each scenario is also independently refitted on the fine mesh.

| Check | Result |
|---|---:|
| Audited prediction/sensitivity states | 180 |
| Recorded accepted inner-history rows | 463 |
| Largest direct fitted-scale free residual | 4.9573e−8 N |
| Largest scaled free residual | 1.0782e−7 N |
| Largest applied-force/reaction mismatch | 5.5355e−8 N |
| Largest top/bottom resultant imbalance | 1.4418e−7 N |
| Minimum J in audited predictions and their recorded histories | 0.424095 |
| Minimum J including separate 13 mm reference-cap solves | 0.350000 |
| Largest direct versus scaled-coarse compression difference | 9.1550e−8 mm |
| Fine/coarse fitted mu relative difference, primary | 1.95e−12 |
| Fine/coarse fitted mu relative difference, beta sensitivity | 1.64e−5 |

All fitted mu values are positive. All audited states converge, retain positive element Jacobians and satisfy admissible compression and force balance. Every nominal curve and every sensitivity scenario is monotone at its evaluated forces. The cap forces are 14.599, 13.935 and 26.996 N for the primary, alpha and beta scenarios, respectively, above the evaluated 11.5 N maximum. The nonzero-beta scale optimum is relatively flat: its tiny mesh-dependent mu change leaves training RMSE unchanged to about 3e−9 mm. This is numerical optimizer sensitivity, not an experimentally meaningful property difference.

These are homogeneous affine consistency checks. Agreement of two meshes does not establish convergence or accuracy for nonuniform indentation, bending, buckling or changing contact. The green layer stays rigid, and its compliance/interlayer shear remain excluded. As documented in Stage 4, plane constraints can support laterally expanded nodes beyond finite card/backing visual footprints; no collision/contact capability was added.

All **31 unit-test methods pass**: 26 existing material/FEM/solver/sponge methods and 5 new calibration methods. New tests verify mass units/shared tare, exclusion of intermediate data, exact scale acceleration against direct laterally coupled FEM, recovery of a known synthetic scale from direct FEM observations, and rejection outside the unchanged compression domain. Existing verification drivers were not rerun or their outputs overwritten.

## Baseline, scope and recommendation

The existing empirical model retains anchors (0,0), (F500,d500/1) and (F1000,d1000/1). Its loaded-interval chord gives the midpoint 6.999649 mm; its below-first-load segment is an unvalidated approximation. The baseline curve stops at its highest observed load rather than extrapolating. Its zero training error is construction, not material-law validation.

The primary FEM predicts the intermediate observations to within the existing engineering allowances, but **does not demonstrate an accuracy improvement over interpolation**, nor adequate agreement with the nominal low-load calibration observation. FEM additionally supplies a 3D equilibrium field, stresses/energy from a constitutive energy, reactions, lateral response and geometric admissibility. Those are mechanical capabilities of the implemented model. Only global equilibrium compression is compared experimentally here; spatial stresses, lateral expansion, arbitrary contact and dynamic recovery are not experimentally validated.

Keep the current primary fit as a documented provisional reference, not a final calibrated material. The smallest existing constitutive-assumption change worth testing next is the already declared alpha = 20, beta = 0 scenario: the **training data alone** show its smaller residuals. Do not fit another parameter merely to interpolate two points. Before promoting either shape, weigh the bottle and verify layer dimensions/calibration in the specimen face plane, then obtain one controlled fresh low/intermediate-load trial with the same plate, centered loading and a defined initial state. Freeze the candidate shape before that comparison and refit only mu to the designated training data. This is more defensible than choosing beta/alpha from the already inspected 750 ml errors.

No damping or recovery time is fitted: the previous post-separation signal remains too small and release force too uncertain. No final mesh demonstration, general contact or video is created in this stage.

## Reproduction and artifacts

From the repository root with existing NumPy, SciPy and Matplotlib:

```powershell
python -B -m unittest discover -s analysis/calibration -p test_calibration.py -v
python -B analysis/calibration/run_calibration.py
```

`calibrate.py` implements the restricted endpoint reader, mass conversion, exact FEM scaling and one-scale SciPy fit. `run_calibration.py` freezes assumptions/fits, evaluates observations, runs sensitivities/direct mesh checks, and creates plots. `test_calibration.py` contains the five new tests. No dependency was installed.

`outputs/` includes `parameters.csv`, all-cycle `predictions.csv`, `metrics.csv`, solved `fem_curve.csv`, empirical baseline curve, force conversions, `sensitivity.csv`, single-endpoint diagnostic scales, objective traces, mesh/refit/domain checks, numerical and iteration audits, and direct solved-node CSVs. The comparison and two sensitivity plots were visually inspected. `protocol.json`, `frozen_fits.json` and `summary.json` preserve the run assumptions/results.

`preserved_sha256.json` verifies **337 pre-existing analysis/video files unchanged**, including prior measurements, reports, code, comparisons, verification artifacts and original videos (excluding Python caches and this new stage directory). No video extraction or original measurement edit was performed. The numerical core is unchanged. Stage 5 ends with calibration, sensitivity and quantitative comparison, awaiting review before the final demonstration.
