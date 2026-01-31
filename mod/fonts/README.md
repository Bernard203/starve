# 中文字体目录

本目录用于存放中文字体文件，以支持Mod界面的中文显示。

## 推荐字体

### 思源黑体 (Source Han Sans)
- 下载地址: https://github.com/adobe-fonts/source-han-sans/releases
- 许可证: SIL Open Font License 1.1
- 将 `SourceHanSansCN-Regular.otf` 或 `.ttf` 文件放到此目录

### 文泉驿微米黑
- 下载地址: http://wenq.org/wqy2/index.cgi?MicroHei
- 许可证: GPL + FE (font exception)
- 将 `wqy-microhei.ttc` 文件放到此目录

### Noto Sans CJK
- 下载地址: https://github.com/googlefonts/noto-cjk/releases
- 许可证: SIL Open Font License 1.1
- 将 `NotoSansCJKsc-Regular.otf` 文件放到此目录

## 安装方法

1. 下载上述任一字体
2. 将字体文件放到此目录 (`mod/fonts/`)
3. 修改 `modmain.lua` 中的 `USE_CUSTOM_FONT = true`
4. 在 Assets 表中取消注释对应的字体声明
5. 重启游戏

## 注意事项

- DST支持 .ttf 和 .otf 格式的字体文件
- 字体文件名不要包含空格和特殊字符
- 如果中文仍然显示为方块，可能需要调整字体大小
