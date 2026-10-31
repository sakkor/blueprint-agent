"""Read source documents as data, derive a reviewable requirement catalog."""
from __future__ import annotations
import hashlib
import json
import re
from pathlib import Path

MAX_INPUT_BYTES = 250_000
PROFILE_ITEMS = [
 ('EMAIL-DESKTOP','Generated game has a native Windows desktop UI, launch entry point and executable build recipe','functional','Professor email dated 2026-10-22'),
 ('SF-INTRO','Introductory scene, main menu, and ending feedback','functional','Documentation / Executive Summary'),
 ('SF-PLAY','Start a fraction game; present questions and submit answers','functional','Views / UseCaseDiagram and SequenceDiagram1'),
 ('SF-SCORE','Calculate and display the score','functional','Views / ActivityDiagram and Game.viewScore'),
 ('SF-HELP','Display help instructions','functional','Views / UseCaseDiagram'),
 ('SF-ADMIN','Authorized administrator can update questions','functional','Views / SequenceDiagram2'),
 ('SF-STATE','Playing, Paused and GameOver transitions including resume','functional','Views / StateDiagram'),
 ('SF-MODEL','Game, Question, User and Admin entities with consistent associations','design','Views / ClassDiagram'),
 ('SF-SERVICES','Game, Question, User and Admin component boundaries and API interactions','design','Views / ComponentDiagram; Documentation / Architecture Overview'),
 ('SF-PERSIST','Persist game state and question data in PostgreSQL; document consistency and recovery','design','Documentation / Detailed Technical Design'),
 ('SF-SECURITY','Authentication, authorization, secrets and TLS design with negative tests','design','Documentation / Security Design'),
 ('SF-CONTRACTS','External OpenAPI and internal RPC contract consistent with source and schemas','design','Documentation / Interface design and Deliverables'),
 ('SF-DEPLOY','Container/deployment configuration aligned with the physical views','design','Views / DeploymentDiagram and ContainerDiagram'),
 ('SF-OPS','Observability, backup, recovery and availability verification plan','quality','Documentation / Operations, Observability and SRE'),
 ('SF-TRACE','Map requirements to implementation, tests and documented assumptions','design','Documentation / Traceability and How to review'),
 ('SF-STACK','Document component responsibilities, stack alternatives and chosen-stack rationale','design','Documentation / Detailed Technical Design and How to review'),
 ('SF-ROLLOUT','Document migration, compatibility and rollout steps','design','Documentation / Migration and Rollout'),
]

def _load(path):
    path = Path(path)
    if path.suffix.lower() != '.md' or not path.is_file():
        raise ValueError('Choose an existing Markdown (.md) file for each input.')
    raw = path.read_bytes()
    if len(raw) > MAX_INPUT_BYTES:
        raise ValueError('Each input must be 250 KB or smaller.')
    text = raw.decode('utf-8-sig')
    if not text.strip():
        raise ValueError(f'{path.name} is empty.')
    return {'name':path.name,'sha256':hashlib.sha256(raw).hexdigest(), 'text':text,
            'headings':re.findall(r'^#{1,6}\s+(.+)$',text,re.M)}

def analyze(document, views):
    doc, view = _load(document), _load(views)
    blocks = re.findall(r'```plantuml[^\n]*\n(.*?)```', view['text'], re.S | re.I)
    if not blocks:
        raise ValueError('The views file has no fenced PlantUML blocks. Select the original .md file, not escaped chat text.')
    diagrams=[]
    for i, source in enumerate(blocks,1):
        match=re.search(r'@startuml\s*([^\r\n]*)',source)
        if not match or '@enduml' not in source:
            raise ValueError(f'PlantUML block {i} is missing @startuml or @enduml.')
        diagrams.append({'id':f'D{i:02d}','name':match.group(1).strip() or f'Diagram{i}', 'source':source.strip()})
    ids=sorted(set(re.findall(r'\b(?:FR|NFR|ASR)-\d+\b',doc['text'])))
    requirements=[]
    for rid in ids:
        row=re.search(r'^\|\s*'+re.escape(rid)+r'\s*\|\s*([^|]+)',doc['text'],re.M)
        inline=re.search(re.escape(rid)+r'\s*\(([^)]+)\)',doc['text'])
        description=row.group(1).strip() if row else inline.group(1).strip().capitalize() if inline else rid+' (see source references)'
        requirements.append({'id':rid,'description':description, 'kind':'functional' if rid.startswith('FR-') else 'quality',
                             'origin':'Original requirement ID in documentation'})
    profile='space-fractions' if 'space fractions' in doc['text'].lower() and 'Game' in view['text'] else 'generic'
    if profile=='space-fractions':
        requirements.extend({'id':rid,'description':desc,'kind':kind,'origin':origin+' (derived checklist ID)'} for rid,desc,kind,origin in PROFILE_ITEMS)
    else:
        usecases=list(dict.fromkeys(re.findall(r'usecase\s+"([^"]+)"',view['text'])))
        requirements.extend({'id':f'UML-{i:02d}','description':title,'kind':'functional','origin':'Derived from UML use case'} for i,title in enumerate(usecases,1))
    deliverables=[]
    for block in re.findall(r'```markdown\s*\n(.*?)```',doc['text'],re.S|re.I):
        for line in block.splitlines():
            name=line.strip().strip('`')
            if re.fullmatch(r'[A-Za-z0-9_./-]+\.[A-Za-z0-9]+',name) and '..' not in name.split('/') and not name.startswith('/'):
                deliverables.append(name)
    deliverables.extend(re.findall(r'\bsql/[A-Za-z0-9_-]+\.sql\b',doc['text']))
    if profile=='space-fractions':deliverables.extend(['desktop.py','desktop-manifest.json','build_game.ps1'])
    findings=[]
    if profile=='space-fractions':
        findings=[
          'Professor email dated 2026-10-22 requires a desktop game rather than a web game. Preserve the originals and explicitly reconcile this later delivery constraint.',
          '99.99% uptime implies a 0.01% unavailability budget, but the document says 1%; record the resolution as an assumption.',
          'No separate complete requirements baseline is supplied. Derived SF-* checklist IDs are not original professor-assigned IDs.',
          'Admin exists in UML but is omitted from part of the written component overview; reconcile component coverage.',
          'Object/collaboration blocks use sequence-style participants; preserve originals and explain their interpretation.',
          'The recommended infrastructure is extensive. Implement specified boundaries and explicitly document any unsupported or deferred infrastructure.',
          'Availability, throughput, security and recovery claims need runtime evidence; static checks cannot certify them.'
        ]
    return {'schema_version':3,'profile':profile,'documentation':doc,'views':view,'diagrams':diagrams,
            'evaluation_constraints':{'source':'Professor email 2026-10-22, supplied by user','generated_game':'Native Windows desktop UI','token_cost_target_usd':1.0,'submission':'Source repository plus YouTube video of agent and generated desktop game'},
            'requirements':requirements,'required_artifacts':sorted(set(deliverables)), 'findings':findings}

def write_snapshot(data, folder):
    folder=Path(folder); folder.mkdir(parents=True,exist_ok=True)
    for key,name in [('documentation','Architecture_Documentation.md'),('views','Architecture_View.md')]:
        (folder/name).write_text(data[key]['text'],encoding='utf-8')
    (folder/'input.json').write_text(json.dumps(data,indent=2,ensure_ascii=False),encoding='utf-8')
    diagrams=folder/'diagrams'; diagrams.mkdir(exist_ok=True)
    for diagram in data['diagrams']:
        name=re.sub(r'[^A-Za-z0-9_-]','_',diagram['name'])[:70]
        (diagrams/(diagram['id']+'-'+name+'.puml')).write_text(diagram['source'],encoding='utf-8')
