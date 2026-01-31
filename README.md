# 饥荒RAG问答助手

基于RAG（检索增强生成）技术的饥荒游戏知识问答系统，支持在游戏内直接使用。

## 功能特性

- **多源数据爬取**：支持 Wiki.gg、Fandom、灰机Wiki、百度贴吧、Steam指南
- **智能数据清洗**：提取结构化信息（配方、属性、分类等）
- **混合检索**：向量检索 + BM25 + 重排序 + MMR多样性
- **智能问答**：支持多轮对话、版本过滤、7种LLM提供商
- **游戏内Mod**：可在游戏中直接使用问答功能（按 Y 键呼出）
- **多端部署**：Web API / Streamlit / Discord Bot

## 系统架构

```
游戏内 Lua Mod  ←→  Python HTTP桥接进程  ←→  FastAPI 后端服务
  (文件IPC)              (HTTP请求)
```

---

## 快速开始

### 1. 安装依赖

```bash
# 克隆项目
git clone <repository-url>
cd starve

# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate   # Windows

# 安装依赖
pip install -r requirements.txt
pip install watchdog  # 桥接脚本需要
```

### 2. 配置环境

```bash
cp .env.example .env
```

编辑 `.env` 文件，关键配置项：

| 配置项 | 说明 | 示例值 |
|--------|------|--------|
| `LLM_PROVIDER` | LLM 提供商 | `ollama` / `openai` / `dashscope` |
| `LLM_MODEL_NAME` | 模型名称 | `qwen2.5:7b` |
| `LLM_API_BASE` | LLM 接口地址 | `http://localhost:11434`（Ollama） |
| `LLM_API_KEY` | API 密钥（Ollama 不需要） | 留空或填写 |
| `EMBEDDING_MODEL_NAME` | 嵌入模型 | `BAAI/bge-base-zh-v1.5` |
| `EMBEDDING_DEVICE` | 嵌入设备 | `auto` / `cpu` / `cuda` |

如果使用 Ollama（推荐本地方案）：
```bash
ollama pull qwen2.5:7b
```

### 3. 爬取数据并构建索引

```bash
# 完整流水线：爬取 → 清洗 → 生成文档
python run.py

# 或分步执行
python run.py --step crawl --max-pages 100  # 爬取
python run.py --step clean                  # 清洗
python run.py --step docs                   # 生成文档

# 构建向量索引
python scripts/integrate_data.py --clear
```

**注意**：首次运行会下载 Embedding 模型（约 400MB）。如果下载慢：
```bash
export HF_ENDPOINT=https://hf-mirror.com
```

### 4. 启动服务

```bash
# FastAPI服务（API接口）
uvicorn src.app.api:app --host 0.0.0.0 --port 8000 --reload

# Streamlit界面（Web UI）
streamlit run src/app/streamlit_app.py
```

启动后访问：
- API 文档：http://localhost:8000/docs
- 健康检查：http://localhost:8000/health

---

## 游戏内 Mod 使用

### 1. 启动 HTTP 桥接进程

桥接进程负责在游戏 Lua Mod 和后端服务之间转发请求：

```bash
cd mod/bridge
python http_bridge.py --api-url http://localhost:8000
```

### 2. 安装 Mod 到饥荒联机版

**方法一：符号链接（开发推荐）**
```bash
ln -s $(pwd)/mod ~/.klei/DoNotStarveTogether/mods/rag_assistant
```

**方法二：复制文件**
```bash
cp -r mod ~/.klei/DoNotStarveTogether/mods/rag_assistant
```

> **注意**：Linux 上 mods 目录可能在 `~/.klei/DoNotStarveTogether/mods/` 或 Steam 安装目录下。

### 3. 游戏内启用

1. 启动饥荒联机版
2. 进入 **Mods** 菜单，启用 **"饥荒RAG助手"**
3. 可配置：快捷键、服务器地址、透明度、字体大小、主题颜色等
4. 进入游戏世界

### 4. 使用方法

- 按 **Y** 键打开/关闭助手窗口
- 输入问题（如"怎么过冬天？"、"火鸡要怎么打？"）
- 按回车发送，等待 AI 回复

### 5. 完整启动顺序

需要保持 **3 个终端** 同时运行：

| 终端 | 命令 | 作用 |
|------|------|------|
| 终端 1 | `uvicorn src.app.api:app --host 0.0.0.0 --port 8000` | FastAPI 后端 |
| 终端 2 | `python mod/bridge/http_bridge.py --api-url http://localhost:8000` | HTTP 桥接 |
| 终端 3 | 启动饥荒联机版游戏 | 游戏客户端 |

### 6. （可选）安装中文字体

```bash
cd mod/bridge
python setup_fonts.py
```

按照提示下载思源黑体并放到 `mod/fonts/` 目录。

---

## 项目结构

```
starve/
├── config/                      # 配置管理
│   └── settings.py              # Pydantic Settings
├── src/                         # 核心模块
│   ├── crawler/                 # 数据采集模块
│   │   ├── base.py              # 基础类和数据模型
│   │   ├── mediawiki_crawler.py # MediaWiki爬虫
│   │   ├── tieba_crawler.py     # 贴吧爬虫
│   │   ├── steam_crawler.py     # Steam爬虫
│   │   ├── pipeline.py          # 爬取流水线
│   │   └── cleaners/            # 数据清洗器
│   ├── indexer/                 # 向量索引模块
│   │   ├── indexer.py           # 向量索引
│   │   └── document_processor.py# 文档处理
│   ├── retriever/               # 检索模块
│   │   ├── retriever.py         # 混合检索器
│   │   ├── bm25.py              # BM25检索
│   │   ├── fusion.py            # 结果融合
│   │   ├── reranker.py          # 重排序
│   │   ├── mmr.py               # 多样性控制
│   │   └── cache.py             # 查询缓存
│   ├── qa/                      # 问答模块
│   │   ├── qa_engine.py         # 问答引擎
│   │   ├── llm_factory.py       # LLM工厂
│   │   ├── session.py           # 会话管理
│   │   └── prompts.py           # 提示词模板
│   ├── app/                     # 应用层
│   │   ├── api.py               # FastAPI接口
│   │   └── streamlit_app.py     # Web界面
│   └── utils/                   # 工具模块
├── mod/                         # 游戏内Mod
│   ├── modinfo.lua              # Mod元信息
│   ├── modmain.lua              # Mod主入口
│   ├── scripts/                 # Lua脚本
│   │   ├── widgets/             # UI组件
│   │   ├── components/          # 功能组件
│   │   └── utils/               # 工具模块
│   └── bridge/                  # Python桥接脚本
│       └── http_bridge.py       # HTTP桥接
├── scripts/                     # 工具脚本
├── tests/                       # 测试
├── docs/                        # 文档
├── data/                        # 数据目录
│   ├── raw/                     # 原始数据
│   ├── processed/               # 处理后数据
│   └── vectors/                 # 向量数据库
├── run.py                       # 主入口
├── pyproject.toml               # 项目配置
└── requirements.txt
```

---

## 配置说明

完整配置项（`.env` 文件）：

```env
# LLM配置
LLM_PROVIDER=ollama           # ollama/openai/dashscope/kimi/gemini/deepseek/anthropic
LLM_MODEL_NAME=qwen2.5:7b
LLM_API_BASE=http://localhost:11434
LLM_API_KEY=
LLM_TEMPERATURE=0.7
LLM_MAX_TOKENS=2048

# Embedding配置
EMBEDDING_MODEL_NAME=BAAI/bge-base-zh-v1.5
EMBEDDING_CHUNK_SIZE=512
EMBEDDING_CHUNK_OVERLAP=100
EMBEDDING_DEVICE=auto         # auto/cpu/cuda

# 检索配置
RETRIEVER_TOP_K=5
RETRIEVER_SIMILARITY_THRESHOLD=0.5
RETRIEVER_USE_RERANKER=true

# 爬虫配置
CRAWLER_REQUEST_DELAY=1.0
CRAWLER_MAX_PAGES=1000

# 应用配置
APP_HOST=0.0.0.0
APP_PORT=8000
APP_DEBUG=false
```

---

## 开发设置

### 安装开发依赖

```bash
pip install -e ".[dev]"
```

### 运行测试

```bash
# 运行所有测试
pytest tests/ -v

# 生成覆盖率报告
pytest tests/ --cov=src --cov-report=html
```

### 代码格式化

```bash
black src/ tests/
isort src/ tests/
ruff check src/ tests/
```

### 类型检查

```bash
mypy src/
```

---

## 故障排除

### 爬虫请求被拒绝 (403/429)

```bash
export CRAWLER_REQUEST_DELAY=2.0  # 增加延迟
```

### Embedding 模型下载失败

```bash
export HF_ENDPOINT=https://hf-mirror.com
```

### 内存不足

```bash
EMBEDDING_MODEL_NAME=BAAI/bge-small-zh-v1.5
EMBEDDING_DEVICE=cpu
```

### ChromaDB 安装失败

```bash
pip install --upgrade pip setuptools wheel
pip install chromadb --prefer-binary
```

### 游戏内无法连接服务器

- 确保后端服务和 HTTP 桥接都在运行
- 检查端口 8000 是否正确
- 查看桥接日志：`tail -f mod/bridge/bridge.log`

### 快捷键 Y 与其他 Mod 冲突

在游戏 Mods 菜单中配置"饥荒RAG助手"，更改快捷键为 U/I/P/H。

### 日志查看

```bash
tail -f crawl.log           # 爬取日志
tail -f logs/app.log        # 应用日志
tail -f mod/bridge/bridge.log  # 桥接日志
```

---

## 数据来源

- [饥荒中文Wiki (wiki.gg)](https://dontstarve.wiki.gg/zh/)
- [饥荒Wiki (Fandom)](https://dontstarve.fandom.com/zh/)
- [百度贴吧 - 饥荒吧](https://tieba.baidu.com/f?kw=饥荒)
- [Steam 社区指南](https://steamcommunity.com/app/219740/guides/)

## 技术栈

| 组件 | 技术 |
|------|------|
| 爬虫 | requests + BeautifulSoup + lxml |
| RAG框架 | LlamaIndex |
| 向量数据库 | ChromaDB |
| Embedding | BAAI/bge-base-zh-v1.5 |
| LLM | Ollama / OpenAI / DashScope / 更多 |
| Web服务 | FastAPI + Streamlit |
| 游戏Mod | Lua + Python桥接 |
| 测试 | pytest + pytest-cov |

## 文档

- [运行指南](docs/运行指南.md)
- [安装指南](docs/INSTALL.md)
- [使用指南](docs/USAGE.md)
- [架构设计](docs/ARCHITECTURE.md)
- [API文档](docs/API.md)

## 许可证

MIT License
