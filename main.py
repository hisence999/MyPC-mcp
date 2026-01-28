import os
import json
import socket
from mcp.server.fastmcp import FastMCP
from tools.screen import register_screen_tools
from tools.system import register_system_tools
from tools.files import register_file_tools
from tools.ssh import register_ssh_tools
from tools.window import register_window_tools
from tools.search import register_search_tools
from starlette.applications import Starlette
from starlette.routing import Route, Mount
from starlette.staticfiles import StaticFiles
from starlette.responses import Response, FileResponse
from urllib.parse import parse_qs

# Configuration
PORT = 9999
DOMAIN = "localhost"  # Public domain with IPv6
CONFIG_FILE = os.path.join(os.path.dirname(__file__), "config.json")
SCREENSHOTS_DIR = os.path.join(os.path.dirname(__file__), "screenshots")
os.makedirs(SCREENSHOTS_DIR, exist_ok=True)

def load_config():
    """Load configuration from config.json."""
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"Warning: Failed to load config.json: {e}")
    return {}

def get_local_ip():
    """Get the local IPv4 address of this machine."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        # Try to connect to a public DNS server
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        try:
            # Fallback: Get hostname then IP
            hostname = socket.gethostname()
            return socket.gethostbyname(hostname)
        except Exception:
            return "127.0.0.1"

def get_local_ipv6():
    """Get the local IPv6 address of this machine."""
    try:
        s = socket.socket(socket.AF_INET6, socket.SOCK_DGRAM)
        s.connect(("2001:4860:4860::8888", 80))  # Google DNS IPv6
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        # IPv6 fallback is harder, just return localhost
        return "::1"

# Load config
config = load_config()
SAFE_ZONES = config.get("safe_zones", None)
SSH_CONFIG = config.get("ssh", None)

def is_safe_path(path: str) -> bool:
    """Check if path is within any safe zone."""
    if not SAFE_ZONES:
        # Defaults if not configured
        default_zones = [
            os.path.expanduser("~/Documents"),
            os.path.expanduser("~/Downloads"),
            os.path.expanduser("~/Desktop"),
        ]
        zones = [os.path.abspath(z) for z in default_zones]
    else:
        zones = [os.path.abspath(z) for z in SAFE_ZONES]

    try:
        abs_path = os.path.abspath(path)
        # Normalize path case for Windows
        norm_path = os.path.normcase(abs_path)

        for zone in zones:
            abs_zone = os.path.abspath(zone)
            norm_zone = os.path.normcase(abs_zone)

            # Check if it's the zone itself
            if norm_path == norm_zone:
                return True

            # Check if it's a file inside the zone
            if not norm_zone.endswith(os.sep):
                norm_zone += os.sep

            if norm_path.startswith(norm_zone):
                return True

        return False
    except Exception:
        return False


LOCAL_IP = get_local_ip()
LOCAL_IPV6 = get_local_ipv6()
BASE_URL = f"http://{DOMAIN}:{PORT}"  # Use domain for public access

# Initialize FastMCP server
mcp = FastMCP("MyPC-MCP")

# Register tools (pass config)
register_screen_tools(mcp, SCREENSHOTS_DIR, BASE_URL)
register_system_tools(mcp)
register_file_tools(mcp, safe_zones=SAFE_ZONES, base_url=BASE_URL)
register_ssh_tools(mcp, ssh_config=SSH_CONFIG)
register_window_tools(mcp, SCREENSHOTS_DIR, BASE_URL)
register_search_tools(mcp, config=config)


class HostHeaderMiddleware:
    """
    Middleware to rewrite Host header to localhost for MCP validation.
    This allows external connections while satisfying MCP's internal checks.
    """
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] == "http":
            # Rewrite headers to make Host appear as localhost
            headers = dict(scope.get("headers", []))
            new_headers = []
            for key, value in scope.get("headers", []):
                if key == b"host":
                    new_headers.append((b"host", b"localhost:9999"))
                else:
                    new_headers.append((key, value))
            scope = dict(scope)
            scope["headers"] = new_headers
        await self.app(scope, receive, send)


class CombinedApp:
    """
    Combines MCP SSE app with static file serving and secure downloads.
    """
    def __init__(self, mcp_app, static_dir):
        self.mcp_app = mcp_app
        self.static_app = StaticFiles(directory=static_dir)

    async def __call__(self, scope, receive, send):
        path = scope.get("path", "")
        query_string = scope.get("query_string", b"").decode("utf-8")

        if path.startswith("/screenshots"):
            # Serve static files
            scope = dict(scope)
            scope["path"] = path[len("/screenshots"):]  # Remove prefix
            await self.static_app(scope, receive, send)

        elif path == "/download":
            # Secure file download
            params = parse_qs(query_string)
            file_path_list = params.get("path")

            if not file_path_list:
                response = Response("Error: Missing 'path' parameter.", status_code=400)
                await response(scope, receive, send)
                return

            file_path = file_path_list[0]

            # Security check
            if not os.path.exists(file_path):
                 response = Response("Error: File not found.", status_code=404)
                 await response(scope, receive, send)
                 return

            if not is_safe_path(file_path):
                 response = Response("Error: Access denied. File is not in a Safe Zone.", status_code=403)
                 await response(scope, receive, send)
                 return

            # Serve file
            filename = os.path.basename(file_path)
            response = FileResponse(file_path, filename=filename)
            await response(scope, receive, send)

        else:
            # Forward to MCP
            await self.mcp_app(scope, receive, send)


if __name__ == "__main__":
    import uvicorn
    print(f"Starting MyPC-MCP on port {PORT} (SSE mode)...")
    print(f"Domain: {DOMAIN}")
    print(f"Local IPv4: {LOCAL_IP}")
    print(f"Local IPv6: {LOCAL_IPV6}")
    print(f"Screenshots URL: {BASE_URL}/screenshots/")
    if SAFE_ZONES:
        print(f"Safe Zones (from config.json):")
        for zone in SAFE_ZONES:
            print(f"  - {zone}")
    else:
        print("Safe Zones: Using defaults (Documents, Downloads, Desktop)")
    print("Accepting connections from all hosts (IPv4 + IPv6)...")

    # Create combined app
    mcp_app = mcp.sse_app()
    combined = CombinedApp(mcp_app, SCREENSHOTS_DIR)
    app = HostHeaderMiddleware(combined)

    # Use "::" to listen on both IPv4 and IPv6
    uvicorn.run(app, host="::", port=PORT)
