# MyPC-MCP 开发计划文档

## 1. 项目概述
本项目旨在构建一个基于 Model Context Protocol (MCP) 的本地服务器，允许 AI 客户端通过 HTTP/SSE 协议与本地计算机进行交互。该服务器将充当"AI 代理管家"，赋予 AI 视觉（截图）、听觉（系统状态）、手脚（控制与执行）的能力。

**域名**: `localhost` (IPv6 公网访问)
**端口**: 9999

## 2. 技术栈
- **核心框架**: Python, MCP SDK (FastMCP / mcp-python)
- **协议**: HTTP / SSE (Server-Sent Events), IPv4 + IPv6 双栈
- **操作系统**: Windows, 兼顾跨平台设计
- **关键库**:
  - `mcp`: MCP 协议实现
  - `mss` / `Pillow`: 屏幕截图与图像处理
  - `pycaw`: Windows 音量控制
  - `psutil`: 系统状态监控与进程管理
  - `paramiko`: SSH 连接与命令执行
  - `pywin32`: Windows API 调用（窗口、进程、COM）
  - `os` / `shutil`: 文件系统操作
  - `send2trash`: 回收站操作

## 3. 功能模块与开发路线图

### ✅ 阶段一：基础框架与系统感知 (已完成)
- [x] **搭建服务器骨架**: 配置 MCP 服务，实现 SSE 传输
- [x] **截图功能**:
  - 实现全屏/多显示器截图
  - 返回 HTTP URL (http://localhost:9999/screenshots/)
- [x] **系统控制**:
  - 获取/设置系统音量
  - 获取 CPU/内存/电池状态
  - 屏幕锁定/休眠/关闭显示器

### ✅ 阶段二：文件系统管理 (已完成)
- [x] **分级权限系统**:
  - 只读操作（任意目录）：list_directory, read_file, get_file_info
  - 写入操作（仅安全区）：write_file, delete_file, move_file, create_directory
  - 复制操作（特殊）：可复制进安全区，不可复制出安全区
- [x] **安全回收站**: 使用 send2trash 移动到回收站

### ✅ 阶段三：远程连接与执行 (已完成)
- [x] **SSH 模块**:
  - 配置多个 SSH 主机
  - 命令白名单机制
  - 多编码支持（UTF-8/GBK/GB2312）
  - 工具：ssh_list_hosts, ssh_execute, ssh_test_connection, ssh_allowed_commands

### 🚧 阶段四：窗口管理增强 (进行中)
- [ ] **活动窗口信息**:
  - 获取当前活动窗口标题
  - 获取窗口进程名称
  - 获取窗口位置和大小
- [ ] **活动窗口截图**:
  - 只截取活动窗口区域
  - 自动识别窗口边界
- [ ] **资源管理器集成**:
  - 获取资源管理器当前路径
  - 获取资源管理器选中项
- [ ] **剪贴板操作**:
  - 读取剪贴板文本/图片
  - 设置剪贴板内容
- [ ] **进程管理器**:
  - 列出所有进程（按 CPU/内存排序）
  - 杀死指定进程

### 📋 阶段五：扩展功能 (计划中)
- [ ] **文件搜索**: 按名称/内容/日期搜索
- [ ] **压缩/解压**: 支持 zip/7z 格式
- [ ] **HTTP 工具**: 发送 HTTP 请求（调用外部 API）
- [ ] **网络监控**: 查看网络连接、端口占用
- [ ] **系统通知**: 发送 Windows Toast 通知

## 4. 工具列表（已实现）

### 屏幕工具 (tools/screen.py)
| 工具名 | 功能 |
|--------|------|
| MyPC-take_screenshot | 全屏/指定显示器截图 |
| MyPC-list_monitors | 列出所有显示器信息 |

### 系统工具 (tools/system.py)
| 工具名 | 功能 |
|--------|------|
| MyPC-get_system_status | CPU/内存/电池状态 |
| MyPC-set_volume | 设置音量 (0-100) |
| MyPC-get_volume | 获取当前音量 |
| MyPC-lock_screen | 锁定屏幕 |
| MyPC-sleep_display | 关闭显示器 |
| MyPC-hibernate | 休眠/睡眠 |

### 文件工具 (tools/files.py)
| 工具名 | 功能 | 权限 |
|--------|------|------|
| MyPC-list_directory | 列出目录 | 只读 |
| MyPC-read_file | 读取文件 | 只读 |
| MyPC-get_file_info | 文件信息 | 只读 |
| MyPC-list_safe_zones | 查看安全区 | 只读 |
| MyPC-write_file | 写入文件 | 安全区 |
| MyPC-move_file | 移动/重命名 | 安全区 |
| MyPC-delete_file | 删除文件 | 安全区 |
| MyPC-create_directory | 创建目录 | 安全区 |
| MyPC-copy_file | 复制文件 | 特殊 |

### SSH 工具 (tools/ssh.py)
| 工具名 | 功能 |
|--------|------|
| MyPC-ssh_list_hosts | 列出配置的主机 |
| MyPC-ssh_execute | 执行远程命令 |
| MyPC-ssh_test_connection | 测试连接 |
| MyPC-ssh_allowed_commands | 查看允许的命令 |

## 5. 安全策略 (Safety Protocol)
1. **沙盒路径**: 文件写入操作限制在安全区内
2. **命令白名单**: SSH 执行受限，仅允许预设的安全命令
3. **危险操作**: 删除文件默认移入回收站
4. **敏感信息**: SSH 密码等存储在 config.json 中

## 6. 目录结构
```
my-computer-mcp/
├── main.py              # 入口文件，MCP服务器定义
├── config.json          # 配置文件（安全区、SSH主机等）
├── requirements.txt     # 依赖列表
├── PLAN.md              # 本文件
├── screenshots/         # 截图保存目录
├── tools/               # 工具模块文件夹
│   ├── screen.py        # 截图相关
│   ├── system.py        # 系统控制
│   ├── files.py         # 文件管理
│   ├── ssh.py           # SSH功能
│   └── window.py        # 窗口管理（待创建）
└── venv/                # 虚拟环境
```

## 7. 配置文件示例 (config.json)
```json
{
    "safe_zones": [
        "C:\\Users\\25286\\Documents",
        "C:\\Users\\25286\\Downloads",
        "C:\\Users\\25286\\Desktop"
    ],
    "ssh": {
        "hosts": {
            "example-server": {
                "host": "192.168.5.7",
                "port": 22,
                "user": "username",
                "password": "password"
            }
        },
        "allowed_commands": ["ls", "pwd", "cat", "docker", "git"]
    }
}
```
