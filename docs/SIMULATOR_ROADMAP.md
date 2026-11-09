# Simulator extension roadmap — planned only

The frozen baseline already supports centered horizontal full-face force-controlled equilibrium through `demo.model.solve` and the [existing prediction/evaluation workflow](../demo/FRESH_VALIDATION.md). This task adds no patch, finger or rigid-indenter mechanics, MuJoCo/Gazebo port, material law or damping.

## Possible future CLI

The following is an interface proposal, not an implemented command:

| Proposed capability | Intended controls / output |
|---|---|
| Full-face compression | Applied force in N; frozen or separately reviewed model identity |
| Finite surface-patch loading | Explicit footprint dimensions/shape, surface, center/location and force direction |
| Different magnitudes and locations | SI units, bounds checks and explicit rejection of unsupported geometry |
| Solved FEM mesh export | Reference/current nodes, connectivity, element states, reaction/convergence diagnostics |
| 3D visualization | Actual solved coordinates, visible support/loading assumptions and units |
| Rigid-indenter contact, later | Reviewed indenter geometry/pose and unilateral contact treatment |

No executable named for this proposal exists. The current API and mass-based evaluator remain the supported baseline entry points.

## Prescribed patch force versus contact

A prescribed surface traction or nodal load specifies where/how the force is applied. Its resultant can be controlled, but this does not discover which surface is touching a rigid object, solve an unknown pressure distribution, prevent penetration, or allow contact opening correctly. The assumed traction profile must be declared; it is not a measured finger pressure.

True unilateral rigid-object contact additionally requires nonpenetration, compression-only contact reactions and separation/contact-set determination, with a numerical contact algorithm and corresponding verification. The current bilateral top/bottom planes cannot be relabeled as that capability. Partial support may also require revisiting the bottom constraint assumption.

## Smallest defensible development sequence

1. Keep this full-face baseline and its observations immutable; place new recordings in [the separate proposed dataset](../experiments/localized_loading/README.md).
2. Specify a controlled patch-load benchmark first, including its exact external loading/support assumptions. Reuse the verified kernel/assembly; do not change material equations to hide contact-model mismatch.
3. Refine the mesh near load gradients, check load integration, force/moment balance, free residuals, positive Jacobians and solution/mesh convergence. The current 6-/48-tet homogeneous affine agreement does not establish localized-load resolution.
4. Obtain independently characterized force/geometry and observed spatial deformation. Compare with new data using a frozen prediction-first split before claiming local stress/lateral/contact validity.
5. Only then consider rigid-indenter contact, friction or time-dependent behavior as separately reviewed extensions. Video-only finger motion does not identify contact force or damping.

No model implementation, new parameter fit or analyzed localized experiment accompanies this roadmap.
