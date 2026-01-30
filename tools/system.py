from mcp.server.fastmcp import FastMCP
import psutil

def register_system_tools(mcp: FastMCP):
    @mcp.tool(name="MyPC-get_system_status")
    def get_system_status() -> str:
        """
        Get current system status including CPU, Memory, and Battery.
        """
        cpu_percent = psutil.cpu_percent(interval=0.1)
        memory = psutil.virtual_memory()

        status = [
            f"CPU Usage: {cpu_percent}%",
            f"Memory Usage: {memory.percent}% ({memory.used // (1024*1024)}MB / {memory.total // (1024*1024)}MB)",
        ]

        if psutil.sensors_battery():
            battery = psutil.sensors_battery()
            plugged = "Plugged In" if battery.power_plugged else "On Battery"
            status.append(f"Battery: {battery.percent}% ({plugged})")
        else:
            status.append("Battery: Not Available (Desktop?)")

        return "\n".join(status)

    @mcp.tool(name="MyPC-set_volume")
    def set_volume(level: int) -> str:
        """
        Set the system master volume level.

        Args:
            level: Volume level from 0 to 100.
        """
        if not (0 <= level <= 100):
            return "Error: Volume level must be between 0 and 100."

        try:
            from comtypes import CoInitialize, CoUninitialize
            from pycaw.pycaw import AudioUtilities

            CoInitialize()

            try:
                speakers = AudioUtilities.GetSpeakers()
                volume = speakers.EndpointVolume
                scalar = level / 100.0
                volume.SetMasterVolumeLevelScalar(scalar, None)
                return f"Volume set to {level}%"
            finally:
                CoUninitialize()

        except Exception as e:
            return f"Error setting volume: {str(e)}"

    @mcp.tool(name="MyPC-get_volume")
    def get_volume() -> str:
        """
        Get the current system master volume level.
        """
        try:
            from comtypes import CoInitialize, CoUninitialize
            from pycaw.pycaw import AudioUtilities

            CoInitialize()

            try:
                speakers = AudioUtilities.GetSpeakers()
                volume = speakers.EndpointVolume
                current_volume = volume.GetMasterVolumeLevelScalar()
                mute_status = volume.GetMute()
                level = int(current_volume * 100)
                mute_text = " (Muted)" if mute_status else ""
                return f"Current volume: {level}%{mute_text}"
            finally:
                CoUninitialize()

        except Exception as e:
            return f"Error getting volume: {str(e)}"

    @mcp.tool(name="MyPC-lock_screen")
    def lock_screen() -> str:
        """
        Lock the computer screen (Windows lock screen).
        """
        try:
            import ctypes
            ctypes.windll.user32.LockWorkStation()
            return "Screen locked successfully."
        except Exception as e:
            return f"Error locking screen: {str(e)}"

    @mcp.tool(name="MyPC-sleep_display")
    def sleep_display() -> str:
        """
        Turn off the display (put monitor to sleep) - non-blocking async.
        """
        try:
            import ctypes
            import threading

            def _turn_off_display():
                # Use PostMessage for async/non-blocking call
                # HWND_BROADCAST = 0xFFFF, WM_SYSCOMMAND = 0x0112, SC_MONITORPOWER = 0xF170
                # Power off = 2
                ctypes.windll.user32.PostMessageW(0xFFFF, 0x0112, 0xF170, 2)

            # Run in background thread to avoid blocking
            thread = threading.Thread(target=_turn_off_display, daemon=True)
            thread.start()

            return "Display turn-off command sent (async)."
        except Exception as e:
            return f"Error turning off display: {str(e)}"

    @mcp.tool(name="MyPC-hibernate")
    def hibernate() -> str:
        """
        Put the computer into hibernation/sleep mode.
        """
        try:
            import ctypes
            ctypes.windll.powrprof.SetSuspendState(0, 1, 0)
            return "Computer is going to sleep..."
        except Exception as e:
            return f"Error hibernating: {str(e)}"
