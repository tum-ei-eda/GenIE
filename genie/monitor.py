"""Launch and monitor CLI flows: python -m genie.monitor [RUN_DIR]."""
import argparse
import json
import logging
from contextlib import contextmanager
import os
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlsplit


class RunStatus:
    """Atomic snapshots; each invocation replaces the plan, preserving old log directories."""

    def __init__(self, directory, name, steps, resume_from=None):
        self.directory = Path(directory)
        self.lock = threading.Lock()
        self.data = dict(name=name, status="running", pid=os.getpid(), started=time.time(),
                         stages=[dict(id=s.id, name=s.name, status="pending") for s in steps])
        if resume_from:
            try:
                previous = json.loads((self.directory / "monitor.json").read_text())
                old = {stage["id"]: stage for stage in previous["stages"]}
                self.data["started"] = previous["started"]
                for index, stage in enumerate(self.data["stages"]):
                    if stage["id"] == resume_from:
                        break
                    prior = old.get(stage["id"])
                    if prior and prior["status"] in ("completed", "skipped"):
                        self.data["stages"][index] = prior
            except (OSError, ValueError, KeyError):
                pass
        self.stopped = threading.Event()
        self.save()
        self.heartbeat_thread = threading.Thread(target=self.heartbeat, daemon=True)
        self.heartbeat_thread.start()

    def heartbeat(self):
        while not self.stopped.wait(3):
            with self.lock:
                self.save()

    def save(self):
        self.data["heartbeat"] = time.time()
        target = self.directory / "monitor.json"
        temporary = target.with_suffix(".json.tmp")
        temporary.write_text(json.dumps(self.data), encoding="utf8")
        temporary.replace(target)

    def stage(self, stage_id, status, directory=None, error=None):
        with self.lock:
            stage = next(s for s in self.data["stages"] if s["id"] == stage_id)
            stage["status"] = status
            stage["updated"] = time.time()
            if status == "running":
                stage["started"] = stage["updated"]
            elif status in ("completed", "failed", "interrupted"):
                stage["finished"] = stage["updated"]
            if directory is not None:
                stage["directory"] = str(Path(directory).relative_to(self.directory))
            if error is not None:
                stage["error"] = str(error)
            self.save()

    @contextmanager
    def capture(self, directory):
        from .logging import register_additional_handler, deregister_additional_handler

        Path(directory).mkdir(parents=True, exist_ok=True)
        handler = logging.FileHandler(Path(directory) / "stage.log", encoding="utf8")
        handler.setLevel(1)
        handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
        register_additional_handler(handler)
        try:
            yield
        finally:
            deregister_additional_handler(handler)
            handler.close()

    def finish(self, status, error=None):
        self.stopped.set()
        self.heartbeat_thread.join()
        with self.lock:
            self.data.update(status=status, finished=time.time())
            if error is not None:
                self.data["error"] = str(error)
                for stage in self.data["stages"]:
                    if stage["status"] == "running":
                        stage.update(status=status, error=str(error), finished=self.data["finished"])
            self.save()


def with_progress(data, root, now=None):
    """Add presentation values without rewriting the runner's snapshot."""
    now = time.time() if now is None else now
    end = data.get("finished", now)
    if data["status"] == "unresponsive":
        end = data.get("heartbeat", end)
    data["elapsed"] = max(0, end - data["started"])
    stages = data["stages"]
    data["progress"] = dict(total=len(stages), completed=sum(s["status"] == "completed" for s in stages),
                            skipped=sum(s["status"] == "skipped" for s in stages))
    for number, stage in enumerate(stages, 1):
        stage["number"] = number
        stage["elapsed"] = None
        if "started" not in stage and stage["status"] == "running" and "updated" in stage:
            stage["started"] = stage["updated"]
        if "started" in stage:
            stage["elapsed"] = max(0, stage.get("finished", end) - stage["started"])
        elif stage["status"] == "completed" and "directory" in stage:
            # Existing snapshots predate per-stage timestamps. runtime.txt is
            # produced by GenIEStep.start and uses HH:MM:SS[.fraction].
            directory = (root / stage["directory"]).resolve()
            if directory.is_relative_to(root):
                try:
                    parts = (directory / "runtime.txt").read_text().strip().split(":")
                    stage["elapsed"] = sum(float(value) * 60 ** index for index, value in enumerate(reversed(parts)))
                except (OSError, ValueError):
                    pass
    return data


PAGE = '''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>GenIE · Flow monitor</title><style>
body{font:15px system-ui;background:#101923;color:#e3ecf5;max-width:1000px;margin:28px auto;padding:0 20px}
h1{margin-bottom:8px}small,#connection{color:#a6b9cb}
article,details.flow,details.data,details.launcher,#pending,#completed{border:1px solid #344657;border-radius:8px;margin:8px 0;padding:10px 12px}
header{display:flex;align-items:center;gap:14px}header strong{flex:1;min-width:0;overflow-wrap:anywhere}.timer{white-space:nowrap;font-variant-numeric:tabular-nums}.badge{font-weight:600;white-space:nowrap}
article.completed{background:#15372b;border-color:#367b58}article.failed,article.interrupted{background:#442525;border-color:#a35252}article.running{background:#17354e;border-color:#4b96c6}article.pending,article.skipped{background:#202b36;border-color:#435260}
summary{cursor:pointer}article summary{margin-top:6px;color:#c5d4df}.stage-error:empty{display:none}.stage-error{margin:8px 0}pre{white-space:pre-wrap;overflow-wrap:anywhere;max-height:360px;overflow:auto;background:#09111a;padding:10px;font-size:13px}a{color:#8acaff}.downloads{margin:8px 0;font-size:13px}
.metrics-table{width:100%;border-collapse:collapse;text-align:left}.metrics-table th{position:sticky;top:0;background:#1c3041;color:#bdddf5}.metrics-table th,.metrics-table td{padding:9px 12px;border-bottom:1px solid #2a3e4e;overflow-wrap:anywhere}.metrics-table tr:nth-child(even){background:#142230}.metrics-table td:last-child{font-variant-numeric:tabular-nums;white-space:pre-wrap}.metric-filter{background:#142333;color:#e3ecf5;border:1px solid #526b80;border-radius:5px;padding:6px 10px;min-width:140px}
.data{margin-top:8px}.data-tools{display:flex;gap:8px;margin:10px 0;align-items:center;flex-wrap:wrap}select,button{background:#142333;color:#e3ecf5;border:1px solid #526b80;border-radius:5px;padding:6px 10px}.json-tree{background:#09111a;padding:12px;max-height:480px;overflow:auto;font:13px ui-monospace,monospace}.json-tree details{margin:3px 0 3px 14px}.json-tree summary{margin:0;color:#a9d4fb}.json-value{margin:4px 0 4px 14px;white-space:pre-wrap;overflow-wrap:anywhere}.json-key{color:#a9d4fb}.json-string{color:#a5e3b8}.json-number,.json-boolean{color:#f3cd91}
.run-progress{background:#142230;border:1px solid #304859;border-radius:10px;padding:14px 16px;margin:16px 0}
.progress-meta{display:flex;align-items:center;gap:12px;margin-bottom:12px;font-size:14px;font-variant-numeric:tabular-nums}
#progress-label{flex:1;font-weight:600}#progress-percent{color:#8ee2c1;font-size:12px}#total-time{color:#bdcedd;white-space:nowrap}
#progress{display:block;width:100%;height:10px;border:0;border-radius:999px;overflow:hidden;appearance:none;-webkit-appearance:none;background:#09141e;color:#54c6aa}
#progress::-webkit-progress-bar{background:#09141e;border-radius:999px;box-shadow:inset 0 1px 3px #0005}
#progress::-webkit-progress-value{background:linear-gradient(90deg,#3198bb,#67d4a6);border-radius:999px;transition:width .4s ease}
#progress::-moz-progress-bar{background:linear-gradient(90deg,#3198bb,#67d4a6);border-radius:999px}
.run-toolbar{display:flex;align-items:center;gap:12px;margin:18px 0}.run-toolbar select{flex:1;min-width:0}.launcher label{display:flex;flex-direction:column;gap:6px;font-size:13px;color:#bdcedd}.form-grid{display:grid;grid-template-columns:1fr 1fr;gap:12px;margin:12px 0}.wide{grid-column:1/-1}input,textarea{box-sizing:border-box;background:#091923;color:#e3ecf5;border:1px solid #526b80;border-radius:5px;padding:8px;font:inherit}textarea{width:100%;font:13px ui-monospace,monospace;resize:vertical}button{cursor:pointer}button:disabled{opacity:.5;cursor:wait}.primary{background:#236f60;border-color:#4aa58d;font-weight:600}.form-error{color:#ffb4ad}.form-help{color:#9fb5c7;font-size:13px}[hidden]{display:none!important}
@media(max-width:600px){header{gap:8px;font-size:13px}body{padding:0 12px}header strong small{display:none}.form-grid{grid-template-columns:1fr}.run-progress{padding:12px}.progress-meta{gap:8px;font-size:12px}#progress-percent{display:none}}
</style>
<h1>GenIE <small>Flow monitor</small></h1><div class="run-toolbar"><label for="run-select">Run</label><select id="run-select" aria-label="Selected run"><option value="">No runs yet</option></select><button id="resume-button" type="button" hidden>Continue run</button><button id="new-run-button" type="button" hidden>New run</button></div>
<details class="launcher" id="new-run" hidden><summary>Create a new run</summary>
<form id="run-form"><div class="form-grid">
<label>Run name<input name="name" maxlength="120" placeholder="Experiment name"></label>
<label>Configuration source<select name="source" id="config-source"><option value="path">Existing workspace file</option><option value="json">Paste JSON configuration</option></select></label>
<label class="wide" id="path-field">Configuration paths (one per line, in CLI order)<textarea name="config_paths" id="config-path" rows="3" placeholder="cfg/cva5_reuseio.yml&#10;cfg/service.yml" required></textarea><span class="data-tools"><select id="config-choice" aria-label="Available configuration files"><option value="">Choose a workspace file…</option></select><button type="button" id="add-config">Add file</button></span></label>
<label class="wide" id="json-field" hidden>Configuration JSON<textarea name="config_text" rows="8" placeholder='{"meta":{"flow":["Misc.VerifyConfig"]},"BENCH":"test/smoke"}'></textarea></label>
<label class="wide">Configuration overrides (JSON object)<textarea name="overrides" rows="3" placeholder='{"BENCH":"test/smoke"}'>{}</textarea></label>
<label>CLI workers (parallel jobs)<input name="jobs" type="number" min="1" max="1024" placeholder="CLI default"><span class="form-help">Worker pool within this run; stages remain sequential. Individual tools may have their own thread settings.</span></label>
</div><details><summary>Step selection (optional)</summary><div class="form-grid"><label>From step<input name="from" placeholder="Step ID or pattern"></label><label>Through step<input name="to" placeholder="Step ID or pattern"></label><label class="wide">Skip steps<input name="skip" placeholder="Comma-separated step IDs or patterns"></label></div></details>
<p class="form-help" id="workspace-hint"></p><p class="form-error" id="form-error" role="alert"></p><button type="submit" id="launch-button" class="primary">Start and monitor</button></form></details>
<p id="run">Waiting for run…</p><section class="run-progress" aria-label="Run progress"><div class="progress-meta"><span id="progress-label">Waiting for steps…</span><span id="progress-percent"></span><span id="total-time"></span></div><progress id="progress" value="0" max="1" aria-labelledby="progress-label"></progress></section><p id="runerror"></p><p id="connection" role="status"></p><div id="global-data"></div><main id="stages"></main><details id="completed" open><summary id="completed-label">Completed stages</summary><div id="completed-stages"></div></details><details id="pending"><summary id="pending-label">Pending stages</summary><div id="pending-stages"></div></details><details class="flow"><summary>Flow log</summary><pre id="flow"></pre></details>
<script>
const cards=new Map();
let launchEnabled=false;
let activeRun=new URLSearchParams(location.search).get('run')||'',lastRunList=0;
function runURL(url,run=activeRun){const value=new URL(url,location.href);if(run)value.searchParams.set('run',run);return value.pathname+value.search}
function selectRun(id){
    activeRun=id;document.querySelector('#resume-button').hidden=true;document.querySelector('#run-select').value=id;
    const url=new URL(location.href);if(id)url.searchParams.set('run',id);else url.searchParams.delete('run');history.replaceState(null,'',url);
    for(const card of cards.values())card.el.remove();cards.clear();
    document.querySelector('#global-data').replaceChildren(dataViewer('','Run data'));
    const flow=document.querySelector('#flow');flow.textContent='';delete flow._logRun;delete flow._logKey;
    document.querySelector('#completed').open=true;document.querySelector('#pending').open=false;
    render({name:id?'Preparing run…':'Create or select a run',status:id?'starting':'idle',elapsed:0,stages:[],progress:{completed:0,total:0,skipped:0}});
    document.querySelector('#connection').textContent=id?'Connecting…':'Ready';
}
async function refreshRuns(){
    const runs=await get('/api/runs'),select=document.querySelector('#run-select');
    select.replaceChildren();
    if(!runs.length){const option=document.createElement('option');option.value='';option.textContent='No runs yet';select.append(option)}
    for(const run of runs){const option=document.createElement('option');option.value=run.id;option.textContent=(run.started?timestamp(run.started)+' · ':'')+run.name+' · '+run.status;select.append(option)}
    select.value=activeRun;
    return runs;
}
function timestamp(value){return value?new Date(value*1000).toLocaleString():''}
function duration(seconds){if(seconds==null||!Number.isFinite(seconds))return '—';seconds=Math.max(0,Math.floor(seconds));const h=Math.floor(seconds/3600),m=Math.floor(seconds%3600/60),s=seconds%60;return (h?h+'h ':'')+(h||m?m+'m ':'')+s+'s'}
async function get(url){const r=await fetch(url.startsWith('/api/')&&!['/api/app','/api/runs'].includes(url)?runURL(url):url,{cache:'no-store'});if(!r.ok)throw Error(await r.text());return r.json()}
async function logs(box,stage,key=null,live=true){
    const requestedRun=activeRun;
    if(!live&&box._logKey===key)return;
    const data=await get('/api/logs?stage='+encodeURIComponent(stage));
    if(requestedRun!==activeRun)return;
    // Check after the request: the reader may have scrolled while it was in flight.
    const first=box._logRun!==requestedRun,position=box.scrollTop;
    const following=first||box.scrollHeight-box.clientHeight-position<=24;
    const content=data.logs.map(l=>'── '+l.name+' (last 64 KiB) ──\\n'+l.text).join('\\n')||'No logs yet.';
    if(box.textContent!==content){box.textContent=content;box.scrollTop=following?box.scrollHeight:position}
    box._logRun=requestedRun;box._logKey=key;
    let links=box.previousElementSibling;
    if(!links||!links.classList.contains('downloads')){links=document.createElement('p');links.className='downloads';box.before(links)}
    const names=JSON.stringify(data.logs.map(l=>l.name));
    if(links._logNames!==names||links._logRun!==requestedRun){
        links.replaceChildren();
        for(const l of data.logs){const a=document.createElement('a');a.textContent='Full '+l.name;a.href=runURL('/api/log?stage='+encodeURIComponent(stage)+'&name='+encodeURIComponent(l.name));a.target='_blank';a.rel='noopener';links.append(a,document.createTextNode(' · '))}
        links._logNames=names;links._logRun=requestedRun;
    }
}

function jsonNode(value,key,depth=0){
    const object=value!==null&&typeof value==='object';
    const node=document.createElement(object?'details':'div');
    if(object){
        const summary=document.createElement('summary');
        summary.textContent=key+' · '+(Array.isArray(value)?'Array':'Object')+' ('+Object.keys(value).length+')';
        node.append(summary);node.open=depth<1;
        for(const [k,v] of Object.entries(value))node.append(jsonNode(v,k,depth+1));
    }else{
        node.className='json-value';
        const label=document.createElement('span'),leaf=document.createElement('span');
        label.className='json-key';label.textContent=key+': ';
        leaf.className='json-'+typeof value;leaf.textContent=JSON.stringify(value);
        node.append(label,leaf);
    }
    return node;
}
function metricsTable(metrics,filter=''){
    const rows=[];
    function collect(value,path){
        if(value!==null&&typeof value==='object'&&!Array.isArray(value)&&Object.keys(value).length){
            for(const [key,child] of Object.entries(value))collect(child,path?path+'.'+key:key);
        }else{rows.push([path,value])}
    }
    if(metrics!==null&&typeof metrics==='object')for(const [key,value] of Object.entries(metrics))collect(value,key);
    const matching=rows.filter(([key,value])=>(key+' '+JSON.stringify(value)).toLowerCase().includes(filter.toLowerCase()));
    if(!matching.length){const empty=document.createElement('p');empty.textContent=rows.length?'No matching metrics.':'No metrics recorded in this state.';return empty}
    const table=document.createElement('table'),caption=document.createElement('caption'),head=document.createElement('thead'),heading=document.createElement('tr'),body=document.createElement('tbody');
    table.className='metrics-table';caption.textContent=matching.length+' metrics';table.append(caption,head,body);head.append(heading);
    for(const title of ['Metric','Value']){const cell=document.createElement('th');cell.scope='col';cell.textContent=title;heading.append(cell)}
    for(const [key,value] of matching){
        const row=document.createElement('tr'),name=document.createElement('td'),cell=document.createElement('td');
        name.textContent=key;cell.textContent=typeof value==='string'?value:JSON.stringify(value);row.append(name,cell);body.append(row);
    }
    return table;
}
function dataViewer(stage,label){
    const panel=document.createElement('details'),summary=document.createElement('summary'),tools=document.createElement('div'),select=document.createElement('select'),refresh=document.createElement('button'),raw=document.createElement('a'),tree=document.createElement('div');
    panel.className='data';summary.textContent=label;tools.className='data-tools';tree.className='json-tree';
    select.setAttribute('aria-label','JSON file');refresh.textContent='Refresh';refresh.type='button';raw.textContent='Raw JSON';raw.target='_blank';raw.rel='noopener';
    const view=document.createElement('select'),filter=document.createElement('input');
    view.setAttribute('aria-label','Data view');
    for(const [value,text] of [['json','JSON tree'],['metrics','Metrics table']]){const option=document.createElement('option');option.value=value;option.textContent=text;view.append(option)}
    view.value='json';view.hidden=true;filter.type='search';filter.placeholder='Filter metrics…';filter.setAttribute('aria-label','Filter metrics');filter.className='metric-filter';filter.hidden=true;
    tools.append(select,view,filter,refresh,raw);panel.append(summary,tools,tree);
    let loaded=null;
    function draw(){
        const state=/^state_(in|out)[.]json$/.test(select.value);
        view.hidden=!state;filter.hidden=!state||view.value!=='metrics';
        tree.replaceChildren(state&&view.value==='metrics'?metricsTable(loaded.metrics,filter.value):jsonNode(loaded,select.value));
    }
    view.addEventListener('change',()=>{if(loaded!==null)draw()});filter.addEventListener('input',()=>{if(loaded!==null)draw()});
    const query='stage='+encodeURIComponent(stage);
    async function show(){
        if(!select.value){tree.textContent='No data files available yet.';raw.hidden=true;view.hidden=true;filter.hidden=true;loaded=null;return}
        const url='/api/data?'+query+'&name='+encodeURIComponent(select.value);raw.href=runURL(url);raw.hidden=false;
        try{loaded=await get(url);draw()}
        catch(e){loaded=null;tree.textContent='File unavailable or still being written. Try Refresh.'}
    }
    async function load(){
        try{
            const previous=select.value,files=await get('/api/files?'+query);
            select.replaceChildren();
            for(const file of files){const option=document.createElement('option');option.value=file;option.textContent=file;select.append(option)}
            if(files.includes(previous))select.value=previous;
            await show();
        }catch(e){tree.textContent='Data unavailable. Try Refresh.'}
    }
    panel.addEventListener('toggle',()=>{if(panel.open)load()});select.addEventListener('change',show);refresh.addEventListener('click',load);
    return panel;
}
document.querySelector('#global-data').append(dataViewer('','Run data'));
function render(run){
    document.querySelector('#run').textContent=(run.created||run.started?timestamp(run.created||run.started)+' · ':'')+(run.label||run.name)+' · '+run.status;
    document.querySelector('#resume-button').hidden=!launchEnabled||!run.can_resume;
    document.querySelector('#runerror').textContent=run.error||'';
    document.querySelector('#progress-label').textContent=run.progress.completed+' / '+run.progress.total+' steps completed'+(run.progress.skipped?' · '+run.progress.skipped+' skipped':'');
    document.querySelector('#progress').max=run.progress.total||1;
    document.querySelector('#progress').value=run.progress.completed;
    document.querySelector('#progress-percent').textContent=Math.round(run.progress.total?100*run.progress.completed/run.progress.total:0)+'%';
    document.querySelector('#total-time').textContent='Total elapsed: '+duration(run.elapsed);
    const visible=document.querySelector('#stages'),pending=document.querySelector('#pending-stages'),completed=document.querySelector('#completed-stages');
    const parentFor=s=>s.status==='pending'?pending:s.status==='completed'?completed:visible;
    const ids=new Set(run.stages.map(s=>s.id));
    for(const [id,card] of cards){if(!ids.has(id)){card.el.remove();cards.delete(id)}}
    for(const s of [...run.stages].reverse()){
        let card=cards.get(s.id);
        if(!card){
            const el=document.createElement('article'),head=document.createElement('header'),name=document.createElement('strong'),badge=document.createElement('span'),detail=document.createElement('details'),summary=document.createElement('summary'),pre=document.createElement('pre'),error=document.createElement('p'),timer=document.createElement('span');
            name.textContent='#'+s.number+' · '+s.name;
            name.title=s.id;
            timer.className='timer';
            error.className='stage-error';
            head.append(name,timer,badge);
            detail.append(summary,pre);
            el.append(head,error,detail,dataViewer(s.id,'Step data'));
            card={el,badge,detail,summary,pre,error,timer,status:null};
            cards.set(s.id,card);
            detail.addEventListener('toggle',()=>{if(detail.open)logs(pre,s.id).catch(e=>pre.textContent=e.message)});
        }
        card.timer.textContent=duration(s.elapsed);
        card.timer.title=s.status==='running'?'Elapsed time':'Duration';
        card.badge.textContent=s.status;
        card.badge.className='badge';
        card.el.className=s.status;
        card.summary.textContent=s.status==='running'?'Live monitor':'Logs';
        card.error.textContent=s.error||'';
        // Set defaults on transitions, preserving a user's toggle between polls.
        if(card.status!==s.status){card.detail.open=s.status==='running';card.status=s.status}
        const parent=parentFor(s);
        // Avoid moving focused/open nodes when the ordering has not changed.
        if(card.el.parentNode!==parent)parent.append(card.el);
    }
    for(const parent of [visible,completed,pending]){
        const ordered=(parent===pending?[...run.stages]:[...run.stages].reverse()).filter(s=>parentFor(s)===parent);
        ordered.forEach((s,i)=>{const el=cards.get(s.id).el;if(parent.children[i]!==el)parent.insertBefore(el,parent.children[i]||null)});
    }
    const completedCount=run.stages.filter(s=>s.status==='completed').length;
    document.querySelector('#completed-label').textContent='Completed stages ('+completedCount+')';
    document.querySelector('#completed').hidden=completedCount===0;
    const count=run.stages.filter(s=>s.status==='pending').length;
    document.querySelector('#pending-label').textContent='Pending stages ('+count+')';
    document.querySelector('#pending').hidden=count===0;
}
async function update(){
    try{
        if(Date.now()-lastRunList>3000){await refreshRuns();lastRunList=Date.now()}
        if(!activeRun)return;
        const requestedRun=activeRun,run=await get('/api/status');
        if(requestedRun!==activeRun)return;
        render(run);
        const terminal=['completed','failed','interrupted'].includes(run.status);
        const logKey=requestedRun+':'+run.status+':'+String(run.returncode);
        for(const s of run.stages){
            if(requestedRun!==activeRun)return;
            const card=cards.get(s.id);
            if(card.detail.open)await logs(card.pre,s.id,logKey+':'+s.status,!terminal&&s.status==='running');
        }
        if(document.querySelector('details.flow').open)await logs(document.querySelector('#flow'),'',logKey,!terminal);
        document.querySelector('#connection').textContent='Connected · refreshes every second';
    }catch(e){document.querySelector('#connection').textContent='Waiting / connection error: '+e.message}
    finally{setTimeout(update,1000)}
}
document.querySelector('details.flow').addEventListener('toggle',()=>{if(document.querySelector('details.flow').open)logs(document.querySelector('#flow'),'').catch(()=>{})});
document.querySelector('#run-select').addEventListener('change',event=>selectRun(event.target.value));
document.querySelector('#new-run-button').addEventListener('click',()=>{const panel=document.querySelector('#new-run');panel.open=!panel.open});
document.querySelector('#add-config').addEventListener('click',()=>{
    const choice=document.querySelector('#config-choice'),field=document.querySelector('#config-path');
    if(choice.value){const paths=field.value.split(String.fromCharCode(10)).map(path=>path.trim()).filter(Boolean);if(!paths.includes(choice.value))paths.push(choice.value);field.value=paths.join(String.fromCharCode(10))}
});
document.querySelector('#config-source').addEventListener('change',event=>{
    const inline=event.target.value==='json';document.querySelector('#path-field').hidden=inline;document.querySelector('#json-field').hidden=!inline;document.querySelector('#config-path').required=!inline;
});
document.querySelector('#resume-button').addEventListener('click',async()=>{
    const button=document.querySelector('#resume-button');button.disabled=true;
    try{
        const response=await fetch('/api/runs/'+encodeURIComponent(activeRun)+'/resume',{method:'POST',headers:{'Content-Type':'application/json'},body:'{}'}),result=await response.json();
        if(!response.ok)throw Error(result.error||'Could not continue run');
        selectRun(result.id);await refreshRuns();
    }catch(e){document.querySelector('#runerror').textContent=e.message}finally{button.disabled=false}
});
document.querySelector('#run-form').addEventListener('submit',async event=>{
    event.preventDefault();const button=document.querySelector('#launch-button'),error=document.querySelector('#form-error');error.textContent='';button.disabled=true;
    try{
        const fields=new FormData(document.querySelector('#run-form')),inline=fields.get('source')==='json';
        const body={name:fields.get('name'),config_paths:inline?[]:fields.get('config_paths').split(String.fromCharCode(10)).map(path=>path.trim()).filter(Boolean),config_text:inline?fields.get('config_text'):'',overrides:JSON.parse(fields.get('overrides')||'{}'),jobs:fields.get('jobs')?Number(fields.get('jobs')):null,from:fields.get('from'),to:fields.get('to'),skip:fields.get('skip')};
        const response=await fetch('/api/runs',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)}),result=await response.json();
        if(!response.ok)throw Error(result.error||'Could not start run');
        selectRun(result.id);await refreshRuns();document.querySelector('#new-run').open=false;
    }catch(e){error.textContent=e.message}finally{button.disabled=false}
});
async function init(){
    try{
        const app=await get('/api/app'),runs=await refreshRuns();
        launchEnabled=app.launch_enabled;
        document.querySelector('#new-run').hidden=!app.launch_enabled;document.querySelector('#new-run-button').hidden=!app.launch_enabled;
        document.querySelector('#workspace-hint').textContent=app.workspace?'Workspace: '+app.workspace+'. Runs use the same GenIE CLI and Python environment as this server.':'';
        for(const path of app.configs||[]){const option=document.createElement('option');option.value=path;option.textContent=path;document.querySelector('#config-choice').append(option)}
        selectRun(runs.some(r=>r.id===activeRun)?activeRun:(runs.length?runs[0].id:''));
        if(!runs.length&&app.launch_enabled)document.querySelector('#new-run').open=true;
    }catch(e){document.querySelector('#connection').textContent=e.message}
    update();
}
init();
</script></html>'''


def handler_for(directory=None, manager=None):
    default_root = Path(directory).resolve() if directory else None

    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):
            path = urlsplit(self.path).path
            resume = path.startswith("/api/runs/") and path.endswith("/resume")
            if (path != "/api/runs" and not resume) or manager is None:
                return self.send_error(404)
            origin = self.headers.get("Origin")
            if (origin and urlsplit(origin).netloc != self.headers.get("Host")) or self.headers.get("Sec-Fetch-Site") == "cross-site":
                return self.send_error(403, "Run submission must come from this app")
            if self.headers.get("Content-Type", "").split(";")[0].strip() != "application/json":
                return self.send_error(415, "Expected application/json")
            try:
                size = int(self.headers.get("Content-Length", "0"))
                if not 0 < size <= 1048576:
                    raise ValueError("Form must be between 1 byte and 1 MiB")
                request = json.loads(self.rfile.read(size))
                result = manager.resume(path[len("/api/runs/"):-len("/resume")]) if resume else manager.launch(request)
                return self.respond(json.dumps(result).encode(), status=201)
            except (ValueError, TypeError, AttributeError) as exc:
                return self.respond(json.dumps(dict(error=str(exc))).encode(), status=400)
            except OSError as exc:
                return self.respond(json.dumps(dict(error=str(exc))).encode(), status=500)

        def do_GET(self):
            url = urlsplit(self.path)
            try:
                if url.path == "/":
                    return self.respond(PAGE.encode(), "text/html; charset=utf-8")
                if url.path == "/api/app":
                    info = manager.app() if manager else {}
                    info["launch_enabled"] = manager is not None
                    return self.respond(json.dumps(info).encode())
                if url.path == "/api/runs":
                    runs = manager.list() if manager else [dict(id="attached", name=default_root.name, status="attached")]
                    return self.respond(json.dumps(runs).encode())
                run_id = parse_qs(url.query, keep_blank_values=True).get("run", [""])[0]
                root = manager.directory(run_id) if manager else default_root
                if root is None:
                    raise ValueError("Select or create a run")
                data = manager.snapshot(root) if manager else json.loads((root / "monitor.json").read_text())
                if url.path == "/api/status":
                    if data["status"] == "running" and time.time() - data.get("heartbeat", 0) > 15:
                        data["status"] = "unresponsive"
                        data["error"] = "No recent heartbeat. The runner may have stopped or become unavailable."
                    return self.respond(json.dumps(with_progress(data, root)).encode())
                if url.path in ("/api/files", "/api/data"):
                    params = parse_qs(url.query, keep_blank_values=True)
                    stage_id = params.get("stage", [""])[0]
                    directory = root
                    if stage_id:
                        stage = next(s for s in data["stages"] if s["id"] == stage_id)
                        if "directory" not in stage:
                            if url.path == "/api/files":
                                return self.respond(b"[]")
                            raise ValueError("Stage has not started yet")
                        directory = (root / stage["directory"]).resolve()
                    allowed = ("config.json", "state_in.json", "state_out.json", "resolved.json")
                    def permitted(name):
                        return name in allowed and directory.is_relative_to(root) and (directory / name).resolve().is_relative_to(root)
                    if url.path == "/api/files":
                        files = [name for name in allowed if permitted(name) and (directory / name).is_file()]
                        return self.respond(json.dumps(files).encode())
                    name = params.get("name", [""])[0]
                    if not permitted(name):
                        raise ValueError("Invalid data file")
                    value = json.loads((directory / name).read_text(encoding="utf8"))
                    return self.respond(json.dumps(value, indent=2, ensure_ascii=False).encode())
                if url.path in ("/api/logs", "/api/log"):
                    stage_id = parse_qs(url.query, keep_blank_values=True).get("stage", [""])[0]
                    directory = root
                    if stage_id:
                        stage = next(s for s in data["stages"] if s["id"] == stage_id)
                        if "directory" not in stage:
                            return self.respond(b'{"logs":[]}')
                        directory = (root / stage["directory"]).resolve()
                    if not directory.is_relative_to(root):
                        raise ValueError("Invalid log directory")
                    if url.path == "/api/log":
                        name = parse_qs(url.query).get("name", [""])[0]
                        path = directory / name
                        console = manager.console(root) if manager and not stage_id else None
                        if name == "cli.log" and console:
                            path = console
                        if Path(name).name != name or path.suffix != ".log" or (path != console and not path.resolve().is_relative_to(root)):
                            raise ValueError("Invalid log name")
                        with path.open("rb") as stream:
                            self.send_response(200)
                            self.send_header("Content-Type", "text/plain; charset=utf-8")
                            self.send_header("X-Content-Type-Options", "nosniff")
                            self.send_header("Cache-Control", "no-store")
                            self.end_headers()
                            while chunk := stream.read(65536):
                                self.wfile.write(chunk)
                        return
                    console = manager.console(root) if manager and not stage_id else None
                    logs = []
                    paths = sorted(directory.glob("*.log"))
                    if console and console.is_file():
                        paths.append(console)
                    for path in paths:
                        if (path != console and not path.resolve().is_relative_to(root)) or not path.is_file():
                            continue
                        with path.open("rb") as stream:
                            stream.seek(max(0, path.stat().st_size - 65536))
                            logs.append(dict(name=path.name, text=stream.read(65536).decode("utf8", errors="replace")))
                    return self.respond(json.dumps(dict(logs=logs)).encode())
                self.send_error(404)
            except (OSError, ValueError, KeyError, StopIteration) as exc:
                self.send_error(404, str(exc))

        def respond(self, body, content_type="application/json", status=200):
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *args):
            pass

    return Handler


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run_dir", type=Path, nargs="?", help="Optional existing run to monitor")
    parser.add_argument("--workspace", type=Path, default=Path.cwd(), help="Config paths and CLI working directory")
    parser.add_argument("--runs-dir", type=Path, help="Storage for runs created in the browser")
    parser.add_argument("--read-only", action="store_true", help="Disable run creation")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8080)
    args = parser.parse_args()
    if args.read_only and args.run_dir is None:
        parser.error("--read-only requires a run directory")
    from .web_runs import RunManager
    manager = None if args.read_only else RunManager(args.workspace, args.runs_dir, args.run_dir)
    server = ThreadingHTTPServer((args.host, args.port), handler_for(args.run_dir, manager))
    print(f"GenIE monitor: http://{args.host}:{server.server_port} (Ctrl-C to stop)", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
