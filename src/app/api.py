"""FastAPI Web服务"""

import uuid
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from config import settings
from src.utils.logger import logger
from src.indexer import VectorIndexer
from src.qa import QAEngine, ModelComparator


# 请求/响应模型
class QuestionRequest(BaseModel):
    """问题请求"""
    question: str = Field(..., description="用户问题", min_length=1, max_length=1000)
    use_history: bool = Field(default=True, description="是否使用对话历史")
    version_filter: Optional[str] = Field(default=None, description="游戏版本过滤")
    session_id: Optional[str] = Field(default=None, description="会话ID，为空时自动生成")


class AnswerResponse(BaseModel):
    """回答响应"""
    answer: str = Field(..., description="回答内容")
    sources: list[dict] = Field(default_factory=list, description="来源信息")
    confidence: float = Field(..., description="置信度")
    session_id: Optional[str] = Field(default=None, description="会话ID")


class HealthResponse(BaseModel):
    """健康检查响应"""
    status: str
    version: str
    index_stats: dict


class SwitchLLMRequest(BaseModel):
    """切换LLM请求"""
    provider: str = Field(..., description="提供商名称")
    model: Optional[str] = Field(default=None, description="模型名称，为空时使用默认模型")


class LLMInfoResponse(BaseModel):
    """LLM信息响应"""
    provider: str
    model: str
    display_name: str


class CompareRequest(BaseModel):
    """模型对比请求"""
    question: str = Field(..., description="测试问题", min_length=1, max_length=1000)
    providers: Optional[list[tuple[str, str]]] = Field(
        default=None,
        description="要对比的模型列表 [(provider, model), ...]"
    )


class GameLLMOption(BaseModel):
    """游戏内LLM选项"""
    id: str
    name: str


class GameLLMListResponse(BaseModel):
    """游戏内LLM列表响应"""
    current: str
    options: list[GameLLMOption]


# 全局变量
qa_engine: Optional[QAEngine] = None


def create_app() -> FastAPI:
    """创建FastAPI应用"""
    app = FastAPI(
        title="饥荒RAG问答助手",
        description="基于RAG技术的饥荒游戏知识问答服务",
        version="0.1.0",
        docs_url="/docs",
        redoc_url="/redoc",
    )

    # CORS配置
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.on_event("startup")
    async def startup():
        """启动时初始化"""
        global qa_engine
        try:
            logger.info("正在初始化问答引擎...")
            indexer = VectorIndexer()
            index = indexer.load_index()

            if index is None:
                logger.warning("未找到索引，请先运行索引工具")
            else:
                qa_engine = QAEngine(index)
                logger.info("问答引擎初始化完成")

        except Exception as e:
            logger.error(f"初始化失败: {e}")

    @app.get("/health", response_model=HealthResponse)
    async def health_check():
        """健康检查"""
        indexer = VectorIndexer()
        stats = indexer.get_collection_stats()

        return HealthResponse(
            status="healthy" if qa_engine else "degraded",
            version="0.1.0",
            index_stats=stats,
        )

    @app.post("/ask", response_model=AnswerResponse)
    async def ask_question(request: QuestionRequest):
        """问答接口"""
        if qa_engine is None:
            raise HTTPException(
                status_code=503,
                detail="问答引擎未就绪，请确保已创建索引"
            )

        # 生成或使用客户端提供的 session_id
        session_id = request.session_id or str(uuid.uuid4())

        try:
            response = qa_engine.ask(
                question=request.question,
                use_history=request.use_history,
                filter_version=request.version_filter,
                session_id=session_id,
            )

            return AnswerResponse(
                answer=response.answer,
                sources=response.sources,
                confidence=response.confidence,
                session_id=session_id,
            )

        except Exception as e:
            logger.error(f"问答失败: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    @app.post("/clear_history")
    async def clear_history(session_id: str = "default"):
        """清空对话历史"""
        if qa_engine:
            qa_engine.clear_history(session_id)
        return {"status": "ok"}

    @app.get("/history")
    async def get_history(session_id: str = "default"):
        """获取对话历史"""
        if qa_engine:
            return {"history": qa_engine.get_history(session_id)}
        return {"history": []}

    @app.get("/sessions")
    async def list_sessions():
        """列出所有会话"""
        if qa_engine:
            return {"sessions": qa_engine.session_manager.list_sessions()}
        return {"sessions": []}

    # ==================== LLM管理API ====================

    @app.get("/llm/current", response_model=LLMInfoResponse)
    async def get_current_llm():
        """获取当前LLM信息"""
        if qa_engine is None:
            raise HTTPException(status_code=503, detail="问答引擎未就绪")

        info = qa_engine.get_current_llm_info()
        return LLMInfoResponse(**info)

    @app.get("/llm/available")
    async def get_available_llms():
        """获取所有可用的LLM提供商和模型"""
        if qa_engine is None:
            raise HTTPException(status_code=503, detail="问答引擎未就绪")

        return qa_engine.get_available_llms()

    @app.post("/llm/switch", response_model=LLMInfoResponse)
    async def switch_llm(request: SwitchLLMRequest):
        """切换LLM模型"""
        if qa_engine is None:
            raise HTTPException(status_code=503, detail="问答引擎未就绪")

        try:
            result = qa_engine.switch_llm(request.provider, request.model)
            return LLMInfoResponse(
                provider=result["provider"],
                model=result["model"],
                display_name=result["display_name"],
            )
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        except Exception as e:
            logger.error(f"切换LLM失败: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    @app.post("/llm/compare")
    async def compare_models(request: CompareRequest):
        """对比多个模型的回答"""
        if qa_engine is None:
            raise HTTPException(status_code=503, detail="问答引擎未就绪")

        try:
            comparator = ModelComparator(qa_engine)
            result = comparator.compare(request.question, request.providers)
            return result.to_dict()
        except Exception as e:
            logger.error(f"模型对比失败: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    # ==================== 游戏插件专用API ====================

    @app.get("/game/llm/list", response_model=GameLLMListResponse)
    async def game_get_llm_list():
        """获取可用模型列表（游戏插件用，简化格式）"""
        if qa_engine is None:
            raise HTTPException(status_code=503, detail="问答引擎未就绪")

        available = qa_engine.get_available_llms()
        current_info = qa_engine.get_current_llm_info()

        options = []
        for provider, models in available.items():
            for model in models:
                options.append(GameLLMOption(
                    id=f"{provider}/{model}",
                    name=f"{provider.upper()} - {model}",
                ))

        return GameLLMListResponse(
            current=f"{current_info['provider']}/{current_info['model']}",
            options=options,
        )

    @app.post("/game/llm/switch")
    async def game_switch_llm(model_id: str):
        """切换模型（游戏插件用）

        Args:
            model_id: 格式为 "provider/model"
        """
        if qa_engine is None:
            raise HTTPException(status_code=503, detail="问答引擎未就绪")

        try:
            if "/" not in model_id:
                raise ValueError("无效的model_id格式，应为 'provider/model'")

            provider, model = model_id.split("/", 1)
            result = qa_engine.switch_llm(provider, model)
            return {
                "status": "ok",
                "current": f"{result['provider']}/{result['model']}",
            }
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        except Exception as e:
            logger.error(f"切换LLM失败: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    return app


# 创建应用实例
app = create_app()
