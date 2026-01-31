-- 饥荒RAG助手 - HTTP桥接工具
-- HTTP Bridge for RAG Assistant (File-based IPC)

local HttpBridge = Class(function(self)
    self.server_url = "http://localhost:8000"
    self.timeout = 30

    -- 文件路径（与Python桥接进程通信）
    self.bridge_dir = nil
    self.request_file = nil
    self.response_file = nil

    -- 请求状态
    self.pending_request = nil
    self.request_id = 0

    -- 回调队列
    self.callbacks = {}

    -- 轮询间隔（秒）
    self.poll_interval = 0.5
    self.poll_task = nil
end)

-- 初始化
function HttpBridge:Init(server_url, timeout)
    self.server_url = server_url or self.server_url
    self.timeout = timeout or self.timeout

    -- 设置桥接文件目录
    if GLOBAL.TheSim then
        -- 使用Mod数据目录
        self.bridge_dir = GLOBAL.PERSISTROOT .. "/rag_bridge"
        self.request_file = self.bridge_dir .. "/request.json"
        self.response_file = self.bridge_dir .. "/response.json"

        -- 确保目录存在
        self:EnsureBridgeDir()
    end

    print("[RAG桥接] 初始化完成")
    print("[RAG桥接] 服务器: " .. self.server_url)
    print("[RAG桥接] 桥接目录: " .. tostring(self.bridge_dir))
end

-- 确保桥接目录存在
function HttpBridge:EnsureBridgeDir()
    if not self.bridge_dir then
        return false
    end

    -- Lua没有直接创建目录的方法，尝试使用os.execute
    local success = pcall(function()
        os.execute("mkdir -p " .. self.bridge_dir)
    end)

    return success
end

-- 生成请求ID
function HttpBridge:GenerateRequestId()
    self.request_id = self.request_id + 1
    return string.format("%d_%d", os.time(), self.request_id)
end

-- 写入请求文件
function HttpBridge:WriteRequest(request_data)
    if not self.request_file then
        print("[RAG桥接] 请求文件路径未设置")
        return false
    end

    local success, err = pcall(function()
        local file = io.open(self.request_file, "w")
        if file then
            -- 简单的JSON序列化
            local json_str = self:SerializeRequest(request_data)
            file:write(json_str)
            file:close()
            return true
        end
        return false
    end)

    if not success then
        print("[RAG桥接] 写入请求失败: " .. tostring(err))
        return false
    end

    return true
end

-- 读取响应文件
function HttpBridge:ReadResponse()
    if not self.response_file then
        return nil
    end

    local success, result = pcall(function()
        local file = io.open(self.response_file, "r")
        if file then
            local content = file:read("*all")
            file:close()

            -- 检查是否有内容
            if content and content ~= "" then
                return self:ParseResponse(content)
            end
        end
        return nil
    end)

    if success then
        return result
    end

    return nil
end

-- 清除响应文件
function HttpBridge:ClearResponse()
    if not self.response_file then
        return
    end

    pcall(function()
        local file = io.open(self.response_file, "w")
        if file then
            file:write("")
            file:close()
        end
    end)
end

-- 序列化请求为JSON
function HttpBridge:SerializeRequest(request_data)
    local parts = {}
    table.insert(parts, "{")

    local items = {}
    for key, value in pairs(request_data) do
        local json_value
        if type(value) == "string" then
            json_value = '"' .. value:gsub('"', '\\"'):gsub("\n", "\\n") .. '"'
        elseif type(value) == "boolean" then
            json_value = value and "true" or "false"
        elseif type(value) == "number" then
            json_value = tostring(value)
        elseif type(value) == "nil" then
            json_value = "null"
        else
            json_value = '"' .. tostring(value) .. '"'
        end
        table.insert(items, string.format('"%s": %s', key, json_value))
    end

    table.insert(parts, table.concat(items, ", "))
    table.insert(parts, "}")

    return table.concat(parts)
end

-- 解析响应JSON
function HttpBridge:ParseResponse(json_str)
    -- 尝试使用内置JSON
    if GLOBAL.json then
        local success, result = pcall(function()
            return GLOBAL.json.decode(json_str)
        end)
        if success then
            return result
        end
    end

    -- 简单的手动解析
    local response = {}

    -- 提取answer字段
    local answer_match = json_str:match('"answer"%s*:%s*"([^"]*)"')
    if answer_match then
        response.answer = answer_match:gsub("\\n", "\n"):gsub('\\"', '"')
    end

    -- 提取error字段
    local error_match = json_str:match('"error"%s*:%s*"([^"]*)"')
    if error_match then
        response.error = error_match
    end

    -- 提取confidence字段
    local confidence_match = json_str:match('"confidence"%s*:%s*([%d%.]+)')
    if confidence_match then
        response.confidence = tonumber(confidence_match)
    end

    -- 提取request_id字段
    local id_match = json_str:match('"request_id"%s*:%s*"([^"]*)"')
    if id_match then
        response.request_id = id_match
    end

    -- 提取status字段
    local status_match = json_str:match('"status"%s*:%s*"([^"]*)"')
    if status_match then
        response.status = status_match
    end

    return response
end

-- 发送问题
function HttpBridge:SendQuestion(question, callback)
    local request_id = self:GenerateRequestId()

    local request_data = {
        type = "ask",
        request_id = request_id,
        question = question,
        timestamp = os.time(),
    }

    -- 清除旧响应
    self:ClearResponse()

    -- 写入请求
    if not self:WriteRequest(request_data) then
        if callback then
            callback(nil, "写入请求失败")
        end
        return
    end

    -- 注册回调
    self.callbacks[request_id] = {
        callback = callback,
        start_time = os.time(),
        timeout = self.timeout,
    }

    self.pending_request = request_id

    -- 开始轮询
    self:StartPolling()

    print("[RAG桥接] 请求已发送: " .. request_id)
end

-- 获取LLM列表
function HttpBridge:GetLLMList(callback)
    local request_id = self:GenerateRequestId()

    local request_data = {
        type = "get_llm_list",
        request_id = request_id,
        timestamp = os.time(),
    }

    self:ClearResponse()

    if not self:WriteRequest(request_data) then
        if callback then
            callback(nil, "写入请求失败")
        end
        return
    end

    self.callbacks[request_id] = {
        callback = callback,
        start_time = os.time(),
        timeout = self.timeout,
    }

    self.pending_request = request_id
    self:StartPolling()

    print("[RAG桥接] 获取LLM列表请求已发送: " .. request_id)
end

-- 切换LLM
function HttpBridge:SwitchLLM(model_id, callback)
    local request_id = self:GenerateRequestId()

    local request_data = {
        type = "switch_llm",
        request_id = request_id,
        model_id = model_id,
        timestamp = os.time(),
    }

    self:ClearResponse()

    if not self:WriteRequest(request_data) then
        if callback then
            callback(nil, "写入请求失败")
        end
        return
    end

    self.callbacks[request_id] = {
        callback = callback,
        start_time = os.time(),
        timeout = self.timeout,
    }

    self.pending_request = request_id
    self:StartPolling()

    print("[RAG桥接] 切换LLM请求已发送: " .. request_id)
end

-- 开始轮询响应
function HttpBridge:StartPolling()
    if self.poll_task then
        return  -- 已经在轮询
    end

    -- 使用游戏的定时器系统
    if GLOBAL.TheWorld then
        self.poll_task = GLOBAL.TheWorld:DoPeriodicTask(self.poll_interval, function()
            self:PollResponse()
        end)
    else
        -- 备用：使用简单循环（不推荐，会阻塞）
        print("[RAG桥接] 警告: 无法使用定时器，响应可能延迟")
    end
end

-- 停止轮询
function HttpBridge:StopPolling()
    if self.poll_task then
        self.poll_task:Cancel()
        self.poll_task = nil
    end
end

-- 轮询响应
function HttpBridge:PollResponse()
    -- 检查是否有待处理的请求
    if not self.pending_request then
        self:StopPolling()
        return
    end

    -- 读取响应
    local response = self:ReadResponse()

    if response then
        local request_id = response.request_id or self.pending_request
        local callback_data = self.callbacks[request_id]

        if callback_data then
            -- 清除回调
            self.callbacks[request_id] = nil
            self.pending_request = nil

            -- 清除响应文件
            self:ClearResponse()

            -- 调用回调
            if response.error then
                if callback_data.callback then
                    callback_data.callback(nil, response.error)
                end
            else
                if callback_data.callback then
                    callback_data.callback(response, nil)
                end
            end

            print("[RAG桥接] 收到响应: " .. request_id)
        end
    else
        -- 检查超时
        for request_id, callback_data in pairs(self.callbacks) do
            local elapsed = os.time() - callback_data.start_time
            if elapsed > callback_data.timeout then
                -- 超时
                self.callbacks[request_id] = nil
                if callback_data.callback then
                    callback_data.callback(nil, "请求超时")
                end
                print("[RAG桥接] 请求超时: " .. request_id)
            end
        end
    end

    -- 如果没有待处理的回调，停止轮询
    local has_pending = false
    for _ in pairs(self.callbacks) do
        has_pending = true
        break
    end

    if not has_pending then
        self:StopPolling()
    end
end

-- 取消所有待处理的请求
function HttpBridge:CancelAll()
    for request_id, callback_data in pairs(self.callbacks) do
        if callback_data.callback then
            callback_data.callback(nil, "已取消")
        end
    end

    self.callbacks = {}
    self.pending_request = nil
    self:StopPolling()
end

-- ============================================================
-- 全局实例
-- ============================================================
RAGHttpBridge = HttpBridge()

return HttpBridge
