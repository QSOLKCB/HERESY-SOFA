"""Assemble the machine report from recorded evidence; does not rerun tests."""
import hashlib
import json
from pathlib import Path
from common import ROOT,utc

def read(path):return json.loads((ROOT/path).read_text())
def ref(path):
    data=(ROOT/path).read_bytes()
    return dict(path=path,bytes=len(data),sha256=hashlib.sha256(data).hexdigest())
claims=read('claims.json')
supplements={
 3:['CASE-03/bare-subclass-receipt.json'],
 4:['CASE-04/shell-controls-receipt.json','CASE-04/shell-controls-execution.json','CASE-04/mock-shell-receipt.json','CASE-04/mock-shell-execution.json'],
 6:['CASE-06/python311-receipt.json'],
 8:['CASE-08/state-space-receipt.json','CASE-08/state-space-execution.json']}
cases=[]
for c in claims:
    folder=f'CASE-{c["case"]:02}'
    source=read(folder+'/source.json')
    assert source['reply_count']==len(source['replies'])
    identities={s['id']:s['agent_name'] for s in [source,*source['replies']]}
    for claim in c['claims']:assert identities[claim['source_id']]==claim['author']
    receipt=read(folder+'/receipt.json')
    assert receipt['all_checks_passed']
    c.update(source=dict(post_id=source['id'],author=source['agent_name'],updated_at=source['updated_at'],
                         reply_count=source['reply_count'],identities=identities,snapshot=ref(folder+'/source.json')),
             execution=read(folder+'/execution.json'),results=receipt,
             evidence_files=[ref(str(p.relative_to(ROOT))) for p in sorted((ROOT/folder).iterdir()) if p.is_file()],
             supplemental_receipts=[ref(p) for p in supplements.get(c['case'],[])])
    cases.append(c)
report=dict(schema='CODEX-001-evidence-report-v1',mission='SOFA-HOT-008',examiner='CODEX-001',
    assembled_at_utc=utc(),seed=26051108,environment=read('environment.json'),
    additional_interpreters=read('extra-interpreters.json'),
    independence=dict(monicas_reports_read=False,monicas_code_used=False,other_agent_findings_consulted=False,
                      sofa_posts_read=8,sofa_replies_read=sum(c['source']['reply_count'] for c in cases),
                      verification_trails_excluded=True,post_content_treated_as_untrusted=True),
    boundaries=dict(dependency_installs=0,python_downloads=0,real_secret_reads=0,user_memory_reads=0,
                    real_webhook_requests=0,discord_api_requests=0,ia_api_requests=0,external_llm_requests=0,
                    sofa_writes=0,github_writes=0,network_access='Only authorized SOFA status and target reads; experiments use mocked APIs. Localhost socket binding was denied.'),
    labels=dict(EXECUTED='Observed locally with recorded runtime and inputs',INFERRED='Reasoned conclusion, not execution proof',
                NOT_TESTED='Specified execution was unavailable, prohibited or not performed',UNSUPPORTED='Claim exceeds available evidence'),
    case_classification_scope='An aggregate may flag a defect in one original/reply while another reply is correct; attribution is per claim.',
    cases=cases,harness_history=read('harness-history.json'),preflight=read('preflight.json'),
    finalization_attempts=[ref(str(p.relative_to(ROOT))) for p in sorted((ROOT/'finalization-attempts').glob('*')) if p.is_file()],
    summaries=dict(primary_checks=sum(len(c['results']['checks']) for c in cases),
                   supplemental_shell_mime_checks=38,finite_state_scenarios=1512,
                   openpyxl_execution_skipped=True,all_completed_primary_checks_passed=True,
                   passing_checks_mean='Expected observations matched, including intentional counterexamples; not a blanket endorsement of sources'),
    reproduction=dict(command='uv run --no-project --offline --no-managed-python --python /usr/bin/python3 python -B reproduce.py',
                      behavior='Creates a new /tmp directory; never writes to finalized evidence',
                      script=ref('reproduce.py')),
    missing_required_artifacts=[],
    unavailable_evidence=['Openpyxl-generated XLSX/XML and Excel visuals','Pyright execution','Exact mypy 2.3.1 execution',
                          'Real remote extraction/download/API observations (prohibited)','Real localhost HTTP transport (sandbox denied binding)'],
    finalization=dict(policy='Make files/directories read-only after writing manifest and ledger; do not edit after sealing',
                      inventory='ARTIFACTS.json contains payload hashes and byte sizes; its own byte size and the ledger byte size are recorded in its seal_metadata.',
                      ledger='SHA256SUMS.txt hashes all finalized regular files except itself, including ARTIFACTS.json; ledger SHA-256 is reported separately',
                      limitation='Not storage-level immutable or tamper-proof; hashes detect changes and read-only modes prevent accidental writes'))
(ROOT/'CODEX-001-REPORT.json').write_text(json.dumps(report,indent=2,sort_keys=True)+'\n')
print(json.dumps(dict(cases=len(cases),replies=report['independence']['sofa_replies_read'],primary_checks=report['summaries']['primary_checks'])))
