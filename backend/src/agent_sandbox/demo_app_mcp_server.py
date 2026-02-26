"""MCP App server demonstrating interactive UI views.

Provides a system stats tool that returns an interactive HTML dashboard
rendered inline in MCP Apps-capable clients (Claude, VS Code Copilot, etc.).
"""

import logging
import os
import platform
import shutil
import time

from agent_framework.observability import configure_otel_providers, get_tracer

# Configure OpenTelemetry BEFORE FastMCP creates its internal Starlette app
configure_otel_providers()

from fastmcp import FastMCP  # noqa: E402 - must be after instrumentation
from starlette.requests import Request  # noqa: E402
from starlette.responses import JSONResponse, Response  # noqa: E402

logger = logging.getLogger(__name__)
tracer = get_tracer()

VIEW_URI = "ui://demo-app/view.html"

mcp = FastMCP(
    name="Demo App",
    instructions=(
        "MCP App server demonstrating interactive UI views. "
        "The system_stats tool returns a live dashboard with "
        "CPU, memory, and disk usage gauges."
    ),
)


@mcp.custom_route("/health", methods=["GET"])
async def health_check(request: Request) -> Response:
    """Health check endpoint."""
    return JSONResponse({"status": "ok"})


def _get_system_stats() -> dict:
    """Collect system statistics using stdlib only."""
    disk = shutil.disk_usage("/")
    disk_pct = round((disk.used / disk.total) * 100, 1)

    try:
        load_1, _, _ = os.getloadavg()
        cpu_count = os.cpu_count() or 1
        cpu_pct = round((load_1 / cpu_count) * 100, 1)
    except OSError:
        cpu_pct = 0.0
        load_1 = 0.0

    try:
        with open("/proc/meminfo") as f:
            meminfo = {}
            for line in f:
                parts = line.split(":")
                if len(parts) == 2:
                    key = parts[0].strip()
                    val = parts[1].strip().split()[0]
                    meminfo[key] = int(val)
            mem_total = meminfo.get("MemTotal", 1)
            mem_avail = meminfo.get("MemAvailable", 0)
            mem_pct = round(((mem_total - mem_avail) / mem_total) * 100, 1)
            mem_total_gb = round(mem_total / 1_048_576, 1)
            mem_used_gb = round((mem_total - mem_avail) / 1_048_576, 1)
    except (FileNotFoundError, KeyError):
        mem_pct = 0.0
        mem_total_gb = 0.0
        mem_used_gb = 0.0

    uptime_secs = time.time() - _BOOT_TIME
    hours, remainder = divmod(int(uptime_secs), 3600)
    minutes, seconds = divmod(remainder, 60)

    return {
        "cpu_percent": min(cpu_pct, 100.0),
        "memory_percent": mem_pct,
        "memory_used_gb": mem_used_gb,
        "memory_total_gb": mem_total_gb,
        "disk_percent": disk_pct,
        "disk_used_gb": round(disk.used / (1024**3), 1),
        "disk_total_gb": round(disk.total / (1024**3), 1),
        "uptime": f"{hours}h {minutes}m {seconds}s",
        "platform": platform.system(),
        "hostname": platform.node(),
        "python_version": platform.python_version(),
    }


_BOOT_TIME = time.time()


@mcp.tool(
    meta={
        "ui": {"resourceUri": VIEW_URI},
    },
)
def system_stats() -> str:
    """Returns current system statistics as a dashboard.

    Displays CPU usage, memory usage, disk usage, and uptime
    in an interactive HTML view with gauges and a refresh button.

    Returns:
        JSON string with system metrics.
    """
    import json

    with tracer.start_as_current_span("tool.system_stats.collect"):
        stats = _get_system_stats()
        stats["_view_uri"] = VIEW_URI
        logger.info(
            "System stats: cpu=%.1f%% mem=%.1f%% disk=%.1f%%",
            stats["cpu_percent"],
            stats["memory_percent"],
            stats["disk_percent"],
        )
        return json.dumps(stats, indent=2)


EMBEDDED_VIEW_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="color-scheme" content="light dark">
  <style>
    * { margin: 0; padding: 0; box-sizing: border-box; }
    body {
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
      padding: 16px;
      background: transparent;
      color: #1f2937;
    }
    @media (prefers-color-scheme: dark) {
      body { color: #e5e7eb; }
      .card { background: #1f2937 !important; border-color: #374151 !important; }
      .gauge-bg { background: #374151 !important; }
      .meta { color: #9ca3af !important; }
    }
    h2 { font-size: 16px; margin-bottom: 12px; }
    .grid { display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 12px; }
    .card {
      background: #f9fafb; border: 1px solid #e5e7eb;
      border-radius: 8px; padding: 12px;
    }
    .card-label {
      font-size: 11px; text-transform: uppercase;
      letter-spacing: 0.5px; color: #6b7280;
    }
    .card-value { font-size: 24px; font-weight: 700; margin: 4px 0; }
    .gauge-bg {
      width: 100%; height: 8px; background: #e5e7eb;
      border-radius: 4px; overflow: hidden; margin-top: 4px;
    }
    .gauge-fill {
      height: 100%; border-radius: 4px;
      transition: width 0.5s ease;
    }
    .gauge-cpu .gauge-fill { background: #3b82f6; }
    .gauge-mem .gauge-fill { background: #8b5cf6; }
    .gauge-disk .gauge-fill { background: #f59e0b; }
    .meta { font-size: 11px; color: #9ca3af; margin-top: 12px; }
    .meta span { margin-right: 12px; }
    .actions { margin-top: 12px; }
    .btn {
      background: #3b82f6; color: white; border: none;
      padding: 6px 14px; border-radius: 6px; font-size: 12px;
      cursor: pointer;
    }
    .btn:hover { background: #2563eb; }
    .btn:disabled { opacity: 0.5; cursor: not-allowed; }
    #status { font-size: 11px; color: #6b7280; margin-left: 8px; }
  </style>
</head>
<body>
  <h2>System Stats</h2>
  <div class="grid">
    <div class="card">
      <div class="card-label">CPU</div>
      <div class="card-value" id="cpu-val">—</div>
      <div class="gauge-bg gauge-cpu">
        <div class="gauge-fill" id="cpu-bar" style="width:0%"></div>
      </div>
    </div>
    <div class="card">
      <div class="card-label">Memory</div>
      <div class="card-value" id="mem-val">—</div>
      <div class="gauge-bg gauge-mem">
        <div class="gauge-fill" id="mem-bar" style="width:0%"></div>
      </div>
      <div class="meta" id="mem-detail"></div>
    </div>
    <div class="card">
      <div class="card-label">Disk</div>
      <div class="card-value" id="disk-val">—</div>
      <div class="gauge-bg gauge-disk">
        <div class="gauge-fill" id="disk-bar" style="width:0%"></div>
      </div>
      <div class="meta" id="disk-detail"></div>
    </div>
  </div>
  <div class="meta" id="info"></div>
  <div class="actions">
    <button class="btn" id="refresh-btn">Refresh</button>
    <span id="status"></span>
  </div>

  <script>
    function update(stats) {
      var el = function(id) { return document.getElementById(id); };
      el('cpu-val').textContent = stats.cpu_percent + '%';
      el('cpu-bar').style.width = stats.cpu_percent + '%';
      el('mem-val').textContent = stats.memory_percent + '%';
      el('mem-bar').style.width = stats.memory_percent + '%';
      el('mem-detail').textContent =
        stats.memory_used_gb + ' / ' + stats.memory_total_gb + ' GB';
      el('disk-val').textContent = stats.disk_percent + '%';
      el('disk-bar').style.width = stats.disk_percent + '%';
      el('disk-detail').textContent =
        stats.disk_used_gb + ' / ' + stats.disk_total_gb + ' GB';
      el('info').innerHTML =
        '<span>Uptime: ' + stats.uptime + '</span>' +
        '<span>' + stats.hostname + '</span>' +
        '<span>Python ' + stats.python_version + '</span>';
      el('status').textContent =
        'Updated ' + new Date().toLocaleTimeString();
    }
  </script>
  <script type="module">
    import { App } from "https://esm.sh/@modelcontextprotocol/ext-apps@1.1.2/app-with-deps";

    const app = new App({ name: "System Stats", version: "1.0.0" });

    app.ontoolresult = (result) => {
      if (result.structuredContent) {
        update(result.structuredContent);
      } else if (result.content) {
        const textItem = result.content.find(c => c.type === 'text');
        if (textItem && textItem.text) {
          try { update(JSON.parse(textItem.text)); } catch(e) { /* ignore */ }
        }
      }
    };

    const btn = document.getElementById('refresh-btn');
    btn.addEventListener('click', async () => {
      btn.disabled = true;
      document.getElementById('status').textContent = 'Refreshing...';
      try {
        const result = await app.callServerTool({ name: 'system_stats', arguments: {} });
        if (result.content) {
          const textItem = result.content.find(c => c.type === 'text');
          if (textItem && textItem.text) update(JSON.parse(textItem.text));
        }
      } catch(e) {
        document.getElementById('status').textContent = 'Error: ' + e.message;
      }
      btn.disabled = false;
    });

    await app.connect();
  </script>
</body>
</html>"""


@mcp.resource(
    VIEW_URI,
    mime_type="text/html;profile=mcp-app",
    meta={"ui": {"csp": {"resourceDomains": ["https://esm.sh"]}}},
)
def view() -> str:
    """HTML view resource for the system stats dashboard."""
    return EMBEDDED_VIEW_HTML


if __name__ == "__main__":
    port = int(os.environ.get("MCP_DEMO_APP_PORT", "8003"))
    mcp.run(transport="streamable-http", port=port)
