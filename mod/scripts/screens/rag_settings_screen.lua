-- 饥荒RAG助手 - 设置界面Screen
-- Settings Screen for RAG Assistant

local Screen = require "widgets/screen"
local Widget = require "widgets/widget"
local Image = require "widgets/image"
local ImageButton = require "widgets/imagebutton"
local Text = require "widgets/text"

-- 设置界面类
local RAGSettingsScreen = Class(Screen, function(self, config, on_save)
    Screen._ctor(self, "RAGSettingsScreen")

    self.config = config or {}
    self.on_save = on_save

    -- 构建UI
    self:BuildUI()
end)

-- 构建UI
function RAGSettingsScreen:BuildUI()
    -- 全屏半透明背景
    self.black = self:AddChild(Image("images/global.xml", "square.tex"))
    self.black:SetVRegPoint(ANCHOR_MIDDLE)
    self.black:SetHRegPoint(ANCHOR_MIDDLE)
    self.black:SetVAnchor(ANCHOR_MIDDLE)
    self.black:SetHAnchor(ANCHOR_MIDDLE)
    self.black:SetScaleMode(SCALEMODE_FILLSCREEN)
    self.black:SetTint(0, 0, 0, 0.7)

    -- 主面板
    self.panel = self:AddChild(Widget("panel"))
    self.panel:SetVAnchor(ANCHOR_MIDDLE)
    self.panel:SetHAnchor(ANCHOR_MIDDLE)

    -- 设置面板Widget
    self.settings = self.panel:AddChild(RAGSettings(self.config, function(new_config)
        -- 实时预览变更
        self:OnSettingsChanged(new_config)
    end))

    -- 关闭按钮
    self.close_btn = self.panel:AddChild(ImageButton("images/global.xml", "close.tex", "close.tex", "close.tex"))
    self.close_btn:SetPosition(220, 230, 0)
    self.close_btn:SetScale(0.5)
    self.close_btn:SetOnClick(function()
        self:Close()
    end)

    -- ESC键关闭
    self:SetupKeyHandlers()
end

-- 设置键盘处理
function RAGSettingsScreen:SetupKeyHandlers()
    -- 暂时使用简单的方式
end

-- 设置变更回调
function RAGSettingsScreen:OnSettingsChanged(new_config)
    -- 可以在这里做实时预览
end

-- 关闭界面
function RAGSettingsScreen:Close()
    -- 保存设置
    if self.on_save and self.settings then
        local final_settings = self.settings:GetSettings()
        self.on_save(final_settings)
    end

    -- 关闭界面
    TheFrontEnd:PopScreen(self)
end

-- 点击背景关闭
function RAGSettingsScreen:OnBecomeInactive()
    Screen.OnBecomeInactive(self)
end

-- 导出
RAGSettingsScreen = RAGSettingsScreen

return RAGSettingsScreen
