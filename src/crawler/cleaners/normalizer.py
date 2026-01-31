"""数据标准化器"""

import re
from typing import Any, Dict, List, Optional


class DataNormalizer:
    """数据标准化器 - 统一不同数据源的格式"""

    # 属性名映射
    STAT_NAME_MAP: Dict[str, List[str]] = {
        'health': ['生命', '生命值', 'health', 'hp', 'ヘルス', '血量'],
        'hunger': ['饥饿', '饥饿值', 'hunger', '飽食度', '满腹度', '饱食'],
        'sanity': ['理智', '理智值', 'sanity', '正気度', 'san'],
        'damage': ['伤害', '攻击', '攻击力', 'damage', 'attack', 'atk'],
        'durability': ['耐久', '耐久度', 'durability', '耐久性'],
        'cook_time': ['烹饪时间', '烹调时间', 'cook time', 'cooking time'],
        'perish_time': ['腐烂时间', '保鲜', 'perish time', '新鮮度'],
        'walk_speed': ['移动速度', '速度', 'walk speed', 'speed'],
        'attack_period': ['攻击间隔', 'attack period', '攻击周期'],
        'range': ['攻击范围', '范围', 'range'],
        'armor': ['护甲', '防御', 'armor', 'protection'],
        'insulation': ['保暖', '隔热', 'insulation'],
        'wetness': ['防水', '湿度', 'wetness', 'waterproof'],
        'fuel': ['燃料', '燃料值', 'fuel'],
        'stack_size': ['堆叠', '堆叠数', 'stack size', 'stackable'],
    }

    # 游戏内物品名称标准化
    ITEM_NAME_MAP: Dict[str, str] = {
        '蒸肉丸': '肉丸',
        '肉丸子': '肉丸',
        'meatballs': '肉丸',
        '蜘蛛女王': '蜘蛛女皇',
        'spider queen': '蜘蛛女皇',
        '锅': '烹饪锅',
        'crock pot': '烹饪锅',
        'cooking pot': '烹饪锅',
    }

    def normalize_stat_name(self, name: str) -> Optional[str]:
        """
        标准化属性名称

        Args:
            name: 原始属性名

        Returns:
            标准化后的属性名，无法识别返回None
        """
        if not name:
            return None

        name_lower = name.lower().strip()

        for canonical, variants in self.STAT_NAME_MAP.items():
            for variant in variants:
                if variant.lower() == name_lower or variant.lower() in name_lower:
                    return canonical

        return None

    def normalize_value(self, value: Any) -> Optional[float]:
        """
        标准化属性值（提取数值）

        Args:
            value: 原始值

        Returns:
            提取的数值，无法提取返回None
        """
        if value is None:
            return None

        if isinstance(value, (int, float)):
            return float(value)

        if isinstance(value, str):
            # 清理字符串
            value = value.strip()

            # 处理范围值（取中间值）
            range_match = re.search(r'([\d.]+)\s*[-~～到]\s*([\d.]+)', value)
            if range_match:
                low = float(range_match.group(1))
                high = float(range_match.group(2))
                return (low + high) / 2

            # 处理带单位的数值
            num_match = re.search(r'[-+]?\d+\.?\d*', value)
            if num_match:
                try:
                    return float(num_match.group())
                except ValueError:
                    pass

        return None

    def normalize_item_name(self, name: str) -> str:
        """
        标准化物品名称

        Args:
            name: 原始物品名

        Returns:
            标准化后的物品名
        """
        if not name:
            return name

        name_lower = name.lower().strip()

        for variant, canonical in self.ITEM_NAME_MAP.items():
            if variant.lower() == name_lower:
                return canonical

        return name

    def normalize_categories(self, categories: List[str]) -> List[str]:
        """
        标准化分类列表

        Args:
            categories: 原始分类列表

        Returns:
            去重后的分类列表
        """
        # 移除前缀
        normalized = []
        for cat in categories:
            # 移除 "Category:" 前缀
            cat = re.sub(r'^(Category|分类)[：:]?\s*', '', cat, flags=re.IGNORECASE)
            cat = cat.strip()
            if cat and cat not in normalized:
                normalized.append(cat)

        return normalized

    def extract_ingredients(self, text: str) -> List[Dict]:
        """
        从文本中提取材料列表

        Args:
            text: 包含材料信息的文本

        Returns:
            材料列表，每项包含 name 和 count
        """
        ingredients = []

        # 匹配 "物品名 x 数量" 或 "物品名 × 数量"
        pattern = r'([^\d\s×x]+)\s*[×x]\s*(\d+)'
        matches = re.findall(pattern, text)

        for name, count in matches:
            name = name.strip()
            if name:
                ingredients.append({
                    'name': self.normalize_item_name(name),
                    'count': int(count),
                })

        return ingredients

    def merge_data(self, *data_dicts: Dict) -> Dict:
        """
        合并多个数据字典，后面的覆盖前面的

        Args:
            *data_dicts: 要合并的字典

        Returns:
            合并后的字典
        """
        result = {}
        for d in data_dicts:
            if d:
                for key, value in d.items():
                    if value is not None and value != '':
                        result[key] = value
        return result
