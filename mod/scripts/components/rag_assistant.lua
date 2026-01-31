-- 饥荒RAG助手 - 助手组件
-- RAG Assistant Component

-- 助手组件类
local RAGAssistant = Class(function(self, inst)
    self.inst = inst

    -- 配置
    self.config = {}

    -- 状态
    self.is_initialized = false
    self.last_question = nil
    self.last_answer = nil

    -- 回调
    self.on_response = nil
    self.on_error = nil
end)

-- 初始化
function RAGAssistant:Init(config)
    self.config = config or {}
    self.is_initialized = true

    print("[RAG组件] 助手组件初始化完成")
end

-- 发送问题
function RAGAssistant:Ask(question, callback)
    if not self.is_initialized then
        if callback then
            callback(nil, "组件未初始化")
        end
        return
    end

    self.last_question = question

    -- 通过全局函数发送
    if GLOBAL.RAG_SendQuestion then
        GLOBAL.RAG_SendQuestion(question)
    end

    -- 通过HTTP桥接发送
    if RAGHttpBridge then
        RAGHttpBridge:SendQuestion(question, function(response, error)
            if error then
                self.last_answer = nil
                if callback then
                    callback(nil, error)
                end
                if self.on_error then
                    self.on_error(error)
                end
            else
                self.last_answer = response.answer
                if callback then
                    callback(response, nil)
                end
                if self.on_response then
                    self.on_response(response)
                end
            end
        end)
    else
        if callback then
            callback(nil, "HTTP桥接未初始化")
        end
    end
end

-- 获取可用LLM列表
function RAGAssistant:GetAvailableLLMs(callback)
    if RAGHttpBridge then
        RAGHttpBridge:GetLLMList(callback)
    else
        if callback then
            callback(nil, "HTTP桥接未初始化")
        end
    end
end

-- 切换LLM
function RAGAssistant:SwitchLLM(model_id, callback)
    if RAGHttpBridge then
        RAGHttpBridge:SwitchLLM(model_id, callback)
    else
        if callback then
            callback(nil, "HTTP桥接未初始化")
        end
    end
end

-- 获取游戏上下文
function RAGAssistant:GetGameContext()
    if GLOBAL.RAG_GetGameContext then
        return GLOBAL.RAG_GetGameContext()
    end
    return nil
end

-- 格式化游戏上下文
function RAGAssistant:FormatGameContext()
    if GLOBAL.RAG_FormatGameContext then
        local context = self:GetGameContext()
        return GLOBAL.RAG_FormatGameContext(context)
    end
    return ""
end

-- 设置响应回调
function RAGAssistant:SetOnResponse(callback)
    self.on_response = callback
end

-- 设置错误回调
function RAGAssistant:SetOnError(callback)
    self.on_error = callback
end

-- 获取最后的问题
function RAGAssistant:GetLastQuestion()
    return self.last_question
end

-- 获取最后的回答
function RAGAssistant:GetLastAnswer()
    return self.last_answer
end

-- 更新配置
function RAGAssistant:UpdateConfig(key, value)
    if key then
        self.config[key] = value

        -- 同步到全局配置
        if GLOBAL.RAG_UpdateConfig then
            GLOBAL.RAG_UpdateConfig(key, value)
        end
    end
end

-- 获取配置
function RAGAssistant:GetConfig(key)
    if key then
        return self.config[key]
    end
    return self.config
end

-- 导出
RAGAssistantComponent = RAGAssistant

return RAGAssistant
