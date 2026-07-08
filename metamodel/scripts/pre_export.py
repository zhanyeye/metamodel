"""
导出模型 zip 包前的处理

输入:
    --model-zip: 建模 ZIP 本地文件路径

输出:
    写入 UDA_SCRIPT_RESULT_FILE（JSON）
"""

from __future__ import annotations

import base64
import io
import sys
import zipfile

from lib.script_runtime import parse_script_cli, write_script_result

try:
    from metamodel_mapper import write_generated_taskplugin_entries
except ImportError:  # pragma: no cover - 精简环境无 mapper 时仍可透传 ZIP
    write_generated_taskplugin_entries = None  # type: ignore[misc, assignment]


def process_zip_bytes(zip_bytes: bytes) -> tuple[str | None, str]:
    """处理 ZIP 字节流，返回 (new_zip_b64, error_detail)。"""
    try:
        input_zip = zipfile.ZipFile(io.BytesIO(zip_bytes), "r")

        output_buffer = io.BytesIO()
        output_zip = zipfile.ZipFile(output_buffer, "w", zipfile.ZIP_DEFLATED)

        for item in input_zip.namelist():
            output_zip.writestr(item, input_zip.read(item))
        if write_generated_taskplugin_entries is not None:
            write_generated_taskplugin_entries(input_zip, output_zip)

        input_zip.close()
        output_zip.close()

        new_zip_content_b64 = base64.b64encode(output_buffer.getvalue()).decode("utf-8")
        return new_zip_content_b64, ""
    except Exception as e:
        return None, str(e)


def process_zip_file(zip_path: str) -> tuple[str | None, str]:
    """从本地 ZIP 路径读取并处理。"""
    with open(zip_path, "rb") as f:
        return process_zip_bytes(f.read())


def process_zip_from_b64(zip_content_b64: str) -> tuple[str | None, str]:
    """从 base64 字符串处理（仅单元测试 / 离线工具使用）。"""
    return process_zip_bytes(base64.b64decode(zip_content_b64))


def main() -> int:
    cli = parse_script_cli()
    zip_path = cli.model_zip_path
    if not zip_path:
        write_script_result({"success": False, "message": "missing --model-zip"})
        return 1
    if not __import__("os").path.isfile(zip_path):
        write_script_result({"success": False, "message": f"zip file not found: {zip_path}"})
        return 1

    print(f"[pre_export] processing zip: {zip_path}")
    new_zip_content, error_detail = process_zip_file(zip_path)

    if new_zip_content:
        write_script_result(
            {
                "success": True,
                "message": "script executed successfully",
                "modelZip": new_zip_content,
            },
        )
        print("[pre_export] completed successfully")
        return 0

    write_script_result(
        {
            "success": False,
            "message": error_detail or "pre_export failed",
        },
    )
    print(f"[pre_export] failed: {error_detail}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
