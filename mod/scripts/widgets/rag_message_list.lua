-- 饥荒RAG助手 - 消息列表Widget
-- Message List Widget for RAG Assistant

local Widget = require "widgets/widget"
local Image = require "widgets/image"
local Text = require "widgets/text"

-- 获取自定义字体（如果可用）
local function GetFont()
    return RAG_FONT or BODYTEXTFONT
end

-- 消息列表类
local RAGMessageList = Class(Widget, function(self, config)
    Widget._ctor(self, "RAGMessageList")

    self.config = config or {}
    self.width = self.config.width or 380
    self.height = self.config.height or 350
    self.font_size = self.config.font_size or 18
    self.font = GetFont()
    self.theme = self.config.theme or {
        primary = {0.2, 0.4, 0.8, 1},
        secondary = {0.1, 0.2, 0.4, 1},
        accent = {0.4, 0.6, 1, 1},
        text = {1, 1, 1, 1},
        bg = {0, 0, 0, 0.8},
    }

    -- 消息数据
    self.messages = {}
    self.message_widgets = {}

    -- 滚动状态
    self.scroll_offset = 0
    self.content_height = 0
    self.visible_height = self.height

    -- 构建UI
    self:BuildUI()
end)

-- 构建UI
function RAGMessageList:BuildUI()
    -- 裁剪区域背景
    self.bg = self:AddChild(Image("images/global.xml", "square.tex"))
    self.bg:SetSize(self.width, self.height)
    self.bg:SetTint(0, 0, 0, 0.3)

    -- 消息容器
    self.container = self:AddChild(Widget("container"))
    self.container:SetPosition(0, 0, 0)

    -- 滚动条背景
    self.scrollbar_bg = self:AddChild(Image("images/global.xml", "square.tex"))
    self.scrollbar_bg:SetSize(8, self.height)
    self.scrollbar_bg:SetPosition(self.width / 2 + 5, 0, 0)
    self.scrollbar_bg:SetTint(0.2, 0.2, 0.2, 0.5)

    -- 滚动条滑块
    self.scrollbar_thumb = self:AddChild(Image("images/global.xml", "square.tex"))
    self.scrollbar_thumb:SetSize(6, 50)
    self.scrollbar_thumb:SetPosition(self.width / 2 + 5, 0, 0)
    self.scrollbar_thumb:SetTint(self.theme.accent[1], self.theme.accent[2], self.theme.accent[3], 0.8)
end

-- 设置消息
function RAGMessageList:SetMessages(messages)
    self.messages = messages or {}
    self:RebuildMessages()
end

-- 重建消息列表
function RAGMessageList:RebuildMessages()
    -- 清除旧的Widget
    for _, widget in ipairs(self.message_widgets) do
        widget:Kill()
    end
    self.message_widgets = {}

    -- 计算内容高度并创建消息Widget
    local y_offset = self.height / 2 - 20
    local spacing = 10

    for i, msg in ipairs(self.messages) do
        local msg_widget = self:CreateMessageWidget(msg)
        self.container:AddChild(msg_widget)

        -- 计算消息高度
        local msg_height = self:CalculateMessageHeight(msg)
        y_offset = y_offset - msg_height / 2

        msg_widget:SetPosition(0, y_offset + self.scroll_offset, 0)

        y_offset = y_offset - msg_height / 2 - spacing

        table.insert(self.message_widgets, msg_widget)
    end

    self.content_height = math.abs(y_offset - self.height / 2 + 20)
    self:UpdateScrollbar()
end

-- 创建消息Widget
function RAGMessageList:CreateMessageWidget(message)
    local widget = Widget("message")

    local is_user = message.role == "user"
    local is_error = message.is_error
    local is_system = message.role == "system"

    -- 消息背景颜色
    local bg_color
    if is_error then
        bg_color = {0.6, 0.1, 0.1, 0.8}
    elseif is_user then
        bg_color = {self.theme.primary[1], self.theme.primary[2], self.theme.primary[3], 0.6}
    elseif is_system then
        bg_color = {0.3, 0.3, 0.3, 0.6}
    else
        bg_color = {self.theme.secondary[1], self.theme.secondary[2], self.theme.secondary[3], 0.6}
    end

    -- 消息气泡宽度
    local bubble_width = self.width - 40
    local text_width = bubble_width - 20

    -- 计算文本高度
    local content = message.content or ""
    local lines = self:WrapText(content, text_width)
    local text_height = #lines * (self.font_size + 4)
    local bubble_height = text_height + 30

    -- 背景气泡
    local bg = widget:AddChild(Image("images/global.xml", "square.tex"))
    bg:SetSize(bubble_width, bubble_height)

    -- 根据角色调整位置
    local x_offset = 0
    if is_user then
        x_offset = 20
    else
        x_offset = -20
    end
    bg:SetPosition(x_offset, 0, 0)
    bg:SetTint(bg_color[1], bg_color[2], bg_color[3], bg_color[4])

    -- 角色标签
    local role_text = is_user and "你" or (is_system and "系统" or "助手")
    local role_label = widget:AddChild(Text(BODYTEXTFONT, self.font_size - 2, role_text))
    role_label:SetPosition(x_offset - bubble_width / 2 + 30, bubble_height / 2 - 12, 0)
    role_label:SetColour(self.theme.accent[1], self.theme.accent[2], self.theme.accent[3], 1)

    -- 消息内容
    local y_pos = bubble_height / 2 - 28
    for _, line in ipairs(lines) do
        local text = widget:AddChild(Text(BODYTEXTFONT, self.font_size, line))
        text:SetPosition(x_offset, y_pos, 0)
        text:SetColour(self.theme.text[1], self.theme.text[2], self.theme.text[3], 1)
        y_pos = y_pos - (self.font_size + 4)
    end

    -- 置信度显示（仅助手消息）
    if message.confidence and message.role == "assistant" then
        local conf_text = string.format("置信度: %.0f%%", message.confidence * 100)
        local conf_label = widget:AddChild(Text(BODYTEXTFONT, self.font_size - 4, conf_text))
        conf_label:SetPosition(x_offset + bubble_width / 2 - 50, -bubble_height / 2 + 10, 0)
        conf_label:SetColour(0.6, 0.6, 0.6, 1)
    end

    widget.height = bubble_height

    return widget
end

-- 文本换行
function RAGMessageList:WrapText(text, max_width)
    local lines = {}
    local chars_per_line = math.floor(max_width / (self.font_size * 0.6))

    -- 按换行符分割
    for segment in text:gmatch("[^\n]+") do
        -- 处理长行
        while #segment > 0 do
            if #segment <= chars_per_line then
                table.insert(lines, segment)
                break
            else
                -- 尝试在空格处断行
                local break_pos = chars_per_line
                local space_pos = segment:sub(1, chars_per_line):match(".*%s()")
                if space_pos then
                    break_pos = space_pos - 1
                end

                table.insert(lines, segment:sub(1, break_pos))
                segment = segment:sub(break_pos + 1):gsub("^%s+", "")
            end
        end
    end

    -- 处理空消息
    if #lines == 0 then
        table.insert(lines, "")
    end

    return lines
end

-- 计算消息高度
function RAGMessageList:CalculateMessageHeight(message)
    local content = message.content or ""
    local text_width = self.width - 60
    local lines = self:WrapText(content, text_width)
    local text_height = #lines * (self.font_size + 4)
    return text_height + 30
end

-- 滚动到底部
function RAGMessageList:ScrollToBottom()
    if self.content_height > self.visible_height then
        self.scroll_offset = self.visible_height - self.content_height
    else
        self.scroll_offset = 0
    end
    self:ApplyScroll()
end

-- 滚动
function RAGMessageList:Scroll(delta)
    local max_scroll = 0
    local min_scroll = self.visible_height - self.content_height

    if min_scroll > 0 then
        min_scroll = 0
    end

    self.scroll_offset = math.max(min_scroll, math.min(max_scroll, self.scroll_offset + delta))
    self:ApplyScroll()
end

-- 应用滚动
function RAGMessageList:ApplyScroll()
    -- 更新消息位置
    local y_offset = self.height / 2 - 20
    local spacing = 10

    for i, msg_widget in ipairs(self.message_widgets) do
        local msg = self.messages[i]
        local msg_height = self:CalculateMessageHeight(msg)
        y_offset = y_offset - msg_height / 2

        msg_widget:SetPosition(0, y_offset + self.scroll_offset, 0)

        y_offset = y_offset - msg_height / 2 - spacing
    end

    self:UpdateScrollbar()
end

-- 更新滚动条
function RAGMessageList:UpdateScrollbar()
    if self.content_height <= self.visible_height then
        self.scrollbar_thumb:Hide()
        return
    end

    self.scrollbar_thumb:Show()

    -- 计算滑块大小
    local thumb_height = math.max(20, (self.visible_height / self.content_height) * self.height)
    self.scrollbar_thumb:SetSize(6, thumb_height)

    -- 计算滑块位置
    local scroll_range = self.content_height - self.visible_height
    local scroll_percent = -self.scroll_offset / scroll_range
    local thumb_range = self.height - thumb_height
    local thumb_y = (self.height / 2 - thumb_height / 2) - (scroll_percent * thumb_range)

    self.scrollbar_thumb:SetPosition(self.width / 2 + 5, thumb_y, 0)
end

-- 设置字体大小
function RAGMessageList:SetFontSize(size)
    self.font_size = size
    self:RebuildMessages()
end

-- 设置主题
function RAGMessageList:SetTheme(theme)
    self.theme = theme
    self.scrollbar_thumb:SetTint(self.theme.accent[1], self.theme.accent[2], self.theme.accent[3], 0.8)
    self:RebuildMessages()
end

-- 鼠标滚轮事件
function RAGMessageList:OnScroll(dir)
    self:Scroll(dir * 30)
end

-- 导出
RAGMessageList = RAGMessageList

return RAGMessageList
