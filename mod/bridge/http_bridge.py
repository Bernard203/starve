#!/usr/bin/env python3
"""
饥荒RAG助手 - Python HTTP桥接脚本
HTTP Bridge for DST RAG Assistant

这个脚本监听Lua写入的请求文件，转发到FastAPI后端，
并将响应写回响应文件供Lua读取。

使用方法:
    python http_bridge.py [--api-url URL] [--bridge-dir DIR]

依赖:
    pip install requests watchdog
"""

import argparse
import json
import logging
import os
import signal
import sys
import time
from pathlib import Path
from typing import Optional, Dict, Any

import requests
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileModifiedEvent

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('bridge.log', encoding='utf-8')
    ]
)
logger = logging.getLogger(__name__)


class RequestHandler(FileSystemEventHandler):
    """处理请求文件变化的事件处理器"""

    def __init__(self, api_url: str, request_file: Path, response_file: Path,
                 timeout: int = 30):
        super().__init__()
        self.api_url = api_url.rstrip('/')
        self.request_file = request_file
        self.response_file = response_file
        self.timeout = timeout
        self.last_request_id = None
        self.processing = False

    def on_modified(self, event):
        """文件修改事件"""
        if not isinstance(event, FileModifiedEvent):
            return

        if Path(event.src_path).resolve() == self.request_file.resolve():
            self.process_request()

    def process_request(self):
        """处理请求"""
        if self.processing:
            return

        self.processing = True

        try:
            # 读取请求
            request_data = self.read_request()
            if not request_data:
                return

            request_id = request_data.get('request_id', 'unknown')

            # 避免重复处理
            if request_id == self.last_request_id:
                return

            self.last_request_id = request_id
            request_type = request_data.get('type', 'ask')

            logger.info(f"处理请求 [{request_id}]: {request_type}")

            # 根据请求类型处理
            if request_type == 'ask':
                response = self.handle_ask(request_data)
            elif request_type == 'get_llm_list':
                response = self.handle_get_llm_list()
            elif request_type == 'switch_llm':
                response = self.handle_switch_llm(request_data)
            else:
                response = {
                    'error': f'未知请求类型: {request_type}',
                    'request_id': request_id
                }

            # 写入响应
            response['request_id'] = request_id
            self.write_response(response)

            logger.info(f"请求完成 [{request_id}]")

        except Exception as e:
            logger.error(f"处理请求失败: {e}")
            self.write_response({
                'error': str(e),
                'request_id': self.last_request_id
            })
        finally:
            self.processing = False

    def read_request(self) -> Optional[Dict[str, Any]]:
        """读取请求文件"""
        try:
            if not self.request_file.exists():
                return None

            content = self.request_file.read_text(encoding='utf-8').strip()
            if not content:
                return None

            return json.loads(content)
        except json.JSONDecodeError as e:
            logger.warning(f"解析请求JSON失败: {e}")
            return None
        except Exception as e:
            logger.error(f"读取请求失败: {e}")
            return None

    def write_response(self, response: Dict[str, Any]):
        """写入响应文件"""
        try:
            self.response_file.write_text(
                json.dumps(response, ensure_ascii=False, indent=2),
                encoding='utf-8'
            )
        except Exception as e:
            logger.error(f"写入响应失败: {e}")

    def handle_ask(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """处理问答请求"""
        question = request_data.get('question', '')

        if not question:
            return {'error': '问题不能为空'}

        try:
            response = requests.post(
                f"{self.api_url}/ask",
                json={
                    "question": question,
                    "use_history": True,
                },
                timeout=self.timeout
            )

            if response.status_code == 200:
                data = response.json()
                return {
                    'answer': data.get('answer', ''),
                    'confidence': data.get('confidence', 0),
                    'sources': data.get('sources', []),
                }
            else:
                return {
                    'error': f'服务器返回错误: {response.status_code}'
                }

        except requests.Timeout:
            return {'error': '请求超时'}
        except requests.ConnectionError:
            return {'error': '无法连接到服务器，请确保后端服务已启动'}
        except Exception as e:
            return {'error': str(e)}

    def handle_get_llm_list(self) -> Dict[str, Any]:
        """处理获取LLM列表请求"""
        try:
            response = requests.get(
                f"{self.api_url}/game/llm/list",
                timeout=self.timeout
            )

            if response.status_code == 200:
                return response.json()
            else:
                return {
                    'error': f'服务器返回错误: {response.status_code}'
                }

        except requests.Timeout:
            return {'error': '请求超时'}
        except requests.ConnectionError:
            return {'error': '无法连接到服务器'}
        except Exception as e:
            return {'error': str(e)}

    def handle_switch_llm(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """处理切换LLM请求"""
        model_id = request_data.get('model_id', '')

        if not model_id:
            return {'error': 'model_id不能为空'}

        try:
            response = requests.post(
                f"{self.api_url}/game/llm/switch",
                params={"model_id": model_id},
                timeout=self.timeout
            )

            if response.status_code == 200:
                return response.json()
            else:
                return {
                    'error': f'服务器返回错误: {response.status_code}'
                }

        except requests.Timeout:
            return {'error': '请求超时'}
        except requests.ConnectionError:
            return {'error': '无法连接到服务器'}
        except Exception as e:
            return {'error': str(e)}


class HTTPBridge:
    """HTTP桥接主类"""

    def __init__(self, api_url: str, bridge_dir: Path, timeout: int = 30):
        self.api_url = api_url
        self.bridge_dir = Path(bridge_dir)
        self.timeout = timeout

        # 确保目录存在
        self.bridge_dir.mkdir(parents=True, exist_ok=True)

        # 请求和响应文件
        self.request_file = self.bridge_dir / "request.json"
        self.response_file = self.bridge_dir / "response.json"

        # 创建空文件
        self.request_file.touch(exist_ok=True)
        self.response_file.touch(exist_ok=True)

        # 文件监控
        self.observer = None
        self.running = False

        # 信号处理
        signal.signal(signal.SIGINT, self._handle_signal)
        signal.signal(signal.SIGTERM, self._handle_signal)

    def _handle_signal(self, signum, frame):
        """处理中断信号"""
        logger.info("收到停止信号...")
        self.stop()

    def start(self):
        """启动桥接服务"""
        logger.info(f"启动HTTP桥接服务")
        logger.info(f"API地址: {self.api_url}")
        logger.info(f"桥接目录: {self.bridge_dir}")
        logger.info(f"请求文件: {self.request_file}")
        logger.info(f"响应文件: {self.response_file}")

        # 测试API连接
        self._test_connection()

        # 创建事件处理器
        handler = RequestHandler(
            api_url=self.api_url,
            request_file=self.request_file,
            response_file=self.response_file,
            timeout=self.timeout
        )

        # 启动文件监控
        self.observer = Observer()
        self.observer.schedule(handler, str(self.bridge_dir), recursive=False)
        self.observer.start()

        self.running = True
        logger.info("桥接服务已启动，等待请求...")

        # 主循环
        try:
            while self.running:
                time.sleep(1)
        except KeyboardInterrupt:
            pass

        self.stop()

    def stop(self):
        """停止桥接服务"""
        self.running = False

        if self.observer:
            self.observer.stop()
            self.observer.join(timeout=5)

        logger.info("桥接服务已停止")

    def _test_connection(self):
        """测试API连接"""
        try:
            response = requests.get(
                f"{self.api_url}/health",
                timeout=5
            )
            if response.status_code == 200:
                logger.info("API连接成功")
                return True
            else:
                logger.warning(f"API返回非200状态: {response.status_code}")
                return False
        except requests.ConnectionError:
            logger.warning("无法连接到API服务器，请确保后端服务已启动")
            return False
        except Exception as e:
            logger.warning(f"测试连接失败: {e}")
            return False


def get_default_bridge_dir() -> Path:
    """获取默认桥接目录"""
    # 尝试DST常见的持久化目录
    possible_dirs = [
        # Linux
        Path.home() / ".klei" / "DoNotStarveTogether" / "client_save" / "rag_bridge",
        # Windows
        Path.home() / "Documents" / "Klei" / "DoNotStarveTogether" / "client_save" / "rag_bridge",
        # macOS
        Path.home() / "Documents" / "Klei" / "DoNotStarveTogether" / "client_save" / "rag_bridge",
        # 备用：当前目录
        Path.cwd() / "bridge_data",
    ]

    for dir_path in possible_dirs:
        try:
            dir_path.mkdir(parents=True, exist_ok=True)
            return dir_path
        except Exception:
            continue

    # 最后的备用
    fallback = Path("/tmp/rag_bridge")
    fallback.mkdir(parents=True, exist_ok=True)
    return fallback


def main():
    parser = argparse.ArgumentParser(
        description='饥荒RAG助手 HTTP桥接脚本'
    )
    parser.add_argument(
        '--api-url',
        default='http://localhost:8000',
        help='FastAPI后端地址 (默认: http://localhost:8000)'
    )
    parser.add_argument(
        '--bridge-dir',
        type=Path,
        default=None,
        help='桥接文件目录 (默认: 自动检测DST存档目录)'
    )
    parser.add_argument(
        '--timeout',
        type=int,
        default=30,
        help='请求超时时间（秒）(默认: 30)'
    )

    args = parser.parse_args()

    # 确定桥接目录
    bridge_dir = args.bridge_dir or get_default_bridge_dir()

    # 创建并启动桥接服务
    bridge = HTTPBridge(
        api_url=args.api_url,
        bridge_dir=bridge_dir,
        timeout=args.timeout
    )

    bridge.start()


if __name__ == '__main__':
    main()
