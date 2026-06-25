import re
import os
import json
import time
import asyncio
import uvicorn
import click
from datetime import datetime
from contextlib import asynccontextmanager
from fastapi import FastAPI, Query, Depends, HTTPException, Header, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse, HTMLResponse # type: ignore
from models import Food, FoodResponse, APIKeyCreate
from api import APIKeyManager
from database import get_database
from fallback import FallbackSearch
from bulk_scraper import BackgroundScraper
from pause_middleware import ScraperPauseMiddleware
from cache import cache
from db_viewer import router as db_router
from worker import WorkerNode
from coordinator import Coordinator
import config

bg_scraper = BackgroundScraper()
coordinator = None
worker_node = None
_server_start_time = time.time()

if config.NODE_MODE == "coordinator":
    coordinator = Coordinator()
elif config.NODE_MODE == "worker":
    worker_node = WorkerNode()


class LinkedServers:
    def __init__(self):
        self.file = "linked_servers.json"
        self.servers = self._load()

    def _load(self):
        if os.path.exists(self.file):
            with open(self.file) as f:
                return json.load(f)
        return {}

    def _save(self):
        with open(self.file, "w") as f:
            json.dump(self.servers, f, indent=2)

    def add(self, name: str, url: str):
        self.servers[name] = {
            "name": name,
            "url": url,
            "status": "unknown",
            "added_at": datetime.now().isoformat(),
        }
        self._save()

    def remove(self, name: str) -> bool:
        if name in self.servers:
            del self.servers[name]
            self._save()
            return True
        return False

    def get_all(self) -> list[dict]:
        return list(self.servers.values())

    def update_status(self, name: str, status: str):
        if name in self.servers:
            self.servers[name]["status"] = status
            self._save()

    async def check_all(self):
        import httpx
        for name, server in list(self.servers.items()):
            async with httpx.AsyncClient(timeout=3) as client:
                try:
                    r = await client.get(f"{server['url']}/api/health")
                    server["status"] = "online" if r.status_code == 200 else "offline"
                except Exception:
                    server["status"] = "offline"
        self._save()


linked = LinkedServers()


async def _start_scraper_delayed():
    await asyncio.sleep(2)
    await bg_scraper.start()


@asynccontextmanager
async def lifespan(application):
    if coordinator:
        await coordinator.start_health_checks()
    if worker_node:
        await worker_node.register()
        await worker_node.start_heartbeat()
    if config.BACKGROUND_SCRAPER_ENABLED and config.NODE_MODE != "worker":
        asyncio.create_task(_start_scraper_delayed())
    yield
    await bg_scraper.stop()
    if worker_node:
        await worker_node.stop()
    if coordinator:
        await coordinator.stop()

app = FastAPI(
    title="Food AI Search API",
    description="AI-powered food database search with Arabic support",
    version="2.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(GZipMiddleware, minimum_size=500)
app.add_middleware(ScraperPauseMiddleware, bg_scraper=bg_scraper)

app.include_router(db_router)


@app.middleware("http") # type: ignore
async def normalize_path(request: Request, call_next): # type: ignore
    path = request.url.path
    if "//" in path:
        normalized = path.replace("//", "/")
        request.scope["path"] = normalized
    response = await call_next(request) # type: ignore
    return response # type: ignore


@app.get("/db", response_class=HTMLResponse)
async def db_viewer_page():
    return """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Food AI - Database Viewer</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; background: #0f172a; color: #e2e8f0; min-height: 100vh; }
        .container { max-width: 1200px; margin: 0 auto; padding: 40px 20px; }
        h1 { font-size: 2rem; margin-bottom: 8px; background: linear-gradient(135deg, #38bdf8, #818cf8); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
        .subtitle { color: #94a3b8; margin-bottom: 30px; }
        .card { background: #1e293b; border-radius: 12px; padding: 24px; margin-bottom: 20px; border: 1px solid #334155; }
        .card h2 { font-size: 1.2rem; margin-bottom: 16px; color: #38bdf8; }
        .stats-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 12px; margin-bottom: 20px; }
        .stat { background: #0f172a; border-radius: 8px; padding: 16px; text-align: center; }
        .stat .value { font-size: 1.5rem; font-weight: bold; color: #38bdf8; }
        .stat .label { font-size: 0.85rem; color: #94a3b8; margin-top: 4px; }
        table { width: 100%; border-collapse: collapse; margin-top: 12px; }
        th, td { padding: 10px 12px; text-align: left; border-bottom: 1px solid #334155; font-size: 0.9rem; }
        th { background: #0f172a; color: #38bdf8; font-weight: 600; position: sticky; top: 0; }
        tr:hover { background: #334155; }
        .table-list { display: flex; gap: 10px; flex-wrap: wrap; margin-bottom: 20px; }
        .table-btn { background: #0f172a; border: 1px solid #334155; color: #e2e8f0; padding: 8px 16px; border-radius: 8px; cursor: pointer; transition: all 0.2s; font-size: 0.9rem; }
        .table-btn:hover, .table-btn.active { background: #164e63; border-color: #38bdf8; color: #38bdf8; }
        .table-btn .count { color: #94a3b8; font-size: 0.8rem; }
        textarea { width: 100%; background: #0f172a; border: 1px solid #334155; color: #e2e8f0; padding: 12px; border-radius: 8px; font-family: monospace; font-size: 0.9rem; resize: vertical; min-height: 80px; }
        textarea:focus { outline: none; border-color: #38bdf8; }
        button.primary { background: #38bdf8; color: #0f172a; border: none; padding: 10px 20px; border-radius: 8px; cursor: pointer; font-weight: 600; margin-top: 8px; }
        button.primary:hover { background: #7dd3fc; }
        button.danger { background: #ef4444; color: white; border: none; padding: 4px 10px; border-radius: 4px; cursor: pointer; font-size: 0.8rem; }
        button.danger:hover { background: #dc2626; }
        .error { color: #fca5a5; margin-top: 8px; }
        .success { color: #34d399; margin-top: 8px; }
        .pagination { display: flex; gap: 8px; margin-top: 12px; align-items: center; }
        .pagination button { background: #164e63; color: #e2e8f0; border: 1px solid #334155; padding: 6px 12px; border-radius: 6px; cursor: pointer; }
        .pagination button:disabled { opacity: 0.4; cursor: not-allowed; }
        .pagination span { color: #94a3b8; font-size: 0.9rem; }
        .schema-info { background: #0f172a; border-radius: 8px; padding: 12px; margin-top: 8px; font-size: 0.85rem; }
        .schema-info code { color: #a3e635; }
        .add-form { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; margin-top: 12px; }
        .add-form input { background: #0f172a; border: 1px solid #334155; color: #e2e8f0; padding: 8px 12px; border-radius: 6px; font-size: 0.9rem; }
        .add-form input:focus { outline: none; border-color: #38bdf8; }
        .add-form .full { grid-column: 1 / -1; }
        a.back { color: #38bdf8; text-decoration: none; margin-bottom: 20px; display: inline-block; }
        a.back:hover { text-decoration: underline; }
        .table-wrapper { overflow-x: auto; max-height: 600px; overflow-y: auto; border-radius: 8px; border: 1px solid #334155; }
    </style>
</head>
<body>
    <div class="container">
        <a class="back" href="/">&larr; Back to Dashboard</a>
        <h1>Database Viewer</h1>
        <p class="subtitle">Browse and manage the food database</p>

        <div class="card">
            <h2>Database Stats</h2>
            <div class="stats-grid" id="db-stats"></div>
        </div>

        <div class="card">
            <h2>Tables</h2>
            <div class="table-list" id="table-list"></div>
        </div>

        <div class="card" id="table-view" style="display:none;">
            <h2 id="table-title">Table Data</h2>
            <div id="schema-info"></div>
            <div class="table-wrapper">
                <table id="data-table">
                    <thead id="data-head"></thead>
                    <tbody id="data-body"></tbody>
                </table>
            </div>
            <div class="pagination" id="pagination"></div>
        </div>

        <div class="card">
            <h2>SQL Query (Read-Only)</h2>
            <textarea id="sql-input" placeholder="SELECT * FROM foods LIMIT 10"></textarea>
            <button class="primary" onclick="runQuery()">Run Query</button>
            <div id="query-result"></div>
        </div>

        <div class="card">
            <h2>Add Food Item</h2>
            <div class="add-form">
                <input id="add-name-en" placeholder="English Name" />
                <input id="add-name-ar" placeholder="Arabic Name" />
                <input id="add-carbs" type="number" placeholder="Carbs (g)" step="0.1" />
                <input id="add-category-en" placeholder="Category (EN)" />
                <input id="add-category-ar" placeholder="Category (AR)" />
                <input id="add-serving" placeholder="Serving Description" />
                <input id="add-api-key" type="password" placeholder="API Key" class="full" />
                <button class="primary full" onclick="addFood()">Add Food</button>
            </div>
            <div id="add-result"></div>
        </div>
    </div>

    <script>
        let currentPage = 1;
        let currentTable = '';

        async function loadStats() {
            const r = await fetch('/api/db/stats');
            const d = await r.json();
            const el = document.getElementById('db-stats');
            el.innerHTML = '';
            if (d.stats && d.stats.tables) {
                for (const [name, count] of Object.entries(d.stats.tables)) {
                    el.innerHTML += `<div class="stat"><div class="value">${count}</div><div class="label">${name}</div></div>`;
                }
            }
            if (d.stats && d.stats.db_size_bytes) {
                const kb = (d.stats.db_size_bytes / 1024).toFixed(1);
                el.innerHTML += `<div class="stat"><div class="value">${kb} KB</div><div class="label">DB Size</div></div>`;
            }
        }

        async function loadTables() {
            const r = await fetch('/api/db/tables');
            const d = await r.json();
            const el = document.getElementById('table-list');
            el.innerHTML = '';
            if (d.tables) {
                for (const t of d.tables) {
                    const btn = document.createElement('button');
                    btn.className = 'table-btn';
                    btn.innerHTML = `${t.name} <span class="count">(${t.row_count})</span>`;
                    btn.onclick = () => loadTable(t.name);
                    el.appendChild(btn);
                }
            }
        }

        async function loadTable(name, page = 1) {
            currentTable = name;
            currentPage = page;
            document.getElementById('table-view').style.display = 'block';
            document.getElementById('table-title').textContent = name;

            document.querySelectorAll('.table-btn').forEach(b => b.classList.remove('active'));
            const btns = document.querySelectorAll('.table-btn');
            for (const b of btns) {
                if (b.textContent.includes(name)) b.classList.add('active');
            }

            const sr = await fetch(`/api/db/table/${name}/schema`);
            const sd = await sr.json();
            const schemaEl = document.getElementById('schema-info');
            if (sd.columns) {
                schemaEl.innerHTML = '<div class="schema-info">Schema: ' +
                    sd.columns.map(c => `<code>${c.name}</code> <span style="color:#94a3b8">${c.type}</span>`).join(' &middot; ') +
                    '</div>';
            }

            const r = await fetch(`/api/db/table/${name}?page=${page}&per_page=50`);
            const d = await r.json();

            const head = document.getElementById('data-head');
            const body = document.getElementById('data-body');
            head.innerHTML = '<tr><th>#</th>' + (d.columns || []).map(c => `<th>${c}</th>`).join('') + '<th>Action</th></tr>';
            body.innerHTML = '';
            if (d.rows) {
                d.rows.forEach((row, i) => {
                    const tr = document.createElement('tr');
                    tr.innerHTML = `<td>${(page - 1) * 50 + i + 1}</td>` +
                        row.map(c => `<td>${c === null ? '<span style="color:#64748b">NULL</span>' : c}</td>`).join('') +
                        `<td><button class="danger" onclick="deleteFood('${row[0]}')">Delete</button></tr>`;
                    body.appendChild(tr);
                });
            }

            const pag = document.getElementById('pagination');
            const totalPages = Math.ceil((d.total || 0) / 50);
            pag.innerHTML = `<button ${page <= 1 ? 'disabled' : ''} onclick="loadTable('${name}', ${page - 1})">Prev</button>` +
                `<span>Page ${page} of ${totalPages} (${d.total || 0} rows)</span>` +
                `<button ${page >= totalPages ? 'disabled' : ''} onclick="loadTable('${name}', ${page + 1})">Next</button>`;
        }

        async function runQuery() {
            const sql = document.getElementById('sql-input').value.trim();
            if (!sql) return;
            const el = document.getElementById('query-result');
            try {
                const r = await fetch('/api/db/query', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({sql})
                });
                const d = await r.json();
                if (!d.success) {
                    el.innerHTML = `<p class="error">${d.detail || 'Query failed'}</p>`;
                    return;
                }
                let html = '<div class="table-wrapper" style="margin-top:12px"><table><thead><tr>';
                (d.columns || []).forEach(c => html += `<th>${c}</th>`);
                html += '</tr></thead><tbody>';
                (d.rows || []).forEach(row => {
                    html += '<tr>' + row.map(c => `<td>${c === null ? '<span style="color:#64748b">NULL</span>' : c}</td>`).join('') + '</tr>';
                });
                html += `</tbody></table></div><p style="margin-top:8px;color:#94a3b8;font-size:0.85rem">${d.row_count} rows returned</p>`;
                el.innerHTML = html;
            } catch(e) {
                el.innerHTML = `<p class="error">${e.message}</p>`;
            }
        }

        async function addFood() {
            const el = document.getElementById('add-result');
            const apiKey = document.getElementById('add-api-key').value;
            if (!apiKey) { el.innerHTML = '<p class="error">API Key required</p>'; return; }
            const food = {
                name_en: document.getElementById('add-name-en').value,
                name_ar: document.getElementById('add-name-ar').value,
                carbs: parseFloat(document.getElementById('add-carbs').value) || 0,
                category_en: document.getElementById('add-category-en').value,
                category_ar: document.getElementById('add-category-ar').value,
                serving_description: document.getElementById('add-serving').value,
            };
            if (!food.name_en) { el.innerHTML = '<p class="error">English name required</p>'; return; }
            try {
                const r = await fetch('/api/foods', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json', 'X-API-Key': apiKey},
                    body: JSON.stringify(food)
                });
                const d = await r.json();
                if (d.success) {
                    el.innerHTML = '<p class="success">Food added successfully!</p>';
                    loadTables();
                    loadStats();
                } else {
                    el.innerHTML = `<p class="error">${d.detail || 'Failed'}</p>`;
                }
            } catch(e) {
                el.innerHTML = `<p class="error">${e.message}</p>`;
            }
        }

        async function deleteFood(foodId) {
            const apiKey = prompt('Enter API Key to delete:');
            if (!apiKey) return;
            try {
                const r = await fetch(`/api/foods/${foodId}`, {
                    method: 'DELETE',
                    headers: {'X-API-Key': apiKey}
                });
                const d = await r.json();
                if (d.success) {
                    loadTable(currentTable, currentPage);
                    loadTables();
                    loadStats();
                } else {
                    alert(d.detail || 'Failed to delete');
                }
            } catch(e) {
                alert(e.message);
            }
        }

        loadStats();
        loadTables();
    </script>
</body>
</html>"""


key_manager = APIKeyManager()
fallback = FallbackSearch()


def is_arabic(query: str) -> bool:
    return bool(re.search(r'[\u0600-\u06FF]', query))


async def verify_api_key(x_api_key: str = Header(...)):
    if not key_manager.validate_key(x_api_key):
        raise HTTPException(status_code=401, detail="Invalid or inactive API key")
    return x_api_key


@app.get("/", response_class=HTMLResponse)
async def root():
    return """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Food AI</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; background: #0f172a; color: #e2e8f0; min-height: 100vh; }
        .container { max-width: 900px; margin: 0 auto; padding: 40px 20px; }
        h1 { font-size: 2.5rem; margin-bottom: 8px; background: linear-gradient(135deg, #38bdf8, #818cf8); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
        .subtitle { color: #94a3b8; margin-bottom: 40px; font-size: 1.1rem; }
        .card { background: #1e293b; border-radius: 12px; padding: 24px; margin-bottom: 20px; border: 1px solid #334155; }
        .card h2 { font-size: 1.2rem; margin-bottom: 16px; color: #38bdf8; }
        .status-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(160px, 1fr)); gap: 12px; }
        .stat { background: #0f172a; border-radius: 8px; padding: 16px; text-align: center; }
        .stat .value { font-size: 1.6rem; font-weight: bold; color: #38bdf8; }
        .stat .label { font-size: 0.85rem; color: #94a3b8; margin-top: 4px; }
        .state-badge { display: inline-block; padding: 4px 12px; border-radius: 20px; font-size: 0.85rem; font-weight: 600; }
        .state-running { background: #065f46; color: #34d399; }
        .state-idle { background: #374151; color: #9ca3af; }
        .state-stopped { background: #7f1d1d; color: #fca5a5; }
        .state-online { background: #065f46; color: #34d399; }
        .state-offline { background: #7f1d1d; color: #fca5a5; }
        .state-unknown { background: #374151; color: #9ca3af; }
        .endpoints { list-style: none; }
        .endpoints li { padding: 8px 0; border-bottom: 1px solid #334155; display: flex; align-items: center; gap: 10px; }
        .endpoints li:last-child { border-bottom: none; }
        .method { display: inline-block; padding: 2px 8px; border-radius: 4px; font-size: 0.75rem; font-weight: bold; min-width: 50px; text-align: center; }
        .get { background: #164e63; color: #22d3ee; }
        .post { background: #365314; color: #a3e635; }
        .delete { background: #7f1d1d; color: #fca5a5; }
        .endpoint-path { font-family: monospace; color: #e2e8f0; }
        a { color: #38bdf8; text-decoration: none; }
        a:hover { text-decoration: underline; }
        .links { display: flex; gap: 16px; margin-top: 20px; flex-wrap: wrap; }
        .links a { background: #1e293b; border: 1px solid #38bdf8; padding: 10px 20px; border-radius: 8px; transition: background 0.2s; }
        .links a:hover { background: #334155; text-decoration: none; }
        .server-list { list-style: none; }
        .server-item { display: flex; justify-content: space-between; align-items: center; padding: 12px; background: #0f172a; border-radius: 8px; margin-bottom: 8px; }
        .server-name { font-weight: 600; }
        .server-url { font-size: 0.85rem; color: #94a3b8; font-family: monospace; }
        .server-actions { display: flex; gap: 8px; align-items: center; }
        .badge { display: inline-block; padding: 2px 10px; border-radius: 12px; font-size: 0.75rem; font-weight: 600; }
        .badge-online { background: #065f46; color: #34d399; }
        .badge-offline { background: #7f1d1d; color: #fca5a5; }
        .badge-unknown { background: #374151; color: #9ca3af; }
        .btn-sm { background: #1e293b; border: 1px solid #334155; color: #e2e8f0; padding: 4px 12px; border-radius: 6px; cursor: pointer; font-size: 0.8rem; }
        .btn-sm:hover { background: #334155; }
        .btn-danger { border-color: #7f1d1d; color: #fca5a5; }
        .btn-danger:hover { background: #7f1d1d; }
        .btn-primary { background: #38bdf8; color: #0f172a; border: none; padding: 10px 20px; border-radius: 8px; cursor: pointer; font-weight: 600; }
        .btn-primary:hover { background: #7dd3fc; }
        .form-row { display: flex; gap: 12px; margin-top: 12px; }
        .form-row input { flex: 1; background: #0f172a; border: 1px solid #334155; color: #e2e8f0; padding: 10px 14px; border-radius: 8px; font-size: 0.9rem; }
        .form-row input:focus { outline: none; border-color: #38bdf8; }
        .msg { margin-top: 8px; font-size: 0.85rem; }
        .msg-ok { color: #34d399; }
        .msg-err { color: #fca5a5; }
        .empty { color: #64748b; font-size: 0.9rem; padding: 12px; text-align: center; }
    </style>
</head>
<body>
    <div class="container">
        <h1>Food AI</h1>
        <p class="subtitle">Bilingual food nutrition database with background scraping</p>

        <div class="card">
            <h2>Server Status</h2>
            <div class="status-grid">
                <div class="stat">
                    <div class="value" id="s-mode">-</div>
                    <div class="label">Mode</div>
                </div>
                <div class="stat">
                    <div class="value" id="s-uptime">-</div>
                    <div class="label">Uptime</div>
                </div>
                <div class="stat">
                    <div class="value" id="s-memory">-</div>
                    <div class="label">Memory</div>
                </div>
                <div class="stat">
                    <div class="value" id="s-workers">-</div>
                    <div class="label">Workers</div>
                </div>
                <div class="stat">
                    <div class="value" id="s-linked">-</div>
                    <div class="label">Linked Servers</div>
                </div>
            </div>
        </div>

        <div class="card">
            <h2>Background Scraper</h2>
            <div class="status-grid">
                <div class="stat">
                    <div class="value" id="state">-</div>
                    <div class="label">State</div>
                </div>
                <div class="stat">
                    <div class="value" id="scraped">0</div>
                    <div class="label">Foods Scraped</div>
                </div>
                <div class="stat">
                    <div class="value" id="failed">0</div>
                    <div class="label">Failed</div>
                </div>
                <div class="stat">
                    <div class="value" id="batch">0</div>
                    <div class="label">Batch #</div>
                </div>
            </div>
            <p style="margin-top:12px;color:#94a3b8;font-size:0.85rem;">Current: <span id="current">-</span></p>
        </div>

        <div class="card">
            <h2>Linked Servers</h2>
            <ul class="server-list" id="server-list"></ul>
            <div class="form-row">
                <input id="link-name" placeholder="Server name (e.g. laptop-1)" />
                <input id="link-url" placeholder="Server URL (e.g. https://device.ngrok.io)" />
                <button class="btn-primary" onclick="linkServer()">Link</button>
            </div>
            <div id="link-msg" class="msg"></div>
        </div>

        <div class="card">
            <h2>API Endpoints</h2>
            <ul class="endpoints">
                <li><span class="method get">GET</span> <span class="endpoint-path">/api/foods/search?q=</span> Search foods</li>
                <li><span class="method post">POST</span> <span class="endpoint-path">/api/foods/search</span> Search (body)</li>
                <li><span class="method get">GET</span> <span class="endpoint-path">/api/foods</span> List all foods</li>
                <li><span class="method post">POST</span> <span class="endpoint-path">/api/foods</span> Add food (auth)</li>
                <li><span class="method delete">DEL</span> <span class="endpoint-path">/api/foods/{id}</span> Delete food (auth)</li>
                <li><span class="method get">GET</span> <span class="endpoint-path">/api/scraper/status</span> Scraper status</li>
                <li><span class="method post">POST</span> <span class="endpoint-path">/api/scraper/start</span> Start scraper</li>
                <li><span class="method post">POST</span> <span class="endpoint-path">/api/scraper/stop</span> Stop scraper</li>
                <li><span class="method get">GET</span> <span class="endpoint-path">/api/server/status</span> Server status</li>
                <li><span class="method get">GET</span> <span class="endpoint-path">/api/servers</span> Linked servers</li>
            </ul>
        </div>

        <div class="links">
            <a href="/docs">API Documentation</a>
            <a href="/api/health">Health Check</a>
            <a href="/db">Database Viewer</a>
        </div>
    </div>

    <script>
        function fmtUptime(s) {
            if (s < 60) return Math.round(s) + 's';
            if (s < 3600) return Math.round(s/60) + 'm';
            return (s/3600).toFixed(1) + 'h';
        }

        async function updateServerStatus() {
            try {
                const r = await fetch('/api/server/status');
                const d = await r.json();
                document.getElementById('s-mode').textContent = d.mode;
                document.getElementById('s-uptime').textContent = fmtUptime(d.uptime);
                document.getElementById('s-memory').textContent = d.memory_mb + ' MB';
                document.getElementById('s-workers').textContent = d.active_workers + '/' + d.workers;
                document.getElementById('s-linked').textContent = d.linked_servers;
            } catch(e) {}
        }

        async function updateScraperStatus() {
            try {
                const r = await fetch('/api/scraper/status');
                const d = await r.json();
                const s = d.scraper;
                const stateEl = document.getElementById('state');
                stateEl.textContent = s.state;
                stateEl.className = 'value state-' + s.state;
                document.getElementById('scraped').textContent = s.foods_scraped;
                document.getElementById('failed').textContent = s.foods_failed;
                document.getElementById('batch').textContent = s.batch_number;
                document.getElementById('current').textContent = s.current_food || '-';
            } catch(e) {}
        }

        async function updateServers() {
            try {
                const r = await fetch('/api/servers');
                const d = await r.json();
                const el = document.getElementById('server-list');
                if (!d.servers || d.servers.length === 0) {
                    el.innerHTML = '<li class="empty">No linked servers. Add one below.</li>';
                    return;
                }
                el.innerHTML = d.servers.map(s => {
                    const badge = s.status === 'online' ? 'badge-online' : s.status === 'offline' ? 'badge-offline' : 'badge-unknown';
                    return `<li class="server-item">
                        <div>
                            <span class="server-name">${s.name}</span>
                            <span class="badge ${badge}">${s.status}</span>
                            <div class="server-url">${s.url}</div>
                        </div>
                        <div class="server-actions">
                            <button class="btn-sm" onclick="refreshServers()">Refresh</button>
                            <button class="btn-sm btn-danger" onclick="removeServer('${s.name}')">Remove</button>
                        </div>
                    </li>`;
                }).join('');
            } catch(e) {}
        }

        async function linkServer() {
            const name = document.getElementById('link-name').value.trim();
            const url = document.getElementById('link-url').value.trim();
            const msg = document.getElementById('link-msg');
            if (!name || !url) { msg.innerHTML = '<span class="msg-err">Name and URL required</span>'; return; }
            try {
                const r = await fetch('/api/servers', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({name, url})
                });
                const d = await r.json();
                if (d.success) {
                    msg.innerHTML = '<span class="msg-ok">' + d.message + '</span>';
                    document.getElementById('link-name').value = '';
                    document.getElementById('link-url').value = '';
                    updateServers();
                    updateServerStatus();
                } else {
                    msg.innerHTML = '<span class="msg-err">' + (d.detail || 'Failed') + '</span>';
                }
            } catch(e) { msg.innerHTML = '<span class="msg-err">' + e.message + '</span>'; }
        }

        async function removeServer(name) {
            try {
                await fetch('/api/servers/' + encodeURIComponent(name), {method: 'DELETE'});
                updateServers();
                updateServerStatus();
            } catch(e) {}
        }

        async function refreshServers() {
            try {
                await fetch('/api/servers/refresh');
                updateServers();
            } catch(e) {}
        }

        updateServerStatus();
        updateScraperStatus();
        updateServers();
        setInterval(updateServerStatus, 5000);
        setInterval(updateScraperStatus, 5000);
        setInterval(updateServers, 15000);
    </script>
</body>
</html>"""


_linked_round_robin = 0

async def _proxy_to_linked(method: str, path: str, json_data=None):
    global _linked_round_robin
    servers = linked.get_all()
    online = [s for s in servers if s.get("status") != "offline"]
    if not online:
        return None
    import httpx
    server = online[_linked_round_robin % len(online)]
    _linked_round_robin += 1
    async with httpx.AsyncClient(timeout=10) as client:
        try:
            url = f"{server['url']}{path}"
            if method == "GET":
                resp = await client.get(url)
            else:
                resp = await client.post(url, json=json_data)
            if resp.status_code == 200:
                return resp.json()
        except Exception:
            pass
    return None


@app.get("/api/foods/search")
async def search_foods_get(q: str = Query(..., min_length=1)):
    if coordinator and coordinator.get_active_workers():
        result = await coordinator.proxy_request("GET", f"/api/foods/search?q={q}")
        if result:
            return result

    linked_result = await _proxy_to_linked("GET", f"/api/foods/search?q={q}")
    if linked_result:
        return linked_result

    db = get_database()
    lang = "ar" if is_arabic(q) else "en"

    cached = await cache.get(q, lang)
    if cached:
        return cached

    results = db.search(q)
    if results:
        msg = f"تم العثور على {len(results)} نتيجة" if lang == "ar" else f"Found {len(results)} result(s)"
        response = FoodResponse(success=True, query=q, lang=lang, results=results, message=msg)
        await cache.set(q, lang, response.model_dump())
        return response
    fallback_result = await fallback.search(q)
    if fallback_result:
        db.add_food(fallback_result)
        msg = f"تم العثور على نتيجة (من الإنترنت)" if lang == "ar" else f"Found 1 result (from web)"
        response = FoodResponse(success=True, query=q, lang=lang, results=[fallback_result], message=msg)
        await cache.set(q, lang, response.model_dump())
        return response
    msg = f"عذراً، لم يتم العثور على نتائج لـ '{q}'" if lang == "ar" else f"Sorry, no results found for '{q}'"
    return FoodResponse(success=False, query=q, lang=lang, results=[], message=msg)


@app.post("/api/foods/search") # type: ignore
async def search_foods_post(body: dict): # type: ignore
    query = body.get("query", "")# type: ignore
    lang_param = body.get("lang", "auto") # type: ignore
    if not query:
        raise HTTPException(status_code=400, detail="Query field is required")

    linked_result = await _proxy_to_linked("POST", "/api/foods/search", json_data=body)
    if linked_result:
        return linked_result
    db = get_database()
    lang = "ar" if is_arabic(query) else "en"# type: ignore
    if lang_param in ("en", "ar"):
        lang = lang_param

    cached = await cache.get(query, lang)
    if cached:
        return cached

    results = db.search(query)# type: ignore
    if lang_param in ("en", "ar"):
        results = db._search_by_lang(query, lang) # type: ignore
    if results:
        msg = f"تم العثور على {len(results)} نتيجة" if lang == "ar" else f"Found {len(results)} result(s)"# type: ignore
        response = FoodResponse(success=True, query=query, lang=lang, results=results, message=msg)  # type: ignore
        await cache.set(query, lang, response.model_dump())
        return response
    fallback_result = await fallback.search(query)
    if fallback_result:
        db.add_food(fallback_result)
        msg = f"تم العثور على نتيجة (من الإنترنت)" if lang == "ar" else f"Found 1 result (from web)"
        response = FoodResponse(success=True, query=query, lang=lang, results=[fallback_result], message=msg) # type: ignore
        await cache.set(query, lang, response.model_dump())
        return response
    msg = f"عذراً، لم يتم العثور على نتائج لـ '{query}'" if lang == "ar" else f"Sorry, no results found for '{query}'"
    return FoodResponse(success=False, query=query, lang=lang, results=[], message=msg) # type: ignore


@app.get("/api/foods")
async def list_foods():
    db = get_database()
    foods = db.get_all()
    return {"success": True, "count": len(foods), "foods": foods}


@app.post("/api/foods")
async def add_food(food: Food, api_key: str = Depends(verify_api_key)):
    db = get_database()
    if not food.food_id:
        food.food_id = food.name_en.lower().replace(" ", "_")
    if db.add_food(food):
        return {"success": True, "message": f"Food '{food.name_en}' added successfully"}
    raise HTTPException(status_code=409, detail=f"Food '{food.food_id}' already exists")


@app.delete("/api/foods/{food_id}")
async def delete_food(food_id: str, api_key: str = Depends(verify_api_key)):
    db = get_database()
    if db.delete_food(food_id):
        return {"success": True, "message": f"Food '{food_id}' deleted successfully"}
    raise HTTPException(status_code=404, detail=f"Food '{food_id}' not found")


@app.post("/api/auth/key")
async def generate_api_key(body: APIKeyCreate):
    api_key = key_manager.generate_key(body.name)
    return {
        "success": True, # type: ignore
        "message": "API key generated. Save it - it won't be shown again!",
        "key": api_key.key,
        "name": api_key.name,
        "created_at": api_key.created_at,
    }


@app.get("/api/health")
async def health_check():
    return {"status": "healthy", "service": "Food AI Search API", "version": "2.0.0"}


@app.get("/api/ai-keys")
async def list_ai_keys():
    configured = fallback.ai.get_configured_providers()
    return {
        "success": True,
        "configured_providers": configured,
        "total": len(configured),
        "all_available": list(FallbackSearch().ai.PROVIDERS.keys()),
    }


@app.post("/api/foods/bulk")
async def add_foods_bulk(foods: list[Food], api_key: str = Depends(verify_api_key)):
    db = get_database()
    added = 0
    skipped = 0
    for food in foods:
        if not food.food_id:
            food.food_id = food.name_en.lower().replace(" ", "_")
        if db.add_food(food):
            added += 1
        else:
            skipped += 1
    return {"success": True, "added": added, "skipped": skipped, "total": len(foods)}


@app.get("/api/cache/stats")
async def cache_stats():
    return {"success": True, "cache": await cache.stats()}


@app.post("/api/cache/invalidate")
async def cache_invalidate(api_key: str = Depends(verify_api_key)):
    await cache.invalidate()
    return {"success": True, "message": "Cache invalidated"}


@app.get("/api/workers")
async def list_workers():
    if not coordinator:
        return {"success": True, "workers": [], "message": "Not in coordinator mode"}
    return {"success": True, "workers": coordinator.get_all_workers()}


@app.post("/api/workers/register")
async def register_worker(body: dict):
    if not coordinator:
        raise HTTPException(status_code=400, detail="Not in coordinator mode")
    name = body.get("name", "")
    url = body.get("url", "")
    if not name or not url:
        raise HTTPException(status_code=400, detail="name and url are required")
    worker = coordinator.register_worker(name, url)
    return {"success": True, "worker": worker}


@app.delete("/api/workers/{worker_name}")
async def deregister_worker(worker_name: str):
    if not coordinator:
        raise HTTPException(status_code=400, detail="Not in coordinator mode")
    if coordinator.deregister_worker(worker_name):
        return {"success": True, "message": f"Worker '{worker_name}' deregistered"}
    raise HTTPException(status_code=404, detail=f"Worker '{worker_name}' not found")


@app.post("/api/workers/{worker_name}/heartbeat")
async def worker_heartbeat(worker_name: str, body: dict = None):
    if not coordinator:
        raise HTTPException(status_code=400, detail="Not in coordinator mode")
    url = body.get("url") if body else None
    if coordinator.worker_heartbeat(worker_name, url):
        return {"success": True}
    raise HTTPException(status_code=404, detail=f"Worker '{worker_name}' not found")


@app.get("/api/workers/{worker_name}/status")
async def worker_status(worker_name: str):
    if not coordinator:
        raise HTTPException(status_code=400, detail="Not in coordinator mode")
    status = coordinator.get_worker_status(worker_name)
    if status:
        return {"success": True, "worker": status}
    raise HTTPException(status_code=404, detail=f"Worker '{worker_name}' not found")


@app.get("/api/coordinator/health")
async def coordinator_health():
    if not coordinator:
        return {"status": "standalone", "mode": config.NODE_MODE}
    return {
        "status": "healthy",
        "mode": "coordinator",
        "active_workers": len(coordinator.get_active_workers()),
        "total_workers": len(coordinator.workers),
    }


@app.get("/api/worker/info")
async def worker_info():
    if not worker_node:
        return {"status": "standalone", "mode": config.NODE_MODE}
    return {"success": True, "worker": worker_node.get_info()}


@app.get("/api/scraper/status")
async def scraper_status():
    return {"success": True, "scraper": bg_scraper.get_status()}


@app.post("/api/scraper/start")
async def scraper_start():
    await bg_scraper.start()
    return {"success": True, "message": "Background scraper started", "scraper": bg_scraper.get_status()}


@app.post("/api/scraper/stop")
async def scraper_stop():
    await bg_scraper.stop()
    return {"success": True, "message": "Background scraper stopped", "scraper": bg_scraper.get_status()}


@app.get("/api/server/status")
async def server_status():
    import psutil
    proc = psutil.Process()
    return {
        "success": True,
        "mode": config.NODE_MODE,
        "uptime": round(time.time() - _server_start_time, 1),
        "memory_mb": round(proc.memory_info().rss / 1024 / 1024, 1),
        "cpu_percent": proc.cpu_percent(interval=0.1),
        "workers": len(coordinator.get_all_workers()) if coordinator else 0,
        "active_workers": len(coordinator.get_active_workers()) if coordinator else 0,
        "linked_servers": len(linked.get_all()),
    }


@app.get("/api/servers")
async def list_linked_servers():
    return {"success": True, "servers": linked.get_all()}


@app.post("/api/servers")
async def add_linked_server(body: dict):
    name = body.get("name", "").strip()
    url = body.get("url", "").strip()
    if not name or not url:
        raise HTTPException(status_code=400, detail="name and url are required")
    linked.add(name, url)
    return {"success": True, "message": f"Server '{name}' linked"}


@app.delete("/api/servers/{server_name}")
async def remove_linked_server(server_name: str):
    if linked.remove(server_name):
        return {"success": True, "message": f"Server '{server_name}' removed"}
    raise HTTPException(status_code=404, detail=f"Server '{server_name}' not found")


@app.get("/api/servers/refresh")
async def refresh_linked_servers():
    await linked.check_all()
    return {"success": True, "servers": linked.get_all()}


_test_log = []

@app.post("/api/test/load-balance")
async def test_load_balance():
    servers = linked.get_all()
    if not servers:
        return {"success": False, "message": "No linked servers. Add servers from the dashboard first."}

    online = [s for s in servers if s.get("status") != "offline"]
    if not online:
        return {"success": False, "message": "All linked servers are offline."}

    results = []
    for i in range(min(9, len(online) * 3)):
        global _linked_round_robin
        server = online[_linked_round_robin % len(online)]
        _linked_round_robin += 1
        entry = {
            "request": i + 1,
            "assigned_to": server["name"],
            "server_url": server["url"],
            "round_robin_index": _linked_round_robin - 1,
        }
        _test_log.append(entry)
        results.append(entry)

    distribution = {}
    for r in results:
        name = r["assigned_to"]
        distribution[name] = distribution.get(name, 0) + 1

    return {
        "success": True,
        "requests_sent": len(results),
        "distribution": distribution,
        "log": results,
        "round_robin_counter": _linked_round_robin,
    }


@app.get("/api/test/load-balance")
async def test_load_balance_get():
    servers = linked.get_all()
    online = [s for s in servers if s.get("status") != "offline"]
    return {
        "success": True,
        "total_servers": len(servers),
        "online_servers": len(online),
        "round_robin_counter": _linked_round_robin,
        "recent_log": _test_log[-20:],
        "distribution": _calc_distribution(),
    }


def _calc_distribution():
    dist = {}
    for entry in _test_log:
        name = entry["assigned_to"]
        dist[name] = dist.get(name, 0) + 1
    return dist


@click.group()
def cli():
    pass


@cli.command()
@click.option("--query", "-q", required=True, help="Food name to search (English or Arabic)")
def search_cmd(query):
    import asyncio
    db = get_database()
    results = db.search(query)
    lang = "ar" if is_arabic(query) else "en"
    if results:
        _print_results(results, query, lang)
    else:
        print(f"\n  {'جاري البحث في الإنترنت...' if lang == 'ar' else 'Searching the web...'}\n")
        fallback_result = asyncio.run(fallback.search(query))
        if fallback_result:
            db.add_food(fallback_result)
            _print_results([fallback_result], query, lang, source_label="from web")
        else:
            print(f"\n{'عذراً، لم يتم العثور على نتائج' if lang == 'ar' else 'Sorry, no results found'} for '{query}'\n")


def _print_results(results, query, lang, source_label=""):
    label = "نتيجة" if lang == "ar" else "result(s)"
    print(f"\n{'تم العثور على' if lang == 'ar' else 'Found'} {len(results)} {label} for '{query}':\n")
    for food in results:
        name = food.name_ar if lang == "ar" else food.name_en
        other = food.name_en if lang == "ar" else food.name_ar
        cat = food.category_ar if lang == "ar" else food.category_en
        print(f"  {name} ({other})")
        print(f"    {'الكرbohydrات' if lang == 'ar' else 'Carbs'}:    {food.carbs}g")
        if cat:
            print(f"    {'الفئة' if lang == 'ar' else 'Category'}: {cat}")
        if food.serving_description:
            print(f"    {'الحصة' if lang == 'ar' else 'Serving'}:  {food.serving_description}")
        if source_label:
            print(f"    Source: {source_label} ({food.source})")
        print()


@cli.command()
@click.option("--host", default=config.HOST, help="Host to bind")
@click.option("--port", default=config.PORT, type=int, help="Port to bind")
def serve(host, port):
    print(f"Starting Food AI API on http://{host}:{port}")
    print(f"Database: {config.SQLITE_PATH}")
    uvicorn.run(app, host=host, port=port)


@cli.command()
@click.option("--name", "-n", required=True, help="API key name/label")
def generate_key(name):
    api_key = key_manager.generate_key(name)
    print(f"\nAPI Key Generated:")
    print(f"  Name: {api_key.name}")
    print(f"  Key:  {api_key.key}")
    print(f"  Created: {api_key.created_at}")
    print(f"\nSave this key - it won't be shown again!\n")


@cli.command()
def list_keys():
    keys = key_manager.list_keys()
    if keys:
        print("\nAPI Keys:\n")
        for k in keys:
            status = "active" if k.is_active else "revoked"
            print(f"  {k.name}: {k.key[:20]}... ({status})")
    else:
        print("\nNo API keys found.\n")


from bulk_scraper import bulk_scrape, scrape_single

cli.add_command(search_cmd, "search")
cli.add_command(bulk_scrape, "bulk-scrape")
cli.add_command(scrape_single, "scrape-single")


if __name__ == "__main__":
    cli()
