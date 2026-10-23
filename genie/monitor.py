"""Read-only, dependency-free monitor for a CLI run: python -m genie.monitor RUN_DIR."""
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

    def __init__(self, directory, name, steps):
        self.directory = Path(directory)
        self.lock = threading.Lock()
        self.data = dict(name=name, status="running", pid=os.getpid(), started=time.time(),
                         stages=[dict(id=s.id, name=s.name, status="pending") for s in steps])
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
                        stage.update(status=status, error=str(error))
            self.save()


PAGE = '''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>GenIE · Flow monitor</title><style>
body{font:16px system-ui;background:#101923;color:#e3ecf5;max-width:1000px;margin:40px auto;padding:0 20px}h1{margin-bottom:8px}small,#connection{color:#a6b9cb}article,details.flow{border:1px solid #344657;border-radius:8px;margin:12px 0;padding:16px}header{display:flex;justify-content:space-between;gap:20px}.badge{font-weight:bold}.completed{color:#7de1aa}.failed,.interrupted{color:#ff9b98}.running{color:#8acaff}.pending,.skipped{color:#a6b9cb}summary{cursor:pointer;margin-top:12px}pre{white-space:pre-wrap;overflow-wrap:anywhere;max-height:420px;overflow:auto;background:#09111a;padding:12px;font-size:13px}a{color:#8acaff}</style>
<h1>GenIE <small>Flow monitor</small></h1><p id="run">Waiting for run…</p><p id="runerror"></p><p id="connection" role="status"></p><main id="stages"></main><details class="flow"><summary>Flow log</summary><pre id="flow"></pre></details>
<script>
const cards=new Map();
async function get(url){const r=await fetch(url,{cache:'no-store'});if(!r.ok)throw Error(await r.text());return r.json()}
async function logs(box,stage){const data=await get('/api/logs?stage='+encodeURIComponent(stage));box.textContent=data.logs.map(l=>'── '+l.name+' (last 64 KiB) ──\\n'+l.text).join('\\n')||'No logs yet.';box.scrollTop=box.scrollHeight;let links=box.previousElementSibling;if(!links||!links.classList.contains('downloads')){links=document.createElement('p');links.className='downloads';box.before(links)}links.replaceChildren();for(const l of data.logs){const a=document.createElement('a');a.textContent='Full '+l.name;a.href='/api/log?stage='+encodeURIComponent(stage)+'&name='+encodeURIComponent(l.name);a.target='_blank';a.rel='noopener';links.append(a,document.createTextNode(' · '))}}
async function update(){try{const run=await get('/api/status');document.querySelector('#run').textContent=run.name+' · '+run.status;document.querySelector('#runerror').textContent=run.error||'';for(const s of run.stages){let card=cards.get(s.id);if(!card){const el=document.createElement('article'),head=document.createElement('header'),name=document.createElement('strong'),badge=document.createElement('span'),detail=document.createElement('details'),summary=document.createElement('summary'),pre=document.createElement('pre'),error=document.createElement('p');name.textContent=s.name+' · '+s.id;head.append(name,badge);detail.append(summary,pre);el.append(head,error,detail);document.querySelector('#stages').append(el);card={el,badge,detail,summary,pre,error};cards.set(s.id,card);detail.addEventListener('toggle',()=>{if(detail.open)logs(pre,s.id).catch(e=>pre.textContent=e.message)})}card.badge.textContent=s.status;card.badge.className='badge '+s.status;card.summary.textContent=s.status==='running'?'Live monitor':'Logs';card.error.textContent=s.error||'';if(card.detail.open)await logs(card.pre,s.id)}if(document.querySelector('details.flow').open)await logs(document.querySelector('#flow'),'');document.querySelector('#connection').textContent='Connected · refreshes every second'}catch(e){document.querySelector('#connection').textContent='Waiting / connection error: '+e.message}finally{setTimeout(update,1000)}}
document.querySelector('details.flow').addEventListener('toggle',()=>{if(document.querySelector('details.flow').open)logs(document.querySelector('#flow'),'').catch(()=>{})});update();
</script></html>'''


def handler_for(directory):
    root = Path(directory).resolve()

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            url = urlsplit(self.path)
            try:
                if url.path == "/":
                    return self.respond(PAGE.encode(), "text/html; charset=utf-8")
                data = json.loads((root / "monitor.json").read_text())
                if url.path == "/api/status":
                    if data["status"] == "running" and time.time() - data.get("heartbeat", 0) > 15:
                        data["status"] = "unresponsive"
                        data["error"] = "No recent heartbeat. The runner may have stopped or become unavailable."
                    return self.respond(json.dumps(data).encode())
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
                        if Path(name).name != name or path.suffix != ".log" or not path.resolve().is_relative_to(root):
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
                    logs = []
                    for path in sorted(directory.glob("*.log")):
                        if not path.resolve().is_relative_to(root) or not path.is_file():
                            continue
                        with path.open("rb") as stream:
                            stream.seek(max(0, path.stat().st_size - 65536))
                            logs.append(dict(name=path.name, text=stream.read(65536).decode("utf8", errors="replace")))
                    return self.respond(json.dumps(dict(logs=logs)).encode())
                self.send_error(404)
            except (OSError, ValueError, KeyError, StopIteration) as exc:
                self.send_error(404, str(exc))

        def respond(self, body, content_type="application/json"):
            self.send_response(200)
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
    parser.add_argument("run_dir", type=Path)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8080)
    args = parser.parse_args()
    server = ThreadingHTTPServer((args.host, args.port), handler_for(args.run_dir))
    print(f"GenIE monitor: http://{args.host}:{server.server_port} (Ctrl-C to stop)", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
