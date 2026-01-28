import paramiko
from mcp.server.fastmcp import FastMCP

# Default command whitelist for safety
DEFAULT_ALLOWED_COMMANDS = [
    "ls", "pwd", "whoami", "hostname", "uptime", "df", "free",
    "cat", "head", "tail", "grep", "find", "wc",
    "ps", "top", "htop",
    "docker", "docker-compose",
    "git", "npm", "node", "python", "pip",
    "systemctl", "service",
    "ping", "curl", "wget",
    "date", "cal", "echo",
]


def register_ssh_tools(mcp: FastMCP, ssh_config: dict = None):
    """
    Register SSH tools for remote server management.

    Args:
        mcp: FastMCP instance
        ssh_config: Optional dict with SSH configuration:
            - hosts: Dict of named hosts with connection info
            - allowed_commands: List of allowed command prefixes
    """
    config = ssh_config or {}
    hosts = config.get("hosts", {})
    allowed_commands = config.get("allowed_commands", DEFAULT_ALLOWED_COMMANDS)

    def is_command_allowed(command: str) -> bool:
        """Check if command is in whitelist."""
        cmd_name = command.strip().split()[0] if command.strip() else ""
        return any(cmd_name == allowed or cmd_name.startswith(allowed + " ")
                   for allowed in allowed_commands)

    def get_allowed_commands_str() -> str:
        return ", ".join(allowed_commands)

    @mcp.tool(name="MyPC-ssh_list_hosts")
    def ssh_list_hosts() -> str:
        """
        List all configured SSH hosts.

        Returns:
            List of available host names and their addresses.
        """
        if not hosts:
            return "No SSH hosts configured. Add hosts to config.json under 'ssh.hosts'."

        lines = ["Configured SSH Hosts:"]
        for name, info in hosts.items():
            host = info.get("host", "?")
            port = info.get("port", 22)
            user = info.get("user", "?")
            lines.append(f"  - {name}: {user}@{host}:{port}")

        return "\n".join(lines)

    @mcp.tool(name="MyPC-ssh_execute")
    def ssh_execute(host_name: str, command: str) -> str:
        """
        Execute a command on a remote SSH server.

        Args:
            host_name: Name of the configured host (use ssh_list_hosts to see available hosts).
            command: Command to execute (must be in allowed commands list).

        Returns:
            Command output or error message.
        """
        # Validate host
        if host_name not in hosts:
            available = ", ".join(hosts.keys()) if hosts else "none"
            return f"Error: Unknown host '{host_name}'. Available hosts: {available}"

        # Validate command
        if not is_command_allowed(command):
            return f"Error: Command not allowed. Allowed commands: {get_allowed_commands_str()}"

        host_info = hosts[host_name]
        hostname = host_info.get("host")
        port = host_info.get("port", 22)
        username = host_info.get("user")
        password = host_info.get("password")
        key_file = host_info.get("key_file")

        if not hostname or not username:
            return f"Error: Host '{host_name}' is missing required 'host' or 'user' configuration."

        try:
            # Create SSH client
            client = paramiko.SSHClient()
            client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

            # Connect
            connect_kwargs = {
                "hostname": hostname,
                "port": port,
                "username": username,
                "timeout": 10,
            }

            if key_file:
                connect_kwargs["key_filename"] = key_file
            elif password:
                connect_kwargs["password"] = password
            else:
                return f"Error: Host '{host_name}' has no password or key_file configured."

            client.connect(**connect_kwargs)

            # Execute command
            stdin, stdout, stderr = client.exec_command(command, timeout=30)

            # Get output - try multiple encodings
            out_bytes = stdout.read()
            err_bytes = stderr.read()

            # Try UTF-8 first, then GBK (Windows Chinese), then fallback
            for encoding in ['utf-8', 'gbk', 'gb2312', 'latin-1']:
                try:
                    out = out_bytes.decode(encoding)
                    break
                except UnicodeDecodeError:
                    continue
            else:
                out = out_bytes.decode('utf-8', errors='replace')

            for encoding in ['utf-8', 'gbk', 'gb2312', 'latin-1']:
                try:
                    err = err_bytes.decode(encoding)
                    break
                except UnicodeDecodeError:
                    continue
            else:
                err = err_bytes.decode('utf-8', errors='replace')

            exit_code = stdout.channel.recv_exit_status()

            client.close()

            # Format result
            result = []
            if out:
                result.append(f"STDOUT:\n{out}")
            if err:
                result.append(f"STDERR:\n{err}")
            result.append(f"Exit Code: {exit_code}")

            return "\n".join(result) if result else "Command completed with no output."

        except paramiko.AuthenticationException:
            return f"Error: Authentication failed for {username}@{hostname}"
        except paramiko.SSHException as e:
            return f"Error: SSH connection failed: {str(e)}"
        except Exception as e:
            return f"Error: {str(e)}"

    @mcp.tool(name="MyPC-ssh_allowed_commands")
    def ssh_allowed_commands() -> str:
        """
        List all allowed SSH commands.

        Returns:
            List of command prefixes that are allowed to execute.
        """
        return f"Allowed SSH Commands:\n{get_allowed_commands_str()}"

    @mcp.tool(name="MyPC-ssh_test_connection")
    def ssh_test_connection(host_name: str) -> str:
        """
        Test SSH connection to a configured host.

        Args:
            host_name: Name of the configured host.

        Returns:
            Connection status message.
        """
        if host_name not in hosts:
            available = ", ".join(hosts.keys()) if hosts else "none"
            return f"Error: Unknown host '{host_name}'. Available hosts: {available}"

        host_info = hosts[host_name]
        hostname = host_info.get("host")
        port = host_info.get("port", 22)
        username = host_info.get("user")
        password = host_info.get("password")
        key_file = host_info.get("key_file")

        try:
            client = paramiko.SSHClient()
            client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

            connect_kwargs = {
                "hostname": hostname,
                "port": port,
                "username": username,
                "timeout": 10,
            }

            if key_file:
                connect_kwargs["key_filename"] = key_file
            elif password:
                connect_kwargs["password"] = password

            client.connect(**connect_kwargs)

            # Get some basic info
            stdin, stdout, stderr = client.exec_command("hostname && uptime")
            info = stdout.read().decode('utf-8', errors='replace').strip()

            client.close()

            return f"Connection successful to {username}@{hostname}:{port}\n\n{info}"

        except Exception as e:
            return f"Connection failed: {str(e)}"
