# Local FEM force control panel

Start once from the project root after installing requirements:

```powershell
python -B -m analysis.localized_fem.control_panel --open
```

This opens a local browser window. Choose full-face or localized mode; use the force number input or slider, then click **Solve & show result**. Increasing the slider maximum changes the selectable range, not the physics or the last solution. The panel sends a bounded request to the unchanged Python CLI and displays only a returned converged saved-state viewer. Model rotation, true-scale/magnified display and saved equilibrium playback remain available inside the result.

- The terminal must stay running. Ctrl+C stops the service. If the browser does not open, copy the printed http://127.0.0.1:PORT/ address into it.
- Default localized patch: 20 x 30 mm, center (18.25,25) mm; coarse 2/2/1 mesh, unilateral bottom support. Start with 0.3 N. Select another session mesh with `--mesh 4 4 2` if desired; this does not certify accuracy.
- Full-face mode retains the frozen Stage 6 solver, geometry, material and 13 mm compression search limit.
- Every request uses a fresh UUID directory beneath runs/interactive. No previous results are overwritten. Optional --output-root changes this session's result root.
- The localized CLI retains its 180 s nonlinear budget; the panel also limits its child process to 210 s. A single solve runs at a time. Convergence failure/timeout is explicit; a failed result replaces neither the mesh nor the force readout with an invented prediction.
- Force requests must be finite and in 0..20 N. This is an interface guard, NOT a validated force range. The actual acceptable range depends on scenario and solver convergence. The prior 10.54575 N half-area prediction failed and is not rerun automatically.
- This does not add damping, dynamics, contact with a rigid card/finger, fitting or new constitutive behavior. State playback is a sequence of reversible equilibria, not physical recovery time.

The server binds only to loopback, checks the Host and request Origin, requires a per-session token for solve requests, has no cross-origin access allowance, accepts only mode/force/sequence inputs, and serves only registered per-job outputs. It does not accept shell strings, arbitrary file paths, material parameters or commands from the browser. No external JavaScript/CDN or new runtime dependency is used.

Tests exercise real modest full-face/localized solves through HTTP, origin/token/input rejection, serialized jobs, failure without a fake viewer, and slider/button/result/failure JavaScript logic. The JavaScript test uses a DOM test double rather than claiming browser visual QA. New UI code is separate from all frozen physics; numerical protocol source hashes remain unchanged.
