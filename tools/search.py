import subprocess
import os
from mcp.server.fastmcp import FastMCP

# Default paths to look for es.exe
ES_PATHS = [
    r"C:\Program Files\Everything\es.exe",
    r"C:\Program Files (x86)\Everything\es.exe",
    r"D:\APP\Everything\es.exe",
    "es.exe"  # In PATH
]

def find_es_executable(configured_path: str = None) -> str:
    """Find the Everything Command-line Interface (es.exe)."""
    if configured_path and os.path.exists(configured_path):
        return configured_path

    for path in ES_PATHS:
        if os.path.exists(path):
            return path

    # Check PATH
    import shutil
    if shutil.which("es.exe"):
        return "es.exe"

    return None

def register_search_tools(mcp: FastMCP, config: dict = None):
    """
    Register file search tools using Everything (es.exe).

    Args:
        mcp: FastMCP instance
        config: Configuration dictionary potentially containing 'everything_path'
    """

    # Get es.exe path from config or auto-detect
    es_path_config = config.get("everything_path") if config else None
    es_path = find_es_executable(es_path_config)

    @mcp.tool(name="MyPC-search_files")
    def search_files(query: str, limit: int = 20) -> str:
        """
        Search for files and folders using 'Everything' (es.exe).

        This tool supports Everything's powerful search syntax:
        - Wildcards: "*.py", "log*.txt"
        - Extensions: "ext:png;jpg", "ext:doc"
        - Type macros: "pic:", "audio:", "video:", "exe:"
        - Logic: "foo bar" (AND), "foo | bar" (OR), "!foo" (NOT)
        - Paths: "D:\Downloads\ *.zip"

        Args:
            query: The search query (e.g., "config.json", "*.py", "project notes")
            limit: Maximum number of results to return (default: 20)

        Returns:
            List of matching file paths.
        """
        if not es_path:
            return "Error: 'es.exe' (Everything CLI) not found. Please install it to D:\\APP\\Everything\\ or configure 'everything_path' in config.json."

        try:
            # Construct command
            # -n <num>: limit results
            cmd = [es_path, str(query), "-n", str(limit)]

            # Run search
            # creationflags=0x08000000 (CREATE_NO_WINDOW) prevents cmd window popping up
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='replace',
                creationflags=0x08000000
            )

            if result.returncode != 0:
                return f"Search error: {result.stderr}"

            output = result.stdout.strip()

            if not output:
                return f"No results found for '{query}'"

            # Format output
            lines = output.split('\n')
            count = len(lines)

            response = [f"Found {count} results for '{query}':"]
            response.extend(lines)

            if count >= limit:
                response.append(f"\n(Showing first {limit} results)")

            return "\n".join(response)

        except Exception as e:
            return f"Error executing search: {str(e)}"
