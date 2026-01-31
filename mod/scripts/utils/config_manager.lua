-- 饥荒RAG助手 - 配置管理器
-- Config Manager for RAG Assistant

local ConfigManager = Class(function(self)
    self.config = {}
    self.save_path = nil
    self.dirty = false
end)

-- 初始化配置
function ConfigManager:Init(default_config)
    self.config = default_config or {}

    -- 设置保存路径（使用Mod数据目录）
    if GLOBAL.TheSim then
        local mod_name = "rag_assistant"
        self.save_path = GLOBAL.PERSISTROOT .. "/" .. mod_name .. "_config.json"
    end

    -- 尝试加载已保存的配置
    self:Load()

    print("[RAG配置] 配置管理器初始化完成")
end

-- 获取配置项
function ConfigManager:Get(key, default)
    if key then
        return self.config[key] or default
    end
    return self.config
end

-- 设置配置项
function ConfigManager:Set(key, value)
    if key then
        self.config[key] = value
        self.dirty = true
    end
end

-- 批量更新配置
function ConfigManager:Update(updates)
    if type(updates) == "table" then
        for key, value in pairs(updates) do
            self.config[key] = value
        end
        self.dirty = true
    end
end

-- 保存配置到文件
function ConfigManager:Save()
    if not self.save_path then
        print("[RAG配置] 无法保存: 保存路径未设置")
        return false
    end

    -- 将配置转为JSON字符串
    local json_str = self:TableToJSON(self.config)

    -- 写入文件
    local success, err = pcall(function()
        local file = io.open(self.save_path, "w")
        if file then
            file:write(json_str)
            file:close()
        end
    end)

    if success then
        self.dirty = false
        print("[RAG配置] 配置已保存")
        return true
    else
        print("[RAG配置] 保存失败: " .. tostring(err))
        return false
    end
end

-- 从文件加载配置
function ConfigManager:Load()
    if not self.save_path then
        return false
    end

    local success, result = pcall(function()
        local file = io.open(self.save_path, "r")
        if file then
            local content = file:read("*all")
            file:close()
            return content
        end
        return nil
    end)

    if success and result then
        local loaded_config = self:JSONToTable(result)
        if loaded_config then
            -- 合并配置（保留默认值）
            for key, value in pairs(loaded_config) do
                self.config[key] = value
            end
            print("[RAG配置] 配置已加载")
            return true
        end
    end

    print("[RAG配置] 使用默认配置")
    return false
end

-- 重置为默认配置
function ConfigManager:Reset(default_config)
    self.config = default_config or {}
    self.dirty = true
    self:Save()
end

-- 简单的Table转JSON（DST Lua环境可能没有json库）
function ConfigManager:TableToJSON(tbl, indent)
    indent = indent or 0
    local spaces = string.rep("  ", indent)
    local result = {}

    if type(tbl) ~= "table" then
        if type(tbl) == "string" then
            return '"' .. tbl:gsub('"', '\\"'):gsub("\n", "\\n") .. '"'
        elseif type(tbl) == "boolean" then
            return tbl and "true" or "false"
        elseif type(tbl) == "nil" then
            return "null"
        else
            return tostring(tbl)
        end
    end

    -- 检查是否是数组
    local is_array = true
    local max_index = 0
    for k, v in pairs(tbl) do
        if type(k) ~= "number" or k < 1 or k ~= math.floor(k) then
            is_array = false
            break
        end
        max_index = math.max(max_index, k)
    end
    is_array = is_array and max_index == #tbl

    if is_array then
        table.insert(result, "[")
        for i, v in ipairs(tbl) do
            local sep = i < #tbl and "," or ""
            table.insert(result, spaces .. "  " .. self:TableToJSON(v, indent + 1) .. sep)
        end
        table.insert(result, spaces .. "]")
    else
        table.insert(result, "{")
        local items = {}
        for k, v in pairs(tbl) do
            local key = type(k) == "string" and ('"' .. k .. '"') or tostring(k)
            table.insert(items, spaces .. "  " .. key .. ": " .. self:TableToJSON(v, indent + 1))
        end
        table.insert(result, table.concat(items, ",\n"))
        table.insert(result, spaces .. "}")
    end

    return table.concat(result, "\n")
end

-- 简单的JSON转Table
function ConfigManager:JSONToTable(json_str)
    if not json_str or json_str == "" then
        return nil
    end

    -- 尝试使用内置JSON解析（如果有）
    if GLOBAL.json then
        local success, result = pcall(function()
            return GLOBAL.json.decode(json_str)
        end)
        if success then
            return result
        end
    end

    -- 简单的手动解析（仅支持基本类型）
    local success, result = pcall(function()
        -- 移除空白
        json_str = json_str:gsub("^%s+", ""):gsub("%s+$", "")

        -- 简单的递归下降解析器
        local pos = 1

        local function skip_whitespace()
            while pos <= #json_str and json_str:sub(pos, pos):match("%s") do
                pos = pos + 1
            end
        end

        local function parse_value()
            skip_whitespace()
            local char = json_str:sub(pos, pos)

            if char == '"' then
                -- 解析字符串
                pos = pos + 1
                local start = pos
                while pos <= #json_str do
                    local c = json_str:sub(pos, pos)
                    if c == '"' then
                        local str = json_str:sub(start, pos - 1)
                        pos = pos + 1
                        return str:gsub("\\n", "\n"):gsub('\\"', '"')
                    elseif c == '\\' then
                        pos = pos + 2
                    else
                        pos = pos + 1
                    end
                end
            elseif char == '{' then
                -- 解析对象
                pos = pos + 1
                local obj = {}
                skip_whitespace()
                while json_str:sub(pos, pos) ~= '}' do
                    skip_whitespace()
                    local key = parse_value()
                    skip_whitespace()
                    pos = pos + 1  -- 跳过 ':'
                    local value = parse_value()
                    obj[key] = value
                    skip_whitespace()
                    if json_str:sub(pos, pos) == ',' then
                        pos = pos + 1
                    end
                    skip_whitespace()
                end
                pos = pos + 1
                return obj
            elseif char == '[' then
                -- 解析数组
                pos = pos + 1
                local arr = {}
                skip_whitespace()
                while json_str:sub(pos, pos) ~= ']' do
                    table.insert(arr, parse_value())
                    skip_whitespace()
                    if json_str:sub(pos, pos) == ',' then
                        pos = pos + 1
                    end
                    skip_whitespace()
                end
                pos = pos + 1
                return arr
            elseif json_str:sub(pos, pos + 3) == "true" then
                pos = pos + 4
                return true
            elseif json_str:sub(pos, pos + 4) == "false" then
                pos = pos + 5
                return false
            elseif json_str:sub(pos, pos + 3) == "null" then
                pos = pos + 4
                return nil
            else
                -- 解析数字
                local num_str = json_str:match("^%-?%d+%.?%d*", pos)
                if num_str then
                    pos = pos + #num_str
                    return tonumber(num_str)
                end
            end
        end

        return parse_value()
    end)

    if success then
        return result
    else
        print("[RAG配置] JSON解析失败: " .. tostring(result))
        return nil
    end
end

-- ============================================================
-- 全局实例
-- ============================================================
RAGConfigManager = ConfigManager()

return ConfigManager
