#!/usr/bin/env python3
"""
简易KTEX格式生成器
用于将PNG图像转换为饥荒TEX格式的基础版本

注意：这是一个简化实现，可能不完全兼容所有DST版本
推荐使用ktools中的ktech进行正式编译
"""

import struct
import zlib
from PIL import Image
import os


def png_to_tex(png_path: str, tex_path: str):
    """
    将PNG转换为基础TEX格式

    KTEX格式简介:
    - 文件头: "KTEX" 魔数
    - 平台标识
    - 纹理格式信息
    - 压缩的像素数据
    """

    # 加载PNG图像
    img = Image.open(png_path)

    # 确保是RGBA格式
    if img.mode != 'RGBA':
        img = img.convert('RGBA')

    width, height = img.size

    # 验证尺寸是2的幂次方
    if (width & (width - 1)) != 0 or (height & (height - 1)) != 0:
        raise ValueError(f"图像尺寸必须是2的幂次方，当前: {width}x{height}")

    # 获取像素数据
    pixels = img.tobytes()

    # KTEX文件格式
    # 参考: https://github.com/nsimplex/ktools

    # 魔数
    magic = b'KTEX'

    # 头部信息 (简化版本)
    # platform: 12 = PC
    # compression: 5 = DXT5
    # texture_type: 0 = 2D
    # mipmap_count: 1
    # flags: 0x11 (premultiplied alpha, cubemap=false)

    header_data = struct.pack('<4sIIHHHH',
        magic,           # 魔数
        0,               # 保留
        1,               # 纹理数量
        0x0C,            # 平台 (PC)
        5,               # 压缩格式 (DXT5)
        0,               # 纹理类型 (2D)
        1                # mipmap数量
    )

    # Mipmap信息
    mipmap_info = struct.pack('<HHI',
        width,           # 宽度
        height,          # 高度
        len(pixels)      # 数据大小（未压缩）
    )

    # 对于简单情况，我们直接存储RGBA数据（无DXT压缩）
    # 注意：这不是标准的KTEX格式，可能需要ktech进行正确编译

    # 写入文件
    with open(tex_path, 'wb') as f:
        f.write(header_data)
        f.write(mipmap_info)
        f.write(pixels)

    print(f"TEX文件已生成: {tex_path}")
    print(f"尺寸: {width}x{height}")
    print(f"注意: 这是简化格式，建议使用ktech进行正式编译")

    return True


def create_placeholder_tex(tex_path: str):
    """
    创建占位符TEX文件
    仅用于测试Mod加载，实际使用需要正确编译
    """

    # 创建一个简单的1x1像素TEX
    # 这样Mod至少可以加载而不会报错

    # 简化的KTEX头部
    data = bytearray()

    # KTEX魔数
    data.extend(b'KTEX')

    # 版本和标志 (简化)
    data.extend(struct.pack('<I', 0))  # header specs
    data.extend(struct.pack('<I', 1))  # num_textures

    # 纹理信息
    data.extend(struct.pack('<H', 1))   # width
    data.extend(struct.pack('<H', 1))   # height
    data.extend(struct.pack('<H', 1))   # pitch
    data.extend(struct.pack('<H', 5))   # format (DXT5)

    # 1x1像素的DXT5数据 (16字节块)
    # 这是一个橙色像素
    dxt5_block = bytes([
        0xFF, 0xFF, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,  # Alpha
        0x00, 0xF8, 0x00, 0xF8, 0x00, 0x00, 0x00, 0x00   # Color (orange)
    ])
    data.extend(dxt5_block)

    with open(tex_path, 'wb') as f:
        f.write(data)

    print(f"占位符TEX文件已创建: {tex_path}")
    print("警告: 这是占位符文件，实际图标可能无法正确显示")
    print("请使用以下方法生成正确的TEX文件:")
    print("")
    print("方法1: 安装ktools")
    print("  git clone https://github.com/nsimplex/ktools.git")
    print("  cd ktools && cmake . && make && sudo make install")
    print("  ktech modicon.png modicon.tex")
    print("")
    print("方法2: 使用在线工具或TEXCreator")


def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    mod_dir = os.path.dirname(script_dir)

    png_path = os.path.join(mod_dir, "modicon.png")
    tex_path = os.path.join(mod_dir, "modicon.tex")

    if os.path.exists(png_path):
        try:
            # 尝试完整转换
            png_to_tex(png_path, tex_path)
        except Exception as e:
            print(f"完整转换失败: {e}")
            print("创建占位符文件...")
            create_placeholder_tex(tex_path)
    else:
        print(f"PNG文件不存在: {png_path}")
        print("请先运行 generate_icon.py 生成图标")
        print("创建占位符TEX文件...")
        create_placeholder_tex(tex_path)


if __name__ == '__main__':
    main()
