"""Preserve fenced source verbatim; never execute this extraction output implicitly."""
import html
import json
import re
from pathlib import Path
from common import ROOT

for folder in sorted(ROOT.glob('CASE-*')):
    source = json.loads((folder/'source.json').read_text())
    manifest = []
    for item in [source, *source['replies']]:
        for number, match in enumerate(re.finditer(r'```([^\n]*)\n(.*?)```', item['body'], re.S), 1):
            language, body = match.groups()
            extension = {'python':'py','py':'py','bash':'sh'}.get(language.strip(),'txt')
            name = f'source-{item["id"]}-block-{number:02}.{extension}'
            (folder/name).write_text(body)
            manifest.append(dict(file=name, source_id=item['id'], author=item['agent_name'],
                                 language=language, transformation='None; exact fenced bytes from JSON body'))
    if folder.name == 'CASE-07':
        body = source['body'].split('class Solution:')[1].split('\n\nIs this')[0]
        body = 'class Solution:' + body
        body = html.unescape(body).replace('\xa0',' ')
        body = '\n'.join(line.rstrip() for line in body.splitlines()) + '\n'
        (folder/'original.py').write_text(body)
        manifest.append(dict(file='original.py',source_id=source['id'],author=source['agent_name'],
                             transformation='HTML entities decoded, NBSP converted to spaces, trailing spaces removed; code otherwise unchanged; imports supplied by harness'))
    (folder/'snippet-manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
