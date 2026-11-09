# Submission completeness checklist

Cross-checked against both pages of the [original assignment](../Assignment/Dirac-Research-TakeHome.pdf). This is a readiness audit, not a claim that the assignment has been submitted. The assignment asks for observed deformation/recovery, a fresh interaction, reproducible code/model, input media, a short result video or viewer, assumptions/limitations/credits, and an email containing repository/result links. It separately requires readiness to discuss two papers; neither reproduction nor a written paper submission is requested.

| Item | Status | Evidence / remaining action |
|---|---|---|
| Original experimental videos | Present, preserved | [Three input clips and photograph](../Videos/); hashes in [baseline manifest](BASELINE_MANIFEST.json) |
| Observation-derived measurements | Present | [Extraction report](../analysis/REPORT.md), [cycle summary](../analysis/outputs/cycle_summary.csv), per-frame/marker CSVs |
| Material-scale calibration | Present, conditional | [Stage 5 report](../analysis/calibration/REPORT.md); official first 500/1000 cycles only; low-load discrepancy unresolved |
| Numerical verification | Pass | Existing 36 test methods run by `python -B demo/check.py`; [audit](REPOSITORY_AUDIT.md) |
| 3D simulation | Present for full-face equilibrium | Verified material/Tet4/global solver/geometry; [technical summary](../demo/TECHNICAL_SUMMARY.md) |
| Real/FEM comparison | Present, retrospective | [Viewer](../demo/outputs/index.html), six residual rows; 750 ml held out from FEM fitting but previously inspected |
| Fresh prospective interaction | **Pending** | No genuinely new recorded prediction-first observation/score found; [protocol ready](../demo/FRESH_VALIDATION.md) |
| Quasi-static recovery demonstration | Present within stated scope | [MP4](../demo/outputs/demonstration.mp4) / [GIF](../demo/outputs/demonstration.gif) traverse reversible equilibria to reference |
| Physical recovery timing | **Unresolved** | No identified damping/time integrator; existing free-recovery amplitude/release input insufficient; not a time-accurate recovery claim |
| Short demo video / viewer | Present locally | MP4/GIF and HTML with valid relative media/document links; ordinary GitHub HTML file view is not hosting |
| Reproducibility | Verified in installed environment | [Requirements and command evidence](REPRODUCIBILITY.md); demo/calibration generators inspected, deliberately not rerun over fixed outputs; clean install untested |
| Model limits and references | Documented | [Root README](../README.md), technical reports and external references; no general fingertip/contact capability claimed |
| Paper-reading preparation | **User readiness unverified** | [3D Gaussian Splatting PDF](<../Papers/3D Gaussian splatting.pdf>), [Hybrid Particle-Voxel PDF](../Papers/2611.04492v1.pdf); prepare ideas/assumptions/limitations for interview |
| Local Git baseline | **Partially committed externally during audit** | Started with no commits/tracked files; commits and tracked files appeared outside this task's actions. Latest observed short HEAD was `5d56d8e`; root README remains modified and many assets/docs untracked. Suggested tag only, not created by this task |
| GitHub publication / hiring-team access | **Not verified/performed** | Local `origin` exists, but no push/access/publication check was performed; user must review and publish/provide access |
| Hosted result link | **Pending** | Choose an accessible video/release/viewer location; local HTML path is not an externally shared result URL |
| Required submission communication | **Pending** | User must reply to assignment email with GitHub/result links and confirm hiring-team access; no emails sent |

## Before describing this as a complete submission

- Keep the distinction between numerical verification and physical validation. Do not remove the visible low-load mismatch or promote alpha = 20 using the already inspected intermediate observations.
- Either obtain a genuine new prediction-first trial and informative recovery data, or explicitly disclose those assignment gaps in the submission explanation. Do not manufacture an apparent successful validation or arbitrary recovery animation timescale.
- Review the uncommitted files, publication size/access strategy and the [baseline identity](BASELINE.md). A user-created commit and eventual `baseline-v1-fullface-fem` tag can provide Git provenance after review; none was created automatically.
- Confirm repository/result links work for the hiring team before sending the required communication. Recording location guides and the roadmap are future plans, not completed experiments/features.

Two new recordings arrived during this audit and are [cataloged separately](../experiments/localized_loading/README.md). They do not close the fresh prospective validation gap: no prior frozen prediction, measured force/displacement or scored observation for them has been established here.
