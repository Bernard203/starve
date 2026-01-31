-- 饥荒RAG助手 Mod信息文件
-- Don't Starve Together RAG Assistant

name = "饥荒RAG助手"
description = [[基于AI的游戏内问答助手

功能特点：
- 游戏内智能问答，快速获取攻略信息
- 支持多种LLM模型切换
- 可自定义界面透明度、颜色、字体
- 支持游戏上下文感知（季节、天数、角色状态）

使用方法：
- 按 Y 键打开/关闭助手窗口
- 输入问题后按回车发送
- 在设置中自定义外观和AI模型

注意：需要启动后端服务才能使用
]]

author = "Starve RAG Team"
version = "0.1.0"

-- DST API版本
api_version = 10

-- 兼容性设置
dst_compatible = true
dont_starve_compatible = false
reign_of_giants_compatible = false
shipwrecked_compatible = false
hamlet_compatible = false

-- 仅客户端Mod
client_only_mod = true
all_clients_require_mod = false

-- 图标
icon_atlas = "modicon.xml"
icon = "modicon.tex"

-- 服务器标签
server_filter_tags = {"RAG", "AI", "助手", "攻略"}

-- 配置选项
configuration_options = {
    -- 快捷键设置
    {
        name = "hotkey",
        label = "打开快捷键",
        hover = "按此键打开/关闭助手窗口",
        options = {
            {description = "Y", data = KEY_Y},
            {description = "U", data = KEY_U},
            {description = "I", data = KEY_I},
            {description = "P", data = KEY_P},
            {description = "H", data = KEY_H},
        },
        default = KEY_Y,
    },

    -- 服务器地址
    {
        name = "server_host",
        label = "服务器地址",
        hover = "RAG后端服务器地址",
        options = {
            {description = "localhost", data = "localhost"},
            {description = "127.0.0.1", data = "127.0.0.1"},
        },
        default = "localhost",
    },

    -- 服务器端口
    {
        name = "server_port",
        label = "服务器端口",
        hover = "RAG后端服务器端口",
        options = {
            {description = "8000", data = 8000},
            {description = "8080", data = 8080},
            {description = "3000", data = 3000},
        },
        default = 8000,
    },

    -- 默认透明度
    {
        name = "default_transparency",
        label = "默认透明度",
        hover = "窗口背景默认透明度",
        options = {
            {description = "100%", data = 1.0},
            {description = "90%", data = 0.9},
            {description = "80%", data = 0.8},
            {description = "70%", data = 0.7},
            {description = "60%", data = 0.6},
            {description = "50%", data = 0.5},
        },
        default = 0.8,
    },

    -- 字体大小
    {
        name = "font_size",
        label = "字体大小",
        hover = "聊天窗口字体大小",
        options = {
            {description = "小", data = 16},
            {description = "中", data = 18},
            {description = "大", data = 20},
            {description = "特大", data = 24},
        },
        default = 18,
    },

    -- 主题颜色
    {
        name = "theme_color",
        label = "主题颜色",
        hover = "界面主题颜色",
        options = {
            {description = "蓝色", data = "blue"},
            {description = "绿色", data = "green"},
            {description = "紫色", data = "purple"},
            {description = "橙色", data = "orange"},
            {description = "红色", data = "red"},
        },
        default = "blue",
    },

    -- 窗口位置
    {
        name = "window_position",
        label = "窗口位置",
        hover = "默认窗口位置",
        options = {
            {description = "右下角", data = "bottom_right"},
            {description = "右上角", data = "top_right"},
            {description = "左下角", data = "bottom_left"},
            {description = "左上角", data = "top_left"},
            {description = "居中", data = "center"},
        },
        default = "bottom_right",
    },

    -- 自动发送游戏上下文
    {
        name = "auto_context",
        label = "自动上下文",
        hover = "自动在问题中附加游戏状态信息",
        options = {
            {description = "开启", data = true},
            {description = "关闭", data = false},
        },
        default = true,
    },

    -- 请求超时
    {
        name = "timeout",
        label = "请求超时",
        hover = "等待AI回复的最长时间（秒）",
        options = {
            {description = "15秒", data = 15},
            {description = "30秒", data = 30},
            {description = "60秒", data = 60},
            {description = "120秒", data = 120},
        },
        default = 30,
    },
}
