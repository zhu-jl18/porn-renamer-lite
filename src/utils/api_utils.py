"""
API调用工具函数模块
提供HTTP请求封装、重试机制和错误处理
"""
import asyncio
import logging
from typing import Optional, Dict, Any
import httpx
from ..config.settings import settings

logger = logging.getLogger(__name__)

class APIUtils:
    """API工具类"""

    @staticmethod
    async def call_api_with_retry(
        client: httpx.AsyncClient,
        endpoint: str,
        payload: Dict[str, Any],
        max_retries: int = None,
        timeout: int = 30
    ) -> Optional[str]:
        """
        带重试机制的API调用
        """
        if max_retries is None:
            max_retries = settings.max_retries

        for attempt in range(max_retries + 1):
            try:
                response = await client.post(
                    endpoint,
                    json=payload,
                    timeout=timeout
                )

                if response.status_code == 200:
                    result = response.json()
                    return result.get("response", "").strip()
                else:
                    logger.warning(f"API调用失败 (状态码: {response.status_code}): {response.text}")

            except httpx.TimeoutException:
                logger.warning(f"API调用超时 (尝试 {attempt + 1}/{max_retries + 1})")
            except httpx.NetworkError as e:
                logger.warning(f"网络错误 (尝试 {attempt + 1}/{max_retries + 1}): {e}")
            except Exception as e:
                logger.error(f"API调用异常 (尝试 {attempt + 1}/{max_retries + 1}): {e}")

            # 如果不是最后一次尝试，等待一段时间
            if attempt < max_retries:
                wait_time = min(2 ** attempt, 10)  # 指数退避，最大等待10秒
                await asyncio.sleep(wait_time)

        logger.error(f"API调用失败，已达到最大重试次数 {max_retries}")
        return None

    @staticmethod
    def create_image_analysis_payload(
        image_base64: str,
        prompt: str = None
    ) -> Dict[str, Any]:
        """
        创建图片分析的API负载
        """
        if prompt is None:
            prompt = settings.analysis_prompt

        return {
            "prompt": prompt,
            "image_data": image_base64,
            "model": "gemini-2.5-flash"
        }

    @staticmethod
    async def test_api_connection(
        client: httpx.AsyncClient,
        endpoint: str = None
    ) -> bool:
        """
        测试API连接
        """
        if endpoint is None:
            endpoint = settings.api_url

        try:
            # 创建测试负载
            test_image_b64 = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChAI/hQyHqQAAAABJRU5ErkJggg=="  # 1x1像素的PNG
            test_payload = {
                "prompt": "这是一个连接测试，请回复'连接正常'",
                "image_data": test_image_b64,
                "model": "gemini-2.5-flash"
            }

            response = await client.post(
                endpoint,
                json=test_payload,
                timeout=10
            )

            return response.status_code == 200
        except Exception as e:
            logger.error(f"API连接测试失败: {e}")
            return False

    @staticmethod
    def parse_api_response(response: str) -> Optional[str]:
        """
        解析API响应，提取文件名建议
        """
        if not response:
            return None

        # 移除可能的引号和多余空格
        cleaned = response.strip().strip('"\'').strip()

        # 检查是否为空或过长
        if not cleaned or len(cleaned) > 100:
            return None

        # 检查是否包含敏感词汇或无效内容
        invalid_patterns = [
            r'^[^a-zA-Z0-9\u4e00-\u9fa5]',
            r'[^a-zA-Z0-9\u4e00-\u9fa5]$',
            r'[<>:"/\\|?*]',  # 文件名不允许的字符
        ]

        for pattern in invalid_patterns:
            import re
            if re.search(pattern, cleaned):
                return None

        return cleaned if cleaned else None