#!/usr/bin/env python3
"""
Mod图标生成脚本
生成256x256的饥荒风格Mod图标

使用方法:
    python generate_icon.py

依赖:
    pip install Pillow
"""

from PIL import Image, ImageDraw, ImageFont
import math
import os

def create_dst_style_icon(output_path: str = "modicon.png", size: int = 256):
    """
    创建饥荒风格的Mod图标

    设计元素:
    - 深色背景（饥荒典型的暗棕色调）
    - 聊天气泡图标
    - "RAG"文字
    - 边框装饰
    """

    # 创建RGBA图像
    img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # 饥荒配色
    DARK_BROWN = (35, 25, 20, 255)      # 深棕色背景
    ORANGE = (220, 140, 40, 255)         # 橙色（饥荒特色）
    LIGHT_ORANGE = (255, 180, 80, 255)   # 浅橙色
    CREAM = (240, 220, 180, 255)         # 奶油色文字
    DARK_OUTLINE = (20, 15, 10, 255)     # 深色轮廓

    # 圆角矩形背景
    padding = 8
    corner_radius = 20

    # 绘制背景（带圆角效果的多边形近似）
    bg_points = []
    for i in range(4):
        angle_start = i * 90 + 45
        cx = size // 2 + (size // 2 - padding - corner_radius) * math.cos(math.radians(angle_start))
        cy = size // 2 + (size // 2 - padding - corner_radius) * math.sin(math.radians(angle_start))
        for j in range(-45, 46, 15):
            angle = angle_start + j
            x = cx + corner_radius * math.cos(math.radians(angle))
            y = cy + corner_radius * math.sin(math.radians(angle))
            bg_points.append((x, y))

    # 简化：使用圆角矩形
    draw.rounded_rectangle(
        [padding, padding, size - padding, size - padding],
        radius=corner_radius,
        fill=DARK_BROWN,
        outline=ORANGE,
        width=3
    )

    # 绘制聊天气泡形状
    bubble_center_x = size // 2
    bubble_center_y = size // 2 - 20
    bubble_width = 140
    bubble_height = 90

    # 气泡主体
    draw.rounded_rectangle(
        [
            bubble_center_x - bubble_width // 2,
            bubble_center_y - bubble_height // 2,
            bubble_center_x + bubble_width // 2,
            bubble_center_y + bubble_height // 2
        ],
        radius=15,
        fill=CREAM,
        outline=DARK_OUTLINE,
        width=2
    )

    # 气泡尾巴（三角形）
    tail_points = [
        (bubble_center_x - 20, bubble_center_y + bubble_height // 2 - 5),
        (bubble_center_x - 40, bubble_center_y + bubble_height // 2 + 25),
        (bubble_center_x + 5, bubble_center_y + bubble_height // 2 - 5),
    ]
    draw.polygon(tail_points, fill=CREAM, outline=DARK_OUTLINE)

    # 绘制"RAG"文字
    try:
        # 尝试使用系统字体
        font_large = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 42)
    except:
        try:
            font_large = ImageFont.truetype("arial.ttf", 42)
        except:
            font_large = ImageFont.load_default()

    # RAG文字
    text = "RAG"
    text_bbox = draw.textbbox((0, 0), text, font=font_large)
    text_width = text_bbox[2] - text_bbox[0]
    text_height = text_bbox[3] - text_bbox[1]
    text_x = bubble_center_x - text_width // 2
    text_y = bubble_center_y - text_height // 2 - 8

    # 文字阴影
    draw.text((text_x + 2, text_y + 2), text, fill=DARK_OUTLINE, font=font_large)
    # 主文字
    draw.text((text_x, text_y), text, fill=ORANGE, font=font_large)

    # 绘制AI图标元素（小圆点表示思考）
    dot_y = bubble_center_y + bubble_height // 2 + 40
    for i, offset in enumerate([-30, 0, 30]):
        dot_x = bubble_center_x + offset
        dot_size = 8 + (i % 2) * 2
        draw.ellipse(
            [dot_x - dot_size, dot_y - dot_size, dot_x + dot_size, dot_y + dot_size],
            fill=LIGHT_ORANGE,
            outline=DARK_OUTLINE
        )

    # 底部"助手"文字
    try:
        font_small = ImageFont.truetype("/usr/share/fonts/truetype/wqy/wqy-microhei.ttc", 20)
        subtitle = "助手"
    except:
        try:
            font_small = ImageFont.truetype("/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc", 20)
            subtitle = "助手"
        except:
            font_small = font_large
            subtitle = "AI"

    sub_bbox = draw.textbbox((0, 0), subtitle, font=font_small)
    sub_width = sub_bbox[2] - sub_bbox[0]
    sub_x = bubble_center_x - sub_width // 2
    sub_y = size - 45

    draw.text((sub_x + 1, sub_y + 1), subtitle, fill=DARK_OUTLINE, font=font_small)
    draw.text((sub_x, sub_y), subtitle, fill=CREAM, font=font_small)

    # 保存图像
    img.save(output_path, 'PNG')
    print(f"图标已保存到: {output_path}")

    return img


def create_modicon_xml(output_path: str = "modicon.xml", size: int = 256):
    """
    创建modicon.xml配置文件
    """
    # 计算UV坐标（1像素边距）
    margin = 1.0 / size
    u1 = margin
    u2 = 1.0 - margin
    v1 = margin
    v2 = 1.0 - margin

    xml_content = f'''<Atlas>
    <Texture filename="modicon.tex" />
    <Elements>
        <Element name="modicon.tex" u1="{u1:.10f}" u2="{u2:.10f}" v1="{v1:.10f}" v2="{v2:.10f}" />
    </Elements>
</Atlas>'''

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(xml_content)

    print(f"XML配置已保存到: {output_path}")


def main():
    # 切换到mod目录
    script_dir = os.path.dirname(os.path.abspath(__file__))
    mod_dir = os.path.dirname(script_dir)  # 上级目录即mod目录

    # 如果在bridge目录下运行，则输出到mod根目录
    if os.path.basename(script_dir) == 'bridge':
        output_dir = mod_dir
    else:
        output_dir = script_dir

    png_path = os.path.join(output_dir, "modicon.png")
    xml_path = os.path.join(output_dir, "modicon.xml")

    # 生成图标
    create_dst_style_icon(png_path)

    # 生成XML
    create_modicon_xml(xml_path)

    print("\n" + "=" * 50)
    print("图标资源生成完成！")
    print("=" * 50)
    print(f"\n生成的文件:")
    print(f"  - {png_path}")
    print(f"  - {xml_path}")
    print(f"\n下一步: 将PNG转换为TEX格式")
    print("方法1: 使用ktech工具")
    print(f"  ktech {png_path} {os.path.join(output_dir, 'modicon.tex')}")
    print("\n方法2: 使用dst-tex-tools")
    print(f"  pip install dst-tex-tools")
    print(f"  dst-tex {png_path} {os.path.join(output_dir, 'modicon.tex')}")
    print("\n方法3: 使用TEXCreator GUI工具")


if __name__ == '__main__':
    main()
