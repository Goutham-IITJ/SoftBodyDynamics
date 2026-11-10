# Reviewer usability update

Requested fixes: install/setup before run commands; explicit MP4 download instructions; a GitHub-rendered comparison instead of an unexplained HTML-source link; obvious saved-output locations; clarify successful small-load localized cases versus the failed nominal bottle-load prediction.

Implemented a separate launcher and offline saved-result browser viewer. The launcher delegates to the unchanged solver CLI. The viewer uses exact saved nodal states, resultant-force labels, displacement colors, drag rotation and discrete equilibrium playback. Default scale is 1x; optional 5x/10x magnification is explicitly visualization-only and leaves numeric readouts/data unchanged. No solver runs in the browser. This is a visualization/usability update, not new physics or physical validation.

Original material/element/solver/calibration sources and the frozen Phase 7C numerical protocol hashes remain unchanged. Historical reports/manifests are preserved; the README allowance is extended with a separate chained delta. User-created runs are not committed or replaced. No nominal-force localized attempt or refinement study was repeated.

Verification: the existing 36 regression methods and 18 localized/support/CLI methods, plus four viewer tests. The latter check exported-state equality and preservation, failure without solved nodes, JavaScript projection/state/playback/magnification via a DOM/canvas test double, and launcher output messages. Node is used only by an optional development test, not by reviewers running the simulator or viewer. The automated browser surface blocks file:// previews, so no browser screenshot/visual-QA claim is made. The generated page is standalone local HTML with no remote scripts, services or CDN.

Publication contains presentation/launch/viewing files and verification logs only. Existing demo media, measurement CSVs, model parameters and numerical implementations are not edited.
