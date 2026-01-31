"""应用启动入口"""

import argparse
import uvicorn


def main():
    """应用主程序入口"""
    parser = argparse.ArgumentParser(description="饥荒RAG问答助手服务")
    parser.add_argument(
        "--mode",
        choices=["api", "streamlit"],
        default="api",
        help="运行模式: api(FastAPI) 或 streamlit"
    )
    parser.add_argument(
        "--host",
        type=str,
        default="0.0.0.0",
        help="服务主机 (默认: 0.0.0.0)"
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="服务端口 (默认: 8000)"
    )
    parser.add_argument(
        "--reload",
        action="store_true",
        help="开发模式（热重载）"
    )
    args = parser.parse_args()

    if args.mode == "api":
        # 启动FastAPI服务
        uvicorn.run(
            "src.app.api:app",
            host=args.host,
            port=args.port,
            reload=args.reload,
        )
    else:
        # 启动Streamlit
        import subprocess
        import sys

        cmd = [
            sys.executable, "-m", "streamlit", "run",
            "src/app/streamlit_app.py",
            "--server.address", args.host,
            "--server.port", str(args.port),
        ]
        subprocess.run(cmd)


if __name__ == "__main__":
    main()
