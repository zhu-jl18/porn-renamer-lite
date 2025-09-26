"""
视频处理模块
负责视频截图、关键帧提取和预处理
"""
import os
import cv2
import logging
from pathlib import Path
from typing import List, Optional, Tuple
import numpy as np
from ..utils.image_utils import ImageUtils
from ..config.settings import settings

logger = logging.getLogger(__name__)

class VideoProcessor:
    """视频处理器"""

    def __init__(self, temp_dir: str = None):
        self.temp_dir = Path(temp_dir) if temp_dir else Path(settings.temp_dir)
        self.temp_dir.mkdir(exist_ok=True)

    def can_process_video(self, video_path: Path) -> bool:
        """
        检查是否可以处理该视频文件
        """
        try:
            cap = cv2.VideoCapture(str(video_path))
            if not cap.isOpened():
                return False

            # 检查是否可以读取帧
            ret, frame = cap.read()
            cap.release()

            return ret
        except Exception as e:
            logger.error(f"视频文件检查失败 {video_path}: {e}")
            return False

    def get_video_info(self, video_path: Path) -> Optional[dict]:
        """
        获取视频信息
        """
        try:
            cap = cv2.VideoCapture(str(video_path))
            if not cap.isOpened():
                return None

            # 获取视频基本信息
            fps = cap.get(cv2.CAP_PROP_FPS)
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

            # 计算时长
            duration = total_frames / fps if fps > 0 else 0

            cap.release()

            return {
                "fps": fps,
                "total_frames": total_frames,
                "width": width,
                "height": height,
                "duration": duration,
                "file_size_mb": round(video_path.stat().st_size / (1024 * 1024), 2)
            }
        except Exception as e:
            logger.error(f"获取视频信息失败 {video_path}: {e}")
            return None

    def calculate_screenshot_positions(self, duration: float, count: int = None) -> List[float]:
        """
        计算截图时间点（秒）
        """
        if count is None:
            count = settings.screenshot_count

        if duration <= 0:
            return []

        positions = []

        if duration <= 10:
            # 短视频：均匀分布
            for i in range(count):
                positions.append(duration * (i + 1) / (count + 1))
        else:
            # 长视频：策略性选择
            positions = [
                max(1.0, duration * 0.1),   # 10%位置，最少1秒
                duration * 0.5,            # 中间位置
                min(duration - 1.0, duration * 0.9)  # 90%位置，最多结束前1秒
            ]

            # 如果需要更多截图，在中间位置添加
            while len(positions) < count:
                mid_pos = duration * (len(positions) + 1) / (count + 1)
                positions.insert(-1, mid_pos)  # 插入到倒数第二个位置

        # 确保不超过视频时长
        positions = [min(pos, duration - 0.1) for pos in positions]

        return positions[:count]

    def extract_frames_at_time(self, video_path: Path, time_seconds: float) -> Optional[np.ndarray]:
        """
        在指定时间点提取视频帧
        """
        try:
            cap = cv2.VideoCapture(str(video_path))
            if not cap.isOpened():
                return None

            # 设置时间位置
            fps = cap.get(cv2.CAP_PROP_FPS)
            if fps <= 0:
                cap.release()
                return None

            frame_position = int(time_seconds * fps)
            cap.set(cv2.CAP_PROP_POS_FRAMES, frame_position)

            # 读取帧
            ret, frame = cap.read()
            cap.release()

            if ret:
                # 预处理帧
                return ImageUtils.preprocess_frame(frame)
            else:
                return None

        except Exception as e:
            logger.error(f"提取视频帧失败 {video_path} @ {time_seconds}s: {e}")
            return None

    def extract_key_frames(self, video_path: Path) -> List[str]:
        """
        提取视频关键帧并保存为图片
        返回截图文件路径列表
        """
        # 获取视频信息
        video_info = self.get_video_info(video_path)
        if not video_info:
            logger.error(f"无法获取视频信息: {video_path}")
            return []

        # 计算截图时间点
        positions = self.calculate_screenshot_positions(video_info["duration"])
        if not positions:
            logger.error(f"无法计算截图时间点: {video_path}")
            return []

        screenshot_paths = []
        video_name = video_path.stem

        for i, time_pos in enumerate(positions):
            try:
                # 提取帧
                frame = self.extract_frames_at_time(video_path, time_pos)
                if frame is None:
                    logger.warning(f"无法提取帧 {video_path} @ {time_pos}s")
                    continue

                # 生成截图路径
                screenshot_path = self.temp_dir / f"{video_name}_frame_{i+1}.jpg"

                # 保存截图
                if ImageUtils.save_screenshot(frame, screenshot_path):
                    screenshot_paths.append(str(screenshot_path))
                    logger.debug(f"保存截图: {screenshot_path}")
                else:
                    logger.warning(f"保存截图失败: {screenshot_path}")

            except Exception as e:
                logger.error(f"处理截图失败 {video_path} @ {time_pos}s: {e}")

        logger.info(f"从 {video_path.name} 提取了 {len(screenshot_paths)} 张截图")
        return screenshot_paths

    def extract_best_frame(self, video_path: Path) -> Optional[str]:
        """
        提取最佳质量的单个帧
        """
        # 提取多个帧
        frame_paths = self.extract_key_frames(video_path)
        if not frame_paths:
            return None

        # 计算每个帧的质量评分
        best_frame = None
        best_score = 0

        for frame_path in frame_paths:
            try:
                quality_score = ImageUtils.calculate_image_quality(frame_path)
                if quality_score > best_score:
                    best_score = quality_score
                    best_frame = frame_path
            except Exception as e:
                logger.warning(f"计算图片质量失败 {frame_path}: {e}")

        # 清理其他帧
        for frame_path in frame_paths:
            if frame_path != best_frame:
                try:
                    os.remove(frame_path)
                except Exception as e:
                    logger.warning(f"清理临时文件失败 {frame_path}: {e}")

        logger.info(f"选择最佳帧: {best_frame} (评分: {best_score:.1f})")
        return best_frame

    def cleanup_temp_files(self, video_path: Path = None):
        """
        清理临时文件
        如果指定video_path，只清理该视频相关的临时文件
        否则清理所有临时文件
        """
        try:
            if video_path:
                # 清理特定视频的临时文件
                pattern = f"{video_path.stem}_frame_*.jpg"
                for temp_file in self.temp_dir.glob(pattern):
                    try:
                        temp_file.unlink()
                        logger.debug(f"清理临时文件: {temp_file}")
                    except Exception as e:
                        logger.warning(f"清理临时文件失败 {temp_file}: {e}")
            else:
                # 清理所有临时文件
                for temp_file in self.temp_dir.glob("*.jpg"):
                    try:
                        # 检查文件是否超过1小时
                        import time
                        file_age = time.time() - temp_file.stat().st_mtime
                        if file_age > 3600:  # 1小时
                            temp_file.unlink()
                            logger.debug(f"清理过期临时文件: {temp_file}")
                    except Exception as e:
                        logger.warning(f"清理临时文件失败 {temp_file}: {e}")

        except Exception as e:
            logger.error(f"清理临时文件失败: {e}")

    def batch_process_videos(self, video_paths: List[Path]) -> dict:
        """
        批量处理视频，提取截图
        返回处理结果统计
        """
        results = {
            "total": len(video_paths),
            "success": 0,
            "failed": 0,
            "screenshots_extracted": 0,
            "errors": []
        }

        for video_path in video_paths:
            try:
                screenshots = self.extract_key_frames(video_path)
                if screenshots:
                    results["success"] += 1
                    results["screenshots_extracted"] += len(screenshots)
                else:
                    results["failed"] += 1
                    results["errors"].append(f"无法提取截图: {video_path.name}")

            except Exception as e:
                results["failed"] += 1
                results["errors"].append(f"处理失败 {video_path.name}: {e}")

        logger.info(f"批量处理完成: {results}")
        return results