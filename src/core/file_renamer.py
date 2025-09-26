"""
文件重命名模块
负责安全重命名文件、冲突检测和操作日志
"""
import os
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime
from ..utils.filename_utils import FilenameUtils
from ..config.settings import settings

logger = logging.getLogger(__name__)

class FileRenamer:
    """文件重命名器"""

    def __init__(self, dry_run: bool = False):
        self.dry_run = dry_run  # 试运行模式，不实际重命名
        self.rename_log = []

    def rename_single_file(self, original_path: Path, new_name: str) -> bool:
        """
        重命名单个文件
        """
        try:
            # 验证原文件
            if not original_path.exists():
                logger.error(f"原文件不存在: {original_path}")
                return False

            if not original_path.is_file():
                logger.error(f"路径不是文件: {original_path}")
                return False

            # 生成新文件路径
            new_path = self._generate_new_path(original_path, new_name)

            # 检查是否需要重命名
            if original_path.name == new_path.name:
                logger.info(f"文件名未改变，跳过: {original_path.name}")
                return True

            # 记录重命名操作
            log_entry = {
                "timestamp": datetime.now().isoformat(),
                "original_path": str(original_path),
                "original_name": original_path.name,
                "new_path": str(new_path),
                "new_name": new_path.name,
                "success": False
            }

            try:
                if self.dry_run:
                    logger.info(f"[试运行] 将重命名: {original_path.name} -> {new_path.name}")
                    log_entry["success"] = True
                    log_entry["dry_run"] = True
                else:
                    # 执行重命名
                    original_path.rename(new_path)
                    logger.info(f"重命名成功: {original_path.name} -> {new_path.name}")
                    log_entry["success"] = True

            except Exception as e:
                logger.error(f"重命名失败: {original_path.name} -> {new_path.name}: {e}")
                log_entry["error"] = str(e)

            # 添加到日志
            self.rename_log.append(log_entry)
            return log_entry["success"]

        except Exception as e:
            logger.error(f"重命名文件异常 {original_path}: {e}")
            return False

    def batch_rename_files(self, rename_map: Dict[Path, str]) -> Dict[str, Any]:
        """
        批量重命名文件
        rename_map: {原文件路径: 新文件名}
        """
        results = {
            "total": len(rename_map),
            "success": 0,
            "failed": 0,
            "skipped": 0,
            "rename_operations": []
        }

        logger.info(f"开始批量重命名 {results['total']} 个文件")

        for original_path, new_name in rename_map.items():
            try:
                # 检查文件是否存在
                if not original_path.exists():
                    logger.warning(f"文件不存在，跳过: {original_path}")
                    results["skipped"] += 1
                    continue

                # 执行重命名
                success = self.rename_single_file(original_path, new_name)

                if success:
                    results["success"] += 1
                else:
                    results["failed"] += 1

                # 记录操作
                results["rename_operations"].append({
                    "original_path": str(original_path),
                    "new_name": new_name,
                    "success": success
                })

            except Exception as e:
                logger.error(f"批量重命名异常 {original_path}: {e}")
                results["failed"] += 1

        logger.info(f"批量重命名完成: {results}")
        return results

    def _generate_new_path(self, original_path: Path, new_name: str) -> Path:
        """
        生成新的文件路径，处理文件名冲突
        """
        # 确保新文件名有正确的扩展名
        if not any(new_name.lower().endswith(ext) for ext in settings.video_extensions):
            new_name = new_name + original_path.suffix

        # 创建新路径
        new_path = original_path.parent / new_name

        # 处理文件名冲突
        return FilenameUtils.resolve_filename_conflict(new_path)

    def preview_rename(self, rename_map: Dict[Path, str]) -> List[Dict[str, str]]:
        """
        预览重命名结果
        """
        preview = []

        for original_path, new_name in rename_map.items():
            new_path = self._generate_new_path(original_path, new_name)
            preview.append({
                "original": str(original_path),
                "original_name": original_path.name,
                "new": str(new_path),
                "new_name": new_path.name
            })

        return preview

    def undo_rename(self) -> bool:
        """
        撤销重命名操作（仅限本次会话）
        """
        if self.dry_run:
            logger.info("试运行模式，无需撤销")
            return True

        undo_success = True
        undo_count = 0

        # 反向遍历日志，从最后的操作开始撤销
        for log_entry in reversed(self.rename_log):
            if log_entry.get("success") and not log_entry.get("dry_run"):
                try:
                    original_path = Path(log_entry["original_path"])
                    new_path = Path(log_entry["new_path"])

                    if new_path.exists():
                        new_path.rename(original_path)
                        undo_count += 1
                        logger.info(f"撤销重命名: {log_entry['new_name']} -> {log_entry['original_name']}")
                    else:
                        logger.warning(f"无法撤销，文件不存在: {log_entry['new_name']}")

                except Exception as e:
                    logger.error(f"撤销重命名失败: {e}")
                    undo_success = False

        logger.info(f"撤销完成，共撤销 {undo_count} 个操作")
        return undo_success

    def save_rename_log(self, log_file_path: str = None) -> bool:
        """
        保存重命名日志到文件
        """
        if log_file_path is None:
            log_file_path = f"rename_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

        try:
            import json
            with open(log_file_path, 'w', encoding='utf-8') as f:
                json.dump(self.rename_log, f, ensure_ascii=False, indent=2)

            logger.info(f"重命名日志已保存到: {log_file_path}")
            return True

        except Exception as e:
            logger.error(f"保存重命名日志失败: {e}")
            return False

    def get_rename_statistics(self) -> Dict[str, Any]:
        """
        获取重命名统计信息
        """
        total_operations = len(self.rename_log)
        successful_operations = sum(1 for entry in self.rename_log if entry.get("success"))

        return {
            "total_operations": total_operations,
            "successful_operations": successful_operations,
            "failed_operations": total_operations - successful_operations,
            "success_rate": (successful_operations / total_operations * 100) if total_operations > 0 else 0
        }

    def validate_rename_map(self, rename_map: Dict[Path, str]) -> Dict[str, Any]:
        """
        验证重命名映射
        """
        validation_result = {
            "valid": True,
            "warnings": [],
            "errors": []
        }

        for original_path, new_name in rename_map.items():
            # 检查原文件
            if not original_path.exists():
                validation_result["errors"].append(f"原文件不存在: {original_path}")
                validation_result["valid"] = False
                continue

            # 检查新文件名
            if not new_name or not new_name.strip():
                validation_result["errors"].append(f"新文件名为空: {original_path}")
                validation_result["valid"] = False
                continue

            # 检查文件名长度
            if len(new_name) > 255:  # Windows文件名长度限制
                validation_result["warnings"].append(f"文件名过长: {new_name[:50]}...")

            # 检查文件名字符
            invalid_chars = '<>:"/\\|?*'
            if any(char in new_name for char in invalid_chars):
                validation_result["errors"].append(f"文件名包含非法字符: {new_name}")
                validation_result["valid"] = False

        return validation_result

    def cleanup_duplicate_files(self, directory: Path) -> Dict[str, Any]:
        """
        清理重复文件（基于文件名模式）
        返回清理结果
        """
        # 查找可能的重复文件
        file_groups = {}
        for file_path in directory.glob("*"):
            if file_path.is_file():
                base_name = self._extract_base_name(file_path.name)
                if base_name not in file_groups:
                    file_groups[base_name] = []
                file_groups[base_name].append(file_path)

        # 找到有重复的组
        duplicates = {k: v for k, v in file_groups.items() if len(v) > 1}

        results = {
            "duplicate_groups": len(duplicates),
            "total_duplicates": sum(len(v) for v in duplicates.values()),
            "files_to_remove": [],
            "files_to_keep": []
        }

        # 对于每组重复文件，保留最新的一个
        for group_name, file_list in duplicates.items():
            # 按修改时间排序，最新的在前
            file_list.sort(key=lambda f: f.stat().st_mtime, reverse=True)

            # 保留最新的，其余标记为删除
            results["files_to_keep"].append(str(file_list[0]))
            results["files_to_remove"].extend(str(f) for f in file_list[1:])

        return results

    def _extract_base_name(self, filename: str) -> str:
        """
        提取基础文件名（移除数字后缀）
        """
        import re
        name_part = os.path.splitext(filename)[0]

        # 移除常见的数字后缀模式
        patterns = [
            r'_\d+$',
            r'\(\d+\)$',
            r'-\d+$',
            r'\s\d+$',
        ]

        for pattern in patterns:
            name_part = re.sub(pattern, '', name_part)

        return name_part