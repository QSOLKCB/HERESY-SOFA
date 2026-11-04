"""Validate, hash and make this evidence package read-only. Run once, with python -B."""
import ast
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
from common import ROOT,command,utc

assert not (ROOT/'SHA256SUMS.txt').exists(), 'Already finalized; do not modify the seal'
for cache in ROOT.rglob('__pycache__'):
    shutil.rmtree(cache)

validation=dict(validated_at_utc=utc(),source_snapshots=0,source_replies=0,verbatim_fences_checked=0,
                primary_case_exits={},json_files_parsed=0,python_files_parsed=0,missing_required_artifacts=[],checks=[])
required=['CODEX-001-REPORT.json','CODEX-001-REVIEW.md','claims.json','environment.json','reproduce.py']
for i in range(1,9):required += [f'CASE-{i:02}/{f}' for f in ['test.py','source.json','receipt.json','execution.json']]
for name in required:
    if not (ROOT/name).is_file():validation['missing_required_artifacts'].append(name)
assert not validation['missing_required_artifacts']
for path in ROOT.rglob('*.json'):
    json.loads(path.read_text());validation['json_files_parsed']+=1
for path in ROOT.rglob('*.py'):
    ast.parse(path.read_text(),filename=str(path));validation['python_files_parsed']+=1
for i in range(1,9):
    folder=ROOT/f'CASE-{i:02}'
    source=json.loads((folder/'source.json').read_text())
    assert source['reply_count']==len(source['replies'])
    validation['source_snapshots']+=1;validation['source_replies']+=len(source['replies'])
    for item in [source,*source['replies']]:
        for index,match in enumerate(re.finditer(r'```([^\n]*)\n(.*?)```',item['body'],re.S),1):
            lang,body=match.groups();ext={'python':'py','py':'py','bash':'sh'}.get(lang.strip(),'txt')
            path=folder/f'source-{item["id"]}-block-{index:02}.{ext}'
            assert path.read_text()==body,str(path)
            validation['verbatim_fences_checked']+=1
    execution=json.loads((folder/'execution.json').read_text())
    validation['primary_case_exits'][str(i)]=execution['exit_code'];assert execution['exit_code']==0
    receipt=json.loads((folder/'receipt.json').read_text());assert receipt['all_checks_passed']
    if i==5:assert not receipt['checks'] and receipt['limitations']
for name in ['CASE-04/shell-controls-receipt.json','CASE-04/mock-shell-receipt.json','CASE-08/state-space-receipt.json']:
    assert json.loads((ROOT/name).read_text())['all_checks_passed']
assert json.loads((ROOT/'reproduction-validation.json').read_text())['exit_code']==0
report=json.loads((ROOT/'CODEX-001-REPORT.json').read_text())
assert report['summaries']['primary_checks']==239
assert report['independence']['sofa_replies_read']==11
all_sources={s['id']:s['agent_name'] for i in range(1,9)
             for source in [json.loads((ROOT/f'CASE-{i:02}/source.json').read_text())]
             for s in [source,*source['replies']]}
all_evaluated={c['source_id']:c['author'] for case in report['cases'] for c in case['claims']}
assert all_sources==all_evaluated
validation['checks'] += ['Every original and reply has attributed claims', 'All current primary and supplemental controls passed',
                         'Original code fences match captured source bodies', 'Reproduction wrapper completed successfully',
                         'CASE-05 zero-execution skip is explicit; no missing dependency interpreted as an implementation defect']
fake='SYNTHETIC_ONLY_'+'A9'*24
for path in (ROOT/'CASE-02').rglob('*.json'):
    if path.name=='source.json':continue
    assert fake not in path.read_text(),'Synthetic credential leaked into a log'
validation['checks'].append('Generated fake credential value absent from CASE-02 JSON logs')
git=command(['git','-C',str(ROOT),'rev-parse','--show-toplevel'])
assert git['exit_code']==128 and 'not a git repository' in git['stderr']
validation['repository_boundary']=git
validation['seal_policy']='No content writes after hashes are finalized; regular files 0444 and directories 0555. This is not a storage-level immutable flag.'
(ROOT/'validation.json').write_text(json.dumps(validation,indent=2)+'\n')

payload=[p for p in sorted(ROOT.rglob('*')) if p.is_file()]
assert not any(p.is_symlink() for p in ROOT.rglob('*'))
rows=[]
for path in payload:
    data=path.read_bytes()
    rows.append(dict(path=str(path.relative_to(ROOT)),bytes=len(data),sha256=hashlib.sha256(data).hexdigest()))
ledger_names=sorted([r['path'] for r in rows]+['ARTIFACTS.json'])
ledger_size=sum(64+2+len(name.encode())+1 for name in ledger_names)
inventory=dict(created_at_utc=utc(),files=rows,
    seal_metadata=dict(payload_files=len(rows),inventory_bytes=0,ledger_bytes=ledger_size,
                       inventory_hash='Recorded in SHA256SUMS.txt',ledger_hash='Returned in final response/tool finalization output',
                       self_reference_note='An integrity ledger cannot contain its own digest. The inventory does not recursively hash itself or the ledger.'))
while True:
    encoded=(json.dumps(inventory,indent=2,sort_keys=True)+'\n').encode()
    if len(encoded)==inventory['seal_metadata']['inventory_bytes']:break
    inventory['seal_metadata']['inventory_bytes']=len(encoded)
(ROOT/'ARTIFACTS.json').write_bytes(encoded)
digests={r['path']:r['sha256'] for r in rows}
digests['ARTIFACTS.json']=hashlib.sha256(encoded).hexdigest()
ledger=''.join(digests[name]+'  '+name+'\n' for name in ledger_names).encode()
assert len(ledger)==ledger_size
(ROOT/'SHA256SUMS.txt').write_bytes(ledger)
# Check content and inventory sizes before sealing. No further file creation follows.
for name,digest in digests.items():assert hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==digest
for row in rows:assert (ROOT/row['path']).stat().st_size==row['bytes']
for path in ROOT.rglob('*'):
    if path.is_file():path.chmod(0o444)
for path in sorted([p for p in ROOT.rglob('*') if p.is_dir()],key=lambda p:len(p.parts),reverse=True):path.chmod(0o555)
ROOT.chmod(0o555)
print(json.dumps(dict(finalized_at_utc=utc(),root=str(ROOT),finalized_files=len(rows)+2,
                     ledger_entries=len(digests),payload_bytes=sum(r['bytes'] for r in rows),
                     inventory_bytes=len(encoded),inventory_sha256=digests['ARTIFACTS.json'],
                     ledger_bytes=len(ledger),ledger_sha256=hashlib.sha256(ledger).hexdigest(),
                     missing_required_artifacts=[],content_hashes_verified=True,read_only=True),indent=2))
