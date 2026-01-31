"""Streamlit Web界面"""

import uuid
import streamlit as st
from typing import Optional

from src.indexer import VectorIndexer
from src.qa import QAEngine, ModelComparator


def init_session_state():
    """初始化会话状态"""
    if "qa_engine" not in st.session_state:
        st.session_state.qa_engine = None
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []
    if "initialized" not in st.session_state:
        st.session_state.initialized = False
    if "current_provider" not in st.session_state:
        st.session_state.current_provider = None
    if "current_model" not in st.session_state:
        st.session_state.current_model = None
    if "session_id" not in st.session_state:
        st.session_state.session_id = str(uuid.uuid4())


def load_qa_engine() -> Optional[QAEngine]:
    """加载问答引擎"""
    if st.session_state.qa_engine is not None:
        return st.session_state.qa_engine

    try:
        with st.spinner("正在加载知识库..."):
            indexer = VectorIndexer()
            index = indexer.load_index()

            if index is None:
                st.error("未找到知识库索引，请先运行索引工具")
                return None

            qa_engine = QAEngine(index)
            st.session_state.qa_engine = qa_engine
            st.session_state.initialized = True

            # 初始化当前模型状态
            info = qa_engine.get_current_llm_info()
            st.session_state.current_provider = info["provider"]
            st.session_state.current_model = info["model"]

            return qa_engine

    except Exception as e:
        st.error(f"加载失败: {e}")
        return None


def render_model_selector(qa_engine: QAEngine):
    """渲染模型选择器"""
    st.markdown("### 🤖 模型设置")

    # 获取可用模型
    available = qa_engine.get_available_llms()
    current_info = qa_engine.get_current_llm_info()

    if not available:
        st.warning("无可用模型")
        return

    # 提供商选择
    providers = list(available.keys())
    current_provider_idx = providers.index(current_info["provider"]) if current_info["provider"] in providers else 0

    selected_provider = st.selectbox(
        "选择提供商",
        options=providers,
        index=current_provider_idx,
        format_func=lambda x: {
            "openai": "OpenAI",
            "anthropic": "Anthropic",
            "ollama": "Ollama (本地)",
            "dashscope": "通义千问",
            "kimi": "Kimi (Moonshot)",
            "gemini": "Gemini",
            "deepseek": "DeepSeek",
        }.get(x, x.title()),
        key="provider_select",
    )

    # 模型选择
    models = available.get(selected_provider, [])
    if models:
        # 如果当前提供商和选择的一致，使用当前模型作为默认
        if selected_provider == current_info["provider"] and current_info["model"] in models:
            current_model_idx = models.index(current_info["model"])
        else:
            current_model_idx = 0

        selected_model = st.selectbox(
            "选择模型",
            options=models,
            index=current_model_idx,
            key="model_select",
        )

        # 切换按钮
        is_current = (selected_provider == current_info["provider"] and
                      selected_model == current_info["model"])

        if st.button(
            "✅ 当前模型" if is_current else "🔄 切换模型",
            disabled=is_current,
            use_container_width=True,
        ):
            try:
                with st.spinner("正在切换模型..."):
                    result = qa_engine.switch_llm(selected_provider, selected_model)
                    st.session_state.current_provider = result["provider"]
                    st.session_state.current_model = result["model"]
                    st.success(f"已切换到 {result['display_name']}")
                    st.rerun()
            except Exception as e:
                st.error(f"切换失败: {e}")

        # 显示当前模型信息
        st.caption(f"当前: {current_info['display_name']}")


def render_model_compare(qa_engine: QAEngine):
    """渲染模型对比功能"""
    st.markdown("### 📊 模型对比")

    with st.expander("对比多个模型", expanded=False):
        compare_question = st.text_input(
            "测试问题",
            placeholder="输入问题进行模型对比...",
            key="compare_question",
        )

        available = qa_engine.get_available_llms()

        # 多选模型
        model_options = []
        for provider, models in available.items():
            for model in models:
                model_options.append(f"{provider}/{model}")

        selected_models = st.multiselect(
            "选择要对比的模型",
            options=model_options,
            default=model_options[:2] if len(model_options) >= 2 else model_options,
            max_selections=4,
            key="compare_models",
        )

        if st.button("🚀 开始对比", disabled=not compare_question or len(selected_models) < 2):
            if compare_question and len(selected_models) >= 2:
                providers = [tuple(m.split("/", 1)) for m in selected_models]

                with st.spinner("正在对比模型（这可能需要一些时间）..."):
                    comparator = ModelComparator(qa_engine)
                    result = comparator.compare(compare_question, providers)

                    # 显示结果
                    st.markdown("#### 对比结果")

                    # 指标卡片
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("最快响应", result.metrics.fastest_provider,
                                  f"{result.metrics.fastest_latency:.2f}s")
                    with col2:
                        st.metric("最长回答", result.metrics.longest_answer_provider,
                                  f"{result.metrics.longest_answer_length}字")
                    with col3:
                        st.metric("成功率",
                                  f"{result.metrics.success_count}/{result.metrics.total_count}")

                    # 详细结果
                    for key, response in result.results.items():
                        with st.expander(f"📝 {key}", expanded=response.success):
                            if response.success:
                                st.markdown(f"**延迟**: {response.latency:.2f}s | "
                                            f"**Token数**: ~{response.token_count}")
                                st.markdown("**回答**:")
                                st.markdown(response.answer)
                            else:
                                st.error(f"失败: {response.error}")


def main():
    """Streamlit主页面"""
    st.set_page_config(
        page_title="饥荒RAG问答助手",
        page_icon="🎮",
        layout="wide",
    )

    init_session_state()

    # 侧边栏
    with st.sidebar:
        st.title("🎮 饥荒助手")
        st.markdown("---")

        # 版本过滤
        version_filter = st.selectbox(
            "游戏版本",
            options=["all", "ds", "dst", "rog", "sw", "ham"],
            format_func=lambda x: {
                "all": "全部版本",
                "ds": "单机版 (DS)",
                "dst": "联机版 (DST)",
                "rog": "巨人统治 (RoG)",
                "sw": "海难 (SW)",
                "ham": "哈姆雷特 (HAM)",
            }.get(x, x)
        )

        st.markdown("---")

        # 模型选择器（需要qa_engine加载后）
        qa_engine = load_qa_engine()
        if qa_engine:
            render_model_selector(qa_engine)
            st.markdown("---")

        # 清空对话
        if st.button("🗑️ 清空对话", use_container_width=True):
            st.session_state.chat_history = []
            if st.session_state.qa_engine:
                st.session_state.qa_engine.clear_history(st.session_state.session_id)
            st.session_state.session_id = str(uuid.uuid4())
            st.rerun()

        # 统计信息
        st.markdown("---")
        st.markdown("### 📊 统计")
        try:
            indexer = VectorIndexer()
            stats = indexer.get_collection_stats()
            st.metric("知识库文档数", stats.get("count", 0))
        except Exception:
            st.metric("知识库文档数", "N/A")

    # 主区域
    st.title("饥荒游戏问答助手")
    st.markdown("基于RAG技术，为您解答饥荒游戏的各种问题")

    # 模型对比功能
    if qa_engine:
        render_model_compare(qa_engine)

    st.markdown("---")

    # 显示对话历史
    for msg in st.session_state.chat_history:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
            if msg.get("sources"):
                with st.expander("📚 来源"):
                    for src in msg["sources"]:
                        if src.get("url"):
                            st.markdown(f"- [{src['title']}]({src['url']})")
                        elif src.get("title"):
                            st.markdown(f"- {src['title']}")

    # 用户输入
    if prompt := st.chat_input("请输入您的问题..."):
        if qa_engine is None:
            st.error("问答引擎未就绪")
            return

        # 添加用户消息
        st.session_state.chat_history.append({
            "role": "user",
            "content": prompt,
        })

        with st.chat_message("user"):
            st.markdown(prompt)

        # 生成回答
        with st.chat_message("assistant"):
            with st.spinner("思考中..."):
                filter_version = None if version_filter == "all" else version_filter

                response = qa_engine.ask(
                    question=prompt,
                    use_history=True,
                    filter_version=filter_version,
                    session_id=st.session_state.session_id,
                )

                st.markdown(response.answer)

                # 显示来源
                if response.sources:
                    with st.expander("📚 来源"):
                        for src in response.sources:
                            if src.get("url"):
                                st.markdown(f"- [{src['title']}]({src['url']})")
                            elif src.get("title"):
                                st.markdown(f"- {src['title']}")

                # 显示置信度
                confidence_color = "green" if response.confidence > 0.7 else "orange" if response.confidence > 0.5 else "red"
                st.markdown(f"置信度: :{confidence_color}[{response.confidence:.0%}]")

        # 保存助手回复
        st.session_state.chat_history.append({
            "role": "assistant",
            "content": response.answer,
            "sources": response.sources,
        })


if __name__ == "__main__":
    main()
