# 饥荒RAG问答助手

基于RAG（检索增强生成）技术的饥荒游戏知识问答系统。

## 功能特性

- 🕷️ **多源数据爬取**：支持Wiki.gg、Fandom、灰机Wiki、百度贴吧、Steam指南
- 🧹 **智能数据清洗**：提取结构化信息（配方、属性、分类等）
- 🔍 **混合检索**：向量检索 + BM25 + 重排序 + MMR多样性
- 💬 **智能问答**：支持多轮对话、版本过滤、7种LLM提供商
- 🎮 **游戏内Mod**：可在游戏中直接使用问答功能
- 🌐 **多端部署**：Web API / Streamlit / Discord Bot

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
```

### 2. 配置环境

```bash
# 复制示例配置
cp .env.example .env

# 编辑配置文件，设置LLM提供商
vim .env
```

### 3. 爬取和处理数据

```bash
# 使用完整流水线（推荐）
python run.py

# 或分步执行
python run.py --step crawl --max-pages 100  # 爬取
python run.py --step clean                  # 清洗
python run.py --step docs                   # 生成文档
```

### 4. 构建索引

```bash
python scripts/integrate_data.py --clear
```

### 5. 启动服务

```bash
# FastAPI服务（API接口）
uvicorn src.app.api:app --reload

# Streamlit界面（Web UI）
streamlit run src/app/streamlit_app.py
```

## 项目结构

```
starve/
├── config/                      # 配置管理
│   ├── __init__.py
│   └── settings.py              # Pydantic Settings
├── src/                         # 核心模块
│   ├── crawler/                 # 数据采集模块
│   │   ├── base.py              # 基础类和数据模型
│   │   ├── mediawiki_crawler.py # MediaWiki爬虫
│   │   ├── tieba_crawler.py     # 贴吧爬虫
│   │   ├── steam_crawler.py     # Steam爬虫
│   │   ├── pipeline.py          # 爬取流水线
│   │   ├── factory.py           # 工厂模式
│   │   ├── parser.py            # 内容解析
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

## 配置说明

支持环境变量配置，也可创建 `.env` 文件：

```env
# LLM配置
LLM_PROVIDER=ollama           # ollama/openai/dashscope/kimi/gemini/deepseek/anthropic
LLM_MODEL_NAME=qwen2.5:7b
LLM_API_BASE=http://localhost:11434

# Embedding配置
EMBEDDING_MODEL_NAME=BAAI/bge-base-zh-v1.5
EMBEDDING_DEVICE=auto         # auto/cpu/cuda

# 检索配置
RETRIEVER_TOP_K=5
RETRIEVER_USE_RERANKER=true
```

## 开发设置

### 安装开发依赖

```bash
pip install -e ".[dev]"
```

### 运行测试

```bash
# 运行所有测试
pytest tests/ -v

# 运行特定模块测试
pytest tests/crawler/ -v

# 生成覆盖率报告
pytest tests/ --cov=src --cov-report=html
```

### 代码格式化

```bash
# 格式化代码
black src/ tests/
isort src/ tests/

# 检查代码风格
ruff check src/ tests/
```

### 类型检查

```bash
mypy src/
```

## 故障排除

### 常见问题

**Q: 爬虫请求被拒绝 (403/429)**

```bash
# 调整请求延迟
export CRAWLER_REQUEST_DELAY=2.0  # 增加延迟

# 或在 .env 中设置
CRAWLER_REQUEST_DELAY=2.0
```

**Q: Embedding 模型下载失败**

```bash
# 使用 HuggingFace 镜像
export HF_ENDPOINT=https://hf-mirror.com

# 或手动下载模型
python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('BAAI/bge-base-zh-v1.5')"
```

**Q: 内存不足**

```bash
# 使用更小的模型
EMBEDDING_MODEL_NAME=BAAI/bge-small-zh-v1.5

# 或使用 CPU
EMBEDDING_DEVICE=cpu
```

**Q: ChromaDB 安装失败**

```bash
# 安装构建工具
pip install --upgrade pip setuptools wheel

# 使用预编译包
pip install chromadb --prefer-binary
```

**Q: llama_index 导入错误**

```bash
# 安装完整依赖
pip install llama-index-core llama-index-embeddings-huggingface llama-index-vector-stores-chroma
```

### 日志查看

```bash
# 查看爬取日志
tail -f crawl.log

# 查看应用日志
tail -f logs/app.log
```

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
| 测试 | pytest + pytest-cov |

## 文档

- [安装指南](docs/INSTALL.md)
- [使用指南](docs/USAGE.md)
- [架构设计](docs/ARCHITECTURE.md)
- [API文档](docs/API.md)

## 许可证

MIT License
