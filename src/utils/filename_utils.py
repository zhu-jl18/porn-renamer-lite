"""
文件名工具函数模块
提供文件名清理、验证和冲突解决功能
"""
import os
import re
from pathlib import Path
from typing import Optional
from ..config.settings import settings

class FilenameUtils:
    """文件名工具类"""

    @staticmethod
    def is_garbled_filename(filename: str) -> bool:
        """
        判断是否为乱码文件名
        识别标准：长串十六进制字符组成
        """
        # 移除扩展名
        name_part = os.path.splitext(filename)[0]

        # 检查长度
        if len(name_part) < 8:
            return False

        # 检查是否为纯十六进制字符
        hex_pattern = r'^[a-f0-9]+$'
        return bool(re.match(hex_pattern, name_part.lower()))

    @staticmethod
    def is_video_file(filepath: Path) -> bool:
        """检查是否为视频文件"""
        return filepath.suffix.lower() in settings.video_extensions

    @staticmethod
    def clean_filename(filename: str) -> str:
        """
        清理文件名，移除不允许的字符
        """
        # 移除不允许的字符，保留中文、字母、数字、下划线、横线、空格
        safe_chars = []
        for char in filename:
            if char.isalnum() or char in ['-', '_', ' ', '（）', '【】']:
                safe_chars.append(char)

        safe_name = ''.join(safe_chars).strip()

        # 移除连续的空格
        safe_name = re.sub(r'\s+', ' ', safe_name)

        # 控制长度
        if len(safe_name) > settings.max_filename_length:
            safe_name = safe_name[:settings.max_filename_length]

        return safe_name

    @staticmethod
    def resolve_filename_conflict(filepath: Path) -> Path:
        """
        解决文件名冲突
        如果文件已存在，添加数字后缀
        """
        if not filepath.exists():
            return filepath

        base, ext = filepath.stem, filepath.suffix
        counter = 1

        while filepath.exists():
            new_name = f"{base}_{counter}{ext}"
            filepath = filepath.parent / new_name
            counter += 1

        return filepath

    @staticmethod
    def generate_safe_name(ai_suggestion: str, original_ext: str) -> str:
        """
        生成安全的文件名
        """
        # 移除可能的扩展名（AI可能返回完整文件名）
        suggestion_without_ext = os.path.splitext(ai_suggestion)[0]

        # 清理文件名
        safe_name = FilenameUtils.clean_filename(suggestion_without_ext)

        # 确保不为空
        if not safe_name:
            safe_name = "未命名视频"

        # 添加扩展名
        return f"{safe_name}{original_ext}"

    @staticmethod
    def extract_filename_suggestions(ai_response: str) -> Optional[str]:
        """
        从AI响应中提取文件名建议
        """
        if not ai_response:
            return None

        # 移除可能的引号
        cleaned = ai_response.strip().strip('"\'').strip()

        # 检查是否包含文件扩展名
        if not any(cleaned.lower().endswith(ext) for ext in settings.video_extensions):
            # 如果没有扩展名，添加默认的.mp4
            cleaned += ".mp4"

        return cleaned if cleaned else None