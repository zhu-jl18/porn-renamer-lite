#!/usr/bin/env python3
"""
视频文件重命名工具主程序
使用方法：
python scripts/run_renamer.py /path/to/video/files [options]
"""
import asyncio
import logging
import sys
from pathlib import Path
from typing import List, Dict, Any
import click
from tqdm import tqdm

# 添加项目根目录到Python路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.core.file_scanner import FileScanner
from src.core.video_processor import VideoProcessor
from src.core.ai_analyzer import AIAnalyzer
from src.core.file_renamer import FileRenamer
from src.config.settings import settings

# 配置日志
logging.basicConfig(
    level=getattr(logging, settings.log_level),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('video_renamer.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

class VideoRenamerApp:
    """视频重命名应用主类"""

    def __init__(self, target_directory: str, dry_run: bool = False, interactive: bool = False):
        self.target_directory = Path(target_directory)
        self.dry_run = dry_run
        self.interactive = interactive

        # 初始化各个组件
        self.scanner = FileScanner(target_directory)
        self.video_processor = VideoProcessor()
        self.ai_analyzer = AIAnalyzer()
        self.file_renamer = FileRenamer(dry_run=dry_run)

        # 处理统计
        self.stats = {
            "total_files": 0,
            "processed_files": 0,
            "renamed_files": 0,
            "failed_files": 0,
            "errors": []
        }

    async def run(self) -> Dict[str, Any]:
        """运行重命名流程"""
        try:
            # 1. 扫描乱码文件
            logger.info(f"开始扫描目录: {self.target_directory}")
            garbled_files = self.scanner.find_garbled_files(recursive=True)

            if not garbled_files:
                logger.info("没有找到乱码文件名的视频文件")
                return {"status": "success", "message": "没有需要处理的文件"}

            self.stats["total_files"] = len(garbled_files)
            logger.info(f"找到 {len(garbled_files)} 个乱码文件")

            # 2. 测试API连接
            logger.info("测试API连接...")
            if not await self.ai_analyzer.test_api_connection():
                logger.error("API连接测试失败，请检查API服务")
                return {"status": "error", "message": "API连接失败"}

            logger.info("API连接测试成功")

            # 3. 处理每个文件
            rename_map = {}

            for video_path in tqdm(garbled_files, desc="处理视频文件"):
                try:
                    result = await self.process_single_video(video_path)
                    if result:
                        rename_map[video_path] = result

                except Exception as e:
                    error_msg = f"处理文件失败 {video_path.name}: {e}"
                    logger.error(error_msg)
                    self.stats["errors"].append(error_msg)
                    self.stats["failed_files"] += 1

            # 4. 执行重命名
            if rename_map:
                logger.info(f"准备重命名 {len(rename_map)} 个文件")
                rename_results = self.file_renamer.batch_rename_files(rename_map)

                self.stats["processed_files"] = len(rename_map)
                self.stats["renamed_files"] = rename_results["success"]
                self.stats["failed_files"] += rename_results["failed"]

                # 保存重命名日志
                self.file_renamer.save_rename_log()
            else:
                logger.info("没有生成重命名映射")

            # 5. 清理临时文件
            self.video_processor.cleanup_temp_files()

            # 6. 输出结果统计
            self.print_statistics()

            return {
                "status": "success",
                "message": "处理完成",
                "statistics": self.stats
            }

        except Exception as e:
            logger.error(f"运行异常: {e}")
            return {
                "status": "error",
                "message": str(e),
                "statistics": self.stats
            }

    async def process_single_video(self, video_path: Path) -> str:
        """处理单个视频文件"""
        logger.debug(f"开始处理: {video_path.name}")

        # 交互模式确认
        if self.interactive:
            click.echo(f"\n[VIDEO] 处理文件: {video_path.name}")
            file_size_mb = video_path.stat().st_size / (1024 * 1024)
            click.echo(f"[SIZE] 文件大小: {file_size_mb:.1f} MB")

            if not click.confirm("继续处理这个文件吗？"):
                click.echo("[SKIP] 跳过此文件")
                return None

        # 1. 提取视频截图
        click.echo("[SCREENSHOT] 正在提取视频截图...")
        screenshot_paths = self.video_processor.extract_key_frames(video_path)
        if not screenshot_paths:
            logger.warning(f"无法提取截图: {video_path.name}")
            return None

        click.echo(f"[INFO] 成功提取 {len(screenshot_paths)} 张截图")

        # 2. AI分析截图
        click.echo("[AI] 正在AI分析截图内容...")
        filename = await self.ai_analyzer.analyze_video_screenshots(
            video_path, screenshot_paths
        )

        # 3. 如果AI分析失败，使用备用文件名
        if not filename:
            filename = self.ai_analyzer.generate_fallback_filename(video_path)
            logger.warning(f"使用备用文件名: {video_path.name} -> {filename}")

        # 4. 交互模式确认重命名
        if self.interactive:
            click.echo(f"\n[SUGGEST] AI建议重命名为: {filename}")

            if self.dry_run:
                click.echo("[DRY-RUN] [试运行] 将执行重命名")
            else:
                if not click.confirm("确认使用这个文件名吗？"):
                    # 允许用户输入自定义文件名
                    custom_name = click.prompt("请输入自定义文件名（留空使用AI建议）", default="", show_default=False)
                    if custom_name.strip():
                        filename = custom_name.strip()
                        if not filename.endswith('.mp4'):
                            filename += '.mp4'

        # 5. 清理截图
        self.video_processor.cleanup_temp_files(video_path)

        logger.debug(f"处理完成: {video_path.name} -> {filename}")
        return filename

    def print_statistics(self):
        """打印处理统计信息"""
        print("\n" + "="*50)
        print("处理统计信息")
        print("="*50)
        print(f"总文件数: {self.stats['total_files']}")
        print(f"已处理文件: {self.stats['processed_files']}")
        print(f"成功重命名: {self.stats['renamed_files']}")
        print(f"失败文件: {self.stats['failed_files']}")
        print(f"成功率: {self.stats['renamed_files']/max(self.stats['processed_files'],1)*100:.1f}%")

        if self.stats['errors']:
            print(f"\n错误信息:")
            for error in self.stats['errors'][:5]:  # 只显示前5个错误
                print(f"  - {error}")

        print("="*50)

# CLI命令行接口
@click.command()
@click.argument('target_directory', type=click.Path(exists=True, path_type=Path))
@click.option('--dry-run', is_flag=True, help='试运行模式，不实际重命名文件')
@click.option('--recursive', is_flag=True, default=True, help='递归搜索子目录')
@click.option('--workers', default=2, help='并发工作线程数')
@click.option('--verbose', '-v', is_flag=True, help='详细输出')
@click.option('--interactive', '-i', is_flag=True, help='交互模式，逐步确认每个文件')
def main(target_directory: Path, dry_run: bool, recursive: bool, workers: int, verbose: bool, interactive: bool):
    """
    视频文件智能重命名工具

    TARGET_DIRECTORY: 要处理的视频文件目录
    """
    if verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # 确认处理
    if dry_run:
        click.echo("试运行模式 - 不会实际重命名文件")
    else:
        if not click.confirm(f"确定要处理目录 {target_directory} 中的乱码文件吗？"):
            click.echo("操作已取消")
            return

    # 运行应用
    app = VideoRenamerApp(str(target_directory), dry_run=dry_run, interactive=interactive)

    # 运行异步主函数
    result = asyncio.run(app.run())

    # 输出结果
    if result["status"] == "success":
        click.echo(f"\n[SUCCESS] 处理完成！")
    else:
        click.echo(f"\n[FAILED] 处理失败: {result['message']}")
        sys.exit(1)

if __name__ == "__main__":
    main()