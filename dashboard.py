#!/usr/bin/env python3
"""SWE-Bench Pro Pipeline Dashboard — SSE 实时推送, 项目→阶段视图"""
import json, os, time, queue, threading
from datetime import datetime
from pathlib import Path
from http.server import HTTPServer, BaseHTTPRequestHandler
from socketserver import ThreadingMixIn

class ThreadingHTTPServer(ThreadingMixIn, HTTPServer):
    """多线程 HTTP Server — SSE 不阻塞其他请求"""
    daemon_threads = True

DATA_DIR = Path(os.environ.get("SWEBENCH_DATA_DIR", "pipeline_data"))
STAGES = ["discover","mine","classify","fix","verify","gate","package","qa"]
ICONS = {"done":"✅","running":"🔄","failed":"❌","pending":"⏳"}
DESCS = {"discover":"🔍 PR发现","mine":"⛏️ PR挖掘","classify":"📊 PR分类",
         "fix":"🤖 AI修复","verify":"🧪 Docker验证","gate":"🚦 门禁",
         "package":"📦 打包","qa":"✅ 质检"}

# SSE 客户端列表
_sse_clients: list[queue.Queue] = []


def notify_all():
    """通知所有 SSE 客户端刷新"""
    for q in _sse_clients[:]:
        try:
            q.put_nowait("refresh")
        except queue.Full:
            pass


def _find_projects() -> list:
    meta = {"state","history","locks","markers","queues"}
    projects = []
    if DATA_DIR.exists():
        for d in sorted(DATA_DIR.iterdir()):
            if d.is_dir() and d.name not in meta:
                projects.append(d.name)
    return projects or ["default"]


def _project_state(project: str) -> tuple:
    state_dir = DATA_DIR / project / "state"
    stages = []
    if state_dir.exists():
        for f in sorted(state_dir.iterdir()):
            if f.suffix == ".json" and not f.name.startswith("_"):
                stages.append(json.loads(f.read_text()))
    sm = {s.get("name",""): s for s in stages}
    done = sum(1 for s in stages if s.get("status")=="done")
    running = sum(1 for s in stages if s.get("status")=="running")
    failed = sum(1 for s in stages if s.get("status")=="failed")
    return sm, done, running, failed


def _project_artifacts(project: str) -> dict:
    stage_dirs = {"discover":"stage1_discover","mine":"stage2_mine",
        "classify":"stage3_classify","fix":"stage4_fix","verify":"stage5_verify",
        "gate":"stage6_gate","package":"stage7_package","qa":"stage8_qa"}
    result = {}
    for stage, dname in stage_dirs.items():
        d = DATA_DIR / project / dname
        if d.exists():
            files = [{"name":str(f.relative_to(DATA_DIR/project)),"size":f.stat().st_size}
                     for f in sorted(d.rglob("*")) if f.is_file()]
            result[stage] = {"dir": dname, "files": files[:50]}
    return result


def _render_project_panel(project: str) -> str:
    sm, done, running, failed = _project_state(project)
    cards = ""
    for name in STAGES:
        s = sm.get(name,{"status":"pending"})
        st = s.get("status","pending")
        p = s.get("items_processed",0); t = s.get("items_total",0)
        pct = min(100,int(p/max(t,1)*100)) if t else 0
        wids = s.get("worker_ids",[])
        cards += f'<div class="card {st}"><div class="sn">{ICONS.get(st,"?")} {name}</div><div class="sd">{DESCS.get(name,"")}</div><div class="bar"><div style="width:{pct}%"></div></div><div class="st"><span>{p}/{t}</span><span><a href="#" onclick="viewLogs(\'{project}\',\'{name}\');return false" style="color:#3b82f6;text-decoration:none">📋 日志</a> 👷 {len(wids)}</span></div></div>'

    artifacts = _project_artifacts(project)
    afiles = ""
    for stage in STAGES:
        a = artifacts.get(stage,{})
        if a.get("files"):
            afiles += f'<div class="afi"><b>{ICONS.get(sm.get(stage,{}).get("status","pending"),"?")} {stage}:</b> '
            afiles += ", ".join(f'{f["name"]} ({f["size"]}B)' for f in a["files"][:5])
            if len(a.get("files",[])) > 5: afiles += f" ...等{len(a['files'])}个文件"
            afiles += '</div>'

    return f"""<div class="stat"><div class="sb"><div class="sv">{done}/{len(STAGES)}</div><div class="sl">✅ 阶段</div></div><div class="sb"><div class="sv" style="color:#3b82f6">{running}</div><div class="sl">🔄 运行中</div></div><div class="sb"><div class="sv" style="color:#ef4444">{failed}</div><div class="sl">❌ 失败</div></div></div>
<div class="grid">{cards}</div>
{'<div class="artifacts"><h3>📁 产物</h3>'+afiles+'</div>' if afiles else '<div class="artifacts"><h3>📁 产物</h3><div class="afi">暂无产物</div></div>'}"""


PAGE = """<!DOCTYPE html><html lang="zh"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>SWE-Bench Pipeline</title><style>
*{margin:0;padding:0;box-sizing:border-box}body{font-family:system-ui,sans-serif;background:#0f172a;color:#e2e8f0;padding:2rem}
h1{font-size:1.5rem;margin-bottom:.5rem}h1 span{font-size:.8rem;color:#64748b;margin-left:.5rem}
.topbar{display:flex;align-items:center;gap:1rem;margin-bottom:1rem;flex-wrap:wrap}
.topbar input{background:#1e293b;border:1px solid #334155;color:#e2e8f0;padding:.5rem .75rem;border-radius:8px;width:180px}
.btn{color:#fff;border:none;padding:.5rem 1rem;border-radius:8px;cursor:pointer;font-weight:600;font-size:.85rem;transition:.2s}
.btn-run{background:#22c55e}.btn-run:hover{background:#16a34a}
.btn-run:disabled{background:#334155;cursor:not-allowed}
#status{font-size:.75rem;padding:.25rem .5rem;border-radius:4px}
#status.connected{background:#166534;color:#22c55e}
#status.disconnected{background:#991b1b;color:#ef4444}
.tabs{display:flex;gap:.5rem;margin-bottom:1.5rem;flex-wrap:wrap}
.tab{background:#1e293b;color:#94a3b8;border:none;padding:.5rem 1rem;border-radius:8px;cursor:pointer;font-size:.85rem;transition:.2s}
.tab.active,.tab:hover{background:#3b82f6;color:#fff}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(240px,1fr));gap:1rem;margin-bottom:1.5rem}
.card{background:#1e293b;border-radius:12px;padding:1.25rem;border-left:4px solid #334155;transition:all .3s}
.card.done{border-color:#22c55e}.card.running{border-color:#3b82f6;animation:pulse 2s infinite}.card.failed{border-color:#ef4444}.card.pending{opacity:.5}
@keyframes pulse{0%,100%{opacity:1}50%{opacity:.7}}
.sn{font-size:1.1rem;font-weight:600;margin-bottom:.3rem}.sd{font-size:.8rem;color:#94a3b8;margin-bottom:.5rem}
.bar{background:#334155;border-radius:4px;height:6px;overflow:hidden;margin:.5rem 0}
.bar div{background:#3b82f6;height:100%;border-radius:4px;transition:width .5s}
.st{font-size:.75rem;color:#94a3b8;display:flex;justify-content:space-between}
.stat{display:flex;gap:1rem;margin-bottom:1rem;flex-wrap:wrap}
.sb{background:#1e293b;border-radius:8px;padding:.75rem 1.25rem;text-align:center}
.sv{font-size:1.5rem;font-weight:700}.sl{font-size:.7rem;color:#94a3b8}
.artifacts{background:#1e293b;border-radius:12px;padding:1rem;margin-top:1rem}
.artifacts h3{font-size:.9rem;margin-bottom:.5rem}
.afi{font-size:.75rem;color:#94a3b8;margin:.25rem 0;word-break:break-all}
table{width:100%;border-collapse:collapse;font-size:.85rem;margin-top:1rem}
th,td{padding:.5rem .75rem;text-align:left;border-bottom:1px solid #334155}th{color:#94a3b8}
.foot{position:fixed;bottom:1rem;right:1rem;font-size:.7rem;color:#64748b}
</style></head><body>
<h1>🚀 SWE-Bench Pro Pipeline <span id="clock"></span></h1>
<div class="topbar">
<input id="run-models" value="deepseek:2" placeholder="模型:轮次">
<button class="btn btn-run" onclick="runPipeline()">▶ 运行流水线</button>
<span id="run-msg"></span>
<span id="status" class="disconnected">⏳ 连接中...</span>
</div>
<div class="tabs" id="tabs"></div>
<div id="panels"></div>
<div id="history"></div>
<div class="foot">SWE-Bench Pro Pipeline Dashboard</div>
<script>
let currentProject = '';
let pollTimer = null;

function $(id) { return document.getElementById(id); }

// === 状态轮询 (每3秒) ===
async function loadState() {
    try {
        const projs = await (await fetch('/api/projects')).json();
        let tabs = '';
        projs.forEach((p,i) => {
            tabs += `<button class="tab${i===0?' active':''}" onclick="switchProject('${p}')">${p}</button>`;
        });
        $('tabs').innerHTML = tabs;
        if (projs.length > 0 && (!currentProject || !projs.includes(currentProject))) currentProject = projs[0];
        if (currentProject) await loadProject(currentProject);
        await loadHistory();
        $('clock').textContent = new Date().toLocaleTimeString();
        $('status').textContent = '🟢 在线';
        $('status').className = 'connected';
    } catch(e) {
        $('status').textContent = '🔴 离线';
        $('status').className = 'disconnected';
    }
}

function startPolling() {
    loadState();
    pollTimer = setInterval(loadState, 3000);
}

async function loadProject(name) {
    const r = await fetch('/api/panel/'+name);
    $('panels').innerHTML = await r.text();
}

async function loadHistory() {
    const r = await fetch('/api/history');
    $('history').innerHTML = await r.text();
}

function switchProject(name) {
    currentProject = name;
    document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
    event.target.classList.add('active');
    loadProject(name);
}

// === 运行流水线 ===
async function runPipeline() {
    const btn = document.querySelector('.btn-run');
    btn.disabled = true; btn.textContent = '⏳ 启动中...';
    const proj = currentProject || 'default';
    const models = $('run-models').value || 'deepseek:2';
    try {
        const r = await fetch('/api/run', {method:'POST', body:JSON.stringify({project:proj,models:models})});
        const d = await r.json();
        $('run-msg').textContent = '✅ 已启动! 实时更新中...';
        setTimeout(() => $('run-msg').textContent = '', 8000);
    } catch(e) {
        $('run-msg').textContent = '❌ 启动失败';
    }
    btn.disabled = false; btn.textContent = '▶ 运行流水线';
}

// === 日志弹窗 ===
async function viewLogs(proj, stage) {
    const r = await fetch('/api/logs/'+proj+'/'+stage);
    const data = await r.json();
    let html = '<div id="log-modal" style="position:fixed;top:0;left:0;width:100%;height:100%;background:rgba(0,0,0,.8);z-index:999;display:flex;align-items:center;justify-content:center" onclick="if(event.target===this)this.remove()"><div style="background:#1e293b;border-radius:12px;padding:1.5rem;max-width:90%;max-height:80%;overflow:auto;width:900px"><h3 style="display:flex;justify-content:space-between"><span>📋 {proj} / {stage} 日志</span><button onclick="document.getElementById(\'log-modal\').remove()" style="background:#ef4444;color:#fff;border:none;padding:.25rem .75rem;border-radius:6px;cursor:pointer">✕</button></h3>';
    if (data.logs && data.logs.length > 0) {
        data.logs.forEach(l => {
            html += '<details style="margin:.5rem 0"><summary style="cursor:pointer;color:#3b82f6;font-size:.85rem">'+l.file+' ('+l.lines+'行, '+(l.size/1024).toFixed(1)+'KB)</summary><pre style="background:#0f172a;color:#e2e8f0;padding:.75rem;border-radius:6px;font-size:.75rem;overflow-x:auto;max-height:500px;white-space:pre-wrap;word-break:break-all">'+escapeHtml(l.tail)+'</pre></details>';
        });
    } else {
        html += '<div style="color:#94a3b8;padding:1rem">暂无日志文件</div>';
    }
    html += '</div></div>';
    document.body.insertAdjacentHTML('beforeend', html);
}
function escapeHtml(s) { return s.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;'); }

startPolling();
</script></body></html>"""


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        path = self.path.split("?")[0]
        if path == "/api/stream":
            self._handle_sse()
        elif path == "/api/artifacts":
            self._json(self._all_artifacts())
        elif path.startswith("/api/logs/"):
            # /api/logs/{project}/{stage}
            parts = path.split("/")
            self._json(self._get_logs(parts[3], parts[4] if len(parts)>4 else None))
        elif path.startswith("/api/artifacts/"):
            self._json(_project_artifacts(path.split("/")[-1]))
        elif path == "/api/projects":
            self._json(_find_projects())
        elif path.startswith("/api/panel/"):
            proj = path.split("/")[-1]
            self._html(_render_project_panel(proj))
        elif path == "/api/history":
            self._html(self._render_history())
        else:
            self.send_response(200)
            self.send_header("Content-Type","text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(PAGE.encode())

    def do_POST(self):
        if self.path == "/api/run":
            length = int(self.headers.get("Content-Length",0))
            body = json.loads(self.rfile.read(length)) if length else {}
            proj = body.get("project","default")
            models = body.get("models","deepseek:2")
            import subprocess, sys
            subprocess.Popen(
                [sys.executable, "pipeline_prefect.py", "--model", models],
                env={**os.environ, "SWEBENCH_PROJECT": proj},
                stdout=open(f"pipeline_data/{proj}/run.log","w"),
                stderr=subprocess.STDOUT,
            )
            self._json({"status":"started","project":proj})
            # 通知所有客户端
            threading.Thread(target=lambda: (time.sleep(1), notify_all()), daemon=True).start()
        else:
            self._json({"error":"not found"})

    def _handle_sse(self):
        """SSE 长连接"""
        self.send_response(200)
        self.send_header("Content-Type","text/event-stream")
        self.send_header("Cache-Control","no-cache")
        self.send_header("Connection","keep-alive")
        self.send_header("Access-Control-Allow-Origin","*")
        self.end_headers()

        q = queue.Queue(maxsize=10)
        _sse_clients.append(q)
        try:
            self.wfile.write(b"event: refresh\ndata: connected\n\n")
            self.wfile.flush()
            while True:
                try:
                    msg = q.get(timeout=30)
                    self.wfile.write(f"event: refresh\ndata: {msg}\n\n".encode())
                    self.wfile.flush()
                except queue.Empty:
                    self.wfile.write(b": heartbeat\n\n")
                    self.wfile.flush()
        except (BrokenPipeError, ConnectionResetError):
            pass
        finally:
            _sse_clients.remove(q)

    def _json(self, data):
        body = json.dumps(data, indent=2, ensure_ascii=False).encode()
        self.send_response(200)
        self.send_header("Content-Type","application/json; charset=utf-8")
        self.send_header("Content-Length",len(body))
        self.end_headers()
        self.wfile.write(body)

    def _html(self, content):
        data = content.encode()
        self.send_response(200)
        self.send_header("Content-Type","text/html; charset=utf-8")
        self.send_header("Content-Length",len(data))
        self.end_headers()
        self.wfile.write(data)

    def _all_artifacts(self):
        return {p: _project_artifacts(p) for p in _find_projects()}

    def _get_logs(self, project: str, stage: str = None):
        """读取阶段日志。stage=None 返回所有阶段日志摘要"""
        stage_dirs = {"discover":"stage1_discover","mine":"stage2_mine",
            "classify":"stage3_classify","fix":"stage4_fix","verify":"stage5_verify",
            "gate":"stage6_gate","package":"stage7_package","qa":"stage8_qa"}
        if stage and stage in stage_dirs:
            # 返回单个阶段的完整日志
            d = DATA_DIR / project / stage_dirs[stage]
            logs = []
            if d.exists():
                for f in sorted(d.rglob("*.log")):
                    content = f.read_text(errors="replace")
                    logs.append({"file": str(f.relative_to(d)), "size": len(content), "lines": len(content.splitlines()), "tail": content[-3000:]})
                for f in sorted(d.rglob("*.stdout.tmp")):
                    content = f.read_text(errors="replace")
                    logs.append({"file": str(f.relative_to(d)), "size": len(content), "lines": len(content.splitlines()), "tail": content[-3000:]})
            # 还有项目级 run.log
            run_log = DATA_DIR / project / "run.log"
            if run_log.exists():
                content = run_log.read_text(errors="replace")
                logs.append({"file": "run.log", "size": len(content), "lines": len(content.splitlines()), "tail": content[-5000:]})
            return {"project": project, "stage": stage, "logs": logs}
        else:
            # 返回所有阶段的日志摘要
            summary = {}
            for sn, dn in stage_dirs.items():
                d = DATA_DIR / project / dn
                log_count = 0
                total_lines = 0
                if d.exists():
                    for f in d.rglob("*.log"):
                        log_count += 1
                        total_lines += len(f.read_text(errors="replace").splitlines())
                sm = _project_state(project)[0]
                summary[sn] = {"status": sm.get(sn,{}).get("status","pending"), "logs": log_count, "lines": total_lines, "dir": dn}
            return {"project": project, "stages": summary}

    def _render_history(self):
        idx = DATA_DIR / "history" / "index.json"
        rows = ""
        if idx.exists():
            for r in reversed(json.loads(idx.read_text())[-15:]):
                ic = {"success":"✅","failed":"❌","running":"🔄"}.get(r.get("status",""),"?")
                rows += f'<tr><td>{ic}</td><td>{r["run_id"]}</td><td>{r.get("status","?")}</td><td>{r.get("duration_s",0):.0f}s</td><td>{r.get("instance_count",0)}</td><td>{",".join(r.get("models",[]))[:20]}</td></tr>'
        return '<h2 style="margin-top:2rem">📜 运行历史</h2><table><tr><th></th><th>ID</th><th>状态</th><th>耗时</th><th>实例</th><th>模型</th></tr>'+rows+'</table>' if rows else ''

    def log_message(self,f,*a): pass


if __name__ == "__main__":
    port = int(os.environ.get("PORT","4200"))
    print(f"Dashboard (SSE): http://0.0.0.0:{port}")
    ThreadingHTTPServer(("0.0.0.0", port), Handler).serve_forever()
