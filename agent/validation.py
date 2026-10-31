"""Scoped project files and deterministic structural checks. Never execute generated code."""
from __future__ import annotations
import ast, csv, hashlib, io, json, os, re, stat, tempfile
from pathlib import Path, PureWindowsPath
import yaml

MAX_FILE=250_000
MAX_FILES=220
MAX_PROJECT=12_000_000
SOURCE_EXT={'.py','.js','.mjs','.cjs','.ts','.tsx','.jsx','.html','.rs','.go','.java','.cs'}

class UniqueLoader(yaml.SafeLoader):
    pass

def _mapping(loader,node,deep=False):
    result={}
    for key_node,value_node in node.value:
        key=loader.construct_object(key_node,deep=deep)
        if key in result:
            raise ValueError(f'Duplicate YAML key: {key}')
        result[key]=loader.construct_object(value_node,deep=deep)
    return result
UniqueLoader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG,_mapping)

def _linked(path):
    return path.is_symlink() or (path.exists() and bool(getattr(path.stat(follow_symlinks=False),'st_file_attributes',0)&stat.FILE_ATTRIBUTE_REPARSE_POINT))

class Workspace:
    def __init__(self,root,requirements=None,artifacts=None,secret=''):
        self.root=Path(root).absolute()
        self.root.mkdir(parents=True,exist_ok=True)
        if any(_linked(p) for p in [self.root,*self.root.parents]):
            raise ValueError('Project path cannot contain links or junctions.')
        self.root=self.root.resolve()
        self.requirements=requirements or []
        self.artifacts=artifacts or []
        self.secret=secret
        self.revision=0

    def path(self,value):
        if not isinstance(value,str) or not value or len(value)>180 or re.search(r'[\\:*?"<>|\x00-\x1f]',value):
            raise ValueError('Use a relative project path with forward slashes, at most 180 characters.')
        parts=value.split('/')
        if any(p in ('','.','..') or p.endswith((' ','.')) or PureWindowsPath(p).is_reserved() for p in parts):
            raise ValueError('Unsafe or reserved path segment.')
        target=self.root.joinpath(*parts)
        for p in [target,*target.parents]:
            if p==self.root: break
            if _linked(p): raise ValueError('Links and junctions are not allowed.')
        if not target.resolve().is_relative_to(self.root): raise ValueError('Path leaves the project.')
        return target

    def files(self):
        result=[]
        for folder,dirs,files in os.walk(self.root,followlinks=False):
            dirs[:]=[d for d in dirs if not _linked(Path(folder)/d)]
            for name in files:
                p=Path(folder)/name
                if not _linked(p): result.append(p.relative_to(self.root).as_posix())
        return sorted(result)

    def write(self,path,content):
        if not isinstance(content,str): raise ValueError('Content must be a string.')
        raw=content.encode('utf-8')
        if len(raw)>MAX_FILE: raise ValueError('File exceeds 250 KB; split it into modules.')
        if self.secret and self.secret in content: raise ValueError('Do not place the API credential in project files.')
        target=self.path(path); files=self.files()
        if path not in files and len(files)>=MAX_FILES: raise ValueError('Project file count limit reached.')
        total=sum(self.path(p).stat().st_size for p in files)
        old=target.stat().st_size if target.is_file() else 0
        if total-old+len(raw)>MAX_PROJECT: raise ValueError('Project size limit reached.')
        target.parent.mkdir(parents=True,exist_ok=True)
        fd,temporary=tempfile.mkstemp(prefix='.blueprint-',dir=target.parent)
        try:
            with os.fdopen(fd,'wb') as out: out.write(raw)
            os.replace(temporary,target)
        finally:
            if os.path.exists(temporary): os.unlink(temporary)
        self.revision+=1
        return {'written':path,'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()}

    def read(self,path,start_line=1,max_lines=160):
        if type(start_line)!=int or type(max_lines)!=int or start_line<1 or not 1<=max_lines<=500:
            raise ValueError('start_line must be positive; max_lines must be 1–500.')
        p=self.path(path)
        if p.stat().st_size>MAX_FILE: raise ValueError('File exceeds read limit.')
        lines=p.read_text(encoding='utf-8-sig').splitlines()
        return {'path':path,'start_line':start_line,'total_lines':len(lines),
                'content':'\n'.join(lines[start_line-1:start_line-1+max_lines])}

    def validate(self):
        files=self.files(); errors=[]; warnings=[]; parsed={}; coverage=[]
        required=['README.md','PLAN.md','ASSUMPTIONS.md','implementation-map.json',*self.artifacts]
        for name in sorted(set(required)):
            try:
                p=self.path(name)
                if not p.is_file() or p.stat().st_size==0: errors.append('Missing or empty artifact: '+name)
            except ValueError as exc: errors.append('Invalid artifact path: '+name)
        if not any(p in files for p in ['requirements.txt','package.json','pyproject.toml']): errors.append('Missing root dependency manifest.')
        source=[p for p in files if Path(p).suffix in SOURCE_EXT and not p.startswith(('tests/','test/'))]
        tests=[p for p in files if (p.startswith(('tests/','test/')) or re.search(r'\.(test|spec)\.',p)) and Path(p).suffix in SOURCE_EXT- {'.html'}]
        if not source: errors.append('Missing application source files.')
        if not tests: errors.append('Missing test source files.')
        for name in files:
            p=self.path(name)
            if p.stat().st_size>MAX_FILE: errors.append(name+': exceeds file-size limit.'); continue
            try:
                text=p.read_text(encoding='utf-8-sig')
                if Path(name).suffix=='.py': ast.parse(text,filename=name)
                elif Path(name).suffix=='.json': parsed[name]=json.loads(text)
                elif Path(name).suffix in ('.yaml','.yml'):
                    parsed[name]=list(yaml.load_all(text,Loader=UniqueLoader))
                if name in source+tests and not text.strip(): errors.append(name+': empty source/test file.')
                if name in source and re.search(r'\bNotImplementedError\b|TODO\s*:\s*implement',text): warnings.append(name+': possible implementation stub; review required.')
            except (SyntaxError,ValueError,UnicodeError,yaml.YAMLError,TypeError) as exc:
                errors.append(name+': '+str(exc)[:350])
        if 'package.json' in parsed:
            pkg=parsed['package.json']
            if not isinstance(pkg,dict): errors.append('package.json must be an object.')
            elif not isinstance(pkg.get('scripts'),dict) or not pkg['scripts'].get('test'):
                errors.append('package.json must define a test script.')
        for name in ('openapi.yaml','openapi.yml','openapi.json'):
            if name in parsed:
                doc=parsed[name][0] if isinstance(parsed[name],list) and parsed[name] else parsed[name]
                if not isinstance(doc,dict) or not str(doc.get('openapi','')).startswith('3.') or not isinstance(doc.get('info'),dict) or not isinstance(doc.get('paths'),dict) or not doc.get('paths'):
                    errors.append(name+': requires OpenAPI 3.x, info and nonempty paths.')
        for name,obj in parsed.items():
            if name.startswith('k8s/') and isinstance(obj,list):
                for resource in obj:
                    if not isinstance(resource,dict) or not all(k in resource for k in ('apiVersion','kind','metadata')):
                        errors.append(name+': Kubernetes resource is missing apiVersion/kind/metadata.')
                    elif resource.get('kind')=='Deployment':
                        try:
                            spec=resource['spec']; selector=spec['selector']['matchLabels']; labels=spec['template']['metadata']['labels']
                            if not selector or any(labels.get(k)!=v for k,v in selector.items()): raise ValueError('selector mismatch')
                            containers=spec['template']['spec']['containers']
                            if not containers or not all(c.get('name') and c.get('image') for c in containers): raise ValueError('missing containers')
                        except (KeyError,TypeError,ValueError,AttributeError): errors.append(name+': invalid Deployment selector/template/containers.')
        if 'internal.proto' in files:
            proto=self.path('internal.proto').read_text(encoding='utf-8-sig')
            if not all(re.search(pattern,proto) for pattern in (r'syntax\s*=\s*"proto3"',r'\bservice\s+\w+',r'\brpc\s+\w+',r'\bmessage\s+\w+')):
                errors.append('internal.proto needs proto3 syntax, service, RPC and messages.')
        for name in self.artifacts:
            if name.endswith('.sql') and name in files and not re.search(r'\bCREATE\s+TABLE\b',self.path(name).read_text(encoding='utf-8-sig'),re.I):
                errors.append(name+': expected a CREATE TABLE schema.')
        if any(r['id']=='EMAIL-DESKTOP' for r in self.requirements):
            manifest=parsed.get('desktop-manifest.json')
            if not isinstance(manifest,dict) or manifest.get('framework')!='tkinter' or manifest.get('entry_point')!='desktop.py' or manifest.get('build_script')!='build_game.ps1':
                errors.append('desktop-manifest.json must declare tkinter, desktop.py and build_game.ps1.')
            if 'desktop.py' in files:
                try:
                    tree=ast.parse(self.path('desktop.py').read_text(encoding='utf-8-sig'))
                    aliases=set();constructors=set();browser_import=False
                    for node in ast.walk(tree):
                        if isinstance(node,ast.Import):
                            for alias in node.names:
                                if alias.name=='tkinter':aliases.add(alias.asname or alias.name)
                                if alias.name.split('.')[0] in ('webbrowser','webview','streamlit'):browser_import=True
                        elif isinstance(node,ast.ImportFrom):
                            if node.module=='tkinter':constructors.update(a.asname or a.name for a in node.names if a.name=='Tk')
                            if (node.module or '').split('.')[0] in ('webbrowser','webview','streamlit'):browser_import=True
                    calls=[n.func for n in ast.walk(tree) if isinstance(n,ast.Call)]
                    window=any((isinstance(f,ast.Name) and f.id in constructors) or (isinstance(f,ast.Attribute) and isinstance(f.value,ast.Name) and f.value.id in aliases and f.attr=='Tk') for f in calls)
                    loop=any(isinstance(f,ast.Attribute) and f.attr=='mainloop' for f in calls)
                    if not window or not loop or browser_import:errors.append('desktop.py must construct a native tkinter.Tk window and call mainloop; browser-launch/webview substitutes are not accepted.')
                except SyntaxError:pass  # Already reported by the general Python parser.
            if 'build_game.ps1' in files:
                script=self.path('build_game.ps1').read_text(encoding='utf-8-sig').lower()
                if not all(part in script for part in ('pyinstaller','--onefile','--windowed','desktop.py')) or not ('unittest' in script or 'pytest' in script):
                    errors.append('build_game.ps1 must run tests and package desktop.py with PyInstaller --onefile --windowed.')
        mapping=parsed.get('implementation-map.json',{})
        rows=mapping.get('requirements',[]) if isinstance(mapping,dict) else []
        if not isinstance(rows,list): rows=[]; errors.append('implementation-map.json requirements must be an array.')
        indexed={}
        for row in rows:
            if not isinstance(row,dict) or not isinstance(row.get('id'),str): errors.append('Invalid implementation-map entry.'); continue
            if row['id'] in indexed: errors.append('Duplicate implementation-map ID: '+row['id'])
            indexed[row['id']]=row
        for req in self.requirements:
            rid=req['id']; row=indexed.get(rid,{}); paths=row.get('files',[]); test_paths=row.get('tests',[])
            row_errors=[]
            if row.get('status') not in ('implemented','partial','deferred'): row_errors.append('missing/invalid status')
            if not isinstance(paths,list) or not paths or not all(isinstance(p,str) and p in files for p in paths): row_errors.append('missing implementation evidence files')
            if not isinstance(test_paths,list) or not all(isinstance(p,str) and p in tests for p in test_paths): row_errors.append('invalid test references')
            elif req['kind']=='functional' and not test_paths: row_errors.append('functional requirement needs a referenced test')
            if not isinstance(row.get('notes'),str) or not row.get('notes','').strip(): row_errors.append('missing rationale/verification notes')
            if row_errors: errors.append(rid+': '+', '.join(row_errors))
            elif row.get('status')!='implemented': warnings.append(rid+': model reports '+row['status'])
            coverage.append({'id':rid,'description':req['description'],'kind':req['kind'],
                             'mapped':not row_errors,'reported_status':row.get('status','missing'),
                             'files':paths if isinstance(paths,list) else [],'tests':test_paths if isinstance(test_paths,list) else [],
                             'runtime_verified':False})
        if 'traceability_matrix.csv' in files:
            try:
                rows=list(csv.DictReader(io.StringIO(self.path('traceability_matrix.csv').read_text(encoding='utf-8-sig'))))
                csv_ids={str(row.get('Requirement ID',row.get('requirement_id',''))).strip() for row in rows}
                missing={r['id'] for r in self.requirements}-csv_ids
                if missing: errors.append('traceability_matrix.csv missing IDs: '+', '.join(sorted(missing)))
            except (ValueError,csv.Error) as exc: errors.append('Invalid traceability CSV: '+str(exc))
        return {'structural_ok':not errors,'errors':errors,'warnings':warnings,'files':files,'coverage':coverage,
                'mapped_count':sum(r['mapped'] for r in coverage),'requirement_count':len(self.requirements),
                'tests_executed':False,'scope':'Artifact presence, Python/JSON/YAML parsing, selected contract/deployment structure and evidence references. Runtime behavior, full OpenAPI/SQL/protobuf conformance and production qualities are not verified.'}
