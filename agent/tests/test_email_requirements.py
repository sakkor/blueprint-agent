import json,tempfile,unittest,urllib.error
from pathlib import Path
from unittest.mock import patch
from cost_control import CostLedger,BudgetExceeded,CostUncertain,priced_micro
from agent import Agent,DeepSeekClient,SYSTEM,model_input
from blueprint import analyze
from validation import Workspace
from test_blueprint import ROOT,fixture,data,done

class Budget(unittest.TestCase):
    def test_exact_usd_arithmetic(self):
        self.assertEqual(priced_micro(400000,50000),726000)
        self.assertEqual(priced_micro(1000000,0),1320000)
    def test_request_rejected_before_network(self):
        client=DeepSeekClient('fixture',preflight=False,ledger=CostLedger(limit_micro=1))
        with patch('agent.urllib.request.build_opener') as opener:
            with self.assertRaises(BudgetExceeded):client.complete([])
            opener.assert_not_called()
    def test_persistent_usage_across_runs(self):
        with tempfile.TemporaryDirectory() as f:
            path=Path(f)/'budget.json';first=CostLedger(path)
            first.reserve(b'hello',1,5,8192);first.settle({'prompt_tokens':100,'completion_tokens':10,'total_tokens':110});first.close()
            second=CostLedger(path);second.open()
            self.assertEqual(second.state['accounted_micro_usd'],priced_micro(100,10));self.assertEqual(second.snapshot()['this_run_accounted_usd'],0)
            second.close()
    def test_unknown_attempt_keeps_reservation(self):
        ledger=CostLedger();reserve=ledger.reserve(b'hello',1,5,8192)
        ledger.reserve(b'hello',1,5,8192)
        self.assertEqual(ledger.state['accounted_micro_usd'],2*reserve)
        self.assertEqual(ledger.snapshot()['unknown_attempts'],2)
    def test_missing_usage_stops_future_attempts(self):
        ledger=CostLedger();amount=ledger.reserve(b'hi',1,5,8192)
        with self.assertRaises(CostUncertain):ledger.settle(None)
        self.assertEqual(ledger.state['accounted_micro_usd'],amount)
        with self.assertRaises(CostUncertain):ledger.reserve(b'hi',1,5,8192)
    def test_inconsistent_usage_stops(self):
        ledger=CostLedger();ledger.reserve(b'hi',1,5,8192)
        with self.assertRaises(CostUncertain):ledger.settle({'prompt_tokens':20,'completion_tokens':10,'total_tokens':99})
    def test_oversized_usage_invalidates_estimate(self):
        ledger=CostLedger();ledger.reserve(b'x',1,5,8192)
        with self.assertRaises(CostUncertain):ledger.settle({'prompt_tokens':10000,'completion_tokens':1,'total_tokens':10001})
        self.assertIsNotNone(ledger.snapshot()['blocked_reason'])
    def test_invalid_ledger_not_reset(self):
        with tempfile.TemporaryDirectory() as f:
            path=Path(f)/'budget.json';path.write_text('{bad');ledger=CostLedger(path)
            with self.assertRaises(ValueError):ledger.open()
            self.assertEqual(path.read_text(),'{bad');self.assertFalse(path.with_suffix('.json.lock').exists())
    def test_concurrent_run_is_blocked(self):
        with tempfile.TemporaryDirectory() as f:
            path=Path(f)/'budget.json';first=CostLedger(path);first.open()
            try:
                with self.assertRaises(BudgetExceeded):CostLedger(path).open()
            finally:first.close()
    def test_failed_request_reserves_once(self):
        client=DeepSeekClient('fixture',preflight=False)
        with patch.object(client.stop,'wait',return_value=False),patch('agent.urllib.request.build_opener') as factory:
            factory.return_value.open.side_effect=urllib.error.HTTPError('https://api.deepseek.com',429,'rate',{},None)
            with self.assertRaises(RuntimeError):client.complete([])
            self.assertEqual(client.cost.state['attempts'],1);self.assertEqual(client.cost.snapshot()['unknown_attempts'],1)
    def test_exhausted_ledger_stops_agent_and_saves_report(self):
        with tempfile.TemporaryDirectory() as f:
            client=DeepSeekClient('fixture',preflight=False,ledger=CostLedger(Path(f)/'ledger.json',limit_micro=1))
            with patch('agent.urllib.request.build_opener') as factory:
                report=Agent(data(),Path(f)/'run',client).run();factory.assert_not_called()
            self.assertEqual(report['status'],'budget_limit');self.assertTrue((Path(f)/'run/report.html').exists())
            self.assertFalse((Path(f)/'ledger.json.lock').exists())
    def test_guard_cannot_be_raised_above_ninety_cents(self):
        with self.assertRaises(ValueError):CostLedger(limit_micro=1000001)

class DesktopOutput(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        req=[{'id':'EMAIL-DESKTOP','description':'Native desktop game','kind':'functional'}]
        self.w=Workspace(self.tmp.name,req,['desktop.py','desktop-manifest.json','build_game.ps1'])
        for name,text in fixture().items():self.w.write(name,text.replace('FR-1','EMAIL-DESKTOP'))
        self.w.write('desktop-manifest.json',json.dumps({'framework':'tkinter','entry_point':'desktop.py','build_script':'build_game.ps1'}))
        self.w.write('build_game.ps1','python -m unittest discover -s tests\npython -m PyInstaller --onefile --windowed desktop.py')
    def test_native_window_structure_accepted(self):
        self.w.write('desktop.py','import tkinter as tk\nroot=tk.Tk()\nroot.mainloop()\n')
        result=self.w.validate();self.assertTrue(result['structural_ok'],result['errors'])
    def test_browser_launcher_rejected(self):
        self.w.write('desktop.py','import webbrowser\nwebbrowser.open("http://localhost:8000")\n')
        self.assertIn('native tkinter',' '.join(self.w.validate()['errors']))
    def test_import_only_stub_rejected(self):
        self.w.write('desktop.py','import tkinter\n# no real desktop entry point\n')
        self.assertFalse(self.w.validate()['structural_ok'])
    def test_packaging_recipe_required(self):
        self.w.write('desktop.py','from tkinter import Tk\nroot=Tk()\nroot.mainloop()')
        self.w.write('build_game.ps1','echo done')
        self.assertIn('package desktop.py',' '.join(self.w.validate()['errors']))
    def test_manifest_wrong_framework_rejected(self):
        self.w.write('desktop.py','import tkinter as tk\nroot=tk.Tk()\nroot.mainloop()')
        self.w.write('desktop-manifest.json','{"framework":"web"}')
        self.assertIn('must declare tkinter',' '.join(self.w.validate()['errors']))
    def test_email_requirement_and_deduplicated_prompt(self):
        d=analyze(ROOT/'examples/Architecture_Documentation.md',ROOT/'examples/Architecture_View.md')
        self.assertIn('EMAIL-DESKTOP',{r['id'] for r in d['requirements']});self.assertIn('desktop.py',d['required_artifacts'])
        payload=model_input(d);self.assertNotIn('source',payload['diagrams'][0]);self.assertEqual(payload['views']['text'],d['views']['text'])
        self.assertIn('not a browser/web-only',SYSTEM)

if __name__=='__main__':unittest.main()
