这个段代码在干啥？
"""
iceberg_fields - Iceberg Table 字段解析工具

根据 Flink 任务的 inputs/outputs 配置，从 Iceberg Table 配置文件中提取 schema 信息，
生成 SQL 字段注释。

输入:
    - folder_path: 模型文件所在目录
    - io: Iceberg Table 配置 dict，包含 name 和 refId
    - io_type: input 或 output

输出:
    - 字符串，格式如:
      -- input: xxx (IcebergTable.xxx)  IcebergTable.IcebergDatabase.ods.user_behavior.yaml
      event_time,    -- timestamp
      user_id,    -- long
"""

import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from typing import Optional

from ruamel.yaml import YAML
from file_util import find_file


_yaml = YAML()


def _parse_yaml(file_path: str) -> dict:
    """
    解析 YAML 文件

    Args:
        file_path: YAML 文件路径

    Returns:
        解析后的 dict 对象
    """
    with open(file_path, 'r', encoding='utf-8') as f:
        return _yaml.load(f)


def _get_iceberg_columns(folder_path: str, ref_id: str) -> str:
    """
    根据 IcebergTable refId 获取字段列表

    Args:
        folder_path: 模型文件所在目录
        ref_id: IcebergTable ID，如 IcebergTable.IcebergDatabase.ods.user_behavior

    Returns:
        字段列表字符串，格式:
        -- IcebergTable.IcebergDatabase.ods.user_behavior.yaml
        event_time,    -- timestamp
        user_id,    -- long
    """
    yaml_file = find_file(folder_path, f"{ref_id}.yaml")
    if not yaml_file:
        return ""

    yaml_data = _parse_yaml(yaml_file)
    columns = yaml_data.get('columns', [])
    if not columns:
        return ""

    yaml_filename = os.path.basename(yaml_file)
    lines = []
    for col in columns:
        col_name = col.get('name', '')
        col_type = col.get('type', '')
        lines.append(f"{col_name},    -- {col_type}")
    return "-- " + yaml_filename + "\n" + "\n".join(lines)


def get_iceberg_io_fields(folder_path: str, io: dict, io_type: str) -> str:
    """
    获取单个 Iceberg IO 的字段信息

    Args:
        folder_path: 模型文件所在目录
        io: IO 配置 dict，包含 name 和 refId
        io_type: input 或 output

    Returns:
        字段信息字符串，格式:
        -- input: xxx (IcebergTable.xxx)  IcebergTable.IcebergDatabase.ods.user_behavior.yaml
        event_time,    -- timestamp
    """
    name = io.get('name', '')
    ref_id = io.get('refId', '')

    fields_str = _get_iceberg_columns(folder_path, ref_id)
    if not fields_str:
        return ""

    yaml_filename = fields_str.split("\n")[0].replace("-- ", "")
    fields_content = "\n".join(fields_str.split("\n")[1:])

    return f"-- {io_type}: {name} ({ref_id})  {yaml_filename}\n{fields_content}"
