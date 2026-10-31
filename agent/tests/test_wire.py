"""Offline wire-level integration: a controlled local server, never a paid API."""
import json,subprocess,sys,tempfile,threading,unittest
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from agent import Agent,DeepSeekClient,MODEL
from test_blueprint import fixture,data,calls,done

class WireIntegration(unittest.TestCase):
    def test_http_tool_roundtrip_and_fixture_runtime(self):
        received=[];answers=iter([calls(fixture()),done('Controlled offline fixture; no DeepSeek call.')])
        class Handler(BaseHTTPRequestHandler):
            def do_POST(self):
                payload=json.loads(self.rfile.read(int(self.headers['Content-Length'])))
                received.append({'path':self.path,'auth':self.headers.get('Authorization'),'payload':payload})
                raw=json.dumps({'choices':[next(answers)],'usage':{'prompt_tokens':50,'completion_tokens':20,'total_tokens':70}}).encode()
                self.send_response(200);self.send_header('Content-Type','application/json');self.send_header('Content-Length',str(len(raw)));self.end_headers();self.wfile.write(raw)
            def log_message(self,*args):pass
        server=ThreadingHTTPServer(('127.0.0.1',0),Handler);worker=threading.Thread(target=server.serve_forever,daemon=True);worker.start()
        try:
            with tempfile.TemporaryDirectory() as f,patch('agent.ENDPOINT',f'http://127.0.0.1:{server.server_port}/chat/completions'):
                result=Agent(data(),Path(f)/'run',DeepSeekClient('offline-fixture-token',preflight=False)).run()
                self.assertEqual(result['status'],'ready_for_runtime_test',result['summary']);self.assertEqual(result['usage']['total_tokens'],140)
                self.assertEqual(len(received),2);self.assertEqual(received[0]['payload']['model'],MODEL)
                self.assertEqual(received[0]['auth'],'Bearer offline-fixture-token')
                messages=received[1]['payload']['messages'];tool_results=[m for m in messages if m['role']=='tool']
                self.assertEqual(len(tool_results),len(fixture()))
                process=subprocess.run([sys.executable,'-m','unittest','discover','-s','tests','-v'],cwd=Path(f)/'run/project',capture_output=True,text=True,timeout=15)
                self.assertEqual(process.returncode,0,process.stdout+process.stderr)
                self.assertIn('test_add',process.stderr)
        finally:
            server.shutdown();server.server_close();worker.join(timeout=2)

if __name__=='__main__':unittest.main()

