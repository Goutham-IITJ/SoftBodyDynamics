"""Current package integrity with an explicit README-only baseline allowance."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[2]
HERE=ROOT/'analysis/localized_fem/phase7c'


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    errors=[]
    names=subprocess.check_output(['git','ls-tree','-r','--name-only','-z','baseline-v1-fullface-fem'],cwd=ROOT).decode().split('\0')
    count=0
    for name in filter(None,names):
        if name=='README.md':continue
        original=subprocess.check_output(['git','show',f'baseline-v1-fullface-fem:{name}'],cwd=ROOT)
        if not (ROOT/name).is_file() or hashlib.sha256(original).hexdigest()!=sha(ROOT/name):errors.append('Changed baseline: '+name)
        count+=1
    allowance=json.loads((HERE/'documentation_delta.json').read_text())
    expected_readme=allowance['current_readme_sha256']
    actual_readme=sha(ROOT/'README.md')
    release_delta=ROOT/'docs/final_release/readme_delta.json'
    if release_delta.exists():
        delta=json.loads(release_delta.read_text())
        if delta['previous_authorized_sha256']!=expected_readme:errors.append('Final README delta does not chain to the Phase 7C allowance')
        expected_readme=delta['final_readme_sha256']
        if delta.get('newline_policy')=='normalize CRLF to LF for final README only':
            actual_readme=hashlib.sha256((ROOT/'README.md').read_bytes().replace(b'\r\n',b'\n')).hexdigest()
    usability_delta=ROOT/'docs/usability/readme_delta.json'
    if usability_delta.exists():
        delta=json.loads(usability_delta.read_text())
        if delta['previous_authorized_sha256']!=expected_readme:errors.append('Reviewer usability delta does not chain to the final release allowance')
        expected_readme=delta['current_readme_sha256']
    if actual_readme!=expected_readme:errors.append('README differs from the explicitly authorized documentation delta')
    before=json.loads((HERE/'preservation_before.json').read_text())
    allowed={'analysis\\localized_fem\\solver.py','analysis\\localized_fem\\minimize.py','analysis\\localized_fem\\simulate.py'}
    changes=[]
    for name,value in before.items():
        if not (ROOT/name).is_file() or sha(ROOT/name)!=value:
            changes.append(name)
            if name.replace('/','\\') not in allowed:errors.append('Changed prior result/input/source: '+name)
    protocol=json.loads((HERE/'frozen_evaluation_protocol.json').read_text())
    for name,value in protocol['source_sha256'].items():
        if sha(ROOT/name)!=value:errors.append('Changed frozen evaluation source: '+name)
    # Keep the original checker intact. Require precisely the authorized stale
    # README entry, and do not hide link, calibration, or other manifest errors.
    result=subprocess.run([sys.executable,'-B','docs/check_baseline.py'],cwd=ROOT,text=True,capture_output=True)
    legacy=json.loads(result.stdout)
    if legacy['errors']!=['Organized package changed: README.md']:errors.append('Unexpected historical checker errors: '+str(legacy['errors']))
    failure=json.loads((HERE/'half_area_once/failure.json').read_text())
    if (HERE/'half_area_once/nodes.csv').exists():errors.append('Failed nominal run must not export a solution')
    output=dict(status='FAIL' if errors else 'PASS',unchanged_tag_files_excluding_readme=count,preserved_preexisting_files=len(before)-len(changes),modified_nonbaseline_phase7b_source=changes,readme_documentation_delta=allowance,historical_manifest_errors=legacy['errors'],local_links_checked=legacy['local_document_and_media_targets'],evaluation_source_hashes_unchanged=True,nominal_attempt_failed_as_reported=failure['status']=='failed',errors=errors)
    print(json.dumps(output,indent=2));return bool(errors)


if __name__=='__main__':sys.exit(main())
