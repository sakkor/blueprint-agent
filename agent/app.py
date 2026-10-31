"""Blueprint Agent — Windows desktop interface and packaged smoke test."""
from __future__ import annotations
import argparse, json, os, queue, sys, tempfile, threading, uuid
from datetime import datetime
from pathlib import Path
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from tkinter.scrolledtext import ScrolledText
from blueprint import analyze
from agent import Agent, DeepSeekClient, MODEL, VERSION
from cost_control import CostLedger

BASE=Path(sys.executable).parent if getattr(sys,'frozen',False) else Path(__file__).resolve().parent
EXAMPLES=BASE/'examples'
if not EXAMPLES.is_dir() and getattr(sys,'frozen',False): EXAMPLES=Path(sys._MEIPASS)/'examples'
BG='#edf2f8'; INK='#15283f'; TEAL='#087e8b'; MUTED='#5e7084'; NAVY='#14273e'

class App:
    def __init__(self,root):
        self.root=root; self.queue=queue.Queue(); self.stop=threading.Event(); self.running=False
        self.data=None; self.last_run=None
        self.paths={'doc':EXAMPLES/'Architecture_Documentation.md','views':EXAMPLES/'Architecture_View.md','output':BASE/'Results'}
        root.title('Blueprint Agent | Architecture to Code'); root.geometry('1180x800'); root.minsize(1000,760); root.configure(bg=BG)
        style=ttk.Style(root); style.theme_use('clam')
        style.configure('TFrame',background=BG); style.configure('Card.TFrame',background='white')
        style.configure('TLabel',background=BG,foreground=INK,font=('Segoe UI',10))
        style.configure('Card.TLabel',background='white',foreground=INK,font=('Segoe UI',10))
        style.configure('Hint.TLabel',background=BG,foreground=MUTED,font=('Segoe UI',9))
        style.configure('TButton',font=('Segoe UI',10),padding=(10,6))
        style.configure('Primary.TButton',background=TEAL,foreground='white',font=('Segoe UI',10,'bold'))
        style.map('Primary.TButton',background=[('disabled','#93b7bd'),('active','#096977')])
        style.configure('Treeview',font=('Segoe UI',9),rowheight=30,background='white',fieldbackground='white',foreground=INK)
        style.configure('Treeview.Heading',font=('Segoe UI',9,'bold'),padding=7)
        style.configure('TNotebook',background=BG,borderwidth=0)
        style.configure('TNotebook.Tab',padding=(17,10),font=('Segoe UI',10))
        header=tk.Frame(root,bg=NAVY,padx=28,pady=14); header.pack(fill='x')
        tk.Label(header,text='BLUEPRINT  /  AGENT',font=('Segoe UI',12,'bold'),fg='#62d2cb',bg=NAVY).pack(anchor='w')
        tk.Label(header,text='Architecture, made traceable.',font=('Segoe UI',23,'bold'),fg='white',bg=NAVY).pack(anchor='w',pady=(5,0))
        header_row=tk.Frame(header,bg=NAVY);header_row.pack(fill='x',pady=(7,0))
        tk.Label(header_row,text=f'Official DeepSeek API  /  {MODEL}  /  v{VERSION}',font=('Segoe UI',10),fg='#b8c9db',bg=NAVY).pack(side='left')
        self.check_button=ttk.Button(header_row,text='Check API (no generation)',command=self.check_api);self.check_button.pack(side='right')
        body=ttk.Frame(root,padding=16); body.pack(fill='both',expand=True)
        body.columnconfigure(1,weight=1); body.rowconfigure(0,weight=1)
        left=ttk.Frame(body,width=340); left.grid(row=0,column=0,sticky='ns',padx=(0,22)); left.pack_propagate(False)
        right=ttk.Frame(body); right.grid(row=0,column=1,sticky='nsew')
        self.key=tk.StringVar(value=os.environ.get('DEEPSEEK_API_KEY',''))
        self.show_key=tk.BooleanVar(value=False); self.show_paths=tk.BooleanVar(value=False)
        self.labels={k:tk.StringVar() for k in self.paths}; self.fields=[self.check_button]
        ttk.Label(left,text='01  CONFIGURE',font=('Segoe UI',11,'bold')).pack(anchor='w',pady=(0,8))
        ttk.Label(left,text='DeepSeek API key').pack(anchor='w')
        self.key_entry=ttk.Entry(left,textvariable=self.key,show='*',font=('Segoe UI',11)); self.key_entry.pack(fill='x',pady=(5,3)); self.fields.append(self.key_entry)
        show=ttk.Checkbutton(left,text='Show key',variable=self.show_key,command=lambda:self.key_entry.configure(show='' if self.show_key.get() else '*')); show.pack(anchor='w'); self.fields.append(show)
        for k,title in [('doc','Architecture documentation'),('views','UML views'),('output','Output folder')]:
            ttk.Label(left,text=title).pack(anchor='w',pady=(9,4))
            line=ttk.Frame(left); line.pack(fill='x')
            entry=ttk.Entry(line,textvariable=self.labels[k],state='readonly',font=('Segoe UI',9));entry.pack(side='left',fill='x',expand=True)
            button=ttk.Button(line,text='Browse',command=lambda key=k:self.browse(key));button.pack(side='right',padx=(6,0)); self.fields.append(button)
        toggle=ttk.Checkbutton(left,text='Show full paths',variable=self.show_paths,command=self.refresh_paths);toggle.pack(anchor='w',pady=(6,8));self.fields.append(toggle)
        limits=ttk.Frame(left);limits.pack(fill='x')
        self.turns=tk.IntVar(value=40);self.budget=tk.IntVar(value=500)
        ttk.Label(limits,text='Max turns').grid(row=0,column=0,sticky='w')
        ttk.Label(limits,text='Cost guard (USD estimate)').grid(row=0,column=1,sticky='w',padx=(12,0))
        turns=ttk.Spinbox(limits,from_=5,to=120,textvariable=self.turns,width=7);turns.grid(row=1,column=0,sticky='w',pady=5)
        ttk.Label(limits,text='$0.90 / shared output folder',font=('Segoe UI',9,'bold')).grid(row=1,column=1,sticky='w',padx=(12,0),pady=5)
        self.fields.append(turns)
        ttk.Label(left,text='Documents go to DeepSeek. API usage is billed.\nNo automatic retries. Check API before generating.\nVerify the final official charge is within $1.',style='Hint.TLabel',wraplength=335).pack(anchor='w',pady=(8,10))
        self.inspect_button=ttk.Button(left,text='Inspect inputs',command=self.inspect);self.inspect_button.pack(fill='x',pady=(0,7));self.fields.append(self.inspect_button)
        self.generate_button=ttk.Button(left,text='Generate desktop game',style='Primary.TButton',command=self.start);self.generate_button.pack(fill='x')
        self.cancel_button=ttk.Button(left,text='Stop after current request',state='disabled',command=self.cancel);self.cancel_button.pack(fill='x',pady=(7,0))
        self.status=tk.StringVar(value='Inspect the example inputs, then generate with your key.')
        self.profile=tk.StringVar(value='02  INSPECT & BUILD')
        ttk.Label(right,textvariable=self.profile,font=('Segoe UI',11,'bold')).pack(anchor='w',pady=(0,10))
        self.notebook=ttk.Notebook(right);self.notebook.pack(fill='both',expand=True)
        self.source_text=self.text_tab('Input review')
        self.log_text=self.text_tab('Activity',dark=True)
        cover=ttk.Frame(self.notebook,padding=8);self.notebook.add(cover,text='Coverage')
        ttk.Label(cover,text='References mapped ≠ behavior verified. Generated tests are not executed.',wraplength=650,style='Hint.TLabel').pack(anchor='w',pady=(0,8))
        table_frame=ttk.Frame(cover);table_frame.pack(fill='both',expand=True)
        self.tree=ttk.Treeview(table_frame,columns=('id','mapped','claim'),show='headings',selectmode='browse')
        for k,title,width in [('id','Requirement',120),('mapped','Evidence',150),('claim','Model claim',130)]: self.tree.heading(k,text=title);self.tree.column(k,width=width)
        self.tree.pack(side='left',fill='both',expand=True)
        scrollbar=ttk.Scrollbar(table_frame,orient='vertical',command=self.tree.yview);scrollbar.pack(side='right',fill='y');self.tree.configure(yscrollcommand=scrollbar.set)
        self.usage=tk.StringVar(value='No API requests yet')
        ttk.Label(right,textvariable=self.usage,style='Hint.TLabel').pack(anchor='w',pady=(10,5))
        self.progress=ttk.Progressbar(right,mode='indeterminate');self.progress.pack(fill='x')
        ttk.Label(right,textvariable=self.status,wraplength=720).pack(anchor='w',pady=(9,10))
        actions=ttk.Frame(right);actions.pack(fill='x')
        self.report_button=ttk.Button(actions,text='View evidence report',state='disabled',command=lambda:self.open_result('report.html'));self.report_button.pack(side='left')
        self.folder_button=ttk.Button(actions,text='Open generated files',state='disabled',command=lambda:self.open_result('project'));self.folder_button.pack(side='left',padx=8)
        self.refresh_paths(); self.inspect(silent=True)
        root.protocol('WM_DELETE_WINDOW',self.close);root.after(120,self.poll)

    def text_tab(self,title,dark=False):
        frame=ttk.Frame(self.notebook);self.notebook.add(frame,text=title)
        text=ScrolledText(frame,font=('Consolas',10),wrap='word',borderwidth=0,padx=14,pady=14,
                          bg=NAVY if dark else 'white',fg='#dce8f5' if dark else INK,state='disabled')
        text.pack(fill='both',expand=True);return text

    def put(self,widget,text,append=False):
        widget.configure(state='normal')
        if not append:widget.delete('1.0','end')
        widget.insert('end',text);widget.see('end');widget.configure(state='disabled')

    def refresh_paths(self):
        for k,p in self.paths.items(): self.labels[k].set(str(p) if self.show_paths.get() else p.name)

    def browse(self,key):
        path=filedialog.askdirectory(parent=self.root,title='Select output folder') if key=='output' else filedialog.askopenfilename(parent=self.root,title='Select architecture Markdown',filetypes=[('Markdown','*.md')])
        if path:self.paths[key]=Path(path);self.refresh_paths();self.data=None

    def inspect(self,silent=False):
        try:
            self.data=analyze(self.paths['doc'],self.paths['views'])
            lines=['SOURCE PROFILE: '+self.data['profile'],'',f"{len(self.data['requirements'])} requirements / {len(self.data['diagrams'])} UML blocks",'', 'REQUIREMENTS']
            lines.extend(r['id']+'  '+r['description'] for r in self.data['requirements'])
            lines+=['','REQUIRED ARCHITECTURE ARTIFACTS',*self.data['required_artifacts'],'','DIAGRAMS']
            lines.extend(d['id']+'  '+d['name'] for d in self.data['diagrams'])
            lines+=['','SOURCE FINDINGS / ASSUMPTIONS TO RESOLVE',*['• '+s for s in self.data['findings']]]
            self.put(self.source_text,'\n'.join(lines));self.source_text.configure(state='normal');self.source_text.see('1.0');self.source_text.configure(state='disabled')
            self.profile.set(f"02  {len(self.data['requirements'])} REQUIREMENTS  /  {len(self.data['diagrams'])} DIAGRAMS")
            if not silent:self.status.set('Inputs inspected. Review findings, then generate.');self.notebook.select(0)
            return True
        except Exception as exc:
            self.data=None
            if not silent:messagebox.showerror('Input review',str(exc),parent=self.root)
            else:self.put(self.source_text,'Choose both Markdown inputs using Browse, then select Inspect inputs.')
            return False

    def start(self):
        if self.running or not self.inspect():return
        try:
            turns=self.turns.get();budget=self.budget.get()*1000
            if not 5<=turns<=120 or not 50000<=budget<=3000000:raise ValueError('Choose 5–120 turns and 50–3000 thousand tokens.')
            self.stop=threading.Event()
            parent=self.paths['output']
            client=DeepSeekClient(self.key.get(),self.stop,lambda text:self.queue.put({'kind':'log','text':text}),ledger=CostLedger(parent/'evaluation-budget.json'))
            parent.mkdir(parents=True,exist_ok=True)
            self.last_run=parent/('blueprint-'+datetime.now().strftime('%Y%m%d-%H%M%S')+'-'+uuid.uuid4().hex[:5])
            runner=Agent(self.data,self.last_run,client,self.stop,self.queue.put,turns,budget)
        except Exception as exc:messagebox.showerror('Configuration',str(exc),parent=self.root);return
        self.running=True;self.generate_button.configure(state='disabled');self.cancel_button.configure(state='normal')
        self.report_button.configure(state='disabled');self.folder_button.configure(state='disabled')
        for widget in self.fields:widget.configure(state='disabled')
        for item in self.tree.get_children():self.tree.delete(item)
        self.put(self.log_text,'Starting a new DeepSeek run.\n');self.notebook.select(1)
        self.usage.set('Waiting for API usage');self.status.set('Generating…');self.progress.start(14)
        def worker():
            try:runner.run()
            except Exception as exc:self.queue.put({'kind':'fatal','text':str(exc).replace(client.key,'[REDACTED]')})
        threading.Thread(target=worker,daemon=True).start()

    def check_api(self):
        if self.running:return
        try:
            self.stop=threading.Event()
            client=DeepSeekClient(self.key.get(),self.stop)
        except ValueError as exc:messagebox.showerror('API check',str(exc),parent=self.root);return
        self.running=True
        for widget in self.fields:widget.configure(state='disabled')
        self.generate_button.configure(state='disabled');self.cancel_button.configure(state='normal')
        self.notebook.select(1);self.put(self.log_text,'Checking official API metadata only. No architecture documents or generation request are sent.\n')
        self.status.set('Checking key, model access and balance...');self.progress.start(14)
        def worker():
            try:message=client.check_connection()
            except Exception as exc:message=str(exc).replace(client.key,'[REDACTED]')
            finally:client.close()
            self.queue.put({'kind':'preflight','text':message})
        threading.Thread(target=worker,daemon=True).start()

    def cancel(self):
        self.stop.set();self.cancel_button.configure(state='disabled');self.status.set('Stopping after current request; socket inactivity timeout is 180 seconds.')

    def show_coverage(self,validation):
        for item in self.tree.get_children():self.tree.delete(item)
        for row in validation['coverage']:self.tree.insert('','end',values=(row['id'],'Mapped' if row['mapped'] else 'Missing',row['reported_status']))

    def finish(self):
        self.running=False;self.progress.stop();self.generate_button.configure(state='normal');self.cancel_button.configure(state='disabled')
        for widget in self.fields:widget.configure(state='normal')
        if self.last_run:
            self.folder_button.configure(state='normal' if (self.last_run/'project').is_dir() else 'disabled')
            self.report_button.configure(state='normal' if (self.last_run/'report.html').is_file() else 'disabled')

    def poll(self):
        try:
            while True:
                event=self.queue.get_nowait();kind=event['kind'];text=event['text']
                if kind not in ('validation','billing'):self.put(self.log_text,text+'\n',append=True)
                if kind in ('request','billing'):
                    u=event.get('usage',{});self.usage.set(f"Tokens: {u.get('total_tokens',0):,} · Estimate incl. reservations: ${event.get('cost',{}).get('evaluation_accounted_usd',0):.4f} / $0.90")
                    if kind=='request':self.status.set(text)
                elif kind=='validation':self.show_coverage(event['validation'])
                elif kind=='done':
                    report=event['report'];u=report['usage'];self.show_coverage(report['validation']);self.finish()
                    labels={'ready_for_runtime_test':'Files created. Runtime tests still need to be run.','needs_review':'Files created with review notes. Open the evidence report.','failed':'Generation failed. Open the report for the error.','cancelled':'Stopped. Partial files preserved.','cost_review':'Usage is uncertain. Review the cost report before continuing.','budget_limit':'Cost/token budget reached. Partial files preserved.','incomplete':'Turn limit reached. Partial files preserved.'}
                    self.status.set(labels.get(text,text));self.usage.set(f"Tokens: {u.get('total_tokens',0):,} · Estimate incl. reservations: ${report.get('cost',{}).get('evaluation_accounted_usd',0):.4f} / $0.90")
                elif kind in ('fatal','preflight'):self.finish();self.status.set(text)
        except queue.Empty:pass
        self.root.after(120,self.poll)

    def open_result(self,name):
        if self.last_run and (self.last_run/name).exists():os.startfile(str(self.last_run/name))

    def close(self):
        if self.running:messagebox.showinfo('Run active','Stop the run and wait for its report before closing.',parent=self.root);return
        self.key.set('');self.root.destroy()

def main():
    parser=argparse.ArgumentParser(description='Blueprint Agent desktop')
    parser.add_argument('--self-test',metavar='REPORT',help='Offline runtime/GUI/parser smoke test; no API call')
    parser.add_argument('--connection-diagnostic',metavar='REPORT',help='Unauthenticated endpoint diagnostic; no generation or key')
    args=parser.parse_args()
    if args.connection_diagnostic:
        import urllib.request,urllib.error,ssl,traceback
        checks=[]
        for route in ['system','direct']:
            result={'route':route,'key_used':False,'generation_requested':False}
            try:
                opener=urllib.request.build_opener() if route=='system' else urllib.request.build_opener(urllib.request.ProxyHandler({}))
                with opener.open('https://api.deepseek.com/models',timeout=15) as response:result['http_status']=response.status
            except urllib.error.HTTPError as exc:result['http_status']=exc.code
            except Exception as exc:
                reason=getattr(exc,'reason',exc)
                result.update(error_type=type(exc).__name__,reason_type=type(reason).__name__,detail=str(reason),trace=traceback.format_exc(),errno=getattr(reason,'errno',None),winerror=getattr(reason,'winerror',None))
            checks.append(result)
        Path(args.connection_diagnostic).write_text(json.dumps({'frozen':bool(getattr(sys,'frozen',False)),'checks':checks},indent=2),encoding='utf-8')
        return
    if args.self_test:
        import ssl
        context=ssl.create_default_context()
        assert context.check_hostname and context.verify_mode==ssl.CERT_REQUIRED
        from validation import Workspace
        from agent import write_html
        with tempfile.TemporaryDirectory() as folder:
            root_dir=Path(folder);w=Workspace(root_dir/'project')
            w.write('main.py','def answer(): return 42\n');w.write('data.yaml','answer: 42\n')
            v=w.validate();assert not any('syntax' in e.lower() for e in v['errors'])
            assert w.read('main.py')['content'].startswith('def answer')
        root=tk.Tk();root.withdraw();app=App(root);root.update_idletasks()
        assert app.data and len(app.data['diagrams'])==13
        report={'ok':True,'frozen':bool(getattr(sys,'frozen',False)),'version':VERSION,'tk':tk.TkVersion,
                'requirements':len(app.data['requirements']),'diagrams':13,'yaml_parser':True,'api_called':False,'desktop_requirement':any(r['id']=='EMAIL-DESKTOP' for r in app.data['requirements']),'cost_guard_usd':0.90,'tls_context_ready':True,'tls_certificate_verification':True}
        root.destroy();Path(args.self_test).write_text(json.dumps(report,indent=2),encoding='utf-8');return
    root=tk.Tk();App(root);root.mainloop()

if __name__=='__main__':main()
