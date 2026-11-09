# Stage 2: linear tetrahedron and affine patch verification

## Outcome and scope

The total-Lagrangian four-node tetrahedron and minimal force assembly pass the required verification checks. **Seven FEM test methods and all seven existing material test methods pass.** The independent patch driver passes 27 material/deformation/mesh cases and 162 integrated face-reaction comparisons.

This verifies the element formulation and its assembly for the tested states. It does not validate a sponge model, establish material constants, demonstrate a nonlinear equilibrium solver or establish convergence for nonhomogeneous contact problems. No fitting, contact, damping, stiffness matrix, two-layer sponge geometry or complete simulation was added.

## Reuse of Stage 1

`tetra.py` imports `Hyperfoam` from `analysis.material.hyperfoam`; it does not duplicate the energy or constitutive stress equations. The existing `evaluate(F)` interface returns energy density W, first Piola stress P and Cauchy stress sigma. The FEM integration and gradients use W and P. Cauchy stress is used only in an independent current-surface traction check.

The material code, its tests and verification files, and prior extracted CSVs are protected by before/after hashes in `verification/summary.json`. Stage 1 regression tests were run without regenerating or changing its outputs.

## Derivation and conventions

Each position array has shape (4,3): rows hold nodal xyz coordinates. Edge matrices use **columns**:

\[
D_m=[X_1-X_0\quad X_2-X_0\quad X_3-X_0],\qquad
D_s=[x_1-x_0\quad x_2-x_0\quad x_3-x_0].
\]

Linear interpolation in the reference tetrahedron gives the spatially constant deformation gradient

\[
F=D_sD_m^{-1},\qquad J=\det F,\qquad
V_0=\frac{|\det D_m|}{6},\qquad E_e=V_0W(F).
\]

Reference geometry is fixed during variation. With P = dW/dF and A:B = tr(A^T B),

\[
\delta E_e=V_0P:\delta F
=V_0\operatorname{tr}(P^T\delta D_sD_m^{-1})
=\operatorname{tr}[(V_0PD_m^{-T})^T\delta D_s].
\]

Define G = V0 P Dm^(-T). Because column i of delta Ds is delta x_i − delta x_0,

\[
g_i=\frac{\partial E_e}{\partial x_i}=G_{:,i},\quad i=1,2,3,
\qquad g_0=-(g_1+g_2+g_3).
\]

Indices i = 1,2,3 here refer to the corresponding three edge columns. Implementation arrays store these vectors in rows 1–3. Internal nodal forces are **f_int,a = −g_a**. For a patch in static equilibrium, the balancing external traction or constraint load is **f_ext,a = g_a**. A solver that defines its internal residual as positive g must not apply the negative sign a second time.

Equivalently, g_a = V0 P grad_X N_a. The reference shape gradients sum to zero, so the element has zero resultant internal force. Objectivity gives symmetry of P F^T, which implies zero resultant moment of internal forces about the current geometry. The torque check uses current positions, not reference positions.

Coordinates are metres; V0 is m³; W is J/m³; P and sigma are Pa; element energy is J; nodal energy gradients and forces are N; moments are N m. F and J are dimensionless. Current volume J V0 is **not** used in the reference-energy integration.

## Implementation

- `Tet4(X)` caches reference geometry, volume and a linear-system-derived inverse edge map.
- `deformation_gradient(x)` validates current geometry and returns F.
- `evaluate(x, material)` returns F, J, energy, W, P, Cauchy stress, nodal energy gradient and internal forces.
- `TetAssembly(X, connectivity)` provides only the minimal homogeneous-material summation needed for patch checks. Repeated global indices are accumulated with `np.add.at`.

Nonfinite or complex positions, incorrect array shapes, degenerate reference/current configurations, repeated element nodes and invalid connectivity are rejected. Reference edge condition numbers above 1e12 are rejected as numerically ill-conditioned; this is a dimensionless numerical admissibility check, not artificial stiffness. Extremely unrepresentable numeric states are rejected. There is no geometry clamping or repair.

Reference orientation and physical inversion are distinguished. Either sign of det Dm is accepted as a local node-order convention, with positive reference volume. A consistently permuted current/reference element has identical physical response. Inversion means det F <= 0, including a current orientation inconsistent with its reference; such states are rejected. Tests include odd permutations and actual inversions separately. No nodes are silently reordered.

## Material scenarios

All verification scenarios use the synthetic common scale **mu = 2000 Pa**:

| Label | alpha | beta |
|---|---:|---:|
| Primary formulation check | 10 | 0 |
| Shape sensitivity | 20 | 0 |
| Lateral-coupling check | 10 | 0.125 |

The scale isolates numerical correctness and is not a new sponge fit. The conditional effective coefficients from Stage 1 were not described as intrinsic properties or refitted. No 750 ml data were used.

## Single-element verification

The tests use both an axis-aligned tetrahedron with independently known volume and a skew tetrahedron. Reference and pure-rotation energies/forces vanish to floating-point tolerance; deformed states preserve energy under translation and rotation, while force vectors rotate covariantly.

Central finite differences perturb each of the **12 nodal coordinates individually**. The report driver covers eight deformation cases per material, including compression, expansion, combined shear/compression and five random positive-J affine states. Five step sizes give 120 gradient comparisons. Perturbations range from 1e−3 to 1e−7 times the longest reference edge. Every sampled perturbed state is evaluated through the same positive-J validation, with no repair.

Relative gradient error is

\[
\epsilon_g=\frac{\|g_{\mathrm{FD}}-g\|_F}{\|g\|_F},
\]

using a 1e−12 N denominator floor in the driver. Nontrivial test cases have nonzero force; zero-force states are checked with absolute tolerances instead. The acceptance threshold is 3e−6 at relative step 1e−5. The observed maximum at that step is **9.78e−9**. The plot shows the expected central-difference truncation decrease followed by roundoff sensitivity at very small steps; it does not hide errors by choosing one favorable perturbation size.

Element force resultant is at most **1.36e−17 N** and torque at most **1.42e−18 N m** in the report sweep. The unit tests also enforce internal force = negative energy gradient explicitly.

## Independent affine patch test

The synthetic block is **30 × 20 × 10 mm**, deliberately different from sponge geometry. It is homogeneous and contains no material interface or contact.

Three discretizations are tested:

1. Eight nodes, six tetrahedra.
2. Twenty-seven nodes, 48 tetrahedra, with an interior node.
3. A reflected 48-tetrahedron partition with a different body-diagonal layout.

The two refined meshes check cancellation at an interior node. The reflection also exercises reference orientation conventions. All meshes fill reference volume 6e−6 m³.

Prescribed homogeneous states are:

- Axial compression lambda_z = 0.6, with traction-free lateral stretch from the existing material helper. For beta = 0.125, lateral stretch is allowed to change.
- Uniform expansion F = 1.12 I.
- Simple shear F = I + 0.3 e_x tensor e_y.

A constant translation is included. This is a prescribed affine verification problem, not an equilibrium solve; interior equilibrium is checked by its residual.

For each prescribed F, the independent exact energy is V_block W(F). Every element must recover F and the global energy must match this value. This checks more than the tautology of summing stored element energies.

Boundary triangles are identified topologically. Outward reference area vectors are calculated by cross products and the opposite-vertex test, independently of Dm inverse or shape-function gradients. For a boundary triangle with reference area vector A0 N,

\[
f_{\mathrm{triangle}}=P N A_0,
\qquad f_{\mathrm{node}}=f_{\mathrm{triangle}}/3.
\]

These are consistent nodal loads because the mean of each linear shape function over the triangle is 1/3. The resulting load vector is compared with the assembled energy gradient **at every node**, including edges/corners. Summing nodal gradients merely over nodes lying on one face would mix contributions from adjacent faces; the face-reaction check instead sums the tractions of that face's triangles.

An additional independent check uses deformed triangle area vectors and sigma n da. It agrees with P N dA0, checking the first-Piola/Cauchy distinction and Nanson transformation. Volume-integrated P and the nodal identity sum_a g_a tensor X_a = V_block P are also checked.

| Quantity | Maximum error in 27 patches |
|---|---:|
| Total energy vs analytical reference-volume energy | 4.24e−15 relative |
| Assembled gradient vs reference boundary loads | 7.03e−15 relative |
| Reference-Piola vs current-Cauchy surface loads | 3.77e−16 relative |
| Interior-node residual | 1.51e−15 normalized |

The common acceptance threshold for normalized patch quantities is 2e−10; deformation-gradient error must be below 1e−11, and reference volume error below 1e−12 relative. Force normalization uses norm(P) times a characteristic area; torque adds a characteristic block length. These are numerical test tolerances, not experimental uncertainty estimates.

The mesh-consistency unit test compares energies directly between discretizations. All also reproduce analytical volume-integrated stress and boundary reactions. This demonstrates homogeneous affine consistency, **not general convergence for bending, locking, contact or highly distorted nonuniform deformation**.

A separate nonaffine assembly test perturbs the interior node, checks that its residual becomes nonzero, and finite-differences nine assembled coordinates spanning interior and boundary nodes. This guards against an assembler that would pass only homogeneous cases through cancellation.

## Reproduce and inspect

From the repository root, with existing dependencies:

```powershell
python -B -m unittest discover -s analysis/material -p test_hyperfoam.py -v
python -B -m unittest discover -s analysis/fem -p test_tetra.py -v
python -B analysis/fem/patch_test.py
```

The driver writes only `analysis/fem/verification/` and requires no installation. No experimental data are loaded for fitting. Files are:

- `patch_tests.csv`: gradients, reference volume, energy, Jacobians, stress integration and force/moment diagnostics.
- `boundary_reactions.csv`: actual and analytical force components for 162 material/case/mesh/block-face combinations.
- `nodal_gradients.csv`: all finite-difference step-sweep errors.
- `element_balance.csv`: isolated-element resultant and torque.
- `summary.json`: maxima and protected-input hashes.
- `verification.png`: step convergence and patch-load error plots.
- `synthetic_patch_meshes.png`: coarse/refined synthetic block under affine shear.

All requested formulation checks pass. The next stage can build on these elements, but will still need an independently verified equilibrium solver and boundary/contact treatment. No complete sponge mesh or solver has been constructed, and no physical-validation claim is made.
