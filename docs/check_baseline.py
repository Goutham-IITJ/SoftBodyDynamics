"""Read-only baseline and local-link verification. No regeneration or video decoding."""
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import hashlib
from html.parser import HTMLParser
import json
import re
from urllib.parse import unquote,urlsplit
from demo.model import configuration

ROOT=Path(__file__).resolve().parents[1]
PRIVATE_REMOVED='Videos/photo1.jpeg'  # User-authorized privacy removal; historical hash retained.


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


class Links(HTMLParser):
    def __init__(self):super().__init__();self.targets=[]
    def handle_starttag(self,tag,attrs):
        self.targets.extend(value for key,value in attrs if key in ['href','src'] and value)


def headings(path):
    result=set();counts={}
    for line in path.read_text(encoding='utf-8').splitlines():
        match=re.match(r'^#{1,6}\s+(.+?)\s*#*$',line)
        if match:
            text=re.sub(r'[`*]','',match[1]).lower()
            slug=re.sub(r'[^\w\- ]','',text).replace(' ','-')
            count=counts.get(slug,0);counts[slug]=count+1
            result.add(slug if not count else f'{slug}-{count}')
    return result


def check():
    manifest=json.loads((ROOT/'docs/BASELINE_MANIFEST.json').read_text(encoding='utf-8'))
    errors=[];preserved=0
    if (ROOT/PRIVATE_REMOVED).exists():errors.append('Removed private ID-card photograph must not be published')
    for name,entry in manifest['files'].items():
        if name=='README.md':continue  # The sole explicitly authorized pre-existing documentation edit.
        if name==PRIVATE_REMOVED:continue
        path=ROOT/name
        if not path.is_file() or sha(path)!=entry['sha256']:errors.append(f'Changed/missing frozen file: {name}')
        else:preserved+=1
    config=configuration()
    frozen=json.loads((ROOT/'demo/frozen_models.json').read_text())['primary']
    if config!=frozen:errors.append('Frozen primary differs from canonical sources')
    historic=json.loads((ROOT/'demo/outputs/package_manifest.json').read_text())['sha256']
    for name,expected in historic.items():
        if name!='README.md' and (not (ROOT/name).is_file() or sha(ROOT/name)!=expected):errors.append(f'Stage 6 package mismatch: {name}')
    targets=[]
    for path in ROOT.rglob('*.md'):
        if any(p in path.parts for p in ['.git','.venv','venv','env','__pycache__']):continue
        for match in re.finditer(r'!?\[[^\]]*\]\((<[^>]+>|[^\s()]+)\)',path.read_text(encoding='utf-8')):
            targets.append((path,match[1].strip('<>')))
    viewer=ROOT/'demo/outputs/index.html';parser=Links();parser.feed(viewer.read_text(encoding='utf-8'))
    targets.extend((viewer,target) for target in parser.targets)
    local=0;html_local=0
    for source,target in targets:
        parts=urlsplit(target)
        if parts.scheme or parts.netloc:continue  # External availability is not a local-file check.
        path=(source.parent/unquote(parts.path)).resolve() if parts.path else source
        local+=1;html_local+=source==viewer
        if not path.is_relative_to(ROOT) or not path.exists():errors.append(f'Broken local target: {source.relative_to(ROOT)} -> {target}')
        elif parts.fragment and path.suffix=='.md' and unquote(parts.fragment) not in headings(path):
            errors.append(f'Broken heading: {source.relative_to(ROOT)} -> {target}')
    submission=ROOT/'docs/SUBMISSION_MANIFEST.json';submission_checked=0
    if submission.exists():
        for name,entry in json.loads(submission.read_text(encoding='utf-8'))['files'].items():
            if not (ROOT/name).is_file() or sha(ROOT/name)!=entry['sha256']:errors.append(f'Organized package changed: {name}')
            submission_checked+=1
    result=dict(status='FAIL' if errors else 'PASS',unchanged_preexisting_files=preserved,
                authorized_preexisting_document_edit='README.md',local_document_and_media_targets=local,
                authorized_privacy_removal=PRIVATE_REMOVED,
                local_viewer_targets=html_local,organized_manifest_files_checked=submission_checked,
                canonical_mu_Pa=config['mu_Pa'],errors=errors)
    print(json.dumps(result,indent=2));return not errors


if __name__=='__main__':sys.exit(not check())
