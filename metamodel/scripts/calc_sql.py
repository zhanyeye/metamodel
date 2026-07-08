"""
calc_sql - Spark/Flink SQL 任务字段注释追加工具

根据 Spark/Flink SQL 任务的 inputs 和 outputs 配置，自动生成字段注释，
追加到 sql 字段尾部。

支持多种 IO 类型：
- KafkaTopic.* → Kafka 字段
- IcebergTable.* → Iceberg 字段

输入:
    --model-yaml-path: FlinkSQLJob yaml 文件的本地路径
    --field-name: 变更字段名（可忽略）
    --model-zip: 建模 ZIP 本地路径（可忽略）

输出:
    - file_content: 追加注释后的 yaml 字符串
    - zip_content: 新的zip包字节流，None表示没有新建模型
    - result: 1 成功 / 0 失败
    - fail_detail: 失败原因
"""

import json
import os
import sys
from typing import Tuple

from lib.io_fields import get_io_fields
from lib.script_runtime import parse_script_cli, read_model_yaml_at
from lib.yaml_util import YamlUtil


def get_io_fields_from_content(base_folder: str, file_content: str) -> Tuple[str, str]:
    """
    从 yaml 内容中提取 inputs 和 outputs 的字段信息

    Args:
        base_folder: 模型文件所在目录
        file_content: yaml 文件字符串

    Returns:
        (inputs_str, outputs_str) 元组
    """
    yaml_util = YamlUtil()
    job_data = yaml_util.yaml.load(file_content)
    inputs = job_data.get('inputs', [])
    outputs = job_data.get('outputs', [])

    inputs_parts = []
    for io in inputs:
        field_str = get_io_fields(base_folder, io, "input")
        if field_str:
            inputs_parts.append(field_str)
    inputs_str = "\n".join(inputs_parts)

    outputs_parts = []
    for io in outputs:
        field_str = get_io_fields(base_folder, io, "output")
        if field_str:
            outputs_parts.append(field_str)
    outputs_str = "\n".join(outputs_parts)

    return inputs_str, outputs_str


def append_io_fields_to_sql(file_content: str) -> Tuple[bool, str, str]:
    """
    将字段注释追加到 sql 字段尾部

    Args:
        file_content: yaml 文件字符串

    Returns:
        (success, error_detail, new_content) 元组
        - success: True/False
        - error_detail: 错误信息
        - new_content: 修改后的 yaml 字符串
    """
    try:
        base_folder = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

        inputs_str, outputs_str = get_io_fields_from_content(base_folder, file_content)

        comment_lines = []
        if inputs_str:
            comment_lines.append(inputs_str)
        if inputs_str and outputs_str:
            comment_lines.append("")
        if outputs_str:
            comment_lines.append(outputs_str)

        if not comment_lines:
            return True, "", file_content

        comment_block = "\n/*\n" + "\n".join(comment_lines) + "\n*/"

        yaml_util = YamlUtil()
        job_data = yaml_util.yaml.load(file_content)
        original_sql = job_data.get('sql', '')
        job_data['sql'] = original_sql + "\n" + comment_block

        new_file_content = yaml_util.dump(job_data)

        return True, "", new_file_content

    except Exception as e:
        return False, str(e), ""


if __name__ == "__main__":
    cli = parse_script_cli()
    file_content = read_model_yaml_at(cli.model_yaml_path)

    success, error_detail, new_content = append_io_fields_to_sql(file_content)

    result = 1 if success else 0
    print(json.dumps({
        "file_content": new_content if success else file_content,
        "zip_content": None,
        "result": result,
        "fail_detail": error_detail,
    }, ensure_ascii=False))
    if not success:
        sys.exit(1)
