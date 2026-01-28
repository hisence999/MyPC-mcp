# MYPC-MCP

**English** | [中文](#中文)

A Model Context Protocol (MCP) server that gives AI agents comprehensive control over a local Windows PC.

---

## Features

- 🖥️ **Screen Capture**: Full screen, active window, and webcam screenshots with optional AI analysis.
- 🪟 **Window Management**: List windows, get active window info, manage processes.
- 📁 **File Operations**: Read, write, edit, search, and manage files with safety zones.
- 🌐 **SSH Remote Access**: Execute commands on remote Linux servers with command whitelisting.
- 📊 **System Control**: Adjust volume, lock screen, show notifications, get hardware status.
- 🖱️ **Input Automation**: (Planned) Focus windows and simulate keyboard input.
- 📝 **Clipboard**: Read and write clipboard content.

---

## Installation

### Prerequisites

- Python 3.10 or higher
- Windows 10/11

### Setup

1. **Clone the repository**:
   ```bash
   git clone https://github.com/hisence999/MYPC-MCP.git
   cd MYPC-MCP
   ```

2. **Create a virtual environment**:
   ```bash
   python -m venv venv
   ```

3. **Activate the virtual environment**:
   - **Windows (Command Prompt)**:
     ```bash
     venv\Scripts\activate
     ```
   - **Windows (PowerShell)**:
     ```bash
     venv\Scripts\Activate.ps1
     ```

4. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

5. **Configure the server**:
   - Copy `config.example.json` to `config.json`.
   - Edit `config.json` with your settings:
     - **Safe Zones**: Folders where write operations are allowed (e.g., your Documents folder).
     - **VLM API**: (Optional) Configure a Vision Language Model API for AI image analysis.
     - **SSH Hosts**: (Optional) Configure remote Linux servers for management.

6. **Run the server**:
   ```bash
   python main.py
   ```

The server will start on `http://localhost:9999` by default.

---

## Tools

### Screen Tools
- `MyPC-take_screenshot`: Capture full screen or specific monitor.
- `MyPC-screenshot_active_window`: Capture active window only.
- `MyPC-take_webcam_photo`: Capture photo from webcam.
- `MyPC-list_monitors`: List available monitors.

### Window Tools
- `MyPC-get_active_window`: Get info about the active window.
- `MyPC-list_windows`: List all visible windows.
- `MyPC-focus_window`: Bring a specific window to the foreground.
- `MyPC-list_processes`: List running processes with resource usage.
- `MyPC-show_notification`: Send a Windows Toast notification.

### File Tools
- `MyPC-read_file`: Read text, Word (.docx), Excel (.xlsx), PPT (.pptx), and PDF files.
- `MyPC-write_file`: Write text to a file.
- `MyPC-edit_file`: Search and replace text in a file.
- `MyPC-list_directory`: List contents of a directory.
- `MyPC-search_files`: Search for files using "Everything" (must be installed).
- `MyPC-copy_file`, `MyPC-move_file`, `MyPC-delete_file`: File management.

### SSH Tools
- `MyPC-ssh_list_hosts`: List configured SSH hosts.
- `MyPC-ssh_execute`: Execute a command on a remote server.
- `MyPC-ssh_test_connection`: Test connectivity to a remote server.

### System Tools
- `MyPC-set_volume`: Adjust system volume.
- `MyPC-lock_screen`: Lock the workstation.
- `MyPC-get_hardware_status`: Get CPU, memory, GPU, and disk info.

---

## Configuration

### Safe Zones

Define folders where file write operations are allowed. By default, this includes your Documents, Downloads, and Desktop.

### AI Analysis (Optional)

To enable AI analysis for screenshots, configure a VLM (Vision Language Model) API in `config.json`:

```json
"vlm": {
    "base_url": "https://open.bigmodel.cn/api/paas/v4",
    "api_key": "YOUR_API_KEY",
    "model": "glm-4.6v",
    "prompt": "Please identify all text in this image."
}
```

### SSH Hosts

Configure remote Linux servers for command execution:

```json
"ssh": {
    "hosts": {
        "MyServer": {
            "host": "192.168.1.100",
            "port": 22,
            "user": "username",
            "password": "password"
        }
    },
    "allowed_commands": ["docker", "git", "ls", ...]
}
```

---

## Security

- **Safe Zones**: Write operations are restricted to configured directories only.
- **SSH Whitelist**: Commands executed on remote servers must be in a whitelist.
- **Recycle Bin**: File deletions move files to the Recycle Bin instead of permanent deletion.

---

## Development

### Project Structure

- `main.py`: Server entry point.
- `tools/`: Tool modules (screen, files, ssh, window, system).
- `config.json`: Configuration file.
- `requirements.txt`: Python dependencies.

### Adding New Tools

To add a new tool, register it in the appropriate module:

```python
@mcp.tool(name="MyPC-my_tool")
def my_tool(param: str) -> str:
    """Tool description."""
    # Your logic here
    return "Result"
```

---

## License

MIT License

---

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

---

# 中文

一个基于 Model Context Protocol (MCP) 的服务器，允许 AI 智能体全面控制本地 Windows 电脑。

---

## 功能特性

- 🖥️ **屏幕截取**：支持全屏、活动窗口和网络摄像头截图，并可选择进行 AI 分析。
- 🪟 **窗口管理**：列出窗口、获取活动窗口信息、管理进程。
- 📁 **文件操作**：读取、写入、编辑、搜索和管理文件，具备安全区保护。
- 🌐 **SSH 远程访问**：通过命令白名单在远程 Linux 服务器上执行命令。
- 📊 **系统控制**：调整音量、锁屏、显示通知、获取硬件状态。
- 🖱️ **输入自动化**：（计划中）聚焦窗口并模拟键盘输入。
- 📝 **剪贴板**：读取和写入剪贴板内容。

---

## 安装

### 前置要求

- Python 3.10 或更高版本
- Windows 10/11

### 设置步骤

1. **克隆仓库**：
   ```bash
   git clone https://github.com/hisence999/MYPC-MCP.git
   cd MYPC-MCP
   ```

2. **创建虚拟环境**：
   ```bash
   python -m venv venv
   ```

3. **激活虚拟环境**：
   - **Windows (命令提示符)**：
     ```bash
     venv\Scripts\activate
     ```
   - **Windows (PowerShell)**：
     ```bash
     venv\Scripts\Activate.ps1
     ```

4. **安装依赖**：
   ```bash
   pip install -r requirements.txt
   ```

5. **配置服务器**：
   - 将 `config.example.json` 复制为 `config.json`。
   - 编辑 `config.json` 填入您的设置：
     - **安全区**：允许写入操作的文件夹（例如您的文档文件夹）。
     - **VLM API**：（可选）配置视觉语言模型 API 以启用 AI 图像分析。
     - **SSH 主机**：（可选）配置远程 Linux 服务器以进行管理。

6. **运行服务器**：
   ```bash
   python main.py
   ```

服务器将默认在 `http://localhost:9999` 上启动。

---

## 工具列表

### 屏幕工具
- `MyPC-take_screenshot`：截取全屏或特定显示器。
- `MyPC-screenshot_active_window`：仅截取活动窗口。
- `MyPC-take_webcam_photo`：从网络摄像头拍照。
- `MyPC-list_monitors`：列出可用显示器。

### 窗口工具
- `MyPC-get_active_window`：获取活动窗口信息。
- `MyPC-list_windows`：列出所有可见窗口。
- `MyPC-focus_window`：将特定窗口置于前台。
- `MyPC-list_processes`：列出运行中的进程及其资源使用情况。
- `MyPC-show_notification`：发送 Windows Toast 通知。

### 文件工具
- `MyPC-read_file`：读取文本、Word (.docx)、Excel (.xlsx)、PPT (.pptx) 和 PDF 文件。
- `MyPC-write_file`：将文本写入文件。
- `MyPC-edit_file`：在文件中搜索并替换文本。
- `MyPC-list_directory`：列出目录内容。
- `MyPC-search_files`：使用 "Everything" 搜索文件（需安装）。
- `MyPC-copy_file`、`MyPC-move_file`、`MyPC-delete_file`：文件管理。

### SSH 工具
- `MyPC-ssh_list_hosts`：列出已配置的 SSH 主机。
- `MyPC-ssh_execute`：在远程服务器上执行命令。
- `MyPC-ssh_test_connection`：测试到远程服务器的连接。

### 系统工具
- `MyPC-set_volume`：调整系统音量。
- `MyPC-lock_screen`：锁定工作站。
- `MyPC-get_hardware_status`：获取 CPU、内存、GPU 和磁盘信息。

---

## 配置说明

### 安全区

定义允许进行文件写入操作的文件夹。默认情况下，这包括您的文档、下载和桌面文件夹。

### AI 分析（可选）

要启用截图的 AI 分析功能，请在 `config.json` 中配置 VLM（视觉语言模型）API：

```json
"vlm": {
    "base_url": "https://open.bigmodel.cn/api/paas/v4",
    "api_key": "YOUR_API_KEY",
    "model": "glm-4.6v",
    "prompt": "请识别这张图片中的所有文字。"
}
```

### SSH 主机

配置远程 Linux 服务器以执行命令：

```json
"ssh": {
    "hosts": {
        "MyServer": {
            "host": "192.168.1.100",
            "port": 22,
            "user": "username",
            "password": "password"
        }
    },
    "allowed_commands": ["docker", "git", "ls", ...]
}
```

---

## 安全性

- **安全区**：文件写入操作仅限于配置的目录。
- **SSH 白名单**：在远程服务器上执行的命令必须在白名单中。
- **回收站**：文件删除操作会将文件移至回收站，而不是永久删除。

---

## 开发

### 项目结构

- `main.py`：服务器入口点。
- `tools/`：工具模块（screen、files、ssh、window、system）。
- `config.json`：配置文件。
- `requirements.txt`：Python 依赖项。

### 添加新工具

要添加新工具，请在相应模块中注册：

```python
@mcp.tool(name="MyPC-my_tool")
def my_tool(param: str) -> str:
    """工具描述。"""
    # 您的逻辑代码
    return "结果"
```

---

## 许可证

MIT License

---

## 贡献

欢迎贡献！请随时提交 Pull Request。
