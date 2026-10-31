"""Conservative USD admission control, persisted across runs in one output folder.

This is an estimate guard, not a provider-enforced billing cap. Confirm the final
charge in the official account. Prices are intentionally peak, uncached rates.
"""
from __future__ import annotations
import json, os, tempfile
from pathlib import Path

LIMIT_MICRO_USD=900_000
INPUT_CENTS_PER_MILLION=132
OUTPUT_CENTS_PER_MILLION=396
PRICE_CHECKED='2026-10-29'
PRICE_SOURCE='https://api-docs.deepseek.com/quick_start/pricing/'

class BudgetExceeded(RuntimeError):pass
class CostUncertain(RuntimeError):pass

def priced_micro(input_tokens,output_tokens):
    return (input_tokens*INPUT_CENTS_PER_MILLION+output_tokens*OUTPUT_CENTS_PER_MILLION+99)//100

class CostLedger:
    def __init__(self,path=None,limit_micro=LIMIT_MICRO_USD):
        if type(limit_micro)!=int or not 1<=limit_micro<=LIMIT_MICRO_USD:raise ValueError('Cost limit must be positive and at most $0.90.')
        self.path=Path(path) if path else None
        self.limit=limit_micro;self.active=False;self.lock_fd=None;self.pending=None
        self.state={'schema':1,'accounted_micro_usd':0,'attempts':0,'settled_attempts':0,'blocked_reason':None}
        self.run_start=0

    def open(self):
        if self.active:return
        if self.path:
            self.path.parent.mkdir(parents=True,exist_ok=True)
            self.lock=self.path.with_suffix(self.path.suffix+'.lock')
            try:self.lock_fd=os.open(self.lock,os.O_CREAT|os.O_EXCL|os.O_WRONLY)
            except FileExistsError:raise BudgetExceeded('This output folder has an active/stale budget lock. Close the other run; review the ledger before recovering a stale lock.') from None
            try:
                if self.path.exists():
                    state=json.loads(self.path.read_text(encoding='utf-8'))
                    if not isinstance(state,dict) or state.get('schema')!=1:raise ValueError('Invalid budget ledger schema.')
                    for name in ('accounted_micro_usd','attempts','settled_attempts'):
                        if type(state.get(name))!=int or state[name]<0:raise ValueError('Invalid budget ledger values; refusing to reset it.')
                    if state['settled_attempts']>state['attempts']:raise ValueError('Invalid ledger attempt counts.')
                    if state.get('blocked_reason') is not None and not isinstance(state['blocked_reason'],str):raise ValueError('Invalid ledger blocked reason.')
                    self.state=state
            except Exception:
                os.close(self.lock_fd);self.lock_fd=None;self.lock.unlink();raise
        self.run_start=self.state['accounted_micro_usd'];self.active=True

    def _save(self):
        if not self.path:return
        fd,name=tempfile.mkstemp(prefix='.budget-',dir=self.path.parent)
        try:
            with os.fdopen(fd,'w',encoding='utf-8') as f:
                json.dump(self.state,f,indent=2);f.flush();os.fsync(f.fileno())
            os.replace(name,self.path)
        finally:
            if os.path.exists(name):os.unlink(name)

    def reserve(self,body,message_count,tool_count,max_output):
        self.open()
        if self.state.get('blocked_reason'):raise CostUncertain(self.state['blocked_reason'])
        # A prior failed/unknown attempt retains its full reservation. Never refund it.
        self.pending=None
        prompt_bound=len(body)+4096+128*(message_count+tool_count)
        reserve=priced_micro(prompt_bound,max_output)
        if self.state['accounted_micro_usd']+reserve>self.limit:
            raise BudgetExceeded('Next request would exceed the $0.90 conservative budget. Partial output is preserved; no request was sent.')
        self.state['accounted_micro_usd']+=reserve;self.state['attempts']+=1
        self.pending=(reserve,prompt_bound,max_output);self._save()
        return reserve

    def settle(self,usage):
        if self.pending is None:raise CostUncertain('No matching request reservation.')
        reserve,prompt_bound,max_output=self.pending;self.pending=None
        good=isinstance(usage,dict) and all(type(usage.get(k))==int and usage[k]>=0 for k in ('prompt_tokens','completion_tokens','total_tokens'))
        if not good or usage['total_tokens']!=usage['prompt_tokens']+usage['completion_tokens']:
            self.state['blocked_reason']='Missing/inconsistent API usage. Full reservation retained; check official billing before further requests.'
            self._save();raise CostUncertain(self.state['blocked_reason'])
        measured=priced_micro(usage['prompt_tokens'],usage['completion_tokens'])
        if usage['prompt_tokens']>prompt_bound or usage['completion_tokens']>max_output:
            self.state['accounted_micro_usd']+=max(0,measured-reserve)
            self.state['blocked_reason']='API usage exceeded the conservative reservation assumptions. Stop and check official billing.'
            self._save();raise CostUncertain(self.state['blocked_reason'])
        self.state['accounted_micro_usd']+=measured-reserve;self.state['settled_attempts']+=1;self._save()

    def snapshot(self):
        return {'guard_limit_usd':self.limit/1_000_000,'evaluation_accounted_usd':self.state['accounted_micro_usd']/1_000_000,
                'this_run_accounted_usd':(self.state['accounted_micro_usd']-self.run_start)/1_000_000,
                'attempts':self.state['attempts'],'unknown_attempts':self.state['attempts']-self.state['settled_attempts'],
                'blocked_reason':self.state.get('blocked_reason'),'price_checked':PRICE_CHECKED,'price_source':PRICE_SOURCE,
                'input_usd_per_million':INPUT_CENTS_PER_MILLION/100,'output_usd_per_million':OUTPUT_CENTS_PER_MILLION/100,
                'method':'UTF-8 request bytes plus framing allowance reserved before EVERY attempt; actual usage settled at peak uncached rates. Unknown attempts retain full reservation.',
                'billing_verified':False,'scope':'Shared by runs using this output folder. Not an account-wide provider cap; verify final official charge is within $1.'}

    def close(self):
        if self.lock_fd is not None:
            os.close(self.lock_fd);self.lock_fd=None;self.lock.unlink()
        self.active=False
