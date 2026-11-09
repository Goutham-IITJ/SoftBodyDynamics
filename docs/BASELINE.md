# Stage 6 full-face FEM baseline identity

This is a **byte-identified working-tree baseline**, not a Git commit/tag or a new material fit. It preserves the completed scientific/computational Stage 6 state. No entire-repository copy was made.

## Official configuration

Canonical source: the `primary` row of [Stage 5 parameters](../analysis/calibration/outputs/parameters.csv), checked against [demo/frozen_models.json](../demo/frozen_models.json). Values were read from those files, not copied from rounded plot labels.

- One-term compressible hyperfoam: **mu = 6999.814990181902 Pa, alpha = 10, beta = 0**.
- Yellow deformable dimensions: 0.073 × 0.050 × 0.020 m; bottom z = 0.007 m, top z = 0.027 m.
- Green backing: rigid 0.007 m, no assigned material coefficient.
- Rigid horizontal massless 0.085 × 0.050 m card; frictionless full-face normal constraints, nominal foam area 0.00365 m².
- Quasi-static force-controlled equilibrium, no experimentally identified damping or recovery timescale.
- Demonstration resolution: 2 × 2 × 2 cells, 27 nodes/48 Tet4 elements; existing 65% yellow-compression search cap retained.

Alpha = 20 remains the separate recorded sensitivity model. Neither its parameters nor the primary were changed by organization. No observations were added to any fit.

## Baseline identifiers

[BASELINE_MANIFEST.json](BASELINE_MANIFEST.json) stores byte sizes and SHA-256 values for **446 pre-existing non-cache files**, together with Git status before edits. It includes original videos, all measurements, source/tests/configuration, stage reports, verified outputs, papers, assignment and Stage 6 media. Nothing is duplicated except these metadata records. The previous [Stage 6 package manifest](../demo/outputs/package_manifest.json) and [preservation manifest](../demo/outputs/preserved_sha256.json) also remain unchanged.

The single authorized pre-existing edit is the root README. Its old hash is retained in both historical inventories; it is documentation, not a changed model/data artifact. All **445 other pre-existing non-cache files** must remain byte-identical. The Python cache is disposable and was not deleted. [SUBMISSION_MANIFEST.json](SUBMISSION_MANIFEST.json) separately identifies the organized package, including the revised README and new documentation; it excludes only itself and caches/Git internals.

Selected complete SHA-256 identifiers (the full inventory is authoritative):

| Canonical file / artifact | SHA-256 |
|---|---|
| [analysis/calibration/outputs/parameters.csv](../analysis/calibration/outputs/parameters.csv) | `ea2e929209e2291efa49f757b9477cf50e756b9be31dbcaf9584559796aeb0f1` |
| [demo/frozen_models.json](../demo/frozen_models.json) | `95e0c4262a33282f465d6469c250388c8f8d3ae90591b8b8b064b7e7e39c51c2` |
| [analysis/calibration/outputs/protocol.json](../analysis/calibration/outputs/protocol.json) | `b4e1b6c68667184e3b9450e47d1a0aeda2a2c0c170d7bbed023f13cdf435ebf5` |
| [analysis/outputs/cycle_summary.csv](../analysis/outputs/cycle_summary.csv) | `be745a8c04ff6812739d8683c5b62798d6175b117977b84f298efa5a375cf9ca` |
| [analysis/material/hyperfoam.py](../analysis/material/hyperfoam.py) | `3b309f73c8edfd79fde391162acd59b3f7025016a128b7d72561caef3618e7ce` |
| [analysis/fem/tetra.py](../analysis/fem/tetra.py) | `ec986dbeac692ddf698e5f52f603f7ec2451d5dc1cadcd0c4e53e66dccd78833` |
| [analysis/fem_solver/solver.py](../analysis/fem_solver/solver.py) | `5ea8dc847ee5fe49be2322cf64c02dbc25ab486c9eb08d222194db86609aee76` |
| [analysis/sponge/geometry.py](../analysis/sponge/geometry.py) | `be600c9e37db0674daa74c7832e0467a01e391869440a76942bedbf86b37d0ee` |
| [analysis/calibration/calibrate.py](../analysis/calibration/calibrate.py) | `192b02492d5d243b88fc5b781c686c6020dff94e4dff0772f53c0c115a8e474b` |
| [analysis/calibration/run_calibration.py](../analysis/calibration/run_calibration.py) | `8ede971fcb36e0f246d833c4b7844d1df7145278ef3a821a2314ad4332054a6d` |
| [demo/model.py](../demo/model.py) | `9c3f1ead8b58f035d809a2a6eb41d8a2913bfa70daefb511ea08a961f38495d1` |
| [demo/evaluate.py](../demo/evaluate.py) | `d7736ee735e95a9e9e0c500cc74871804c95574981733a24df0f3fe51da9aab2` |
| [demo/render.py](../demo/render.py) | `a558611c53e2e51628f5763f1b793c087ca453119284f493067004cd85f70adc` |
| [demo/run_demo.py](../demo/run_demo.py) | `0d39c414a6b82175ab83ef4ea297158b565252e44af871fc68355799394cd444` |
| [demo/outputs/solved_fem_states.npz](../demo/outputs/solved_fem_states.npz) | `f92ff2cd61528eaca3a9d8e06eb9ed0fd279d83f8b717cb8371b3d822f83dd12` |
| [demo/outputs/demonstration.mp4](../demo/outputs/demonstration.mp4) | `96fa57798e1dcd4ab962bc46e6af965c2e49bf822ee6b85de9edfd146d5a31cc` |
| [demo/outputs/demonstration.gif](../demo/outputs/demonstration.gif) | `deab4bb511136c68c8d6206ff2ad3b9c19245c36f6210aea376f8dc20aa15ab5` |
| [demo/outputs/index.html](../demo/outputs/index.html) | `5fd03bf0729b4986d1a37f7bd59442e32f5368a2c26635c60b6a0fac3ffede43` |

The existing primary configuration digest is `c145150ca08a3ecc317dbf30f1e8277197cdf1697ab5eaf3e1c350b01d6a9a8f`, as recorded in the unchanged [demo summary](../demo/outputs/summary.json). This digest describes the configuration object; the file hashes above identify exact bytes. Neither alone is independent proof of prospective experimental registration.

## Check without changing outputs

Publication exception: the user subsequently deleted `Videos/photo1.jpeg` because it contained personal ID-card information. The historical inventory remains unchanged; the checker explicitly permits only this missing private asset and verifies the remaining 444 pre-existing non-cache files. The current submission inventory excludes the photograph. Model code, parameters, measurements, videos and demonstration results are unchanged. See [the publication note](PUBLICATION_CHECKPOINT.md).

```sh
python -B docs/check_baseline.py
python -B demo/check.py
```

The first checks preserved bytes, canonical frozen configuration, local Markdown/HTML targets and the organized manifest when present. A failure means investigate; do not regenerate results or normalize file bytes merely to make the check pass.

## Git state and proposed user action

At the initial snapshot, local branch `main` had **no commits and no tracked files**; that historical state is retained in the start-of-task manifest. An `origin` remote was configured. During this audit, commits/tracked files appeared outside this task's actions (latest observed short HEAD `5d56d8e`, subject `material report`). The final audit records the observed Git state; it must not be confused with the earlier snapshot. Root README is modified and many files remain untracked. No remote publication/access/history was verified, and this task created no commit, tag, branch, push or email.

Recommended tag name after the user reviews and commits the desired complete baseline: **`baseline-v1-fullface-fem`**. No tag exists merely because this name is documented, and none was created here. Two new recordings also appeared at `Videos/fingertip.mp4` and `Videos/half area.mp4`; they are outside the original 446-file inventory and remain unreviewed/unanalysed. They are cataloged in the organized-package manifest without changing the full-face calibration. Keep future localized-loading development separate from the frozen observations/configuration and use a distinct reviewed baseline for any later parameter/contact changes.
