"""
AI分析模块
负责调用API分析图片内容并生成文件名建议
"""
import asyncio
import logging
from pathlib import Path
from typing import List, Optional, Dict, Any
import httpx
from ..utils.image_utils import ImageUtils
from ..utils.api_utils import APIUtils
from ..utils.filename_utils import FilenameUtils
from ..config.settings import settings

logger = logging.getLogger(__name__)

class AIAnalyzer:
    """AI分析器"""

    def __init__(self, api_url: str = None):
        self.api_url = api_url or settings.api_url
        self.timeout = 30

    async def analyze_single_image(self, image_path: str) -> Optional[str]:
        """
        分析单个图片，返回文件名建议
        """
        try:
            # 编码图片为base64
            image_base64 = ImageUtils.encode_image_to_base64(image_path)

            # 创建API负载
            payload = APIUtils.create_image_analysis_payload(image_base64)

            # 调用API
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await APIUtils.call_api_with_retry(
                    client, self.api_url, payload
                )

            if response:
                # 解析响应
                filename = APIUtils.parse_api_response(response)
                if filename:
                    # 生成完整的文件名（包含扩展名）
                    return FilenameUtils.generate_safe_name(filename, ".mp4")

            return None

        except Exception as e:
            logger.error(f"分析图片失败 {image_path}: {e}")
            return None

    async def analyze_multiple_images(self, image_paths: List[str]) -> List[Optional[str]]:
        """
        并发分析多个图片，返回文件名建议列表
        """
        if not image_paths:
            return []

        tasks = [self.analyze_single_image(path) for path in image_paths]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # 处理异常结果
        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"分析第{i+1}张图片时发生异常: {result}")
                processed_results.append(None)
            else:
                processed_results.append(result)

        logger.info(f"分析完成 {len(processed_results)} 张图片，成功 {sum(1 for r in processed_results if r)} 个")
        return processed_results

    async def select_best_filename(self, image_paths: List[str]) -> Optional[str]:
        """
        分析多张图片，选择最佳的文件名建议
        """
        if not image_paths:
            return None

        # 分析所有图片
        filename_suggestions = await self.analyze_multiple_images(image_paths)

        # 过滤掉None结果
        valid_suggestions = [name for name in filename_suggestions if name]

        if not valid_suggestions:
            logger.warning("所有图片分析都失败了")
            return None

        # 如果只有一个有效结果，直接返回
        if len(valid_suggestions) == 1:
            return valid_suggestions[0]

        # 多个结果时，选择最合适的
        best_filename = self._select_best_suggestion(valid_suggestions, image_paths)

        logger.info(f"选择最佳文件名: {best_filename}")
        return best_filename

    def _select_best_suggestion(self, suggestions: List[str], image_paths: List[str]) -> str:
        """
        从多个文件名建议中选择最佳的
        """
        if not suggestions:
            return "未命名视频.mp4"

        # 简单策略：选择第一个非空的建议
        # 可以根据需要实现更复杂的策略，比如：
        # - 基于图片质量评分
        # - 基于文件名的描述性
        # - 基于重复性检测

        return suggestions[0]

    async def test_api_connection(self) -> bool:
        """
        测试API连接
        """
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                return await APIUtils.test_api_connection(client, self.api_url)
        except Exception as e:
            logger.error(f"API连接测试失败: {e}")
            return False

    async def analyze_video_screenshots(self, video_path: Path, screenshot_paths: List[str]) -> Optional[str]:
        """
        分析视频截图，返回文件名建议
        """
        try:
            # 检查截图数量
            if not screenshot_paths:
                logger.warning(f"没有截图可供分析: {video_path.name}")
                return None

            # 如果只有一张截图，直接分析
            if len(screenshot_paths) == 1:
                filename = await self.analyze_single_image(screenshot_paths[0])
                if filename:
                    logger.info(f"单截图分析成功: {video_path.name} -> {filename}")
                return filename

            # 多张截图，选择最佳结果
            filename = await self.select_best_filename(screenshot_paths)
            if filename:
                logger.info(f"多截图分析成功: {video_path.name} -> {filename}")
            else:
                logger.warning(f"多截图分析失败: {video_path.name}")

            return filename

        except Exception as e:
            logger.error(f"分析视频截图失败 {video_path}: {e}")
            return None

    async def batch_analyze_videos(self, video_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        批量分析多个视频
        video_data格式: [{"video_path": Path, "screenshot_paths": List[str]}, ...]
        """
        if not video_data:
            return {"total": 0, "success": 0, "failed": 0, "results": {}}

        # 创建分析任务
        tasks = []
        for item in video_data:
            task = self.analyze_video_screenshots(
                item["video_path"],
                item["screenshot_paths"]
            )
            tasks.append(task)

        # 并发执行分析
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # 处理结果
        analysis_results = {
            "total": len(video_data),
            "success": 0,
            "failed": 0,
            "results": {},
            "errors": []
        }

        for i, (item, result) in enumerate(zip(video_data, results)):
            video_name = item["video_path"].name

            if isinstance(result, Exception):
                analysis_results["failed"] += 1
                analysis_results["errors"].append(f"{video_name}: {result}")
            elif result:
                analysis_results["success"] += 1
                analysis_results["results"][video_name] = result
            else:
                analysis_results["failed"] += 1
                analysis_results["errors"].append(f"{video_name}: 分析失败")

        logger.info(f"批量分析完成: {analysis_results}")
        return analysis_results

    def generate_fallback_filename(self, video_path: Path) -> str:
        """
        生成备用文件名（当AI分析失败时使用）
        """
        # 基于文件大小或时间戳生成简单的文件名
        import time

        try:
            file_size_mb = video_path.stat().st_size / (1024 * 1024)
            timestamp = int(time.time())

            if file_size_mb < 10:
                return f"小视频_{timestamp}.mp4"
            elif file_size_mb < 100:
                return f"中视频_{timestamp}.mp4"
            elif file_size_mb < 1000:
                return f"大视频_{timestamp}.mp4"
            else:
                return f"超大视频_{timestamp}.mp4"

        except Exception:
            return f"未命名视频_{int(time.time())}.mp4"