-- 饥荒RAG助手 - 聊天窗口Widget
-- Chat Window Widget for RAG Assistant

local Widget = require "widgets/widget"
local Image = require "widgets/image"
local ImageButton = require "widgets/imagebutton"
local Text = require "widgets/text"
local TextEdit = require "widgets/textedit"

-- 获取自定义字体（如果可用）
local function GetFont()
    return RAG_FONT or BODYTEXTFONT
end

local function GetTitleFont()
    return RAG_TITLE_FONT or TITLEFONT
end

-- 聊天窗口类
local RAGChatWindow = Class(Widget, function(self, config)
    Widget._ctor(self, "RAGChatWindow")

    self.config = config or {}

    -- 默认配置
    self.width = self.config.width or 400
    self.height = self.config.height or 500
    self.transparency = self.config.transparency or 0.8
    self.font_size = self.config.font_size or 18
    self.font = GetFont()
    self.title_font = GetTitleFont()
    self.theme = self.config.theme or {
        primary = {0.2, 0.4, 0.8, 1},
        secondary = {0.1, 0.2, 0.4, 1},
        accent = {0.4, 0.6, 1, 1},
        text = {1, 1, 1, 1},
        bg = {0, 0, 0, 0.8},
    }

    -- 消息历史
    self.messages = {}
    self.max_messages = 50

    -- 状态
    self.is_loading = false
    self.is_dragging = false
    self.drag_offset = {x = 0, y = 0}

    -- 构建UI
    self:BuildUI()

    -- 设置初始位置
    self:SetPosition(self:GetDefaultPosition())

    -- 默认隐藏
    self:Hide()
end)

-- 获取默认位置
function RAGChatWindow:GetDefaultPosition()
    local pos = self.config.window_position or "bottom_right"
    local screen_w, screen_h = TheSim:GetScreenSize()
    local padding = 20

    local positions = {
        bottom_right = {screen_w / 2 - self.width / 2 - padding, -screen_h / 2 + self.height / 2 + padding},
        top_right = {screen_w / 2 - self.width / 2 - padding, screen_h / 2 - self.height / 2 - padding},
        bottom_left = {-screen_w / 2 + self.width / 2 + padding, -screen_h / 2 + self.height / 2 + padding},
        top_left = {-screen_w / 2 + self.width / 2 + padding, screen_h / 2 - self.height / 2 - padding},
        center = {0, 0},
    }

    local default_pos = positions[pos] or positions.bottom_right
    return default_pos[1], default_pos[2], 0
end

-- 构建UI
function RAGChatWindow:BuildUI()
    -- 背景面板
    self.bg = self:AddChild(Image("images/global.xml", "square.tex"))
    self.bg:SetSize(self.width, self.height)
    self.bg:SetTint(self.theme.bg[1], self.theme.bg[2], self.theme.bg[3], self.transparency)

    -- 标题栏
    self.titlebar = self:AddChild(Widget("titlebar"))
    self.titlebar:SetPosition(0, self.height / 2 - 20, 0)

    self.titlebar_bg = self.titlebar:AddChild(Image("images/global.xml", "square.tex"))
    self.titlebar_bg:SetSize(self.width, 40)
    self.titlebar_bg:SetTint(self.theme.primary[1], self.theme.primary[2], self.theme.primary[3], 1)

    self.title = self.titlebar:AddChild(Text(BODYTEXTFONT, 20, "饥荒RAG助手"))
    self.title:SetColour(self.theme.text[1], self.theme.text[2], self.theme.text[3], 1)
    self.title:SetPosition(-self.width / 2 + 100, 0, 0)

    -- 关闭按钮
    self.close_btn = self.titlebar:AddChild(ImageButton("images/global.xml", "close.tex", "close.tex", "close.tex"))
    self.close_btn:SetPosition(self.width / 2 - 25, 0, 0)
    self.close_btn:SetScale(0.5)
    self.close_btn:SetOnClick(function()
        self:Hide()
    end)

    -- 设置按钮
    self.settings_btn = self.titlebar:AddChild(ImageButton("images/global.xml", "button.tex", "button.tex", "button.tex"))
    self.settings_btn:SetPosition(self.width / 2 - 60, 0, 0)
    self.settings_btn:SetScale(0.4)
    self.settings_btn:SetText("设置")
    self.settings_btn:SetOnClick(function()
        self:OpenSettings()
    end)

    -- 消息列表区域
    self.message_area = self:AddChild(Widget("message_area"))
    self.message_area:SetPosition(0, 20, 0)

    self.message_list = self.message_area:AddChild(RAGMessageList({
        width = self.width - 20,
        height = self.height - 120,
        font_size = self.font_size,
        theme = self.theme,
    }))

    -- 输入区域
    self.input_area = self:AddChild(Widget("input_area"))
    self.input_area:SetPosition(0, -self.height / 2 + 40, 0)

    self.input_bg = self.input_area:AddChild(Image("images/global.xml", "square.tex"))
    self.input_bg:SetSize(self.width - 80, 50)
    self.input_bg:SetTint(self.theme.secondary[1], self.theme.secondary[2], self.theme.secondary[3], 1)
    self.input_bg:SetPosition(-30, 0, 0)

    -- 输入框
    self.input_box = self.input_area:AddChild(RAGInputBox({
        width = self.width - 100,
        height = 40,
        font_size = self.font_size,
        on_submit = function(text)
            self:OnSubmit(text)
        end,
    }))
    self.input_box:SetPosition(-30, 0, 0)

    -- 发送按钮
    self.send_btn = self.input_area:AddChild(ImageButton("images/global.xml", "button.tex", "button.tex", "button.tex"))
    self.send_btn:SetPosition(self.width / 2 - 35, 0, 0)
    self.send_btn:SetScale(0.5)
    self.send_btn:SetText("发送")
    self.send_btn:SetOnClick(function()
        local text = self.input_box:GetText()
        if text and text ~= "" then
            self:OnSubmit(text)
        end
    end)

    -- 加载指示器
    self.loading_indicator = self:AddChild(Text(BODYTEXTFONT, 16, ""))
    self.loading_indicator:SetPosition(0, -self.height / 2 + 80, 0)
    self.loading_indicator:SetColour(self.theme.accent[1], self.theme.accent[2], self.theme.accent[3], 1)
    self.loading_indicator:Hide()

    -- 拖拽区域（标题栏）
    self:SetupDragging()
end

-- 设置拖拽功能
function RAGChatWindow:SetupDragging()
    self.titlebar.OnMouseButton = function(_, button, down, x, y)
        if button == MOUSEBUTTON_LEFT then
            if down then
                self.is_dragging = true
                local pos = self:GetPosition()
                self.drag_offset.x = pos.x - x
                self.drag_offset.y = pos.y - y
            else
                self.is_dragging = false
            end
            return true
        end
        return false
    end

    -- 全局鼠标移动处理
    self.inst:ListenForEvent("mousemove", function(inst, data)
        if self.is_dragging then
            local x, y = TheSim:GetPosition()
            self:SetPosition(x + self.drag_offset.x, y + self.drag_offset.y, 0)
        end
    end, TheInput)
end

-- 提交问题
function RAGChatWindow:OnSubmit(text)
    if not text or text == "" then
        return
    end

    if self.is_loading then
        return  -- 正在加载中，不接受新请求
    end

    -- 添加用户消息
    self:AddMessage({
        role = "user",
        content = text,
        timestamp = os.time(),
    })

    -- 清空输入框
    self.input_box:SetText("")

    -- 显示加载状态
    self:SetLoading(true)

    -- 发送请求
    if GLOBAL.RAG_SendQuestion then
        GLOBAL.RAG_SendQuestion(text)

        -- 注册响应回调（通过HTTP桥接）
        if RAGHttpBridge then
            RAGHttpBridge:SendQuestion(text, function(response, error)
                self:OnResponse(response, error)
            end)
        end
    else
        -- 模拟响应（用于测试）
        self.inst:DoTaskInTime(2, function()
            self:OnResponse({
                answer = "这是一个测试回复。RAG后端未连接。",
                confidence = 0.5,
            }, nil)
        end)
    end
end

-- 处理响应
function RAGChatWindow:OnResponse(response, error)
    self:SetLoading(false)

    if error then
        self:AddMessage({
            role = "system",
            content = "错误: " .. tostring(error),
            timestamp = os.time(),
            is_error = true,
        })
        return
    end

    if response and response.answer then
        self:AddMessage({
            role = "assistant",
            content = response.answer,
            confidence = response.confidence,
            sources = response.sources,
            timestamp = os.time(),
        })
    end
end

-- 添加消息
function RAGChatWindow:AddMessage(message)
    table.insert(self.messages, message)

    -- 限制消息数量
    while #self.messages > self.max_messages do
        table.remove(self.messages, 1)
    end

    -- 更新消息列表显示
    if self.message_list then
        self.message_list:SetMessages(self.messages)
        self.message_list:ScrollToBottom()
    end
end

-- 设置加载状态
function RAGChatWindow:SetLoading(loading)
    self.is_loading = loading

    if loading then
        self.loading_indicator:SetString("正在思考...")
        self.loading_indicator:Show()
        self.send_btn:Disable()

        -- 动画效果
        self:StartLoadingAnimation()
    else
        self.loading_indicator:Hide()
        self.send_btn:Enable()
        self:StopLoadingAnimation()
    end
end

-- 加载动画
function RAGChatWindow:StartLoadingAnimation()
    self.loading_task = self.inst:DoPeriodicTask(0.5, function()
        if self.is_loading then
            local dots = {"", ".", "..", "..."}
            local current = (os.time() % 4) + 1
            self.loading_indicator:SetString("正在思考" .. dots[current])
        end
    end)
end

function RAGChatWindow:StopLoadingAnimation()
    if self.loading_task then
        self.loading_task:Cancel()
        self.loading_task = nil
    end
end

-- 打开设置
function RAGChatWindow:OpenSettings()
    if RAGSettingsScreen then
        TheFrontEnd:PushScreen(RAGSettingsScreen(self.config, function(new_config)
            self:ApplyConfig(new_config)
        end))
    end
end

-- 应用新配置
function RAGChatWindow:ApplyConfig(config)
    if config.transparency then
        self.transparency = config.transparency
        self.bg:SetTint(self.theme.bg[1], self.theme.bg[2], self.theme.bg[3], self.transparency)
    end

    if config.font_size then
        self.font_size = config.font_size
        if self.message_list then
            self.message_list:SetFontSize(self.font_size)
        end
    end

    if config.theme then
        self.theme = config.theme
        self:UpdateTheme()
    end
end

-- 更新主题
function RAGChatWindow:UpdateTheme()
    self.bg:SetTint(self.theme.bg[1], self.theme.bg[2], self.theme.bg[3], self.transparency)
    self.titlebar_bg:SetTint(self.theme.primary[1], self.theme.primary[2], self.theme.primary[3], 1)
    self.input_bg:SetTint(self.theme.secondary[1], self.theme.secondary[2], self.theme.secondary[3], 1)
    self.title:SetColour(self.theme.text[1], self.theme.text[2], self.theme.text[3], 1)
    self.loading_indicator:SetColour(self.theme.accent[1], self.theme.accent[2], self.theme.accent[3], 1)

    if self.message_list then
        self.message_list:SetTheme(self.theme)
    end
end

-- 清空聊天记录
function RAGChatWindow:ClearMessages()
    self.messages = {}
    if self.message_list then
        self.message_list:SetMessages({})
    end
end

-- 显示窗口
function RAGChatWindow:Show()
    Widget.Show(self)
    if self.input_box then
        self.input_box:SetFocus()
    end
end

-- 隐藏窗口
function RAGChatWindow:Hide()
    Widget.Hide(self)
end

-- 切换显示
function RAGChatWindow:Toggle()
    if self.shown then
        self:Hide()
    else
        self:Show()
    end
end

-- 清理
function RAGChatWindow:OnDestroy()
    self:StopLoadingAnimation()
    Widget.OnDestroy(self)
end

-- 导出
RAGChatWindow = RAGChatWindow

return RAGChatWindow
