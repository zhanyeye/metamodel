"""
file_util - 文件操作工具

提供通用的文件查找等功能
"""

import os
from typing import Optional


def find_file(folder_path: str, filename: str) -> Optional[str]:
    """
    在文件夹中递归查找指定文件名

    Args:
        folder_path: 要搜索的目录路径
        filename: 要查找的文件名

    Returns:
        文件完整路径，未找到返回 None
    """
    for root, _, files in os.walk(folder_path):
        if filename in files:
            return os.path.join(root, filename)
    return None
