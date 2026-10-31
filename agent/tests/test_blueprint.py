import copy, hashlib, io, json, tempfile, threading, unittest, urllib.error
from pathlib import Path
from unittest.mock import patch
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from blueprint import analyze,write_snapshot
from validation import Workspace
from agent import Agent,DeepSeekClient,MODEL,ENDPOINT,NoRedirect

ROOT=Path(__file__).resolve().parents[1]
REQ=[{'id':'FR-1','description':'Answer a fraction question','kind':'functional'}]

def fixture():
    return {'README.md':'Run python main.py; test with python -m unittest discover -s tests.\n',
      'PLAN.md':'Implement fraction addition and check correctness.','ASSUMPTIONS.md':'Offline test fixture, not DeepSeek-generated.',
      'requirements.txt':'# Standard library only\n','main.py':'from fractions import Fraction\ndef add(a,b): return str(Fraction(a)+Fraction(b))\n',
      'tests/test_main.py':'import unittest\nfrom main import add\nclass TestMath(unittest.TestCase):\n def test_add(self): self.assertEqual(add("1/2","1/3"),"5/6")\n',
      'implementation-map.json':json.dumps({'requirements':[{'id':'FR-1','status':'implemented','files':['main.py'],'tests':['tests/test_main.py'],'notes':'Check the rational arithmetic with unittest.'}]}),
      'traceability_matrix.csv':'Requirement ID,Short Text,Diagram(s),Component(s),Artifact filename(s),Rationale\nFR-1,Answer,D01,Game,main.py,Rational arithmetic\n'}

def data():
    return {'requirements':copy.deepcopy(REQ),'required_artifacts':['traceability_matrix.csv'],'findings':[],
      'documentation':{'text':'Test specification','sha256':'fixture-doc'},'views':{'text':'Test view','sha256':'fixture-view'},'diagrams':[]}

def calls(files):
    return {'finish_reason':'tool_calls','message':{'content':None,'tool_calls':[{'id':str(i),'type':'function','function':{'name':'write_file','arguments':json.dumps({'path':p,'content':c})}} for i,(p,c) in enumerate(files.items())]}}

def done(text='Files ready; tests not run.'):
    return {'finish_reason':'stop','message':{'content':text}}

class FakeClient:
    key='unit-test-secret-not-real'
    usage_missing=False
    def __init__(self,answers):self.answers=iter(answers);self.usage={'prompt_tokens':0,'completion_tokens':0,'total_tokens':0};self.responses=0;self.messages=[]
    def complete(self,messages):
        self.messages.append(copy.deepcopy(messages));self.responses+=1;self.usage['total_tokens']+=100
        value=next(self.answers)
        if isinstance(value,Exception):raise value
        return value

class Inputs(unittest.TestCase):
    def test_original_catalog(self):
        d=analyze(ROOT/'examples/Architecture_Documentation.md',ROOT/'examples/Architecture_View.md')
        self.assertEqual(len(d['diagrams']),13);self.assertEqual(len(d['requirements']),21)
        self.assertEqual({r['id'] for r in d['requirements'] if r['id'].startswith(('FR-','NFR-','ASR-'))},{'FR-1','NFR-1','ASR-1','ASR-2'})
        self.assertIn('sql/question_ddl.sql',d['required_artifacts']);self.assertEqual(len(d['required_artifacts']),10)
        self.assertEqual(d['documentation']['sha256'],hashlib.sha256((ROOT/'examples/Architecture_Documentation.md').read_bytes()).hexdigest())
    def test_generic_use_case(self):
        with tempfile.TemporaryDirectory() as f:
            p=Path(f);(p/'doc.md').write_text('# Notes\nA catalog');(p/'view.md').write_text('```plantuml\n@startuml\nusecase "Browse catalog"\n@enduml\n```')
            d=analyze(p/'doc.md',p/'view.md');self.assertEqual(d['requirements'][0]['description'],'Browse catalog')
    def test_empty_and_malformed_inputs(self):
        with tempfile.TemporaryDirectory() as f:
            p=Path(f);(p/'d.md').write_text('');(p/'v.md').write_text('invalid')
            with self.assertRaises(ValueError):analyze(p/'d.md',p/'v.md')
            (p/'d.md').write_text('doc')
            with self.assertRaises(ValueError):analyze(p/'d.md',p/'v.md')
            (p/'v.md').write_text('```plantuml\n@startuml\n```')
            with self.assertRaises(ValueError):analyze(p/'d.md',p/'v.md')
    def test_snapshot_retains_sources_and_diagrams(self):
        d=analyze(ROOT/'examples/Architecture_Documentation.md',ROOT/'examples/Architecture_View.md')
        with tempfile.TemporaryDirectory() as f:
            write_snapshot(d,f);self.assertEqual(len(list((Path(f)/'diagrams').glob('*.puml'))),13)
            self.assertEqual(json.loads((Path(f)/'input.json').read_text())['documentation']['text'],d['documentation']['text'])

class Files(unittest.TestCase):
    def setUp(self):self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.w=Workspace(self.tmp.name,REQ,['traceability_matrix.csv'])
    def populate(self):
        for p,c in fixture().items():self.w.write(p,c)
    def test_traversal_reserved_and_absolute_denied(self):
        for p in ['../oops','/absolute','C:/temp/oops','a/../b','a\\b','NUL.txt','CON','a//b','file:stream','a.','a /b','./test','a\x00b']:
            with self.subTest(p=p),self.assertRaises(ValueError):self.w.write(p,'no')
    def test_size_limit_and_key_rejection(self):
        with self.assertRaises(ValueError):self.w.write('large.txt','x'*250001)
        self.w.secret='test-secret'
        with self.assertRaises(ValueError):self.w.write('key.txt','test-secret')
    def test_atomic_replacement_and_bounded_read(self):
        self.w.write('dir/a.txt','old');self.w.write('dir/a.txt','one\ntwo\nthree')
        self.assertEqual(self.w.read('dir/a.txt',2,1)['content'],'two');self.assertEqual(self.w.files(),['dir/a.txt'])
        with self.assertRaises(ValueError):self.w.read('dir/a.txt',0,1)
        with self.assertRaises(ValueError):self.w.read('dir/a.txt',1,501)
    def test_complete_fixture_is_structurally_valid(self):
        self.populate();r=self.w.validate();self.assertTrue(r['structural_ok'],r['errors']);self.assertFalse(r['tests_executed']);self.assertEqual(r['mapped_count'],1)
    def test_missing_artifacts(self):
        self.assertFalse(self.w.validate()['structural_ok'])
    def test_syntax_errors(self):
        self.populate()
        for p,c in [('main.py','def broken('),('bad.json','{'),('bad.yaml','a: [')]:self.w.write(p,c)
        errors=' '.join(self.w.validate()['errors'])
        for name in ['main.py','bad.json','bad.yaml']:self.assertIn(name,errors)
    def test_yaml_duplicate_and_unsafe_constructor(self):
        self.populate();self.w.write('dup.yaml','a: 1\na: 2');self.w.write('unsafe.yaml','!!python/object/apply:os.system [echo unsafe]')
        errors=' '.join(self.w.validate()['errors']);self.assertIn('Duplicate YAML',errors);self.assertIn('unsafe.yaml',errors)
    def test_evidence_requires_real_test_paths(self):
        self.populate();self.w.write('implementation-map.json',json.dumps({'requirements':[{'id':'FR-1','status':'implemented','files':['missing.py'],'tests':['README.md'],'notes':'claim'}]}))
        r=self.w.validate();self.assertFalse(r['structural_ok']);self.assertFalse(r['coverage'][0]['mapped'])
    def test_partial_claim_remains_warning(self):
        self.populate();self.w.write('implementation-map.json',fixture()['implementation-map.json'].replace('implemented','partial'))
        r=self.w.validate();self.assertTrue(r['structural_ok']);self.assertTrue(r['warnings']);self.assertFalse(r['coverage'][0]['runtime_verified'])
    def test_csv_must_cover_requirements(self):
        self.populate();self.w.write('traceability_matrix.csv','Requirement ID\nOTHER\n');self.assertIn('missing IDs',' '.join(self.w.validate()['errors']))
    def test_contract_and_deployment_checks(self):
        self.populate();self.w.artifacts+=['openapi.yaml','internal.proto','sql/game.sql','k8s/app.yaml']
        for p,c in {'openapi.yaml':'openapi: 3.0.3\ninfo: {title: Fixture, version: 1}\npaths: {/play: {get: {responses: {"200": {description: OK}}}}}',
                    'internal.proto':'syntax = "proto3"; message Request {} message Response {} service Game { rpc Play(Request) returns (Response); }',
                    'sql/game.sql':'CREATE TABLE games(id INTEGER PRIMARY KEY);',
                    'k8s/app.yaml':'apiVersion: apps/v1\nkind: Deployment\nmetadata: {name: game}\nspec:\n  selector: {matchLabels: {app: game}}\n  template:\n    metadata: {labels: {app: game}}\n    spec: {containers: [{name: game, image: game:1}]}\n'}.items():self.w.write(p,c)
        self.assertTrue(self.w.validate()['structural_ok'],self.w.validate()['errors'])
        self.w.write('openapi.yaml','openapi: 2.0\npaths: {}');self.w.write('internal.proto','empty');self.w.write('sql/game.sql','-- no schema');self.w.write('k8s/app.yaml','apiVersion: apps/v1\nkind: Deployment\nmetadata: {}\nspec: {}')
        self.assertGreaterEqual(len(self.w.validate()['errors']),4)
    def test_node_manifest_requires_test_command(self):
        self.populate();self.w.write('package.json','{"scripts":{}}');self.assertIn('test script',' '.join(self.w.validate()['errors']))

class Loop(unittest.TestCase):
    def setUp(self):self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.path=Path(self.tmp.name)/'run'
    def run_client(self,answers,**kwargs):
        client=FakeClient(answers);runner=Agent(data(),self.path,client,**kwargs);return runner.run(),client
    def test_tool_result_pairing_and_success(self):
        r,c=self.run_client([calls(fixture()),done()]);self.assertEqual(r['status'],'ready_for_runtime_test');self.assertFalse(r['validation']['tests_executed'])
        m=c.messages[1];assistant=next(x for x in m if x['role']=='assistant');results=[x for x in m if x['role']=='tool']
        self.assertEqual([x['id'] for x in assistant['tool_calls']],[x['tool_call_id'] for x in results])
        self.assertTrue((self.path/'report.html').exists())
    def test_early_completion_is_repaired(self):
        r,c=self.run_client([done('finished'),calls(fixture()),done()]);self.assertEqual(r['status'],'ready_for_runtime_test')
        self.assertIn('Completion rejected',c.messages[1][-1]['content'])
    def test_tool_error_returns_to_model(self):
        bad=calls({'../outside.py':'x'})
        r,c=self.run_client([bad,calls(fixture()),done()]);self.assertEqual(r['status'],'ready_for_runtime_test')
        self.assertIn('error',c.messages[1][-1]['content']);self.assertFalse((self.path.parent/'outside.py').exists())
    def test_duplicate_calls_rejected_before_write(self):
        value=calls({'a.py':'x','b.py':'y'});value['message']['tool_calls'][1]['id']='0'
        r,c=self.run_client([value]);self.assertEqual(r['status'],'failed');self.assertFalse((self.path/'project/a.py').exists())
    def test_truncated_calls_never_execute(self):
        value=calls({'a.py':'x'});value['finish_reason']='length'
        r,c=self.run_client([value,value,value]);self.assertEqual(r['status'],'failed');self.assertFalse((self.path/'project/a.py').exists())
    def test_stop_preserves_report(self):
        stop=threading.Event();stop.set();r,c=self.run_client([],stop=stop);self.assertEqual(r['status'],'cancelled');self.assertEqual(c.responses,0)
    def test_turn_budget(self):
        r,c=self.run_client([calls(fixture())],max_turns=1);self.assertEqual(r['status'],'incomplete')
    def test_token_budget(self):
        client=FakeClient([]);client.usage['total_tokens']=1000
        r=Agent(data(),self.path,client,token_budget=1000).run();self.assertEqual(r['status'],'budget_limit');self.assertEqual(client.responses,0)
    def test_secret_redacted_and_html_escaped(self):
        r,c=self.run_client([calls(fixture()),done('<script>alert(1)</script>'+FakeClient.key)])
        for path in self.path.glob('*'):
            if path.is_file():self.assertNotIn(FakeClient.key,path.read_text(encoding='utf-8'))
        page=(self.path/'report.html').read_text();self.assertNotIn('<script>',page);self.assertIn('&lt;script&gt;',page)
    def test_existing_destination_not_overwritten(self):
        self.path.mkdir();(self.path/'keep.txt').write_text('keep')
        with self.assertRaises(FileExistsError):self.run_client([])
        self.assertEqual((self.path/'keep.txt').read_text(),'keep')
    def test_provider_failure_is_reported(self):
        r,c=self.run_client([RuntimeError('Provider failed')]);self.assertEqual(r['status'],'failed');self.assertIn('Provider failed',r['summary'])

class Client(unittest.TestCase):
    def test_request_contract_and_usage(self):
        response={'choices':[done()],'usage':{'prompt_tokens':12,'completion_tokens':8,'total_tokens':20}}
        with patch('agent.urllib.request.build_opener') as factory:
            factory.return_value.open.return_value.__enter__.return_value.read.return_value=json.dumps(response).encode()
            client=DeepSeekClient('test-key',preflight=False);client.complete([{'role':'user','content':'fixture'}])
            request=factory.return_value.open.call_args.args[0];payload=json.loads(request.data)
            self.assertEqual(request.full_url,ENDPOINT);self.assertEqual(payload['model'],MODEL);self.assertEqual(payload['thinking'],{'type':'disabled'});self.assertEqual(len(payload['tools']),5);self.assertEqual(client.usage['total_tokens'],20)
    def test_auth_error_does_not_echo_body(self):
        with patch('agent.urllib.request.build_opener') as factory:
            factory.return_value.open.side_effect=urllib.error.HTTPError(ENDPOINT,401,'secret body',{},None)
            with self.assertRaisesRegex(RuntimeError,'Invalid API key'):DeepSeekClient('test',preflight=False).complete([])
            self.assertEqual(factory.return_value.open.call_count,1)
    def test_failed_request_is_not_retried(self):
        stop=threading.Event()
        with patch.object(stop,'wait',return_value=False),patch('agent.urllib.request.build_opener') as factory:
            factory.return_value.open.side_effect=urllib.error.HTTPError(ENDPOINT,429,'rate',{},None)
            with self.assertRaisesRegex(RuntimeError,'429'):DeepSeekClient('test',stop,preflight=False).complete([])
            self.assertEqual(factory.return_value.open.call_count,1)
    def test_missing_usage_marked(self):
        with patch('agent.urllib.request.build_opener') as factory:
            factory.return_value.open.return_value.__enter__.return_value.read.return_value=json.dumps({'choices':[done()]}).encode()
            client=DeepSeekClient('test',preflight=False)
            from cost_control import CostUncertain
            with self.assertRaises(CostUncertain):client.complete([])
            self.assertTrue(client.usage_missing)
    def test_redirect_disabled(self):self.assertIsNone(NoRedirect().redirect_request(None,None,302,'',{},'https://example.com'))

if __name__=='__main__':unittest.main()
