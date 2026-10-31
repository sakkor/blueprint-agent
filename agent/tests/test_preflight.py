import json,socket,tempfile,unittest,urllib.error
from pathlib import Path
from unittest.mock import patch
from agent import DeepSeekClient,Agent,MODEL,connection_hint
from test_blueprint import FakeClient,data,done,calls,fixture

class Response:
    def __init__(self,obj):self.raw=json.dumps(obj).encode()
    def __enter__(self):return self
    def __exit__(self,*args):pass
    def read(self,*args):return self.raw

class Preflight(unittest.TestCase):
    def test_tls_context_initializes_with_verification(self):
        import ssl
        context=ssl.create_default_context()
        self.assertTrue(context.check_hostname)
        self.assertEqual(context.verify_mode,ssl.CERT_REQUIRED)

    def test_metadata_only_no_tokens_no_reservation(self):
        with patch('agent.urllib.request.build_opener') as factory:
            factory.return_value.open.side_effect=[Response({'data':[{'id':MODEL}]}),Response({'is_available':True})]
            client=DeepSeekClient('offline-key');text=client.check_connection()
            requests=[c.args[0] for c in factory.return_value.open.call_args_list]
            self.assertEqual([r.full_url for r in requests],['https://api.deepseek.com/models','https://api.deepseek.com/user/balance'])
            self.assertTrue(all(r.get_method()=='GET' and r.data is None for r in requests))
            self.assertTrue(client.preflight_ok);self.assertEqual(client.cost.state['attempts'],0)
            self.assertEqual(client.usage['total_tokens'],0)
    def test_invalid_key_blocks_generation_without_reservation(self):
        with patch('agent.urllib.request.build_opener') as factory:
            factory.return_value.open.side_effect=urllib.error.HTTPError('https://api.deepseek.com/models',401,'secret',{},None)
            client=DeepSeekClient('offline-key')
            with self.assertRaisesRegex(RuntimeError,'Invalid official API key'):client.complete([])
            self.assertEqual(factory.return_value.open.call_count,1);self.assertEqual(client.cost.state['attempts'],0)
    def test_missing_model_blocks_generation(self):
        with patch('agent.urllib.request.build_opener') as factory:
            factory.return_value.open.return_value=Response({'data':[{'id':'different'}]})
            client=DeepSeekClient('offline-key')
            with self.assertRaisesRegex(RuntimeError,'unavailable'):client.complete([])
            self.assertEqual(factory.return_value.open.call_count,1);self.assertEqual(client.cost.state['attempts'],0)
    def test_empty_balance_blocks_generation(self):
        with patch('agent.urllib.request.build_opener') as factory:
            factory.return_value.open.side_effect=[Response({'data':[{'id':MODEL}]}),Response({'is_available':False})]
            client=DeepSeekClient('offline-key')
            with self.assertRaisesRegex(RuntimeError,'no available API balance'):client.complete([])
            self.assertEqual(client.cost.state['attempts'],0)
    def test_metadata_then_single_generation_request(self):
        with patch('agent.urllib.request.build_opener') as factory:
            factory.return_value.open.side_effect=[Response({'data':[{'id':MODEL}]}),Response({'is_available':True}),Response({'choices':[done()],'usage':{'prompt_tokens':12,'completion_tokens':8,'total_tokens':20}})]
            client=DeepSeekClient('offline-key');client.complete([])
            self.assertEqual([c.args[0].get_method() for c in factory.return_value.open.call_args_list],['GET','GET','POST'])
            self.assertEqual(client.cost.state['attempts'],1);self.assertEqual(client.responses,1)
    def test_timeout_not_retried(self):
        with patch('agent.urllib.request.build_opener') as factory:
            factory.return_value.open.side_effect=urllib.error.URLError(socket.timeout())
            client=DeepSeekClient('offline-key',preflight=False)
            with self.assertRaisesRegex(RuntimeError,'No automatic retry'):client.complete([])
            self.assertEqual(factory.return_value.open.call_count,1);self.assertEqual(client.cost.snapshot()['unknown_attempts'],1)
    def test_cancellation_during_metadata_prevents_paid_request(self):
        from agent import Cancelled
        client=DeepSeekClient('offline-key')
        def metadata(request,timeout):
            if request.full_url.endswith('/models'):return Response({'data':[{'id':MODEL}]})
            client.stop.set()
            return Response({'is_available':True})
        with patch('agent.urllib.request.build_opener') as factory:
            factory.return_value.open.side_effect=metadata
            with self.assertRaises(Cancelled):client.complete([])
            self.assertEqual(factory.return_value.open.call_count,2)
            self.assertEqual(client.cost.state['attempts'],0)

    def test_metadata_network_error_no_spend(self):
        with patch('agent.urllib.request.build_opener') as factory:
            factory.return_value.open.side_effect=urllib.error.URLError(socket.gaierror())
            client=DeepSeekClient('offline-key')
            with self.assertRaisesRegex(RuntimeError,'DNS'):client.complete([])
            self.assertEqual(client.cost.state['attempts'],0)
    def test_completed_responses_preserved(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)/'run';client=FakeClient([calls(fixture()),done()]);Agent(data(),root,client).run()
            self.assertTrue((root/'response-001.json').exists());self.assertTrue((root/'response-002.json').exists())
            self.assertNotIn(client.key,(root/'response-001.json').read_text())

if __name__=='__main__':unittest.main()
