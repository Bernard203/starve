-- 饥荒RAG助手 主入口文件
-- Don't Starve Together RAG Assistant - Main Entry

-- ============================================================
-- 全局变量声明
-- ============================================================
GLOBAL = GLOBAL or _G
local TheInput = GLOBAL.TheInput
local ThePlayer = GLOBAL.ThePlayer
local TheFrontEnd = GLOBAL.TheFrontEnd
local STRINGS = GLOBAL.STRINGS

-- ============================================================
-- 资源声明 (图标、字体等)
-- ============================================================
Assets = {
    -- Mod图标
    Asset("ATLAS", "modicon.xml"),
    Asset("IMAGE", "modicon.tex"),

    -- 中文字体 (如果存在则加载)
    -- 注意: 需要将字体文件放到 mod/fonts/ 目录
    -- Asset("FONT", "fonts/SourceHanSansCN-Regular.ttf"),
}

-- ============================================================
-- 自定义字体配置
-- ============================================================
-- 检查自定义字体是否存在，如果存在则使用，否则回退到系统字体
local CUSTOM_FONT_PATH = "fonts/SourceHanSansCN-Regular"
local USE_CUSTOM_FONT = false

-- 尝试检测字体文件
local function CheckFontExists()
    -- DST没有直接的文件存在检查API
    -- 这里我们通过尝试加载来检测
    -- 实际上，如果字体在Assets中声明且文件存在，就会被加载
    return false  -- 默认使用系统字体，等字体文件添加后再启用
end

-- 全局字体变量 (供Widget使用)
RAG_FONT = USE_CUSTOM_FONT and CUSTOM_FONT_PATH or GLOBAL.BODYTEXTFONT
RAG_TITLE_FONT = USE_CUSTOM_FONT and CUSTOM_FONT_PATH or GLOBAL.TITLEFONT

-- ============================================================
-- 资源加载
-- ============================================================

-- 加载自定义脚本
modimport("scripts/utils/config_manager.lua")
modimport("scripts/utils/http_bridge.lua")
modimport("scripts/widgets/rag_chat_window.lua")
modimport("scripts/widgets/rag_input_box.lua")
modimport("scripts/widgets/rag_message_list.lua")
modimport("scripts/widgets/rag_settings.lua")
modimport("scripts/screens/rag_settings_screen.lua")
modimport("scripts/components/rag_assistant.lua")

-- ============================================================
-- 配置获取
-- ============================================================
local HOTKEY = GetModConfigData("hotkey") or KEY_Y
local SERVER_HOST = GetModConfigData("server_host") or "localhost"
local SERVER_PORT = GetModConfigData("server_port") or 8000
local DEFAULT_TRANSPARENCY = GetModConfigData("default_transparency") or 0.8
local FONT_SIZE = GetModConfigData("font_size") or 18
local THEME_COLOR = GetModConfigData("theme_color") or "blue"
local WINDOW_POSITION = GetModConfigData("window_position") or "bottom_right"
local AUTO_CONTEXT = GetModConfigData("auto_context")
local TIMEOUT = GetModConfigData("timeout") or 30

if AUTO_CONTEXT == nil then AUTO_CONTEXT = true end

-- ============================================================
-- 主题颜色定义
-- ============================================================
local THEME_COLORS = {
    blue = {
        primary = {0.2, 0.4, 0.8, 1},
        secondary = {0.1, 0.2, 0.4, 1},
        accent = {0.4, 0.6, 1, 1},
        text = {1, 1, 1, 1},
        bg = {0, 0, 0, 0.8},
    },
    green = {
        primary = {0.2, 0.7, 0.3, 1},
        secondary = {0.1, 0.35, 0.15, 1},
        accent = {0.4, 0.9, 0.5, 1},
        text = {1, 1, 1, 1},
        bg = {0, 0, 0, 0.8},
    },
    purple = {
        primary = {0.6, 0.2, 0.8, 1},
        secondary = {0.3, 0.1, 0.4, 1},
        accent = {0.8, 0.4, 1, 1},
        text = {1, 1, 1, 1},
        bg = {0, 0, 0, 0.8},
    },
    orange = {
        primary = {0.9, 0.5, 0.1, 1},
        secondary = {0.45, 0.25, 0.05, 1},
        accent = {1, 0.7, 0.3, 1},
        text = {1, 1, 1, 1},
        bg = {0, 0, 0, 0.8},
    },
    red = {
        primary = {0.8, 0.2, 0.2, 1},
        secondary = {0.4, 0.1, 0.1, 1},
        accent = {1, 0.4, 0.4, 1},
        text = {1, 1, 1, 1},
        bg = {0, 0, 0, 0.8},
    },
}

-- ============================================================
-- 全局RAG助手实例
-- ============================================================
local RAGAssistantInstance = nil

-- ============================================================
-- 初始化函数
-- ============================================================
local function InitRAGAssistant(inst)
    if RAGAssistantInstance then
        return RAGAssistantInstance
    end

    -- 获取当前主题
    local theme = THEME_COLORS[THEME_COLOR] or THEME_COLORS.blue

    -- 创建配置
    local config = {
        server_url = string.format("http://%s:%d", SERVER_HOST, SERVER_PORT),
        transparency = DEFAULT_TRANSPARENCY,
        font_size = FONT_SIZE,
        theme = theme,
        window_position = WINDOW_POSITION,
        auto_context = AUTO_CONTEXT,
        timeout = TIMEOUT,
        hotkey = HOTKEY,
    }

    -- 初始化HTTP桥接
    if RAGHttpBridge then
        RAGHttpBridge:Init(config.server_url, config.timeout)
    end

    -- 初始化配置管理器
    if RAGConfigManager then
        RAGConfigManager:Init(config)
    end

    print("[RAG助手] 初始化完成")
    print("[RAG助手] 服务器地址: " .. config.server_url)
    print("[RAG助手] 按 " .. (HOTKEY == KEY_Y and "Y" or "其他键") .. " 键打开助手窗口")

    return config
end

-- ============================================================
-- 显示/隐藏聊天窗口
-- ============================================================
local ChatWindowVisible = false
local ChatWindowWidget = nil

local function ToggleChatWindow()
    if not ThePlayer then
        return
    end

    ChatWindowVisible = not ChatWindowVisible

    if ChatWindowVisible then
        -- 显示窗口
        if not ChatWindowWidget and TheFrontEnd then
            -- 创建聊天窗口
            local screen = TheFrontEnd:GetActiveScreen()
            if screen and RAGChatWindow then
                ChatWindowWidget = screen:AddChild(RAGChatWindow(RAGAssistantInstance))
                ChatWindowWidget:Show()
                print("[RAG助手] 窗口已打开")
            end
        elseif ChatWindowWidget then
            ChatWindowWidget:Show()
            print("[RAG助手] 窗口已显示")
        end
    else
        -- 隐藏窗口
        if ChatWindowWidget then
            ChatWindowWidget:Hide()
            print("[RAG助手] 窗口已隐藏")
        end
    end
end

-- ============================================================
-- 获取游戏上下文
-- ============================================================
local function GetGameContext()
    if not ThePlayer then
        return nil
    end

    local context = {}

    -- 世界状态
    if GLOBAL.TheWorld and GLOBAL.TheWorld.state then
        local state = GLOBAL.TheWorld.state
        context.day = state.cycles or 0
        context.season = state.season or "unknown"
        context.phase = state.phase or "day"
        context.temperature = state.temperature
        context.moisture = state.moisture
        context.precipitationrate = state.precipitationrate
    end

    -- 玩家状态
    if ThePlayer then
        context.character = ThePlayer.prefab or "unknown"

        -- 生命值
        if ThePlayer.components and ThePlayer.components.health then
            context.health = ThePlayer.components.health:GetPercent()
        end

        -- 饥饿值
        if ThePlayer.replica and ThePlayer.replica.hunger then
            context.hunger = ThePlayer.replica.hunger:GetPercent()
        elseif ThePlayer.components and ThePlayer.components.hunger then
            context.hunger = ThePlayer.components.hunger:GetPercent()
        end

        -- 理智值
        if ThePlayer.replica and ThePlayer.replica.sanity then
            context.sanity = ThePlayer.replica.sanity:GetPercent()
        elseif ThePlayer.components and ThePlayer.components.sanity then
            context.sanity = ThePlayer.components.sanity:GetPercent()
        end
    end

    return context
end

-- 格式化上下文为字符串
local function FormatGameContext(context)
    if not context then
        return ""
    end

    local parts = {}

    -- 天数和季节
    if context.day and context.season then
        local season_names = {
            autumn = "秋天",
            winter = "冬天",
            spring = "春天",
            summer = "夏天",
        }
        local season_cn = season_names[context.season] or context.season
        table.insert(parts, string.format("第%d天", context.day))
        table.insert(parts, season_cn)
    end

    -- 时间段
    if context.phase then
        local phase_names = {
            day = "白天",
            dusk = "黄昏",
            night = "夜晚",
        }
        table.insert(parts, phase_names[context.phase] or context.phase)
    end

    -- 角色
    if context.character then
        table.insert(parts, "角色:" .. context.character)
    end

    -- 状态
    if context.health then
        table.insert(parts, string.format("生命%.0f%%", context.health * 100))
    end
    if context.hunger then
        table.insert(parts, string.format("饥饿%.0f%%", context.hunger * 100))
    end
    if context.sanity then
        table.insert(parts, string.format("理智%.0f%%", context.sanity * 100))
    end

    if #parts > 0 then
        return "[" .. table.concat(parts, ", ") .. "] "
    end

    return ""
end

-- 导出上下文函数供其他模块使用
GLOBAL.RAG_GetGameContext = GetGameContext
GLOBAL.RAG_FormatGameContext = FormatGameContext

-- ============================================================
-- 键盘事件处理
-- ============================================================
local function OnKeyPress(key, down)
    if not down then
        return false
    end

    if key == HOTKEY then
        ToggleChatWindow()
        return true
    end

    return false
end

-- ============================================================
-- 玩家初始化
-- ============================================================
AddPlayerPostInit(function(inst)
    if inst ~= ThePlayer then
        return
    end

    -- 初始化RAG助手
    RAGAssistantInstance = InitRAGAssistant(inst)

    -- 注册键盘事件
    TheInput:AddKeyHandler(OnKeyPress)

    print("[RAG助手] 玩家初始化完成")
end)

-- ============================================================
-- 模块卸载清理
-- ============================================================
AddGamePostInit(function()
    print("[RAG助手] 游戏初始化完成")
end)

-- ============================================================
-- 导出全局函数
-- ============================================================

-- 供外部调用的发送问题函数
GLOBAL.RAG_SendQuestion = function(question)
    if not RAGHttpBridge then
        print("[RAG助手] HTTP桥接未初始化")
        return
    end

    -- 添加游戏上下文
    local full_question = question
    if AUTO_CONTEXT then
        local context = GetGameContext()
        local context_str = FormatGameContext(context)
        full_question = context_str .. question
    end

    RAGHttpBridge:SendQuestion(full_question)
end

-- 供外部调用的获取可用LLM列表
GLOBAL.RAG_GetAvailableLLMs = function(callback)
    if not RAGHttpBridge then
        print("[RAG助手] HTTP桥接未初始化")
        return
    end

    RAGHttpBridge:GetLLMList(callback)
end

-- 供外部调用的切换LLM
GLOBAL.RAG_SwitchLLM = function(model_id, callback)
    if not RAGHttpBridge then
        print("[RAG助手] HTTP桥接未初始化")
        return
    end

    RAGHttpBridge:SwitchLLM(model_id, callback)
end

-- 获取当前配置
GLOBAL.RAG_GetConfig = function()
    return RAGAssistantInstance
end

-- 更新配置
GLOBAL.RAG_UpdateConfig = function(key, value)
    if RAGAssistantInstance and key then
        RAGAssistantInstance[key] = value
        if RAGConfigManager then
            RAGConfigManager:Set(key, value)
            RAGConfigManager:Save()
        end
    end
end

print("[RAG助手] Mod加载完成")
