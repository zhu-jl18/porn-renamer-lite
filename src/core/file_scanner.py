"""
文件扫描模块
负责扫描目录、识别乱码文件名和过滤视频文件
"""
import os
import logging
from pathlib import Path
from typing import List, Optional
from ..utils.filename_utils import FilenameUtils
from ..config.settings import settings

logger = logging.getLogger(__name__)

class FileScanner:
    """文件扫描器"""

    def __init__(self, target_directory: str):
        self.target_directory = Path(target_directory)
        self.video_extensions = [ext.lower() for ext in settings.video_extensions]

    def scan_directory(self, recursive: bool = True) -> List[Path]:
        """
        扫描目标目录，返回所有视频文件
        """
        if not self.target_directory.exists():
            logger.error(f"目标目录不存在: {self.target_directory}")
            return []

        video_files = []
        pattern = "**/*" if recursive else "*"

        for file_path in self.target_directory.glob(pattern):
            if file_path.is_file() and FilenameUtils.is_video_file(file_path):
                video_files.append(file_path)

        logger.info(f"扫描完成，找到 {len(video_files)} 个视频文件")
        return video_files

    def find_garbled_files(self, recursive: bool = True) -> List[Path]:
        """
        查找乱码文件名的视频文件
        """
        all_video_files = self.scan_directory(recursive)
        garbled_files = []

        for file_path in all_video_files:
            if FilenameUtils.is_garbled_filename(file_path.name):
                garbled_files.append(file_path)

        logger.info(f"找到 {len(garbled_files)} 个乱码文件名的视频文件")
        return garbled_files

    def filter_by_size(self, files: List[Path], min_size_mb: int = 1, max_size_mb: Optional[int] = None) -> List[Path]:
        """
        按文件大小过滤
        """
        filtered_files = []
        min_size_bytes = min_size_mb * 1024 * 1024
        max_size_bytes = max_size_mb * 1024 * 1024 if max_size_mb else None

        for file_path in files:
            try:
                file_size = file_path.stat().st_size

                # 检查最小大小
                if file_size < min_size_bytes:
                    logger.debug(f"文件过小，跳过: {file_path.name} ({file_size} bytes)")
                    continue

                # 检查最大大小
                if max_size_bytes and file_size > max_size_bytes:
                    logger.debug(f"文件过大，跳过: {file_path.name} ({file_size} bytes)")
                    continue

                filtered_files.append(file_path)

            except OSError as e:
                logger.warning(f"无法获取文件大小 {file_path}: {e}")

        logger.info(f"按大小过滤后剩余 {len(filtered_files)} 个文件")
        return filtered_files

    def filter_by_extension(self, files: List[Path], extensions: List[str]) -> List[Path]:
        """
        按文件扩展名过滤
        """
        target_extensions = [ext.lower() for ext in extensions]
        filtered_files = []

        for file_path in files:
            if file_path.suffix.lower() in target_extensions:
                filtered_files.append(file_path)

        logger.info(f"按扩展名过滤后剩余 {len(filtered_files)} 个文件")
        return filtered_files

    def get_duplicate_candidates(self, files: List[Path]) -> dict:
        """
        查找可能的重复文件（基于文件名模式）
        返回按基础文件名分组的字典
        """
        duplicates = {}

        for file_path in files:
            # 提取基础文件名（移除可能的数字后缀）
            base_name = self._extract_base_name(file_path.name)
            if base_name not in duplicates:
                duplicates[base_name] = []
            duplicates[base_name].append(file_path)

        # 只保留有多个文件的组
        duplicates = {k: v for k, v in duplicates.items() if len(v) > 1}

        logger.info(f"发现 {len(duplicates)} 组可能的重复文件")
        return duplicates

    def _extract_base_name(self, filename: str) -> str:
        """
        提取基础文件名（移除数字后缀）
        例如：file1.mp4 -> file, file(1).mp4 -> file
        """
        name_part = os.path.splitext(filename)[0]

        # 移除末尾的数字
        import re
        # 匹配模式：_数字, (数字), -数字 等
        patterns = [
            r'_\d+$',  # file_1
            r'\(\d+\)$',  # file(1)
            r'-\d+$',  # file-1
            r'\s\d+$',  # file 1
        ]

        for pattern in patterns:
            name_part = re.sub(pattern, '', name_part)

        return name_part

    def validate_files(self, files: List[Path]) -> List[Path]:
        """
        验证文件列表，移除无效或不可访问的文件
        """
        valid_files = []

        for file_path in files:
            try:
                # 检查文件是否存在
                if not file_path.exists():
                    logger.warning(f"文件不存在: {file_path}")
                    continue

                # 检查文件是否可读
                if not os.access(file_path, os.R_OK):
                    logger.warning(f"文件不可读: {file_path}")
                    continue

                # 检查文件大小（避免空文件）
                if file_path.stat().st_size == 0:
                    logger.warning(f"文件为空: {file_path}")
                    continue

                valid_files.append(file_path)

            except Exception as e:
                logger.warning(f"验证文件失败 {file_path}: {e}")

        logger.info(f"验证后剩余 {len(valid_files)} 个有效文件")
        return valid_files

    def get_scan_summary(self, files: List[Path]) -> dict:
        """
        获取扫描摘要信息
        """
        if not files:
            return {
                "total_files": 0,
                "total_size_mb": 0,
                "extensions": {},
                "size_distribution": {}
            }

        total_size = sum(f.stat().st_size for f in files if f.exists())
        extensions = {}
        size_distribution = {
            "small": 0,    # < 10MB
            "medium": 0,   # 10-100MB
            "large": 0,    # 100MB-1GB
            "huge": 0      # > 1GB
        }

        for file_path in files:
            try:
                if file_path.exists():
                    ext = file_path.suffix.lower()
                    extensions[ext] = extensions.get(ext, 0) + 1

                    size_mb = file_path.stat().st_size / (1024 * 1024)
                    if size_mb < 10:
                        size_distribution["small"] += 1
                    elif size_mb < 100:
                        size_distribution["medium"] += 1
                    elif size_mb < 1000:
                        size_distribution["large"] += 1
                    else:
                        size_distribution["huge"] += 1
            except OSError:
                pass

        return {
            "total_files": len(files),
            "total_size_mb": round(total_size / (1024 * 1024), 2),
            "extensions": extensions,
            "size_distribution": size_distribution
        }