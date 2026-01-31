-- 饥荒RAG助手 - 设置面板Widget
-- Settings Panel Widget for RAG Assistant

local Widget = require "widgets/widget"
local Image = require "widgets/image"
local ImageButton = require "widgets/imagebutton"
local Text = require "widgets/text"
local Spinner = require "widgets/spinner"

-- 获取自定义字体（如果可用）
local function GetFont()
    return RAG_FONT or BODYTEXTFONT
end

local function GetTitleFont()
    return RAG_TITLE_FONT or TITLEFONT
end

-- 设置面板类
local RAGSettings = Class(Widget, function(self, config, on_change)
    Widget._ctor(self, "RAGSettings")

    self.config = config or {}
    self.on_change = on_change

    self.width = 400
    self.height = 450
    self.font = GetFont()
    self.title_font = GetTitleFont()

    -- 当前设置值
    self.settings = {
        transparency = self.config.transparency or 0.8,
        font_size = self.config.font_size or 18,
        theme_color = "blue",
        auto_context = self.config.auto_context ~= false,
        timeout = self.config.timeout or 30,
        current_llm = "ollama/qwen2.5:7b",
    }

    -- 可用的LLM列表
    self.available_llms = {}

    -- 构建UI
    self:BuildUI()

    -- 加载LLM列表
    self:LoadLLMList()
end)

-- 构建UI
function RAGSettings:BuildUI()
    -- 背景
    self.bg = self:AddChild(Image("images/global.xml", "square.tex"))
    self.bg:SetSize(self.width, self.height)
    self.bg:SetTint(0.1, 0.1, 0.1, 0.95)

    -- 标题
    self.title = self:AddChild(Text(TITLEFONT, 28, "设置"))
    self.title:SetPosition(0, self.height / 2 - 30, 0)
    self.title:SetColour(1, 1, 1, 1)

    local y_offset = self.height / 2 - 80
    local row_height = 50

    -- =============== 外观设置 ===============
    self:AddSectionTitle("外观设置", y_offset)
    y_offset = y_offset - 35

    -- 透明度设置
    self:AddSliderRow("背景透明度", y_offset, {
        min = 0.3,
        max = 1.0,
        step = 0.1,
        value = self.settings.transparency,
        format = function(v) return string.format("%.0f%%", v * 100) end,
        on_change = function(v)
            self.settings.transparency = v
            self:NotifyChange()
        end,
    })
    y_offset = y_offset - row_height

    -- 字体大小设置
    self:AddSpinnerRow("字体大小", y_offset, {
        options = {
            {text = "小 (16)", data = 16},
            {text = "中 (18)", data = 18},
            {text = "大 (20)", data = 20},
            {text = "特大 (24)", data = 24},
        },
        value = self.settings.font_size,
        on_change = function(v)
            self.settings.font_size = v
            self:NotifyChange()
        end,
    })
    y_offset = y_offset - row_height

    -- 主题颜色
    self:AddSpinnerRow("主题颜色", y_offset, {
        options = {
            {text = "蓝色", data = "blue"},
            {text = "绿色", data = "green"},
            {text = "紫色", data = "purple"},
            {text = "橙色", data = "orange"},
            {text = "红色", data = "red"},
        },
        value = self.settings.theme_color,
        on_change = function(v)
            self.settings.theme_color = v
            self:NotifyChange()
        end,
    })
    y_offset = y_offset - row_height

    -- =============== AI设置 ===============
    self:AddSectionTitle("AI设置", y_offset)
    y_offset = y_offset - 35

    -- LLM选择
    self.llm_spinner_row = self:AddSpinnerRow("AI模型", y_offset, {
        options = {
            {text = "加载中...", data = "loading"},
        },
        value = "loading",
        on_change = function(v)
            if v ~= "loading" then
                self.settings.current_llm = v
                self:SwitchLLM(v)
            end
        end,
    })
    y_offset = y_offset - row_height

    -- 自动上下文
    self:AddToggleRow("自动附加游戏状态", y_offset, {
        value = self.settings.auto_context,
        on_change = function(v)
            self.settings.auto_context = v
            self:NotifyChange()
        end,
    })
    y_offset = y_offset - row_height

    -- 超时设置
    self:AddSpinnerRow("请求超时", y_offset, {
        options = {
            {text = "15秒", data = 15},
            {text = "30秒", data = 30},
            {text = "60秒", data = 60},
            {text = "120秒", data = 120},
        },
        value = self.settings.timeout,
        on_change = function(v)
            self.settings.timeout = v
            self:NotifyChange()
        end,
    })
    y_offset = y_offset - row_height

    -- =============== 底部按钮 ===============
    y_offset = -self.height / 2 + 40

    -- 重置按钮
    self.reset_btn = self:AddChild(ImageButton("images/global.xml", "button.tex", "button.tex", "button.tex"))
    self.reset_btn:SetPosition(-80, y_offset, 0)
    self.reset_btn:SetScale(0.8)
    self.reset_btn:SetText("重置")
    self.reset_btn:SetOnClick(function()
        self:ResetToDefaults()
    end)

    -- 保存按钮
    self.save_btn = self:AddChild(ImageButton("images/global.xml", "button.tex", "button.tex", "button.tex"))
    self.save_btn:SetPosition(80, y_offset, 0)
    self.save_btn:SetScale(0.8)
    self.save_btn:SetText("保存")
    self.save_btn:SetOnClick(function()
        self:Save()
    end)
end

-- 添加分节标题
function RAGSettings:AddSectionTitle(text, y_pos)
    local section = self:AddChild(Text(BODYTEXTFONT, 20, text))
    section:SetPosition(-self.width / 2 + 100, y_pos, 0)
    section:SetColour(0.7, 0.8, 1, 1)

    local line = self:AddChild(Image("images/global.xml", "square.tex"))
    line:SetSize(self.width - 40, 2)
    line:SetPosition(0, y_pos - 15, 0)
    line:SetTint(0.3, 0.3, 0.3, 1)
end

-- 添加滑块行
function RAGSettings:AddSliderRow(label, y_pos, options)
    -- 标签
    local text = self:AddChild(Text(BODYTEXTFONT, 18, label))
    text:SetPosition(-self.width / 2 + 100, y_pos, 0)
    text:SetColour(1, 1, 1, 1)

    -- 值显示
    local value_text = self:AddChild(Text(BODYTEXTFONT, 16, options.format(options.value)))
    value_text:SetPosition(self.width / 2 - 50, y_pos, 0)
    value_text:SetColour(0.8, 0.8, 0.8, 1)

    -- 简化的滑块（用按钮模拟）
    local decrease_btn = self:AddChild(ImageButton("images/global.xml", "arrow.tex", "arrow.tex", "arrow.tex"))
    decrease_btn:SetPosition(self.width / 2 - 130, y_pos, 0)
    decrease_btn:SetScale(0.3)
    decrease_btn:SetRotation(180)
    decrease_btn:SetOnClick(function()
        local new_val = math.max(options.min, options.value - options.step)
        options.value = new_val
        value_text:SetString(options.format(new_val))
        if options.on_change then
            options.on_change(new_val)
        end
    end)

    local increase_btn = self:AddChild(ImageButton("images/global.xml", "arrow.tex", "arrow.tex", "arrow.tex"))
    increase_btn:SetPosition(self.width / 2 - 90, y_pos, 0)
    increase_btn:SetScale(0.3)
    increase_btn:SetOnClick(function()
        local new_val = math.min(options.max, options.value + options.step)
        options.value = new_val
        value_text:SetString(options.format(new_val))
        if options.on_change then
            options.on_change(new_val)
        end
    end)

    return {text = text, value_text = value_text}
end

-- 添加Spinner行
function RAGSettings:AddSpinnerRow(label, y_pos, options)
    -- 标签
    local text = self:AddChild(Text(BODYTEXTFONT, 18, label))
    text:SetPosition(-self.width / 2 + 100, y_pos, 0)
    text:SetColour(1, 1, 1, 1)

    -- Spinner
    local spinner_options = {}
    local initial_idx = 1
    for i, opt in ipairs(options.options) do
        table.insert(spinner_options, opt.text)
        if opt.data == options.value then
            initial_idx = i
        end
    end

    local spinner = self:AddChild(Spinner(spinner_options, 150, 40, nil, nil, BODYTEXTFONT, 16))
    spinner:SetPosition(self.width / 2 - 100, y_pos, 0)
    spinner:SetSelected(initial_idx)
    spinner:SetOnChangedFn(function(selected_text, idx)
        local data = options.options[idx].data
        if options.on_change then
            options.on_change(data)
        end
    end)

    return {text = text, spinner = spinner}
end

-- 添加开关行
function RAGSettings:AddToggleRow(label, y_pos, options)
    -- 标签
    local text = self:AddChild(Text(BODYTEXTFONT, 18, label))
    text:SetPosition(-self.width / 2 + 120, y_pos, 0)
    text:SetColour(1, 1, 1, 1)

    -- 开关按钮
    local toggle_btn = self:AddChild(ImageButton("images/global.xml", "button.tex", "button.tex", "button.tex"))
    toggle_btn:SetPosition(self.width / 2 - 100, y_pos, 0)
    toggle_btn:SetScale(0.6)
    toggle_btn:SetText(options.value and "开" or "关")

    toggle_btn:SetOnClick(function()
        options.value = not options.value
        toggle_btn:SetText(options.value and "开" or "关")
        if options.on_change then
            options.on_change(options.value)
        end
    end)

    return {text = text, toggle = toggle_btn}
end

-- 加载LLM列表
function RAGSettings:LoadLLMList()
    if GLOBAL.RAG_GetAvailableLLMs then
        GLOBAL.RAG_GetAvailableLLMs(function(response, error)
            if response and response.options then
                self.available_llms = response.options
                self.settings.current_llm = response.current
                self:UpdateLLMSpinner()
            end
        end)
    end
end

-- 更新LLM Spinner
function RAGSettings:UpdateLLMSpinner()
    if self.llm_spinner_row and self.llm_spinner_row.spinner and #self.available_llms > 0 then
        local options = {}
        local selected_idx = 1
        for i, llm in ipairs(self.available_llms) do
            table.insert(options, llm.name)
            if llm.id == self.settings.current_llm then
                selected_idx = i
            end
        end

        -- 重建Spinner（DST的Spinner不支持动态更新选项）
        -- 这里简化处理，实际需要重建Widget
    end
end

-- 切换LLM
function RAGSettings:SwitchLLM(model_id)
    if GLOBAL.RAG_SwitchLLM then
        GLOBAL.RAG_SwitchLLM(model_id, function(response, error)
            if error then
                print("[RAG设置] 切换LLM失败: " .. tostring(error))
            else
                print("[RAG设置] 已切换到: " .. model_id)
            end
        end)
    end
end

-- 通知变更
function RAGSettings:NotifyChange()
    if self.on_change then
        self.on_change(self.settings)
    end
end

-- 重置为默认值
function RAGSettings:ResetToDefaults()
    self.settings = {
        transparency = 0.8,
        font_size = 18,
        theme_color = "blue",
        auto_context = true,
        timeout = 30,
        current_llm = self.settings.current_llm,
    }

    -- 重建UI来反映新值
    -- 实际实现需要更新各个控件的显示

    self:NotifyChange()
    print("[RAG设置] 已重置为默认值")
end

-- 保存设置
function RAGSettings:Save()
    -- 保存到配置管理器
    if RAGConfigManager then
        RAGConfigManager:Update(self.settings)
        RAGConfigManager:Save()
    end

    -- 通知变更
    self:NotifyChange()

    print("[RAG设置] 设置已保存")
end

-- 获取当前设置
function RAGSettings:GetSettings()
    return self.settings
end

-- 导出
RAGSettings = RAGSettings

return RAGSettings
