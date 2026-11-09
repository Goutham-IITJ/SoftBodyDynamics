# Technical summary for research discussion

## Decision

The package demonstrates an observation-calibrated **spatial mechanical model**, with clear numerical evidence and an unresolved experimental model discrepancy. Its local presentation combines real specimen frames, force-driven FEM loading/unloading and quantitative comparison. It is ready for review as a reproducible quasi-static demonstration. It is not a complete claim of time-accurate recovery or new prospective validation.

## What the videos taught us

Three videos provide six late-hold compressions: 3.012/2.585 mm at 500 ml, 7.662/6.798 mm at 750 ml and 10.987/10.974 mm at 1000 ml. The assumed forces are 5.64075, 8.09325 and 10.54575 N, conditional on water volume, 75 g unmeasured bottle tare and stationary support. Low/high force and compression ratios differ appreciably, motivating a nonlinear response rather than a single global linear stiffness. They do not establish a unique nonlinear constitutive law.

The videos also expose important uncertainty: nominal versus optical layer dimensions, ruler/face plane mismatch, card translation/tilt, differing initial residual compression and cycle histories. Lateral marker tracks are not sufficiently reliable to identify lateral coupling. Free post-separation recovery spans multiple seconds, but its remaining amplitude is only about 0.11–0.37 mm, comparable to practical optical resolution. Most recovery occurs during lifting while transmitted force is unknown. Neither damping nor a recovery timescale is identified.

Source measurements and reports are preserved. Six selected demonstration photographs were decoded sequentially inside their hold windows, with original frame identities and timestamps cross-checked against existing measurement rows. The photos are not pose-registered to the FEM camera; their labels show settled-window medians, not individual-frame compression.

## Frozen mechanics and parameter meaning

The primary is a one-term compressible hyperfoam, **mu = 6999.814990181902 Pa, alpha = 10, beta = 0**. Only mu was calibrated, using the first 500/1000 ml cycles and equal squared displacement residuals. The Stage 5 parameter CSV supplies its full precision. A reviewed snapshot and hashes prevent a later parameter/core change from silently entering the demonstration or fresh-test receipt.

The actual Stage 4 yellow geometry is 73 × 50 × 20 mm at z = 7–27 mm. Green backing at z = 0–7 mm is rigid geometry, without a modulus or deformable elements. The 85 × 50 mm massless card constrains all top z coordinates to a horizontal plane. Bottom z is fixed; tangential DOFs remain free except minimum rigid-motion pins. There is no general collision solver, friction, plate tilt or interlayer shear. Contact area is the nominal foam footprint, 0.00365 m², not the card area.

Mu is a conditional effective specimen coefficient. Two scalar calibration observations cannot uniquely determine mu, alpha and beta, especially with uncertain geometry/input/reference. Even an exact two-parameter endpoint fit would leave no calibration residual degrees of freedom. Beta = 0 predicts no homogeneous lateral expansion; it is a declared assumption, not a measured lateral property. Optical total-height compression is allocated to yellow under the rigid-backing assumption, despite uncertain apparent green-layer motion.

## Why this is mechanics, not trajectory replay

The verified kernel evaluates strain energy and first Piola stress from each element's deformation gradient. Tet4 elements assemble nodal energy gradients. The nonlinear energy minimizer relaxes free coordinates at prescribed platen displacement; the force-controlled outer root solve finds a reaction matching the requested force. No observed displacement is passed into this sequence, and no vertex is scaled to match an image. Reference/current coordinates, connectivity, applied forces and convergence diagnostics are exported for every demonstrated state.

The demonstration contains **51 actual equilibria**, on 27 nodes/48 tetrahedra, traversing zero → 500 → 750 → 1000 ml nominal force → zero through intermediate forces. Repeated display frames merely provide readable presentation holds. Reusing a cached conservative equilibrium is valid for this history-independent model; the final zero-force request is explicitly re-equilibrated from the preceding loaded state. Every visual vertex comes from the solver's positions.

The MP4/GIF is **45.2 seconds of presentation**, not 45.2 simulated physical seconds. It has no physical timestep. A sequence of reversible equilibria shows the reference-shape limit of unloading; it cannot predict a recovery speed, overshoot, creep or hysteresis.

## Quantitative comparison

| Scenario | Calibration RMSE | 750 ml prediction | 750 ml RMSE | Endpoint-repeat RMSE |
|---|---:|---:|---:|---:|
| Primary alpha = 10, beta = 0 | 0.800 mm | 7.488 mm | 0.504 mm | 1.055 mm |
| Alpha = 20, beta = 0 sensitivity | 0.224 mm | 7.948 mm | 0.838 mm | 0.478 mm |
| Empirical local interpolation | 0 by construction | 7.000 mm | 0.490 mm | 0.302 mm |

At 500/1000 ml the primary predicts 3.923/10.316 mm, yielding +0.911/−0.671 mm training residuals. The low-load discrepancy exceeds the nominal 0.601 mm engineering allowance. Reproducing each endpoint alone would require mu = 8158 and 6512 Pa: one scale cannot reconcile both at fixed alpha = 10. Shape, full-face contact, rigid-backing allocation, force assumptions, optical error and material history are competing explanations. Numerical convergence cannot resolve that ambiguity.

Alpha = 20 changes the force-response curvature and its fitted scale, reducing endpoint residuals. The intermediate response is not fixed by endpoint agreement: its 7.948 mm prediction lies above both 750 ml observations and has larger pair RMSE. This is a curve-shape/generalization tradeoff, not evidence that alpha = 10 is intrinsically correct. Alpha = 20 stays visibly labeled as sensitivity and was not selected using intermediate errors.

The two 750 ml cycles remain excluded from the FEM fit, but were used in earlier model review. Their comparison is retrospective, not pristine prospective validation. The nominal primary/baseline RMSE difference is only 0.014 mm, far below the unresolved measurement sensitivity. FEM has not demonstrated an accuracy advantage. Its additional capabilities are spatial equilibrium, stresses/energy, reactions and geometric admissibility; their experimental validity outside global compression has not been established.

## Verification is distinct from validation

The six unit suites contain **36 passing methods**, including five new frozen-workflow/output tests. They verify known synthetic inverse recovery, mass conversion, split integrity, exact scale acceleration, constitutive/element gradients, coordinate handling and solver safeguards. New tests reassemble all 51 saved meshes and confirm they are actual force-balanced positive-J FEM states, and check the six real frame/timestamp joins.

In the rendered primary sequence, maximum free-coordinate residual is **1.65e−14 N**, minimum J is **0.484199**, maximum applied-force/reaction error is **1.86e−8 N**, and final nodal error from reference is **6.94e−18 m**. These exceptionally small inner residuals reflect the homogeneous beta-zero case, where the existing geometric continuation predictor already reaches the affine equilibrium. Prior nonzero-beta/nonaffine tests exercise genuine lateral optimization. The declared run tolerance remains 5e−8 N; no inference of physical precision follows from residual size.

The 6-/48-tetrahedron mesh agreement from prior stages is an affine consistency check, not convergence evidence for indentation, nonuniform contact or instability. Full-face planes may support expanded nodes beyond finite visible footprints in coupled scenarios. Local stress, lateral deformation and arbitrary-contact predictions remain unvalidated.

## Fresh prediction protocol

`evaluate.py predict` accepts actual measured total bottle mass, supported loading condition and initial-state notes. It solves with the frozen primary and saves a timestamped integrity-checked receipt **without accepting observed compression**. A separate `score` invocation later receives the real settled observation, verifies the same frozen core/configuration and reports error. It never refits or overwrites an existing record. Unit-test synthetic values are temporary fixtures, not presented as a successful fresh experiment. No fresh observations are available in the package.

Smallest useful follow-up: weigh the bottle, verify dimensions/face-plane scale and record one controlled fresh low/intermediate-force interaction with centered plate and documented baseline/history. For temporal recovery, add a rapid characterized release with appreciable motion remaining after definite separation and observe until stable. Only after such data and review should a low-parameter temporal law be introduced; no relaxation time is invented here.

## Assignment coverage and remaining gaps

The two-page assignment requests observation-informed deformation/recovery, a fresh interaction and comparison, code/model with run instructions, input video/link, a short demo video or interactive viewer, assumptions/limitations and tool credits. It also asks for paper-reading discussion at interview, and submission by email with GitHub/result links and hiring-team access if private.

| Item | Package status |
|---|---|
| Observation-informed 3D deformation model | Implemented, calibrated conditionally and numerically verified |
| Real object / simulated response comparison | MP4, GIF, local HTML and comparison PNGs included |
| Code/model, input videos, README and runtime instructions | Present; previous stages and originals preserved |
| Explanation, limitations and credits | README, this summary and detailed stage reports |
| Fresh interaction with prediction fixed before measurement | **Not yet recorded**; two-step protocol ready |
| Recovery matching observed physical timing | **Not established**; reversible equilibria only |
| GitHub publication, hosted result/access and email reply | **Not performed**; prepared locally, no external messages sent |
| Interview discussion of the two papers | No written submission requested; preparation/readiness not certified by this stage |

The package is ready for review and reproducibility, with those experimental/submission gaps explicit. Its local viewer is not an already published result link. Stage 6 stops without introducing a new material/contact/damping model or silently recalibrating any parameter.
