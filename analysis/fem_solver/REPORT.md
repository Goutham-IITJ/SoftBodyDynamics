# Stage 3: global nonlinear equilibrium solver

## Outcome

**The solver passes homogeneous synthetic-block verification.** Six new solver test methods pass, together with all seven Stage 1 material and seven Stage 2 FEM regression methods. The verification driver solves 54 prescribed-displacement/force-controlled cases across two resolutions and three material scenarios.

The solver reuses the Stage 1 material kernel and Stage 2 `TetAssembly`. No existing constitutive or tetrahedral energy/stress equations were replaced or refitted. Previous material/FEM files and verification outputs, plus extracted CSVs, are protected by hashes in `verification/summary.json`. Only this stage-specific directory was created.

No experimental fitting, actual sponge mesh, layers, damping, temporal recovery, general collision detection or localized indentation is included. All loads and materials below are synthetic verification inputs.

## Geometry and constrained DOFs

`structured_block()` constructs configurable positive dimensions and integer subdivisions, with six consistently connected tetrahedra per hexahedral cell. Each reference tetrahedron is positively ordered when generated. Duplicate positions, invalid subdivisions, nonpositive element determinants and incorrect total volume are rejected. This construction does not repair imported inverted meshes.

Verification uses dimensions 0.030 × 0.020 × 0.010 m and reference volume 6e−6 m³:

| Resolution | Nodes | Tetrahedra | Constrained DOFs | Free DOFs |
|---|---:|---:|---:|---:|
| 1 × 1 × 1 cells | 8 | 6 | 11 | 13 |
| 2 × 2 × 2 cells | 27 | 48 | 21 | 60 |

The prescribed platen compression d is positive downward. Constraints are eliminated exactly:

- Every top node has z = H−d; its x and y remain free.
- Every bottom node has z = 0; its x and y remain free except the pins below.
- Bottom origin node: x = 0 and y = 0, removing horizontal translations.
- Bottom corner (Lx,0,0): y = 0, removing yaw without constraining its x expansion.

The horizontal pins are the three DOFs needed after the two horizontal planes remove vertical rigid motion and tilting rotations. They admit arbitrary uniform lateral stretches about the origin. No bottom node is fully welded in all directions beyond the single translation anchor, and the entire bottom is not laterally fixed.

**Contact scope:** z = 0 is a bilateral full-face-support assumption, stronger than unilateral nonpenetration. It is appropriate for this synthetic compression verification only while compressive support reactions are admissible. The solver rejects a converged state requiring a significantly tensile table reaction. It does not implement opening contact, separation or a general active-set contact method. Likewise all top nodes remain attached to the prescribed horizontal plane in the normal direction. Horizontal freedom represents frictionless interfaces under the assumed full-face normal contact.

`constraints.csv` lists every constrained node/component and its displacement rule for each mesh. No penalty springs are used for these constraints.

## Global potential and gradient

With current nodal coordinates x and reference coordinates X,

\[
U(x)=\sum_e V_{0e}W(F_e),\qquad
\Pi(x)=U(x)-\sum_a f_a^{\rm dead}\cdot(x_a-X_a).
\]

Reference volume, not current volume, is used. Stage 2 supplies g = dU/dx and internal forces −g. The residual in energy-gradient convention is r = g−f_dead. Only r on free DOFs must vanish; constrained entries are reactions.

The optimizer variables are dimensionless free displacements q = (x−X)/H. It minimizes Pi/E0 with E0 = mu V_block. The returned gradient is exactly

\[
\frac{\partial(\Pi/E_0)}{\partial q}
=\frac{H}{E_0}\,r_{\rm free}.
\]

This scaling improves numerical conditioning without altering the physical energy, stiffness or equilibrium. The objective supports nodal dead-load work, independently verified by central differences with nonzero loads. The flat-platen verification itself uses no separate nodal loads in the inner solve.

For prescribed d, the platen work is constant with respect to free DOFs and is omitted from the inner objective. Define the relaxed energy Ueq(d). The compressive platen reaction is

\[
R(d)=\frac{dU_{\rm eq}}{dd}=-\sum_{a\in\rm top}g_{a,z}.
\]

The table resultant is +sum_bottom g_a,z. The force-controlled outer problem solves R(d)−Ftarget = 0; its total potential is Ueq(d)−Ftarget d. Thus applied downward force and the positive scalar compressive reaction are not confused with signed top nodal forces. In the presence of additional nodal dead loads, constraint reactions use g−f_dead.

The implementation has separate `energy` and `potential` outputs; the force-controlled potential includes the platen's dead-load work. No first-Piola stress is mistaken for Cauchy stress when calculating reaction: reactions come directly from the verified nodal gradients.

## Numerical method and feasibility

The inner method is a safeguarded inverse-BFGS energy minimizer using SciPy 1.14.1's `BFGS` update object and an explicit Armijo backtracking search. It does not call a black-box optimizer and infer success from its status flag. BFGS curvature failures skip an update; a non-descent direction resets the approximation. These operations change the search direction only, not the physical potential.

An unconstrained optimizer could try an inverted configuration before the material can evaluate it. To avoid substituting fabricated energy/gradient values at invalid states, the search imposes a kinematic feasibility bound. Along a proposed free-DOF direction, compute delta F_e and

\[
a_e=\|F_e^{-1}\delta F_e\|_2,\qquad
s\le\min(1,0.5/\max_e a_e).
\]

For every fraction t along that bounded segment, norm(t s F_e^−1 delta F_e) < 1. Therefore I+t s F_e^−1 delta F_e is nonsingular. By continuity from the positive-J starting state, the entire segment stays orientation-preserving. This is a step-size restriction, not a determinant clamp or artificial stiffness.

Trial states still pass through the element/material positive-J and numerical-validity checks. Backtracking accepts only finite admissible states satisfying sufficient energy decrease. Each accepted state's minimum J and physical residual are recorded. A dedicated test also samples a deliberately large bounded trial direction along the whole segment.

Default convergence and safeguards:

- Maximum absolute free-coordinate residual: **1e−8 N**.
- Up to 600 iterations per inner continuation solve.
- Armijo coefficient 1e−4; at most 60 backtracks per step.
- Initial displacement increments at most 0.05H, with previous converged positions as warm starts.
- Failed increments are halved, with explicit failure if the increment becomes smaller than 1e−6H.
- A geometry-only predictor rescales the previous z coordinates to the new platen height. No analytical material solution or recorded trajectory is used to initialize lateral deformation.
- Line-search stagnation, inadmissible states, iteration limits and bracket failure are reported rather than accepted.

The outer solver uses SciPy `brentq`, bracket expansion and cached converged inner states. Its default search is limited to d/H ≤ 0.65; failure to bracket in that declared domain raises an error. Position root tolerance is 1e−10 m, with an additional explicit reaction-balance check. Increasing verification loads warm-start from nearby cached equilibria. Material response is monotone in the tested range; the implementation does not claim that every nonlinear material has a monotone reaction curve or a unique equilibrium.

## Verification coverage

Synthetic scenarios are exactly:

| Scenario | mu, Pa | alpha | beta |
|---|---:|---:|---:|
| Primary | 2000 | 10 | 0 |
| Shape sensitivity | 2000 | 20 | 0 |
| Lateral coupling | 2000 | 10 | 0.125 |

Prescribed compression d = 0, 1, 2, 3 and 4 mm and force targets 0.05, 0.10, 0.20 and 0.30 N are solved on both meshes: 54 cases. All are homogeneous verification conditions, unrelated to the experimental bottle loads.

The independent analytical comparison uses the verified material-point traction-free branch lambda_t = lambda_z^−nu, with lambda_z = 1−d/H. Analytical reaction is −A0 Pzz and analytical energy is V0 W. The force-control reference displacement is found independently by scalar inversion of that analytical stress relation. The global solver itself never uses this analytical solution.

At beta = 0, the geometry-only predictor with unchanged lateral coordinates is already the exact homogeneous solution. Those cases legitimately require zero optimization iterations. To ensure that this does not mask optimizer errors, tests perturb free coordinates of converged states for **all three scenarios** and verify that nonzero optimization is required to recover equilibrium. The coupled scenario also requires lateral relaxation in the ordinary sweep, with up to 100 total continuation iterations in a reported case.

Additional tests verify:

- Zero-load reference energy, force and configuration.
- Exact reduced gradient including nodal external work.
- Minimal anchors permit independent uniform lateral stretches.
- Nonaffine initial guesses converge to the expected configuration.
- Feasible search segments keep J positive.
- Forced iteration-limit failure and unattainable-load failure do not return success.
- Reaction and energy match the analytical uniaxial state.
- Compression displacement and reaction increase monotonically across the force sequence.

## Results

| Quantity | Maximum observed error / residual |
|---|---:|
| Free-coordinate force residual | 9.95e−9 N |
| Nodal position vs analytical homogeneous state | 8.60e−9 m |
| Reaction vs analytical material-point prediction | 1.40e−8 N |
| Energy vs analytical reference-volume energy | 4.14e−12 relative |
| Resultant of all constraint reactions | 6.67e−8 N |
| Force-controlled displacement vs analytical inverse | 7.01e−11 m |
| Reaction vs specified compressive load | 2.59e−9 N |
| Difference between mesh displacements | 5.83e−11 m |
| Difference between mesh reactions | 2.24e−9 N |

The minimum element J is **0.399999996**, and all 704 recorded accepted-state/continuation history rows have positive J. No continuation retries were needed in the successful verification sweep; retry/failure branches are exercised by unit tests. The observed sweep runtime was about 10 seconds on the current environment, not a performance guarantee.

Representative refined-mesh force-controlled results:

| Scenario | Load, N | Compression, approximately mm |
|---|---:|---:|
| Primary | 0.10 | 0.492 |
| Primary | 0.20 | 1.230 |
| Primary | 0.30 | 2.469 |
| Shape sensitivity | 0.10 | 0.716 |
| Shape sensitivity | 0.20 | 4.000 |
| Shape sensitivity | 0.30 | 6.000 |
| Lateral coupling | 0.10 | 0.428 |
| Lateral coupling | 0.20 | 0.979 |
| Lateral coupling | 0.30 | 1.674 |

The coupled scenario reaches lateral stretch about 1.0524 at 4 mm prescribed compression. The beta-zero cases retain lateral stretch 1 as a material prediction, not a horizontal boundary constraint. Anchor reactions remain numerical residuals rather than substantial lateral support forces.

The independently solved 6- and 48-tetrahedron configurations agree to the tolerances above. **This is homogeneous affine consistency**, not general mesh convergence for contact, layers, bending or nonuniform stresses.

## Files and reproduction

- `solver.py`: structured mesh, eliminated constraints, global objective, safeguarded BFGS and outer load solve.
- `test_solver.py`: six unit-test methods covering success and failure paths.
- `verify_solver.py`: reproducible synthetic sweep, analytical comparisons, CSVs, plots and protected-file hashes.
- `verification/equilibria.csv`: states, residuals, analytical comparisons and termination status.
- `verification/iterations.csv`: accepted-state energy, residual, step length and minimum J.
- `verification/force_root_history.csv`: inner equilibria queried by the outer root solve.
- `verification/continuation_attempts.csv`: successful increments and any retries.
- `verification/constraints.csv`: every constrained node/component.
- `verification/element_jacobians.csv`: elementwise J for each reported equilibrium.
- `verification/mesh_comparison.csv`, `deformed_nodes.csv`, `summary.json` and `equilibrium_checks.png`.

From the repository root, using the existing environment:

```powershell
python -B -m unittest discover -s analysis/material -p test_hyperfoam.py -v
python -B -m unittest discover -s analysis/fem -p test_tetra.py -v
python -B -m unittest discover -s analysis/fem_solver -p test_solver.py -v
python -B analysis/fem_solver/verify_solver.py
```

No packages or environments were changed. A first verification run passed mechanical assertions but failed CSV export because zero-load and continuation histories had different schemas. The history export was corrected and the full sweep rerun successfully. No physical formulation was changed to mask a convergence failure.

## Numerical limits and readiness

This is a small dense quasi-Newton solver with a local convergence criterion. It does not certify a unique global energy minimum, handle arbitrary contact sets, model friction or solve near-incompressible mixed formulations. Larger meshes may need sparse tangent methods and stronger preconditioning. External nodal loads are tested for gradient consistency, not for arbitrary-load benchmark accuracy. Only configurations with the declared positive-J and full-face support assumptions are covered.

**The numerical core is ready to support a reviewed next-stage sponge-geometry implementation.** That stage will still need layer/material assignment, reference-state decisions, geometry checks and boundary/contact validation. Present synthetic results neither identify sponge properties nor validate the actual experiment. No actual two-layer mesh has been constructed here; implementation stops at the homogeneous synthetic-block solver.
