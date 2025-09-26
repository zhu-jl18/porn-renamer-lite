"""
文件扫描模块测试
"""
import pytest
import tempfile
from pathlib import Path
from src.core.file_scanner import FileScanner
from src.utils.filename_utils import FilenameUtils

class TestFileScanner:
    """文件扫描器测试"""

    def test_is_garbled_filename(self):
        """测试乱码文件名识别"""
        # 乱码文件名
        assert FilenameUtils.is_garbled_filename("1a07ebd26e434b4222216a.mp4") == True
        assert FilenameUtils.is_garbled_filename("981b707c0722116fc3dcec8edc71e42e.mp4") == True
        assert FilenameUtils.is_garbled_filename("abc123.mp4") == False  # 太短
        assert FilenameUtils.is_garbled_filename("normal_video.mp4") == False  # 正常文件名

    def test_is_video_file(self):
        """测试视频文件识别"""
        assert FilenameUtils.is_video_file(Path("test.mp4")) == True
        assert FilenameUtils.is_video_file(Path("test.avi")) == True
        assert FilenameUtils.is_video_file(Path("test.txt")) == False
        assert FilenameUtils.is_video_file(Path("test.jpg")) == False

    def test_scanner_initialization(self):
        """测试扫描器初始化"""
        with tempfile.TemporaryDirectory() as temp_dir:
            scanner = FileScanner(temp_dir)
            assert scanner.target_directory.exists()
            assert scanner.target_directory == Path(temp_dir)

    def test_scan_empty_directory(self):
        """测试扫描空目录"""
        with tempfile.TemporaryDirectory() as temp_dir:
            scanner = FileScanner(temp_dir)
            files = scanner.scan_directory()
            assert len(files) == 0

    def test_scan_directory_with_files(self):
        """测试扫描包含文件的目录"""
        with tempfile.TemporaryDirectory() as temp_dir:
            # 创建测试文件
            test_files = ["video1.mp4", "video2.avi", "1a07ebd26e434b4222216a.mp4", "readme.txt"]
            for filename in test_files:
                (Path(temp_dir) / filename).touch()

            scanner = FileScanner(temp_dir)
            files = scanner.scan_directory()

            # 应该只找到视频文件
            assert len(files) == 3
            assert any(f.name == "video1.mp4" for f in files)
            assert any(f.name == "video2.avi" for f in files)
            assert any(f.name == "1a07ebd26e434b4222216a.mp4" for f in files)

    def test_find_garbled_files(self):
        """测试查找乱码文件"""
        with tempfile.TemporaryDirectory() as temp_dir:
            # 创建测试文件
            test_files = [
                "normal_video.mp4",
                "1a07ebd26e434b4222216a.mp4",  # 乱码
                "981b707c0722116fc3dcec8edc71e42e.mp4",  # 乱码
                "another_normal.avi"
            ]
            for filename in test_files:
                (Path(temp_dir) / filename).touch()

            scanner = FileScanner(temp_dir)
            garbled_files = scanner.find_garbled_files()

            # 应该找到2个乱码文件
            assert len(garbled_files) == 2
            assert any(f.name == "1a07ebd26e434b4222216a.mp4" for f in garbled_files)
            assert any(f.name == "981b707c0722116fc3dcec8edc71e42e.mp4" for f in garbled_files)