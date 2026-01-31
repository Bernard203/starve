# 饥荒RAG助手 Mod

基于AI的饥荒游戏内问答助手，让你在游戏中随时获取攻略信息。

## 功能特点

- 🎮 **游戏内问答** - 无需切出游戏，直接在游戏内与AI对话
- 🔄 **多模型支持** - 支持切换不同的LLM提供商（Ollama、OpenAI、通义千问等）
- 🎨 **界面自定义** - 可调整透明度、字体大小、主题颜色
- 🌍 **上下文感知** - 自动获取游戏状态（季节、天数、角色状态）作为问答上下文
- ⌨️ **快捷键支持** - 一键唤起/隐藏助手窗口

## 安装说明

### 1. 安装后端服务

首先需要启动RAG后端服务：

```bash
cd /path/to/starve
pip install -r requirements.txt
python -m uvicorn src.app.api:app --host 0.0.0.0 --port 8000
```

### 2. 启动HTTP桥接

在单独的终端启动HTTP桥接脚本：

```bash
cd /path/to/starve/mod/bridge
pip install requests watchdog
python http_bridge.py --api-url http://localhost:8000
```

### 3. 安装Mod

将 `mod` 文件夹复制到饥荒Mods目录：

- **Linux**: `~/.klei/DoNotStarveTogether/mods/`
- **Windows**: `文档/Klei/DoNotStarveTogether/mods/`
- **macOS**: `~/Documents/Klei/DoNotStarveTogether/mods/`

重命名为 `rag_assistant`：

```bash
cp -r mod ~/.klei/DoNotStarveTogether/mods/rag_assistant
```

### 4. 启用Mod

1. 启动饥荒联机版
2. 进入 Mods 菜单
3. 找到 "饥荒RAG助手" 并启用
4. 配置服务器地址和快捷键

## 使用方法

1. 按 **Y** 键（默认）打开助手窗口
2. 在输入框中输入问题
3. 按回车或点击发送按钮
4. 等待AI回复

### 快捷键

| 按键 | 功能 |
|------|------|
| Y | 打开/关闭助手窗口 |
| Enter | 发送消息 |
| ESC | 关闭设置界面 |

### 设置选项

在助手窗口点击"设置"按钮可以调整：

- **背景透明度** - 0.3 ~ 1.0
- **字体大小** - 小/中/大/特大
- **主题颜色** - 蓝/绿/紫/橙/红
- **AI模型** - 选择不同的LLM
- **自动上下文** - 是否自动附加游戏状态
- **请求超时** - 15/30/60/120秒

## 目录结构

```
mod/
├── modinfo.lua              # Mod元信息和配置选项
├── modmain.lua              # 主入口文件
├── scripts/
│   ├── components/
│   │   └── rag_assistant.lua    # 助手组件
│   ├── widgets/
│   │   ├── rag_chat_window.lua  # 聊天窗口
│   │   ├── rag_input_box.lua    # 输入框
│   │   ├── rag_message_list.lua # 消息列表
│   │   └── rag_settings.lua     # 设置面板
│   ├── screens/
│   │   └── rag_settings_screen.lua # 设置界面
│   └── utils/
│       ├── http_bridge.lua      # Lua端HTTP桥接
│       └── config_manager.lua   # 配置管理
├── bridge/
│   └── http_bridge.py       # Python HTTP桥接脚本
├── images/                  # 图标资源（待添加）
└── fonts/                   # 中文字体（待添加）
```

## 技术架构

```
┌────────────────────────────────────────┐
│         饥荒游戏客户端 (DST)            │
│  ┌──────────────────────────────────┐  │
│  │          Lua Mod 客户端           │  │
│  │  聊天窗口 ←→ HTTP桥接(文件IPC)    │  │
│  └──────────────────────────────────┘  │
└────────────────────────────────────────┘
                    │ 文件读写
                    ▼
┌────────────────────────────────────────┐
│       Python HTTP桥接进程              │
│  监听request.json → 转发HTTP请求       │
│  接收响应 → 写入response.json          │
└────────────────────────────────────────┘
                    │ HTTP
                    ▼
┌────────────────────────────────────────┐
│         RAG后端服务 (FastAPI)          │
│  /ask - 问答接口                       │
│  /game/llm/list - 获取LLM列表         │
│  /game/llm/switch - 切换LLM           │
└────────────────────────────────────────┘
```

## 常见问题

### Q: 无法连接到服务器
A: 确保后端服务和HTTP桥接都已启动，检查端口是否正确。

### Q: 回复很慢
A: 可以尝试切换到更快的LLM模型，或使用本地Ollama部署。

### Q: 中文显示乱码
A: 确保游戏语言设置为中文，或等待字体资源更新。

## 开发说明

### 添加新功能

1. 在 `scripts/` 目录下添加新的Lua模块
2. 在 `modmain.lua` 中导入模块
3. 如需与后端通信，使用 `RAGHttpBridge`

### 调试

在游戏控制台中可以查看日志：
```
[RAG助手] ...
[RAG桥接] ...
[RAG配置] ...
```

## 许可证

MIT License

## 贡献

欢迎提交Issue和Pull Request！
