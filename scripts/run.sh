#!/bin/bash
# 饥荒RAG问答助手 - 快速启动脚本

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${GREEN}饥荒RAG问答助手${NC}"
echo "========================"

# 检查Python版本
python_version=$(python3 --version 2>&1 | cut -d' ' -f2)
echo -e "Python版本: ${python_version}"

# 检查是否安装依赖
if ! python3 -c "import llama_index" 2>/dev/null; then
    echo -e "${YELLOW}正在安装依赖...${NC}"
    pip install -e ".[dev]"
fi

# 显示帮助
show_help() {
    echo ""
    echo "用法: ./scripts/run.sh [命令]"
    echo ""
    echo "命令:"
    echo "  crawl     - 爬取Wiki数据"
    echo "  index     - 构建向量索引"
    echo "  api       - 启动API服务"
    echo "  streamlit - 启动Web界面"
    echo "  test      - 运行测试"
    echo "  help      - 显示帮助"
    echo ""
}

case "$1" in
    crawl)
        echo -e "${GREEN}开始爬取Wiki数据...${NC}"
        python -m src.crawler.main "${@:2}"
        ;;
    index)
        echo -e "${GREEN}开始构建索引...${NC}"
        python -m src.indexer.main "${@:2}"
        ;;
    api)
        echo -e "${GREEN}启动API服务...${NC}"
        python -m src.app.main --mode api "${@:2}"
        ;;
    streamlit)
        echo -e "${GREEN}启动Streamlit界面...${NC}"
        python -m src.app.main --mode streamlit "${@:2}"
        ;;
    test)
        echo -e "${GREEN}运行测试...${NC}"
        pytest tests/ -v "${@:2}"
        ;;
    help|--help|-h)
        show_help
        ;;
    *)
        echo -e "${YELLOW}未知命令: $1${NC}"
        show_help
        exit 1
        ;;
esac
