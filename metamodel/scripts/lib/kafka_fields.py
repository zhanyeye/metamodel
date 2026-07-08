"""
kafka_fields - Kafka Topic 字段解析工具

根据 Flink 任务的 inputs/outputs 配置，从 Kafka Topic 配置文件中提取 schema 信息，
生成 SQL 字段注释。

输入:
    - folder_path: 模型文件所在目录
    - io: Kafka Topic 配置 dict，包含 name 和 refId
    - io_type: input 或 output

输出:
    - 字符串，格式如:
      -- input: xxx (KafkaTopic.xxx)  Message.yyy.yaml
      msgid,    -- BYTES
      streamid,    -- BYTES
"""

import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from typing import List

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


def _get_schema_fields(folder_path: str, schema_id: str) -> str:
    """
    根据 schemaId 获取字段列表

    Args:
        folder_path: 模型文件所在目录
        schema_id: Schema ID，如 Message.msg1

    Returns:
        字段列表字符串，格式:
        -- Message.msg1.yaml
        msgid,    -- BYTES
        streamid,    -- BYTES
    """
    schema_file = find_file(folder_path, f"{schema_id}.yaml")
    if not schema_file:
        return ""

    schema_data = _parse_yaml(schema_file)
    elements = schema_data.get('elements', [])
    if not elements:
        return ""

    schema_filename = os.path.basename(schema_file)
    lines = []
    for elem in elements:
        field_name = elem.get('fieldName', '')
        field_type = elem.get('fieldType', '')
        lines.append(f"{field_name},    -- {field_type}")
    return "-- " + schema_filename + "\n" + "\n".join(lines)


def get_kafka_io_fields(folder_path: str, io: dict, io_type: str) -> str:
    """
    获取单个 Kafka IO 的字段信息

    Args:
        folder_path: 模型文件所在目录
        io: IO 配置 dict，包含 name 和 refId
        io_type: input 或 output

    Returns:
        字段信息字符串，格式:
        -- input: xxx (KafkaTopic.xxx)  Message.yyy.yaml
        msgid,    -- BYTES
    """
    name = io.get('name', '')
    ref_id = io.get('refId', '')

    kafka_file = find_file(folder_path, f"{ref_id}.yaml")
    if not kafka_file:
        return ""

    kafka_data = _parse_yaml(kafka_file)
    schema_id = kafka_data.get('schemaId', '')
    if not schema_id:
        return ""

    fields_str = _get_schema_fields(folder_path, schema_id)
    if not fields_str:
        return ""

    schema_filename = fields_str.split("\n")[0].replace("-- ", "")
    fields_content = "\n".join(fields_str.split("\n")[1:])

    return f"-- {io_type}: {name} ({ref_id})  {schema_filename}\n{fields_content}"
