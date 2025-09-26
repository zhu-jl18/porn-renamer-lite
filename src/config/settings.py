"""
配置管理模块
集中管理所有配置参数
"""
import os
from typing import Optional
from pydantic import BaseSettings, Field
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

class Settings(BaseSettings):
    """应用配置"""

    # API配置
    api_url: str = Field(
        default="http://localhost:3001/proxy/free",
        description="AI API服务地址"
    )

    # 重试配置
    max_retries: int = Field(
        default=3,
        ge=1,
        le=10,
        description="API调用最大重试次数"
    )

    # 并发配置
    max_workers: int = Field(
        default=2,
        ge=1,
        le=10,
        description="最大并发工作线程数"
    )

    # 截图配置
    screenshot_count: int = Field(
        default=3,
        ge=1,
        le=5,
        description="每个视频截图数量"
    )

    # 文件配置
    max_filename_length: int = Field(
        default=50,
        ge=10,
        le=100,
        description="最大文件名长度"
    )

    # 视频格式
    video_extensions: list[str] = Field(
        default=[".mp4", ".avi", ".mkv", ".mov", ".wmv", ".flv", ".ts", ".m4a"],
        description="支持的视频文件扩展名"
    )

    # 临时文件配置
    temp_dir: str = Field(
        default="temp_screenshots",
        description="临时截图目录"
    )

    # 日志配置
    log_level: str = Field(
        default="INFO",
        description="日志级别"
    )

    # AI分析提示词
    analysis_prompt: str = Field(
        default="""请分析这张视频截图，为视频文件生成一个合适的文件名。

要求：
1. 识别视频中的人物特征（性别、年龄、外貌特征）
2. 描述视频内容和场景
3. 识别视频类型（剧情、自拍、专业制作等）
4. 生成一个简洁、有描述性的文件名

文件名格式建议：
- 使用中文
- 2-8个字符
- 避免特殊符号
- 突出主要内容特征

示例：
"美腿自拍.mp4"
"浴室剧情.mp4"
"御姐cosplay.mp4"

请只返回文件名，不要其他解释。""",
        description="AI分析提示词"
    )

    class Config:
        env_file = ".env"
        env_prefix = "VIDEO_RENAMER_"

# 全局配置实例
settings = Settings()

def get_settings() -> Settings:
    """获取配置实例"""
    return settings