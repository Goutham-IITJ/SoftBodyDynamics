# Stage 4: nominal sponge geometry and FEM integration

Stage 4 passes the specified geometry and synthetic equilibrium checks. The yellow layer is a genuine tetrahedral FEM volume. The green backing remains rigid. The force-controlled solve and quasi-static zero-force unloading work at the elevated interface. This is numerical integration verification, not experimental calibration or validation of the specimen's constitutive response.

## Geometry and mechanical assumptions

All internal coordinates, displacements and exported node positions use metres. Visualization axes use millimetres. The nominal geometry specified for this stage is:

| Component | Dimensions | Vertical coordinates | Mechanical role |
|---|---|---|---|
| Table | Horizontal plane | z = 0 | Fixed rigid support |
| Green backing | 73 × 50 × 7 mm | z = 0 to 0.007 m | Rigid visualization geometry; no FEM elements |
| Yellow foam | 73 × 50 × 20 mm | z = 0.007 to 0.027 m | Deformable FEM solid |
| Card/platen | 85 × 50 mm, zero geometric thickness | z = 0.027 − d m | Rigid, horizontal, massless full-face normal constraint |

Yellow reference volume is **7.30e−5 m³**. Nominal foam contact area is **0.00365 m²**, not the card's 0.00425 m². The centered card overhangs by 6 mm at each lengthwise end. Positive compression d is downward. Yellow engineering compression is d/0.020, never d/0.027. Thus d = 8 mm means 40% yellow compression and a top elevation of 19 mm; the backing remains 7 mm thick.

The backing approximation follows qualitative observation, not a measured modulus. It has no material parameters, energy, elements or degrees of freedom. Real backing compliance and interlayer shear coupling are neglected. The green layer and table act as one fixed mechanical support system while remaining visually distinct.

Every yellow bottom node has z = 0.007 m. Every yellow top node has z = 0.027 − d m. Their x/y coordinates remain free except the existing minimum horizontal rigid-body constraints: bottom origin node x/y and bottom corner (73,0,7) mm y. These remove translation/yaw and admit homogeneous lateral expansion; they do not bond the full bottom face. No friction or plate tilt is represented.

These are **bilateral full-face plane constraints**, not a general collision/contact algorithm. The solver checks admissible compressive support reactions. It does not identify opening contact or redistribute contact when foam leaves a finite card/backing footprint. In the nonzero-beta fine-mesh compressed states, three top nodes extend outside the card footprint and five bottom nodes outside the backing footprint (1e−8 m geometric tolerance). They remain constrained to the support/platen planes. This is an explicit limitation of the requested full-face idealization: the finite rigid shapes are retained at their specified sizes, not silently enlarged. Predictions needing finite-footprint contact require a later contact treatment.

The dimensions above are the nominal specification for this stage. The previously documented optical layer-thickness discrepancy is not resolved or refitted here. Geometry uncertainty still matters for subsequent experimental calibration.

## Reused code and minimal solver changes

`geometry.py` defines `SpongeConfig`, constructs a yellow mesh through the existing `structured_block`, extracts outward boundary triangles from FEM connectivity, and provides separate rigid backing/card geometry. `Sponge` delegates equilibrium to the existing `BlockSolver`; it does not assign deformation from video measurements or a displacement lookup table.

The Stage 1 hyperfoam kernel and Stage 2 tetrahedral formulation are unchanged. The Stage 3 optimizer, exact gradients, continuation, Jacobian safeguard and outer force root solve are reused. Only `analysis/fem_solver/solver.py` needed a small extension:

1. An optional finite real `origin=(0,0,0)` preserves the prior default. Surface nodes and horizontal anchors are identified in local reference coordinates, then the mesh is translated before element construction.
2. Prescribed top/bottom elevations include origin z. The continuation predictor scales z **relative to the reference bottom**, rather than scaling absolute world coordinates.
3. The last equilibrium is retained. A zero-force request re-equilibrates from that loaded state instead of returning the cached undeformed object. Nonzero force requests retain the existing conservative-equilibrium cache. This does not implement a path-dependent material or a time integrator.

The original solver file SHA-256 before this extension was `01088c425f7dc61663858866eefd7542f4966f0b5b79522652998b90cf7c5d77`. Existing Stage 1–3 reports and generated verification outputs are preserved as records of those stages.

## Numerical verification

Synthetic inputs only: mu = 2000 Pa, alpha = 10, beta = 0 and 0.125. These are not inferred sponge properties. No bottle measurements are used as targets or calibration inputs.

| Structured cells | Nodes | Tet4 elements | Free DOFs | Boundary triangles |
|---|---:|---:|---:|---:|
| 1 × 1 × 1 | 8 | 6 | 13 | 12 |
| 2 × 2 × 2 | 27 | 48 | 60 | 48 |

For both meshes and materials, the driver checks seven states: zero reference, prescribed 4 and 8 mm compression, force targets 1 and 2 N, return to 1 N, and unloading to 0 N. This gives **28 state records**, plus **six elevated-versus-base-zero comparisons**. Returning to the earlier nonzero force may reuse its converged cached state, which is valid for this hyperelastic quasi-static model. The final zero-load state is explicitly re-solved from the preceding loaded state. With beta = 0.125, this requires lateral relaxation (122 continuation iterations for fine-mesh unloading); it is not a cached reference-shape check.

Reference checks cover nominal bounds, 20 mm deformable height, 7 mm offset, duplicate nodes, integer/range-valid connectivity, positive tetrahedral reference volumes, total volume, upper/lower node identification, outward surface winding and closed-surface volume. Backing vertices remain identical during all operations. Plane constraints, reaction signs, force balance and element Jacobians are checked in solved states, with positive Jacobians also checked in every recorded accepted inner iteration.

Independent reference comparison uses the existing material-point traction-free uniaxial branch at lambda_z = 1 − d/0.020. Expected energy is V0 W and expected compressive reaction is −A0 Pzz. This formula is used only by verification, not by the global solver to initialize lateral nodes or prescribe their response. Beta = 0 has no lateral expansion; its geometry predictor already reaches the exact homogeneous solution and may legitimately require zero optimizer iterations. Nonzero beta exercises actual lateral minimization.

| Quantity | Observed maximum/minimum |
|---|---:|
| Maximum free-coordinate force residual | 9.7111e−9 N |
| Maximum top/bottom resultant imbalance | 5.6509e−9 N |
| Minimum final and recorded-iteration J | 0.600000 |
| Maximum nodal error against homogeneous analytical reference | 1.2723e−9 m |
| Maximum zero-force unloading shape error | 8.7099e−11 m |
| Maximum energy difference under vertical translation | 3.5562e−17 J |
| Maximum reaction difference under vertical translation | 4.4676e−10 N |
| Maximum translated nodal-coordinate difference | 5.1253e−11 m |
| Maximum reaction difference between meshes | 1.8477e−8 N |
| Maximum force-controlled compression difference between meshes | 5.9991e−11 m |

Representative fine-mesh equilibria:

| beta | Prescribed d = 4 mm: reaction | Prescribed d = 8 mm: reaction | Compression at 1 N | Compression at 2 N |
|---|---:|---:|---:|---:|
| 0 | 1.62904 N | 2.41862 N | 1.85175 mm | 5.85664 mm |
| 0.125 | 2.08529 N | 4.04084 N | 1.53266 mm | 3.78454 mm |

The coordinate comparison changes only the reference elevation: otherwise identical yellow solids at base z = 0.007 and z = 0 are compared for 8 mm prescribed compression, 2 N force equilibrium and zero-force unloading. Energy, reaction, compression and translated nodal positions agree within the stated tolerances.

The two meshes reproduce an affine homogeneous solution exactly up to solver error. Their agreement verifies assembly/integration and boundary handling; it is **not** a general mesh-convergence result for indentation, heterogeneous deformation, buckling or finite contact. No claim of global uniqueness or stability against all possible modes follows from these tests.

All **26 unit-test methods pass**: 7 material, 7 tetrahedral FEM, 6 existing solver and 6 sponge integration tests. No required final numerical check remains failed. An initial verification-driver footprint diagnostic had a list/array conversion error; it was corrected and the complete driver rerun successfully.

## Reproduction and outputs

Run from the repository root with the installed Python environment:

```powershell
python -B -m unittest discover -s analysis/material -p test_hyperfoam.py -v
python -B -m unittest discover -s analysis/fem -p test_tetra.py -v
python -B -m unittest discover -s analysis/fem_solver -p test_solver.py -v
python -B -m unittest discover -s analysis/sponge -p test_sponge.py -v
python -B analysis/sponge/verify_sponge.py
```

Only NumPy, SciPy and Matplotlib are needed; no dependencies were installed. The driver writes solely within `analysis/sponge/verification/`:

- `summary.json`: configuration, numerical extrema and pass status.
- `equilibria.csv`, `mesh_checks.csv`, `translation_checks.csv`, `mesh_comparisons.csv`: state and comparison evidence, including footprint-limit diagnostics.
- Per-scenario node CSVs: reference/current coordinates with stable node indices for every recorded state; tetrahedron and outward boundary connectivity CSVs.
- `iteration_history.csv`, per-scenario outer-root/continuation histories: convergence and positive-J evidence.
- `rigid_backing_vertices.csv`, `compressed_platen_vertices.csv`: rigid visualization geometry.
- `sponge_equilibria.png`: undeformed and 8 mm compressed equilibria using the actual solved fine-mesh nodes, all tetrahedral edges, distinct green backing and a translucent card. The image was visually inspected.
- `preserved_analysis_sha256.json`: before/after-equal hashes for **275 pre-existing analysis files**, excluding Stage 4 and Python cache directories. The baseline includes the intentionally extended solver. No previous generated results, measurements or reports were overwritten by the driver. Original videos were not edited or re-extracted.

## Scope at the stopping point

The nominal sponge assembly is ready for review before Stage 5. The material is reversible and hyperelastic: recovery here means returning to a stress-free equilibrium, not recovering over measured time. There is no damping, recovery timescale, plasticity, creep or preconditioning law. There is also no general contact, friction, localized indentation, backing modulus, experimental parameter fit or final demonstration video. Synthetic reactions above must not be interpreted as predictions already validated against the observed sponge.
