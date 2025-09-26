"""
图片处理工具函数模块
提供图片编码、预处理和保存功能
"""
import base64
import io
from pathlib import Path
from typing import Union
import numpy as np
from PIL import Image
import cv2

class ImageUtils:
    """图片工具类"""

    @staticmethod
    def resize_image(image: np.ndarray, max_size: tuple = (640, 480)) -> np.ndarray:
        """
        调整图片大小，保持宽高比
        """
        height, width = image.shape[:2]
        max_width, max_height = max_size

        # 计算缩放比例
        scale = min(max_width / width, max_height / height)
        if scale >= 1:
            return image  # 不需要放大

        # 调整大小
        new_width = int(width * scale)
        new_height = int(height * scale)
        resized = cv2.resize(image, (new_width, new_height), interpolation=cv2.INTER_AREA)

        return resized

    @staticmethod
    def encode_image_to_base64(image_path: Union[str, Path]) -> str:
        """
        将图片文件编码为base64字符串
        """
        try:
            with open(image_path, 'rb') as image_file:
                image_data = image_file.read()
                return base64.b64encode(image_data).decode('utf-8')
        except Exception as e:
            raise Exception(f"图片编码失败: {e}")

    @staticmethod
    def encode_array_to_base64(image_array: np.ndarray, format: str = 'JPEG') -> str:
        """
        将numpy数组编码为base64字符串
        """
        try:
            # 转换为PIL Image
            if len(image_array.shape) == 3:
                # OpenCV使用BGR，需要转换为RGB
                image_rgb = cv2.cvtColor(image_array, cv2.COLOR_BGR2RGB)
                pil_image = Image.fromarray(image_rgb)
            else:
                pil_image = Image.fromarray(image_array)

            # 保存到字节流
            buffer = io.BytesIO()
            pil_image.save(buffer, format=format, quality=85)
            image_bytes = buffer.getvalue()

            # 编码为base64
            return base64.b64encode(image_bytes).decode('utf-8')
        except Exception as e:
            raise Exception(f"图片数组编码失败: {e}")

    @staticmethod
    def save_screenshot(frame: np.ndarray, output_path: Union[str, Path]) -> bool:
        """
        保存视频帧截图
        """
        try:
            # 调整大小
            resized_frame = ImageUtils.resize_image(frame)

            # 保存图片
            success = cv2.imwrite(str(output_path), resized_frame)
            return success
        except Exception as e:
            print(f"保存截图失败 {output_path}: {e}")
            return False

    @staticmethod
    def preprocess_frame(frame: np.ndarray) -> np.ndarray:
        """
        预处理视频帧
        包括亮度调整、对比度增强等
        """
        try:
            # 转换为YUV颜色空间
            yuv = cv2.cvtColor(frame, cv2.COLOR_BGR2YUV)

            # 增强亮度和对比度
            yuv[:,:,0] = cv2.equalizeHist(yuv[:,:,0])

            # 转换回BGR
            enhanced = cv2.cvtColor(yuv, cv2.COLOR_YUV2BGR)

            # 轻微锐化
            kernel = np.array([[-1,-1,-1],
                             [-1, 9,-1],
                             [-1,-1,-1]])
            sharpened = cv2.filter2D(enhanced, -1, kernel)

            return sharpened
        except Exception:
            # 预处理失败，返回原图
            return frame

    @staticmethod
    def calculate_image_quality(image_path: Union[str, Path]) -> float:
        """
        计算图片质量评分 (0-100)
        基于清晰度、亮度、对比度等因素
        """
        try:
            image = cv2.imread(str(image_path))
            if image is None:
                return 0.0

            # 计算清晰度（使用拉普拉斯算子）
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            sharpness = cv2.Laplacian(gray, cv2.CV_64F).var()

            # 计算亮度
            brightness = np.mean(gray)

            # 计算对比度
            contrast = np.std(gray)

            # 综合评分（可根据实际需求调整权重）
            quality_score = (
                min(sharpness / 100, 1.0) * 0.4 +  # 清晰度权重40%
                min(abs(brightness - 128) / 128, 1.0) * 0.3 +  # 亮度权重30%
                min(contrast / 127, 1.0) * 0.3  # 对比度权重30%
            ) * 100

            return max(0.0, min(100.0, quality_score))
        except Exception:
            return 0.0