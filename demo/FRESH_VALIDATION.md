# Frozen-model fresh evaluation

No fresh experiment is included. Do not describe the existing 750 ml comparison or the unit-test fixtures as prospective validation. This workflow adds no fitted parameters and never automatically refits the model.

1. Use the same specimen, horizontal card, rigid table and centered full-face stationary loading. Verify face-plane scale and nominal layer dimensions. Record the card-only baseline, rest duration, previous cycles and initial-state notes. The current model cannot accept tilted, frictional, partially supported or localized loading as equivalent conditions.
2. **Weigh the total bottle plus water.** Use that measured mass directly; do not add the nominal 75 g tare again. Select a force within the previously observed interval if assessing interpolation (5.64075–10.54575 N). Other forces are unvalidated extrapolation; the unchanged force-search cap is 13 mm compression, approximately 14.599 N for this model.
3. Before viewing/measuring the new settled compression, save a prediction. Replace the mass and notes below with actual values; the symbolic mass placeholder is intentionally not a fabricated measurement:

```sh
python -B demo/evaluate.py predict --mass-g ACTUAL_MEASURED_GRAMS --condition centered_full_face_stationary --initial-state "ACTUAL BASELINE AND HISTORY NOTES" --experiment-id fresh-001 --output demo/fresh/fresh-001.prediction.json
```

The output contains the full-precision frozen configuration, input mass, force, numerical diagnostics, UTC creation time and integrity digest. Preserve the file before observing the response, preferably with an independent timestamp or commit. A local digest helps detect accidental changes; it alone is not proof of prospective preregistration.

4. Film the interaction with a fixed face-plane reference. Hold until approximately stationary and define a settled window in advance. Measure compression relative to the original card-on-sponge baseline, retaining uncertainty and all repeat/history notes. Do not reset to a different baseline to make the prediction agree. Copy `demo/fresh_observation.template.json` to a new file and fill its null compression with the actual observed settled value. Match the experiment ID and loading condition; record the actual initial state and any departure from the planned condition.
5. Score that observation separately:

```sh
python -B demo/evaluate.py score --prediction demo/fresh/fresh-001.prediction.json --observation demo/fresh/fresh-001.observation.json --output demo/fresh/fresh-001.evaluation.json
```

The evaluator checks receipt integrity and that the frozen model/core are unchanged. It reports prediction-minus-observation in mm, plus the existing illustrative 0.3 mm + 10% allowance. That allowance is not a confidence interval or proof of success. Model-domain violations and initial-state differences still need scientific review. Preserve failures as well as agreements; do not automatically refit.

## Recovery extension, if required

The animation only traverses equilibrium states. To identify a temporal recovery law, first collect one rapid, independently characterized release with appreciable free-recovery amplitude at definite separation (several times optical resolution; roughly 1.5 mm would be useful), fixed calibration and about 10–15 s of subsequent observation or until stable. Existing late recovery is only about 0.11–0.37 mm and release force is unknown. A declared low-parameter time-dependent law could then be tested against a separate recovery trial. Neither a relaxation time nor damping is supplied here; implementation needs review and informative data first.
