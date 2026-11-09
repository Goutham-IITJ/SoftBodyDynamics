"""Summarize the single frozen half-area attempt; NEVER invokes a solver."""
from pathlib import Path
import csv
import hashlib
import json
from analysis.localized_fem.simulate import write_json

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]


def main():
    directory=HERE/'phase7c';protocol=json.loads((directory/'frozen_evaluation_protocol.json').read_text())
    assert all(hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==sha for name,sha in protocol['source_sha256'].items())
    run=directory/'half_area_once'
    failure=json.loads((run/'failure.json').read_text())
    assert not (run/'nodes.csv').exists(), 'Do not mix a failed run with solved prediction exports'
    with (ROOT/'analysis/localized_experiments/outputs/window_summary.csv').open() as f:
        observations=[row for row in csv.DictReader(f) if row['experiment']=='half_area' and row['window'] in ['cycle1_late_hold','cycle2_late_hold']]
    comparison=dict(status='No admissible nominal-force prediction; no experimental validation',numerical_protocol=protocol,reason=failure['reason'],observations=[dict(window=r['window'],observed_right_apparent_mm=float(r['right_region_compression_mm']),observed_left_apparent_mm=float(r['left_region_compression_mm']),predicted_right_mm=None,predicted_left_mm=None,profile_error_mm=None) for r in observations],shape_comparison='Not assessable at nominal force because no converged nominal FEM state was returned. Observed right depression/left shoulder qualitatively requires spatial coupling; small synthetic patch solves demonstrate that capability only.',finger='Unknown force: qualitative local deformation/coupling/recovery evidence only; no force-depth or recovery-time validation.',uncertainty='Unknown supported force, true depth footprint, card planarity/tilt/pressure, image plane and backing behavior; nominal force is not an independent force measurement.',attempt_count=1,policy='No retries, refits or geometry changes after the frozen attempt.')
    write_json(directory/'half_area_comparison.json',comparison)
    with (directory/'half_area_comparison.csv').open('w',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=list(comparison['observations'][0]));writer.writeheader();writer.writerows(comparison['observations'])


if __name__=='__main__':main()
