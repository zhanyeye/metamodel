"""
script_runtime - 建模 Python 脚本运行时工具。

平台 CLI 参数：
  --model-yaml-path / --field-name / --model-zip

环境变量（场景、结果路径等）：
  UDA_SCRIPT_SCOPE / UDA_MODEL_FILE_NAME / UDA_SCRIPT_RESULT_FILE
"""

from __future__ import annotations

import argparse
import json
import os
from dataclasses import dataclass


@dataclass(frozen=True)
class ScriptCli:
    model_yaml_path: str
    field_name: str
    model_zip_path: str


def parse_script_cli(argv: list[str] | None = None) -> ScriptCli:
    """解析平台传入的 CLI 参数（flag 形式）。"""
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--model-yaml-path", default="")
    parser.add_argument("--field-name", default="")
    parser.add_argument("--model-zip", dest="model_zip_path", default="")
    ns = parser.parse_args(argv)
    return ScriptCli(
        model_yaml_path=(ns.model_yaml_path or "").strip(),
        field_name=(ns.field_name or "").strip(),
        model_zip_path=(ns.model_zip_path or "").strip(),
    )


def read_model_yaml_at(path: str) -> str:
    """读取 model YAML 文件内容；路径不存在或为空文件时返回空字符串。"""
    if path and os.path.isfile(path):
        with open(path, encoding="utf-8") as f:
            return f.read()
    return ""


def result_file_path() -> str | None:
    """读取 UDA_SCRIPT_RESULT_FILE；未设置时返回 None。"""
    path = os.environ.get("UDA_SCRIPT_RESULT_FILE", "").strip()
    return path or None


def write_script_result(payload: dict) -> None:
    """将 scriptRunResponse 形态 dict 以 JSON 写入结果文件（推荐方式）。"""
    path = result_file_path()
    if not path:
        raise RuntimeError("UDA_SCRIPT_RESULT_FILE not set")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False)


def write_script_result_text(text: str) -> None:
    """将任意文本写入结果文件（非 JSON 场景）。"""
    path = result_file_path()
    if not path:
        raise RuntimeError("UDA_SCRIPT_RESULT_FILE not set")
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)
