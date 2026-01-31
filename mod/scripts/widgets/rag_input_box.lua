-- 饥荒RAG助手 - 输入框Widget
-- Input Box Widget for RAG Assistant

local Widget = require "widgets/widget"
local Image = require "widgets/image"
local Text = require "widgets/text"
local TextEdit = require "widgets/textedit"

-- 获取自定义字体（如果可用）
local function GetFont()
    return RAG_FONT or BODYTEXTFONT
end

-- 输入框类
local RAGInputBox = Class(Widget, function(self, config)
    Widget._ctor(self, "RAGInputBox")

    self.config = config or {}
    self.width = self.config.width or 300
    self.height = self.config.height or 40
    self.font_size = self.config.font_size or 18
    self.font = GetFont()
    self.placeholder = self.config.placeholder or "输入问题，按回车发送..."
    self.on_submit = self.config.on_submit

    -- 状态
    self.text = ""
    self.is_focused = false

    -- 构建UI
    self:BuildUI()
end)

-- 构建UI
function RAGInputBox:BuildUI()
    -- 输入框背景
    self.bg = self:AddChild(Image("images/global.xml", "square.tex"))
    self.bg:SetSize(self.width, self.height)
    self.bg:SetTint(0.15, 0.15, 0.15, 1)

    -- 边框
    self.border = self:AddChild(Image("images/global.xml", "square.tex"))
    self.border:SetSize(self.width + 2, self.height + 2)
    self.border:SetTint(0.3, 0.3, 0.3, 1)
    self.border:MoveToBack()

    -- 文本编辑器
    self.text_edit = self:AddChild(TextEdit(
        BODYTEXTFONT,
        self.font_size,
        "",
        {1, 1, 1, 1}
    ))
    self.text_edit:SetPosition(0, 0, 0)
    self.text_edit:SetRegionSize(self.width - 20, self.height)
    self.text_edit:SetHAlign(ANCHOR_LEFT)
    self.text_edit:SetVAlign(ANCHOR_MIDDLE)

    -- 设置文本编辑回调
    self.text_edit.OnTextEntered = function()
        self:OnEnter()
    end

    self.text_edit:SetOnGainFocus(function()
        self:OnGainFocus()
    end)

    self.text_edit:SetOnLoseFocus(function()
        self:OnLoseFocus()
    end)

    -- 占位符文本
    self.placeholder_text = self:AddChild(Text(BODYTEXTFONT, self.font_size, self.placeholder))
    self.placeholder_text:SetPosition(-self.width / 2 + 10, 0, 0)
    self.placeholder_text:SetHAlign(ANCHOR_LEFT)
    self.placeholder_text:SetColour(0.5, 0.5, 0.5, 0.8)
end

-- 回车提交
function RAGInputBox:OnEnter()
    local text = self:GetText()
    if text and text ~= "" then
        if self.on_submit then
            self.on_submit(text)
        end
    end
end

-- 获得焦点
function RAGInputBox:OnGainFocus()
    self.is_focused = true
    self.border:SetTint(0.4, 0.6, 1, 1)  -- 高亮边框
    self:UpdatePlaceholder()
end

-- 失去焦点
function RAGInputBox:OnLoseFocus()
    self.is_focused = false
    self.border:SetTint(0.3, 0.3, 0.3, 1)  -- 恢复边框
    self:UpdatePlaceholder()
end

-- 更新占位符显示
function RAGInputBox:UpdatePlaceholder()
    local text = self:GetText()
    if text and text ~= "" then
        self.placeholder_text:Hide()
    else
        if not self.is_focused then
            self.placeholder_text:Show()
        else
            self.placeholder_text:Hide()
        end
    end
end

-- 获取文本
function RAGInputBox:GetText()
    if self.text_edit then
        return self.text_edit:GetString()
    end
    return ""
end

-- 设置文本
function RAGInputBox:SetText(text)
    if self.text_edit then
        self.text_edit:SetString(text or "")
    end
    self:UpdatePlaceholder()
end

-- 清空文本
function RAGInputBox:Clear()
    self:SetText("")
end

-- 设置焦点
function RAGInputBox:SetFocus()
    if self.text_edit then
        self.text_edit:SetFocus()
    end
end

-- 设置占位符
function RAGInputBox:SetPlaceholder(text)
    self.placeholder = text or ""
    if self.placeholder_text then
        self.placeholder_text:SetString(self.placeholder)
    end
end

-- 设置字体大小
function RAGInputBox:SetFontSize(size)
    self.font_size = size
    if self.text_edit then
        self.text_edit:SetSize(size)
    end
    if self.placeholder_text then
        self.placeholder_text:SetSize(size)
    end
end

-- 启用
function RAGInputBox:Enable()
    if self.text_edit then
        self.text_edit:Enable()
    end
    self.bg:SetTint(0.15, 0.15, 0.15, 1)
end

-- 禁用
function RAGInputBox:Disable()
    if self.text_edit then
        self.text_edit:Disable()
    end
    self.bg:SetTint(0.1, 0.1, 0.1, 0.5)
end

-- 导出
RAGInputBox = RAGInputBox

return RAGInputBox
