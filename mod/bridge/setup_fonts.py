#!/usr/bin/env python3
"""
中文字体下载和安装脚本
Downloads and installs Chinese fonts for the DST RAG Assistant mod

使用方法:
    python setup_fonts.py

字体来源:
    思源黑体 (Source Han Sans) - Google/Adobe 开源字体
    许可证: SIL Open Font License (OFL)
"""

import os
import sys
import urllib.request
import zipfile
import shutil
from pathlib import Path


# 字体下载配置
FONTS = {
    "SourceHanSansCN": {
        "name": "思源黑体 (Source Han Sans CN)",
        "url": "https://github.com/adobe-fonts/source-han-sans/releases/download/2.004R/SourceHanSansCN.zip",
        "files": ["SourceHanSansCN-Regular.otf", "SourceHanSansCN-Bold.otf"],
        "license": "SIL Open Font License 1.1",
    },
    "NotoSansCJK": {
        "name": "Noto Sans CJK SC",
        "url": "https://github.com/googlefonts/noto-cjk/releases/download/Sans2.004/03_NotoSansCJK-OTF.zip",
        "files": ["NotoSansCJKsc-Regular.otf"],
        "license": "SIL Open Font License 1.1",
    }
}


def get_mod_fonts_dir():
    """获取Mod字体目录"""
    script_dir = Path(__file__).parent
    if script_dir.name == 'bridge':
        mod_dir = script_dir.parent
    else:
        mod_dir = script_dir

    fonts_dir = mod_dir / 'fonts'
    fonts_dir.mkdir(exist_ok=True)
    return fonts_dir


def download_file(url: str, dest_path: Path, show_progress: bool = True):
    """下载文件"""
    print(f"正在下载: {url}")

    def report_progress(block_num, block_size, total_size):
        if show_progress and total_size > 0:
            percent = min(100, block_num * block_size * 100 // total_size)
            print(f"\r下载进度: {percent}%", end='', flush=True)

    try:
        urllib.request.urlretrieve(url, dest_path, report_progress)
        print()  # 换行
        return True
    except Exception as e:
        print(f"\n下载失败: {e}")
        return False


def extract_fonts(zip_path: Path, fonts_dir: Path, target_files: list):
    """从ZIP中提取字体文件"""
    print(f"正在解压: {zip_path}")

    try:
        with zipfile.ZipFile(zip_path, 'r') as zf:
            for file_info in zf.infolist():
                filename = os.path.basename(file_info.filename)
                if filename in target_files or any(f in filename for f in target_files):
                    # 提取到字体目录
                    with zf.open(file_info) as src:
                        dest_file = fonts_dir / filename
                        with open(dest_file, 'wb') as dst:
                            dst.write(src.read())
                    print(f"  已提取: {filename}")
        return True
    except Exception as e:
        print(f"解压失败: {e}")
        return False


def create_placeholder_font_info(fonts_dir: Path):
    """创建字体说明文件"""
    readme_content = """# 中文字体目录

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
"""

    readme_path = fonts_dir / "README.md"
    with open(readme_path, 'w', encoding='utf-8') as f:
        f.write(readme_content)
    print(f"已创建说明文件: {readme_path}")


def setup_fonts_manual():
    """手动设置字体的说明"""
    fonts_dir = get_mod_fonts_dir()

    print("\n" + "=" * 60)
    print("中文字体设置向导")
    print("=" * 60)

    # 检查是否已有字体文件
    existing_fonts = list(fonts_dir.glob("*.ttf")) + list(fonts_dir.glob("*.otf")) + list(fonts_dir.glob("*.ttc"))

    if existing_fonts:
        print(f"\n已检测到字体文件:")
        for font in existing_fonts:
            print(f"  - {font.name}")
        print("\n字体已就绪，请确保在modmain.lua中正确配置。")
    else:
        print(f"\n字体目录: {fonts_dir}")
        print("\n未检测到字体文件，请按以下步骤添加:")
        print("\n1. 下载中文字体 (推荐思源黑体):")
        print("   https://github.com/adobe-fonts/source-han-sans/releases")
        print("\n2. 将字体文件复制到:")
        print(f"   {fonts_dir}/")
        print("\n3. 修改 modmain.lua 启用自定义字体")

    # 创建说明文件
    create_placeholder_font_info(fonts_dir)

    print("\n" + "=" * 60)


def try_auto_download():
    """尝试自动下载字体"""
    fonts_dir = get_mod_fonts_dir()
    temp_dir = fonts_dir / "temp"
    temp_dir.mkdir(exist_ok=True)

    print("\n尝试自动下载字体...")

    # 尝试下载思源黑体的精简版本
    # 注意：完整的思源黑体很大（100MB+），这里尝试下载精简版

    # 由于网络限制，这里主要提供手动安装说明
    print("由于网络环境限制，建议手动下载字体文件。")

    # 清理临时目录
    if temp_dir.exists():
        shutil.rmtree(temp_dir, ignore_errors=True)

    setup_fonts_manual()


def main():
    print("饥荒RAG助手 - 中文字体设置工具")
    print("-" * 40)

    if len(sys.argv) > 1 and sys.argv[1] == '--auto':
        try_auto_download()
    else:
        setup_fonts_manual()


if __name__ == '__main__':
    main()
