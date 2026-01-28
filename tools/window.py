import win32gui
import win32process
import win32con
import win32com.client
import psutil
import mss
import mss.tools
import os
import ctypes
import time
from datetime import datetime
from mcp.server.fastmcp import FastMCP
from tools.screen import call_vlm_api, cleanup_screenshots

# ==================== KEYBOARD INPUT HELPERS (ctypes) ====================
# C struct definitions for SendInput
PUL = ctypes.POINTER(ctypes.c_ulong)

class KeyBdInput(ctypes.Structure):
    _fields_ = [("wVk", ctypes.c_ushort),
                ("wScan", ctypes.c_ushort),
                ("dwFlags", ctypes.c_ulong),
                ("time", ctypes.c_ulong),
                ("dwExtraInfo", PUL)]

class HardwareInput(ctypes.Structure):
    _fields_ = [("uMsg", ctypes.c_ulong),
                ("wParamL", ctypes.c_short),
                ("wParamH", ctypes.c_ushort)]

class MouseInput(ctypes.Structure):
    _fields_ = [("dx", ctypes.c_long),
                ("dy", ctypes.c_long),
                ("mouseData", ctypes.c_ulong),
                ("dwFlags", ctypes.c_ulong),
                ("time", ctypes.c_ulong),
                ("dwExtraInfo", PUL)]

class Input_I(ctypes.Union):
    _fields_ = [("ki", KeyBdInput),
                ("mi", MouseInput),
                ("hi", HardwareInput)]

class Input(ctypes.Structure):
    _fields_ = [("type", ctypes.c_ulong),
                ("ii", Input_I)]

# Constants
INPUT_KEYBOARD = 1
KEYEVENTF_EXTENDEDKEY = 0x0001
KEYEVENTF_KEYUP = 0x0002
KEYEVENTF_UNICODE = 0x0004
KEYEVENTF_SCANCODE = 0x0008

# Key mapping (incomplete, but covers basics)
VK_MAPPING = {
    'backspace': 0x08, 'tab': 0x09, 'enter': 0x0D, 'shift': 0x10, 'ctrl': 0x11, 'alt': 0x12,
    'pause': 0x13, 'capslock': 0x14, 'esc': 0x1B, 'space': 0x20, 'pageup': 0x21, 'pagedown': 0x22,
    'end': 0x23, 'home': 0x24, 'left': 0x25, 'up': 0x26, 'right': 0x27, 'down': 0x28,
    'printscreen': 0x2C, 'insert': 0x2D, 'delete': 0x2E, 'lwin': 0x5B, 'rwin': 0x5C,
    'f1': 0x70, 'f2': 0x71, 'f3': 0x72, 'f4': 0x73, 'f5': 0x74, 'f6': 0x75,
    'f7': 0x76, 'f8': 0x77, 'f9': 0x78, 'f10': 0x79, 'f11': 0x7A, 'f12': 0x7B,
}

def _send_key_event(vk_code: int, scan_code: int, flags: int):
    """Send a single key event."""
    extra = ctypes.c_ulong(0)
    ii_ = Input_I()
    ii_.ki = KeyBdInput(vk_code, scan_code, flags, 0, ctypes.pointer(extra))
    x = Input(ctypes.c_ulong(INPUT_KEYBOARD), ii_)
    ctypes.windll.user32.SendInput(1, ctypes.pointer(x), ctypes.sizeof(x))

def press_key_vk(vk_code: int):
    """Press and release a virtual key."""
    _send_key_event(vk_code, 0, 0) # Down
    time.sleep(0.05)
    _send_key_event(vk_code, 0, KEYEVENTF_KEYUP) # Up

def type_unicode(text: str):
    """Type text using unicode characters."""
    for char in text:
        # Down
        _send_key_event(0, ord(char), KEYEVENTF_UNICODE)
        # Up
        _send_key_event(0, ord(char), KEYEVENTF_UNICODE | KEYEVENTF_KEYUP)

def register_window_tools(mcp: FastMCP, screenshots_dir: str, base_url: str):
    """
    Register window management tools.

    Args:
        mcp: FastMCP instance
        screenshots_dir: Directory to save screenshots
        base_url: Base URL for screenshot access
    """

    @mcp.tool(name="MyPC-get_active_window")
    def get_active_window() -> str:
        """
        Get information about the currently active window.

        Returns:
            Window title, process name, position, and size.
        """
        try:
            # Get foreground window handle
            hwnd = win32gui.GetForegroundWindow()

            # Get window title
            title = win32gui.GetWindowText(hwnd)

            # Get process ID and name
            _, pid = win32process.GetWindowThreadProcessId(hwnd)
            try:
                process = psutil.Process(pid)
                process_name = process.name()
                exe_path = process.exe()
            except:
                process_name = "Unknown"
                exe_path = "N/A"

            # Get window position and size
            left, top, right, bottom = win32gui.GetWindowRect(hwnd)
            width = right - left
            height = bottom - top

            # Check if window is minimized
            is_minimized = win32gui.IsIconic(hwnd)

            info = [
                f"Title: {title}",
                f"Process: {process_name}",
                f"PID: {pid}",
                f"Executable: {exe_path}",
                f"Position: ({left}, {top})",
                f"Size: {width}x{height}",
                f"Minimized: {'Yes' if is_minimized else 'No'}",
            ]

            return "\n".join(info)

        except Exception as e:
            return f"Error getting active window: {str(e)}"

    @mcp.tool(name="MyPC-screenshot_active_window")
    def screenshot_active_window(ai_analysis: bool = False) -> str:
        """
        Take a screenshot of the currently active window only.

        Args:
            ai_analysis: If True, use AI (VLM) to analyze image content (default: False).

        Returns:
            str: HTTP URL to the screenshot, and AI analysis if requested.
        """
        try:
            import io
            import glob
            from PIL import Image

            # Get foreground window handle
            hwnd = win32gui.GetForegroundWindow()

            # Check if minimized
            if win32gui.IsIconic(hwnd):
                return "Error: Cannot screenshot minimized window."

            # Get window position
            left, top, right, bottom = win32gui.GetWindowRect(hwnd)
            width = right - left
            height = bottom - top

            # Capture the window region
            with mss.mss() as sct:
                # Define monitor as the window region
                monitor = {
                    "left": left,
                    "top": top,
                    "width": width,
                    "height": height,
                }
                sct_img = sct.grab(monitor)

                # Convert to PIL Image
                img = Image.frombytes("RGB", sct_img.size, sct_img.bgra, "raw", "BGRX")

                # Generate filename and save
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"window_{timestamp}.png"
                filepath = os.path.join(screenshots_dir, filename)
                os.makedirs(screenshots_dir, exist_ok=True)

                # Cleanup old screenshots
                cleanup_screenshots(screenshots_dir)

                # Save to file
                img.save(filepath)

                # Get window title for info
                title = win32gui.GetWindowText(hwnd)

                # Return URL only
                url = f"{base_url}/screenshots/{filename}"
                response = f"Window screenshot captured successfully!\n\n[Window: {title} - {width}x{height}]\n\nURL: {url}"

                if ai_analysis:
                    response += "\n\n(AI Analysis requested...)"
                    try:
                        analysis = call_vlm_api(filepath)
                        response += f"\n\n=== AI Analysis (GLM-4V) ===\n{analysis}"
                    except Exception as e_ai:
                         response += f"\n\n=== AI Analysis Error ===\n{str(e_ai)}"
                else:
                    response += "\n\n(AI Analysis not requested)"

                return response

        except Exception as e:
            import traceback
            return f"Error screenshotting active window: {str(e)}\n\nTraceback:\n{traceback.format_exc()}"

    @mcp.tool(name="MyPC-list_windows")
    def list_windows() -> str:
        """
        List all top-level windows with their titles and processes.

        Returns:
            List of visible windows with process names.
        """
        try:
            windows = []

            def callback(hwnd, result):
                if win32gui.IsWindowVisible(hwnd):
                    title = win32gui.GetWindowText(hwnd)
                    if title:  # Only windows with titles
                        try:
                            _, pid = win32process.GetWindowThreadProcessId(hwnd)
                            process = psutil.Process(pid)
                            process_name = process.name()
                            result.append((title, process_name, hwnd))
                        except:
                            pass

            win32gui.EnumWindows(callback, windows)

            # Format output
            lines = ["Active Windows:"]
            for i, (title, process, hwnd) in enumerate(windows[:50], 1):  # Limit to 50
                is_foreground = " [ACTIVE]" if hwnd == win32gui.GetForegroundWindow() else ""
                lines.append(f"{i}. [{process}] {title}{is_foreground}")

            if len(windows) > 50:
                lines.append(f"... and {len(windows) - 50} more windows")

            return "\n".join(lines) if windows else "No windows found."

        except Exception as e:
            return f"Error listing windows: {str(e)}"

    @mcp.tool(name="MyPC-get_explorer_path")
    def get_explorer_path() -> str:
        """
        Get the current path of active File Explorer windows.

        Returns:
            List of Explorer windows with their current paths.
        """
        try:
            shell = win32com.client.Dispatch("Shell.Application")
            explorers = []

            # Get all explorer windows
            for window in shell.Windows():
                try:
                    # Get the full path of the window
                    location = window.LocationURL
                    hwnd = window.HWND

                    # Check if window is visible
                    if win32gui.IsWindowVisible(hwnd):
                        # Get window title
                        title = win32gui.GetWindowText(hwnd)

                        # Convert file:/// URL to path
                        if location.startswith("file:///"):
                            path = location[8:].replace("/", "\\")
                            # URL decode
                            import urllib.parse
                            path = urllib.parse.unquote(path)
                        elif location.startswith("::"):  # Virtual folder (This PC, etc.)
                            path = window.LocationName  # Use friendly name
                        else:
                            path = location

                        explorers.append(f"[{title}] {path}")
                except Exception as e:
                    # Skip windows that can't be accessed
                    continue

            if explorers:
                return "\n".join(explorers)
            else:
                return "No File Explorer windows found."

        except Exception as e:
            return f"Error getting explorer path: {str(e)}"

    @mcp.tool(name="MyPC-kill_process")
    def kill_process(process_name: str = None, pid: int = None) -> str:
        """
        Kill a process by name or PID.

        Args:
            process_name: Name of the process to kill (e.g., "notepad.exe")
            pid: Process ID to kill

        Returns:
            Success or error message.
        """
        if not process_name and not pid:
            return "Error: Either process_name or pid must be specified."

        try:
            killed = []

            if pid:
                try:
                    process = psutil.Process(pid)
                    process.kill()
                    killed.append(f"PID {pid} ({process.name()})")
                except psutil.NoSuchProcess:
                    return f"Error: No process found with PID {pid}"

            if process_name:
                # Normalize process name
                if not process_name.endswith(".exe"):
                    process_name += ".exe"

                for proc in psutil.process_iter(['name', 'pid']):
                    try:
                        if proc.info['name'] == process_name:
                            proc.kill()
                            killed.append(f"PID {proc.info['pid']} ({process_name})")
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        pass

            if killed:
                return f"Killed: {', '.join(killed)}"
            else:
                return f"No process found matching criteria."

        except Exception as e:
            return f"Error killing process: {str(e)}"

    @mcp.tool(name="MyPC-list_processes")
    def list_processes(sort_by: str = "cpu", limit: int = 20) -> str:
        """
        List running processes sorted by resource usage.

        Args:
            sort_by: Sort by 'cpu', 'memory', or 'name'
            limit: Maximum number of processes to return

        Returns:
            List of processes with resource usage.
        """
        try:
            processes = []
            # First call to populate CPU percent cache (non-blocking)
            psutil.cpu_percent(interval=None)

            for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent']):
                try:
                    # Get CPU percent without interval (uses cached value)
                    cpu = proc.cpu_percent(interval=None)
                    processes.append({
                        'pid': proc.info['pid'],
                        'name': proc.info['name'],
                        'cpu_percent': cpu,
                        'memory_percent': proc.info['memory_percent'] or 0
                    })
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass

            # Sort
            if sort_by == "cpu":
                processes.sort(key=lambda x: x['cpu_percent'], reverse=True)
            elif sort_by == "memory":
                processes.sort(key=lambda x: x['memory_percent'], reverse=True)
            elif sort_by == "name":
                processes.sort(key=lambda x: x['name'])

            # Format output
            lines = [f"{'PID':<8} {'Name':<25} {'CPU%':<8} {'Memory%':<10}"]
            lines.append("-" * 55)

            for proc in processes[:limit]:
                lines.append(
                    f"{proc['pid']:<8} "
                    f"{proc['name'][:24]:<25} "
                    f"{proc['cpu_percent']:<8.1f} "
                    f"{proc['memory_percent']:<10.2f}"
                )

            return "\n".join(lines)

        except Exception as e:
            return f"Error listing processes: {str(e)}"

    @mcp.tool(name="MyPC-get_clipboard")
    def get_clipboard() -> str:
        """
        Get current clipboard text content.

        Returns:
            Clipboard text content.
        """
        try:
            import win32clipboard
            win32clipboard.OpenClipboard()
            try:
                content = win32clipboard.GetClipboardData()
                return f"Clipboard content:\n{content}"
            finally:
                win32clipboard.CloseClipboard()
        except Exception as e:
            return f"Error reading clipboard: {str(e)}"

    @mcp.tool(name="MyPC-set_clipboard")
    def set_clipboard(text: str) -> str:
        """
        Set clipboard text content.

        Args:
            text: Text to set as clipboard content.

        Returns:
            Success message.
        """
        try:
            import win32clipboard
            win32clipboard.OpenClipboard()
            try:
                win32clipboard.EmptyClipboard()
                win32clipboard.SetClipboardText(text)
                return "Clipboard updated successfully."
            finally:
                win32clipboard.CloseClipboard()
        except Exception as e:
            return f"Error setting clipboard: {str(e)}"

    # ==================== NEW FEATURES ====================

    @mcp.tool(name="MyPC-show_notification")
    def show_notification(title: str, message: str, duration: int = 5, app_name: str = "MyPC") -> str:
        """
        Send a Windows Toast notification with a custom app name.
        Uses raw Windows API via ctypes for maximum compatibility and customization.
        """
        try:
            import win32con
            import ctypes
            from ctypes import wintypes

            # Define NOTIFYICONDATAW struct manually
            class GUID(ctypes.Structure):
                _fields_ = [
                    ("Data1", wintypes.DWORD),
                    ("Data2", wintypes.WORD),
                    ("Data3", wintypes.WORD),
                    ("Data4", wintypes.BYTE * 8)
                ]

            class NOTIFYICONDATAW(ctypes.Structure):
                _fields_ = [
                    ("cbSize", wintypes.DWORD),
                    ("hWnd", wintypes.HWND),
                    ("uID", wintypes.UINT),
                    ("uFlags", wintypes.UINT),
                    ("uCallbackMessage", wintypes.UINT),
                    ("hIcon", wintypes.HICON),
                    ("szTip", wintypes.WCHAR * 128),
                    ("dwState", wintypes.DWORD),
                    ("dwStateMask", wintypes.DWORD),
                    ("szInfo", wintypes.WCHAR * 256),
                    ("uVersion", wintypes.UINT),
                    ("szInfoTitle", wintypes.WCHAR * 64),
                    ("dwInfoFlags", wintypes.DWORD),
                    ("guidItem", GUID),
                    ("hBalloonIcon", wintypes.HICON)
                ]

            # Constants
            NIM_ADD = 0x00000000
            NIM_DELETE = 0x00000002
            NIF_MESSAGE = 0x00000001
            NIF_ICON = 0x00000002
            NIF_TIP = 0x00000004
            NIF_INFO = 0x00000010
            NIIF_INFO = 0x00000001
            WM_USER = 0x0400

            # Load icon
            # 32516 is IDI_INFORMATION
            hIcon = ctypes.windll.user32.LoadIconW(None, 32516)

            # Create hidden window
            hInstance = ctypes.windll.kernel32.GetModuleHandleW(None)
            wndClassName = "MyPCToastClass"

            # Window Procedure
            WNDPROC = ctypes.WINFUNCTYPE(wintypes.LPARAM, wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM)
            def DefWindowProc(hwnd, msg, wparam, lparam):
                return ctypes.windll.user32.DefWindowProcW(hwnd, msg, wparam, lparam)

            class WNDCLASSW(ctypes.Structure):
                _fields_ = [
                    ("style", wintypes.UINT),
                    ("lpfnWndProc", WNDPROC),
                    ("cbClsExtra", ctypes.c_int),
                    ("cbWndExtra", ctypes.c_int),
                    ("hInstance", wintypes.HINSTANCE),
                    ("hIcon", wintypes.HICON),
                    ("hCursor", wintypes.HICON),
                    ("hbrBackground", wintypes.HBRUSH),
                    ("lpszMenuName", wintypes.LPCWSTR),
                    ("lpszClassName", wintypes.LPCWSTR),
                ]

            # Register Class
            wc = WNDCLASSW()
            wc.hInstance = hInstance
            wc.lpszClassName = wndClassName
            wc.lpfnWndProc = WNDPROC(DefWindowProc)
            wc.style = 0
            ctypes.windll.user32.RegisterClassW(ctypes.byref(wc))

            # Create Window
            hWnd = ctypes.windll.user32.CreateWindowExW(
                0, wndClassName, "HiddenToastWindow", 0,
                0, 0, 0, 0,
                None, None, hInstance, None
            )

            # Prepare struct
            nid = NOTIFYICONDATAW()
            nid.cbSize = ctypes.sizeof(NOTIFYICONDATAW)
            nid.hWnd = hWnd
            nid.uID = 1
            nid.uFlags = NIF_ICON | NIF_MESSAGE | NIF_TIP | NIF_INFO
            nid.uCallbackMessage = WM_USER + 1
            nid.hIcon = hIcon
            # Strings are automatically assigned to WCHAR arrays
            nid.szTip = app_name
            nid.dwState = 0
            nid.dwStateMask = 0
            nid.szInfo = message
            nid.uVersion = 0
            nid.szInfoTitle = title
            nid.dwInfoFlags = NIIF_INFO
            nid.hBalloonIcon = None

            # Send notification
            ret = ctypes.windll.shell32.Shell_NotifyIconW(NIM_ADD, ctypes.byref(nid))

            # Clean up
            time.sleep(duration)
            ctypes.windll.shell32.Shell_NotifyIconW(NIM_DELETE, ctypes.byref(nid))
            ctypes.windll.user32.DestroyWindow(hWnd)

            if ret:
                return f"Notification sent: {title} (from {app_name})"
            else:
                return "Error: Shell_NotifyIconW returned FALSE."

        except Exception as e:
            import traceback
            return f"Error sending notification: {str(e)}\n{traceback.format_exc()}"

    @mcp.tool(name="MyPC-open_app")
    def open_app(app_name: str, arguments: str = "") -> str:
        """
        Open an application or program.

        Args:
            app_name: Application name or path (e.g., "notepad", "chrome", "C:\\path\\to\\app.exe")
            arguments: Optional command line arguments

        Returns:
            Success message or list of matching apps if path not found.
        """
        try:
            import subprocess
            import os

            # If it's a full path, try to open it directly
            if os.path.exists(app_name) or (":" in app_name and "\\" in app_name):
                subprocess.Popen(f'"{app_name}" {arguments}', shell=True)
                return f"Opened: {app_name}"

            # Try to find the application in PATH
            paths = os.environ.get('PATH', '').split(os.pathsep)
            found = False
            for path in paths:
                full_path = os.path.join(path, app_name)
                if os.path.exists(full_path):
                    subprocess.Popen(f'"{full_path}" {arguments}', shell=True)
                    return f"Opened: {full_path}"

            # Try common app locations
            common_apps = {
                "notepad": "notepad.exe",
                "calc": "calc.exe",
                "mspaint": "mspaint.exe",
                "cmd": "cmd.exe",
                "powershell": "powershell.exe",
                "explorer": "explorer.exe",
                "chrome": "chrome.exe",
                "edge": "msedge.exe",
                "firefox": "firefox.exe",
                "code": "code.exe",
            }

            if app_name.lower() in common_apps:
                # Try with shell execute
                os.startfile(common_apps[app_name.lower()])
                return f"Opened: {app_name}"

            # If nothing found, try startfile anyway (might be registered)
            try:
                os.startfile(app_name)
                return f"Opened: {app_name}"
            except:
                return f"Error: Could not find application '{app_name}'. Try full path."

        except Exception as e:
            return f"Error opening app: {str(e)}"

    @mcp.tool(name="MyPC-get_hardware_status")
    def get_hardware_status() -> str:
        """
        Get detailed hardware status including CPU, GPU, memory, and temperatures.

        Returns:
            Hardware status information.
        """
        try:
            info = []

            # CPU Info
            cpu_percent = psutil.cpu_percent(interval=0.5)
            cpu_count = psutil.cpu_count()
            cpu_freq = psutil.cpu_freq()
            info.append(f"=== CPU ===")
            info.append(f"Usage: {cpu_percent}%")
            info.append(f"Cores: {cpu_count} (Logical: {psutil.cpu_count(logical=True)})")
            if cpu_freq:
                info.append(f"Frequency: {cpu_freq.current:.0f} MHz")

            # CPU Temperature (try WMI)
            try:
                import wmi
                c = wmi.WMI()
                thermal_info = c.Win32_TemperatureProbe()
                if thermal_info:
                    info.append(f"\n=== Temperatures ===")
                    for temp in thermal_info:
                        if temp.CurrentReading:
                            info.append(f"{temp.Name}: {temp.CurrentReading / 10.0:.1f}°C")
            except:
                info.append(f"\n=== Temperatures ===")
                info.append("(Temperature monitoring not available - requires WMI/admin privileges)")

            # Memory Info
            mem = psutil.virtual_memory()
            info.append(f"\n=== Memory ===")
            info.append(f"Total: {mem.total // (1024**3)} GB")
            info.append(f"Used: {mem.used // (1024**3)} GB ({mem.percent}%)")
            info.append(f"Available: {mem.available // (1024**3)} GB")

            # GPU Info (try NVIDIA)
            info.append(f"\n=== GPU ===")
            try:
                import GPUtil
                gpus = GPUtil.getGPUs()
                if gpus:
                    for gpu in gpus:
                        info.append(f"GPU: {gpu.name}")
                        info.append(f"Load: {gpu.load * 100:.1f}%")
                        info.append(f"Memory: {gpu.memoryUsed:.0f} MB / {gpu.memoryTotal:.0f} MB ({gpu.memoryUtil * 100:.1f}%)")
                        info.append(f"Temperature: {gpu.temperature}°C")
                else:
                    info.append("No NVIDIA GPUs detected")
            except Exception as e:
                info.append(f"GPU info not available: {str(e)}")

            # Disk Info
            info.append(f"\n=== Disk ===")
            for disk in psutil.disk_partitions():
                try:
                    usage = psutil.disk_usage(disk.mountpoint)
                    info.append(f"{disk.device}: {usage.used // (1024**3)} GB / {usage.total // (1024**3)} GB ({usage.percent}%)")
                except:
                    pass

            return "\n".join(info)

        except Exception as e:
            return f"Error getting hardware status: {str(e)}"
