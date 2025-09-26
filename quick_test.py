#!/usr/bin/env python3
"""
快速测试脚本 - 用于快速测试视频重命名工具功能
"""
import subprocess
import sys
from pathlib import Path

def run_test():
    """运行快速测试"""
    print("[TEST] 启动视频重命名工具快速测试...")
    print("=" * 50)

    # 目标目录设置为Gallery的未分类文件夹
    target_dir = "X:\\Gallery\\.未分类"

    # 检查目录是否存在
    if not Path(target_dir).exists():
        print(f"[ERROR] 目标目录不存在: {target_dir}")
        return

    print(f"[INFO] 目标目录: {target_dir}")
    print("[INFO] API地址: http://localhost:3001/proxy/free (已硬编码)")
    print("[INFO] 模式: 试运行 + 交互模式")
    print("=" * 50)

    # 构建命令
    cmd = [
        sys.executable, "scripts/run_renamer.py",
        target_dir,
        "--dry-run",      # 试运行模式
        "--interactive",  # 交互模式
        "--verbose",      # 详细输出
        "--workers", "1"  # 单线程处理，便于观察
    ]

    try:
        # 运行命令
        print("[START] 开始执行...")
        result = subprocess.run(cmd, cwd=Path(__file__).parent)

        if result.returncode == 0:
            print("\n[SUCCESS] 测试运行完成！")
        else:
            print(f"\n[FAILED] 运行失败，退出码: {result.returncode}")

    except KeyboardInterrupt:
        print("\n[STOP] 用户中断")
    except Exception as e:
        print(f"\n[ERROR] 运行异常: {e}")

if __name__ == "__main__":
    run_test()