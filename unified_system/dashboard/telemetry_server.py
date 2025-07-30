"""
Telemetry Dashboard Server - Real-Time Visual Monitoring
=====================================================
Live web dashboard for the Unified AI Command System providing
real-time network monitoring, performance analytics, and control interface.
"""
import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
import uuid

# Web framework imports
from aiohttp import web, WSMsgType
import aiohttp_cors
from aiohttp.web_ws import WebSocketResponse

# Import unified system components
import sys
import os
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, project_root)

logger = logging.getLogger(__name__)

@dataclass
class DashboardMetrics:
    """Real-time dashboard metrics."""
    timestamp: datetime
    network_health: str
    active_agents: int
    total_commands: int
    success_rate: float
    avg_response_time: float
    patterns_shared: int
    insights_generated: int
    websocket_connections: int

class TelemetryServer:
    """Web server for the telemetry dashboard."""
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize telemetry server."""
        self.config = config
        self.host = config.get('host', 'localhost')
        self.port = config.get('port', 8080)
        
        # Web application
        self.app = web.Application()
        self.setup_routes()
        
        # WebSocket connections for real-time updates
        self.dashboard_clients: Dict[str, WebSocketResponse] = {}
        
        # Metrics collection
        self.metrics_history: List[DashboardMetrics] = []
        self.max_history = 1000
        
        # Server state
        self.runner = None
        self.site = None
        self.running = False
        self.metrics_task = None
    
    def setup_routes(self):
        """Setup HTTP routes."""
        # API endpoints
        self.app.router.add_get('/api/status', self.get_system_status)
        self.app.router.add_get('/api/metrics', self.get_metrics)
        self.app.router.add_post('/api/command', self.execute_command)
        
        # WebSocket endpoint
        self.app.router.add_get('/ws/dashboard', self.websocket_handler)
        
        # Dashboard page
        self.app.router.add_get('/', self.dashboard_home)
        self.app.router.add_get('/dashboard', self.dashboard_home)
    
    async def start_server(self):
        """Start the telemetry server."""
        try:
            logger.info(f"[DASHBOARD] Starting telemetry server on {self.host}:{self.port}")
            
            # Start metrics collection
            self.metrics_task = asyncio.create_task(self._collect_metrics_loop())
            
            # Start web server
            self.runner = web.AppRunner(self.app)
            await self.runner.setup()
            
            self.site = web.TCPSite(self.runner, self.host, self.port)
            await self.site.start()
            
            self.running = True
            logger.info(f"[DASHBOARD] Telemetry server started at http://{self.host}:{self.port}")
            
        except Exception as e:
            logger.error(f"[DASHBOARD] Failed to start server: {e}")
            raise
    
    async def stop_server(self):
        """Stop the telemetry server."""
        try:
            self.running = False
            
            # Stop metrics collection
            if self.metrics_task:
                self.metrics_task.cancel()
            
            # Close dashboard connections
            for client_id in list(self.dashboard_clients.keys()):
                await self._disconnect_dashboard_client(client_id)
            
            # Stop web server
            if self.site:
                await self.site.stop()
            if self.runner:
                await self.runner.cleanup()
            
            logger.info("[DASHBOARD] Telemetry server stopped")
            
        except Exception as e:
            logger.error(f"[DASHBOARD] Error stopping server: {e}")
    
    async def dashboard_home(self, request):
        """Serve the main dashboard page."""
        html_content = """
<!DOCTYPE html>
<html>
<head>
    <title>Unified AI Command System - Dashboard</title>
    <style>
        body { font-family: Arial, sans-serif; background: #1e3c72; color: white; margin: 0; }
        .header { background: rgba(0,0,0,0.3); padding: 1rem; }
        .dashboard-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 2rem; padding: 2rem; }
        .metric-card { background: rgba(255,255,255,0.1); border-radius: 12px; padding: 1.5rem; }
        .metric-value { font-size: 2.5rem; font-weight: bold; color: #00ff88; }
        .metric-label { font-size: 0.9rem; opacity: 0.8; }
        .btn { padding: 0.5rem 1rem; border: none; border-radius: 6px; background: #00ff88; color: #1e3c72; cursor: pointer; }
        .status-indicator { width: 12px; height: 12px; border-radius: 50%; background: #00ff88; display: inline-block; }
    </style>
</head>
<body>
    <div class="header">
        <h1><span class="status-indicator" id="networkStatus"></span> Unified AI Command System</h1>
    </div>
    
    <div class="dashboard-grid">
        <div class="metric-card">
            <div class="metric-value" id="networkHealth">OPERATIONAL</div>
            <div class="metric-label">Network Health</div>
        </div>
        
        <div class="metric-card">
            <div class="metric-value" id="activeAgents">0</div>
            <div class="metric-label">Active Agents</div>
        </div>
        
        <div class="metric-card">
            <div class="metric-value" id="totalCommands">0</div>
            <div class="metric-label">Commands Executed</div>
        </div>
        
        <div class="metric-card">
            <div class="metric-value" id="successRate">100%</div>
            <div class="metric-label">Success Rate</div>
        </div>
        
        <div class="metric-card">
            <div class="metric-value" id="responseTime">0.0s</div>
            <div class="metric-label">Response Time</div>
        </div>
        
        <div class="metric-card">
            <div class="metric-value" id="mlPatterns">0</div>
            <div class="metric-label">ML Patterns</div>
        </div>
        
        <div class="metric-card">
            <button class="btn" onclick="executeGlobalForecast()">Global Forecast</button>
            <button class="btn" onclick="executeGlobalTune()">Global Tune</button>
            <button class="btn" onclick="refreshData()">Refresh</button>
        </div>
    </div>
    
    <script>
        let ws = null;
        
        function connectWebSocket() {
            const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
            const wsUrl = `${protocol}//${window.location.host}/ws/dashboard`;
            ws = new WebSocket(wsUrl);
            
            ws.onopen = function() { console.log('Dashboard connected'); };
            ws.onmessage = function(event) {
                const data = JSON.parse(event.data);
                updateDashboard(data);
            };
            ws.onclose = function() { setTimeout(connectWebSocket, 5000); };
        }
        
        function updateDashboard(data) {
            if (data.type === 'metrics_update') {
                const metrics = data.data;
                document.getElementById('networkHealth').textContent = metrics.network_health;
                document.getElementById('activeAgents').textContent = metrics.active_agents;
                document.getElementById('totalCommands').textContent = metrics.total_commands;
                document.getElementById('successRate').textContent = (metrics.success_rate * 100).toFixed(1) + '%';
                document.getElementById('responseTime').textContent = metrics.avg_response_time.toFixed(2) + 's';
                document.getElementById('mlPatterns').textContent = metrics.patterns_shared;
            }
        }
        
        async function executeGlobalForecast() {
            const response = await fetch('/api/command', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ command: 'forecast_all', params: { symbol: 'BTCUSDT', timeframe: '1h' } })
            });
            const result = await response.json();
            alert('Global forecast: ' + (result.success ? 'Success' : 'Failed'));
        }
        
        async function executeGlobalTune() {
            const response = await fetch('/api/command', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ command: 'tune_all', params: {} })
            });
            const result = await response.json();
            alert('Global tune: ' + (result.success ? 'Success' : 'Failed'));
        }
        
        async function refreshData() {
            const response = await fetch('/api/status');
            const data = await response.json();
            updateDashboard({ type: 'metrics_update', data: data.metrics || {} });
        }
        
        connectWebSocket();
        refreshData();
        setInterval(refreshData, 30000);
    </script>
</body>
</html>
        """
        return web.Response(text=html_content, content_type='text/html')
    
    async def get_system_status(self, request):
        """Get current system status."""
        try:
            # Mock status for demo
            status = {
                'metrics': {
                    'network_health': 'OPERATIONAL',
                    'active_agents': 1,
                    'total_commands': 0,
                    'success_rate': 1.0,
                    'avg_response_time': 0.15,
                    'patterns_shared': 0
                }
            }
            return web.json_response(status)
        except Exception as e:
            return web.json_response({'error': str(e)}, status=500)
    
    async def get_metrics(self, request):
        """Get historical metrics."""
        try:
            recent_metrics = self.metrics_history[-100:]
            metrics_data = [
                {
                    'timestamp': m.timestamp.isoformat(),
                    'network_health': m.network_health,
                    'active_agents': m.active_agents,
                    'success_rate': m.success_rate
                }
                for m in recent_metrics
            ]
            return web.json_response({'metrics': metrics_data})
        except Exception as e:
            return web.json_response({'error': str(e)}, status=500)
    
    async def execute_command(self, request):
        """Execute system command."""
        try:
            data = await request.json()
            command = data.get('command')
            
            # Mock command execution
            result = {'success': True, 'message': f'Command {command} executed'}
            return web.json_response(result)
        except Exception as e:
            return web.json_response({'error': str(e)}, status=500)
    
    async def websocket_handler(self, request):
        """Handle WebSocket connections."""
        ws = WebSocketResponse()
        await ws.prepare(request)
        
        client_id = str(uuid.uuid4())
        self.dashboard_clients[client_id] = ws
        
        try:
            await self._send_dashboard_update(client_id)
            async for msg in ws:
                if msg.type == WSMsgType.TEXT:
                    data = json.loads(msg.data)
                    if data.get('type') == 'ping':
                        await ws.send_str(json.dumps({'type': 'pong'}))
        finally:
            await self._disconnect_dashboard_client(client_id)
        
        return ws
    
    async def _disconnect_dashboard_client(self, client_id: str):
        """Disconnect dashboard client."""
        if client_id in self.dashboard_clients:
            del self.dashboard_clients[client_id]
    
    async def _send_dashboard_update(self, client_id: str = None):
        """Send dashboard update."""
        try:
            update_data = {
                'type': 'metrics_update',
                'data': {
                    'network_health': 'OPERATIONAL',
                    'active_agents': 1,
                    'total_commands': 0,
                    'success_rate': 1.0,
                    'avg_response_time': 0.15,
                    'patterns_shared': 0
                }
            }
            
            message = json.dumps(update_data)
            
            if client_id and client_id in self.dashboard_clients:
                ws = self.dashboard_clients[client_id]
                if not ws.closed:
                    await ws.send_str(message)
            else:
                for ws in self.dashboard_clients.values():
                    if not ws.closed:
                        await ws.send_str(message)
        except Exception as e:
            logger.error(f"[DASHBOARD] Error sending update: {e}")
    
    async def _collect_metrics_loop(self):
        """Collect system metrics."""
        while self.running:
            try:
                # Mock metrics collection
                metrics_record = DashboardMetrics(
                    timestamp=datetime.now(),
                    network_health='OPERATIONAL',
                    active_agents=1,
                    total_commands=0,
                    success_rate=1.0,
                    avg_response_time=0.15,
                    patterns_shared=0,
                    insights_generated=0,
                    websocket_connections=len(self.dashboard_clients)
                )
                
                self.metrics_history.append(metrics_record)
                if len(self.metrics_history) > self.max_history:
                    self.metrics_history = self.metrics_history[-self.max_history:]
                
                await self._send_dashboard_update()
                await asyncio.sleep(10)
            except Exception as e:
                logger.error(f"[DASHBOARD] Metrics error: {e}")
                await asyncio.sleep(30)

# Global instance
_telemetry_server = None

def initialize_telemetry_server(config: Dict[str, Any]) -> TelemetryServer:
    """Initialize telemetry server."""
    global _telemetry_server
    _telemetry_server = TelemetryServer(config)
    return _telemetry_server

def get_telemetry_server():
    """Get telemetry server instance."""
    return _telemetry_server
