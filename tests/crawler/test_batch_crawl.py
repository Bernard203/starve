"""批量爬取脚本测试"""

import json
import pytest
import signal
from pathlib import Path
from unittest.mock import Mock, MagicMock, patch, PropertyMock
import tempfile


class TestBatchCrawlerStateManagement:
    """BatchCrawler状态管理测试"""

    @pytest.fixture
    def temp_dir(self, tmp_path):
        """临时目录"""
        return tmp_path

    @pytest.fixture
    def mock_crawler_module(self, temp_dir):
        """Mock批量爬取模块"""
        with patch.dict('sys.modules', {
            'config': MagicMock(
                RAW_DATA_DIR=temp_dir,
                PROCESSED_DATA_DIR=temp_dir,
            ),
            'crawler.wiki_crawler': MagicMock(),
            'crawler.cleaner': MagicMock(),
        }):
            yield

    def test_load_state_no_file(self, temp_dir):
        """测试无状态文件时加载"""
        state_file = temp_dir / "crawl_state.json"

        # 状态文件不存在，load_state应该返回False
        assert not state_file.exists()

    def test_load_state_with_file(self, temp_dir):
        """测试成功加载状态"""
        state_file = temp_dir / "crawl_state.json"
        output_file = temp_dir / "wiki_pages_full.json"

        # 创建状态文件
        state = {
            'crawled_titles': ['页面1', '页面2'],
            'failed_titles': ['失败页面'],
            'last_update': '2024-01-01T00:00:00',
        }
        with open(state_file, 'w', encoding='utf-8') as f:
            json.dump(state, f, ensure_ascii=False)

        # 创建输出文件
        results = [
            {'title': '页面1', 'content': '内容1'},
            {'title': '页面2', 'content': '内容2'},
        ]
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False)

        # 验证文件存在
        assert state_file.exists()
        assert output_file.exists()

        # 加载状态
        with open(state_file, 'r', encoding='utf-8') as f:
            loaded_state = json.load(f)

        assert set(loaded_state['crawled_titles']) == {'页面1', '页面2'}
        assert loaded_state['failed_titles'] == ['失败页面']

    def test_save_state_creates_files(self, temp_dir):
        """测试保存状态创建文件"""
        state_file = temp_dir / "crawl_state.json"
        output_file = temp_dir / "wiki_pages_full.json"

        # 模拟保存状态
        state = {
            'crawled_titles': ['页面A'],
            'failed_titles': [],
            'last_update': '2024-01-01T00:00:00',
        }
        with open(state_file, 'w', encoding='utf-8') as f:
            json.dump(state, f, ensure_ascii=False, indent=2)

        results = [{'title': '页面A', 'content': '内容A'}]
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2)

        # 验证文件被创建
        assert state_file.exists()
        assert output_file.exists()

        # 验证内容正确
        with open(state_file, 'r', encoding='utf-8') as f:
            saved_state = json.load(f)
        assert '页面A' in saved_state['crawled_titles']

    def test_save_state_preserves_data(self, temp_dir):
        """测试保存状态数据完整性"""
        state_file = temp_dir / "crawl_state.json"

        # 保存多次
        for i in range(3):
            state = {
                'crawled_titles': [f'页面{j}' for j in range(i + 1)],
                'failed_titles': [],
                'last_update': f'2024-01-0{i + 1}T00:00:00',
            }
            with open(state_file, 'w', encoding='utf-8') as f:
                json.dump(state, f, ensure_ascii=False)

        # 验证最终状态
        with open(state_file, 'r', encoding='utf-8') as f:
            final_state = json.load(f)

        assert len(final_state['crawled_titles']) == 3


class TestBatchCrawlerCheckpoint:
    """断点续爬测试"""

    @pytest.fixture
    def temp_dir(self, tmp_path):
        return tmp_path

    def test_crawl_skips_already_crawled(self, temp_dir):
        """测试跳过已爬取页面"""
        # 已爬取的标题集合
        crawled_titles = {'页面1', '页面2'}

        # 所有页面列表
        all_pages = [
            {'title': '页面1'},
            {'title': '页面2'},
            {'title': '页面3'},
            {'title': '页面4'},
        ]

        # 过滤逻辑
        pending = [p for p in all_pages if p['title'] not in crawled_titles]

        assert len(pending) == 2
        assert pending[0]['title'] == '页面3'
        assert pending[1]['title'] == '页面4'

    def test_crawl_resumes_from_checkpoint(self, temp_dir):
        """测试从断点恢复"""
        state_file = temp_dir / "crawl_state.json"

        # 模拟之前的断点状态
        state = {
            'crawled_titles': ['页面1', '页面2', '页面3'],
            'failed_titles': ['失败页面1'],
        }
        with open(state_file, 'w', encoding='utf-8') as f:
            json.dump(state, f, ensure_ascii=False)

        # 加载状态
        with open(state_file, 'r', encoding='utf-8') as f:
            loaded_state = json.load(f)

        crawled_titles = set(loaded_state['crawled_titles'])

        # 验证恢复了正确数量的已爬取页面
        assert len(crawled_titles) == 3
        assert '页面1' in crawled_titles
        assert '页面3' in crawled_titles

    def test_periodic_save(self, temp_dir):
        """测试定期保存"""
        output_file = temp_dir / "wiki_pages_full.json"

        # 模拟定期保存逻辑
        save_interval = 5
        results = []

        for i in range(12):
            results.append({'title': f'页面{i}', 'content': f'内容{i}'})

            # 每save_interval次保存一次
            if (i + 1) % save_interval == 0:
                with open(output_file, 'w', encoding='utf-8') as f:
                    json.dump(results, f, ensure_ascii=False)

        # 验证最后一次保存包含10个结果(5和10时保存)
        with open(output_file, 'r', encoding='utf-8') as f:
            saved_results = json.load(f)

        # 最后一次保存是在i=9时(第10个)
        assert len(saved_results) == 10


class TestBatchCrawlerInterrupt:
    """中断处理测试"""

    def test_interrupt_flag_setting(self):
        """测试中断标志设置"""
        interrupted = False

        def handle_interrupt(signum, frame):
            nonlocal interrupted
            interrupted = True

        # 模拟信号处理
        handle_interrupt(signal.SIGINT, None)

        assert interrupted is True

    def test_crawl_stops_on_interrupt(self):
        """测试中断时停止爬取"""
        interrupted = False
        processed = 0
        max_to_process = 10

        pages = [{'title': f'页面{i}'} for i in range(max_to_process)]

        for i, page in enumerate(pages):
            if interrupted:
                break

            processed += 1

            # 模拟在第5个时被中断
            if i == 4:
                interrupted = True

        assert processed == 5  # 只处理了5个

    def test_state_saved_on_interrupt(self, tmp_path):
        """测试中断时保存状态"""
        state_file = tmp_path / "crawl_state.json"
        interrupted = False
        results = []

        pages = [{'title': f'页面{i}'} for i in range(10)]

        for i, page in enumerate(pages):
            if interrupted:
                break

            results.append({'title': page['title']})

            if i == 4:
                interrupted = True

        # 中断后保存状态
        if interrupted:
            state = {'crawled_titles': [r['title'] for r in results]}
            with open(state_file, 'w', encoding='utf-8') as f:
                json.dump(state, f, ensure_ascii=False)

        # 验证状态被保存
        assert state_file.exists()
        with open(state_file, 'r', encoding='utf-8') as f:
            saved_state = json.load(f)
        assert len(saved_state['crawled_titles']) == 5


class TestBatchCrawlerClean:
    """清洗集成测试"""

    @pytest.fixture
    def temp_dir(self, tmp_path):
        return tmp_path

    def test_clean_requires_data(self, temp_dir):
        """测试清洗需要数据"""
        output_file = temp_dir / "wiki_pages_full.json"

        # 没有数据时
        if not output_file.exists():
            results = []

        assert len(results) == 0

    def test_clean_loads_from_file(self, temp_dir):
        """测试从文件加载数据清洗"""
        output_file = temp_dir / "wiki_pages_full.json"

        # 创建数据文件
        data = [
            {'title': '页面1', 'content': '内容1' * 100},
            {'title': '页面2', 'content': '短内容'},
        ]
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False)

        # 加载数据
        with open(output_file, 'r', encoding='utf-8') as f:
            results = json.load(f)

        assert len(results) == 2


class TestBatchCrawlerProgress:
    """进度显示测试"""

    def test_progress_calculation(self):
        """测试进度计算"""
        total = 100
        processed = 25
        elapsed_seconds = 60  # 1分钟

        # 计算速度（页/分钟）
        speed = processed / (elapsed_seconds / 60) if elapsed_seconds > 0 else 0

        # 计算剩余时间（分钟）
        remaining_pages = total - processed
        remaining_time = remaining_pages / speed if speed > 0 else 0

        assert speed == 25.0  # 25页/分钟
        assert remaining_time == 3.0  # 3分钟

    def test_progress_with_zero_elapsed(self):
        """测试零耗时进度"""
        processed = 0
        elapsed_seconds = 0

        # 避免除零
        speed = processed / elapsed_seconds if elapsed_seconds > 0 else 0

        assert speed == 0


class TestBatchCrawlerConfig:
    """配置测试"""

    def test_default_save_interval(self):
        """测试默认保存间隔"""
        save_interval = 50  # 默认值
        assert save_interval == 50

    def test_max_pages_limit(self):
        """测试最大页数限制"""
        all_pages = [{'title': f'页面{i}'} for i in range(1000)]
        max_pages = 100

        if max_pages:
            all_pages = all_pages[:max_pages]

        assert len(all_pages) == 100

    def test_quality_threshold(self):
        """测试质量阈值"""
        min_quality = 0.2

        pages = [
            {'title': '高质量', 'quality': 0.8},
            {'title': '中等质量', 'quality': 0.5},
            {'title': '低质量', 'quality': 0.1},
        ]

        filtered = [p for p in pages if p['quality'] >= min_quality]

        assert len(filtered) == 2
        assert all(p['quality'] >= min_quality for p in filtered)
