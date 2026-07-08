这段代码是干啥的？
"""
io_fields - 统一 IO 字段解析入口

根据 refId 前缀自动分派到对应的处理函数：
- KafkaTopic.* → get_kafka_io_fields
- IcebergTable.* → get_iceberg_io_fields

输入:
    - folder_path: 模型文件所在目录
    - io: IO 配置 dict，包含 name 和 refId
    - io_type: input 或 output

输出:
    - 字符串，格式如:
      -- input: xxx (KafkaTopic.xxx)  Message.yyy.yaml
      msgid,    -- BYTES
"""

import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from typing import Callable, Tuple

from kafka_fields import get_kafka_io_fields
from iceberg_fields import get_iceberg_io_fields


def _match_prefix(ref_id: str, prefix: str) -> bool:
    """检查 refId 是否以指定前缀开头"""
    return ref_id.startswith(prefix)


def _register_handlers():
    """注册所有 IO 类型处理器"""
    return [
        ("KafkaTopic.", get_kafka_io_fields),
        ("IcebergTable.", get_iceberg_io_fields),
    ]


def get_io_fields(folder_path: str, io: dict, io_type: str) -> str:
    """
    统一获取 IO 字段信息，根据 refId 前缀自动分派

    Args:
        folder_path: 模型文件所在目录
        io: IO 配置 dict，包含 name 和 refId
        io_type: input 或 output

    Returns:
        字段信息字符串
    """
    ref_id = io.get('refId', '')
    if not ref_id:
        return ""

    for prefix, handler in _register_handlers():
        if _match_prefix(ref_id, prefix):
            return handler(folder_path, io, io_type)

    return ""
