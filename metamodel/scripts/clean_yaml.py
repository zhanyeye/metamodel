#!/usr/bin/env python3
"""
清理 YAML 文件中的无用空信息

删除规则：
1. 空对象: {}
2. 空数组: []
3. 递归清理：如果一个键的值被删除后变成空，也继续删除
"""

import yaml
import sys


def clean_dict(obj):
    """
    递归清理字典中的空值
    返回清理后的对象，如果整个对象为空则返回 None
    """
    if obj is None:
        return None

    if isinstance(obj, dict):
        # 递归清理每个值
        cleaned = {}
        for key, value in obj.items():
            cleaned_value = clean_dict(value)
            if cleaned_value is not None:
                cleaned[key] = cleaned_value

        # 如果清理后为空字典，返回 None
        if len(cleaned) == 0:
            return None
        return cleaned

    if isinstance(obj, list):
        # 递归清理每个元素
        cleaned = []
        for item in obj:
            cleaned_item = clean_dict(item)
            if cleaned_item is not None:
                cleaned.append(cleaned_item)

        # 如果清理后为空数组，返回 None
        if len(cleaned) == 0:
            return None
        return cleaned

    # 基础类型直接返回
    return obj


def format_yaml_value(value):
    """格式化 YAML 值"""
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float):
        return str(value)
    if isinstance(value, str):
        # 如果字符串包含特殊字符或空格，需要加引号
        if any(c in value for c in [':', '#', '{', '}', '[', ']', ',', '&', '*', '?', '|', '-', '<', '>', '=', '!', '%', '@', '`', '\n', '"', "'"]) or value.startswith(' ') or value.endswith(' '):
            return "'" + value + "'"
        # 数字格式的字符串也不加引号
        if value.lstrip('-').isdigit():
            return value
        return value
    return str(value)


def write_yaml_with_indent(data, file_handle, indent=0, inline_keys=None):
    """自定义 YAML 写入，保持正确的缩进"""
    if data is None:
        return

    if inline_keys is None:
        inline_keys = set()

    if isinstance(data, dict):
        keys = list(data.keys())
        for i, key in enumerate(keys):
            value = data[key]
            if value is None:
                continue
            if isinstance(value, dict) and len(value) == 0:
                continue
            if isinstance(value, list) and len(value) == 0:
                continue

            # 判断这个键是否需要内联（值是简单类型）
            is_inline = key in inline_keys or (not isinstance(value, (dict, list)))

            if is_inline:
                formatted_value = format_yaml_value(value)
                file_handle.write(' ' * indent + key + ': ' + formatted_value + '\n')
            else:
                file_handle.write(' ' * indent + key + ':\n')
                write_yaml_with_indent(value, file_handle, indent + 2, inline_keys)

    elif isinstance(data, list):
        for item in data:
            if item is None:
                continue
            if isinstance(item, dict) and len(item) == 0:
                continue
            if isinstance(item, list) and len(item) == 0:
                continue

            if isinstance(item, dict):
                keys = list(item.keys())
                first_key = keys[0] if keys else None

                if first_key is None:
                    continue

                first_value = item[first_key]

                # 如果第一个值是复杂类型（dict或list），需要换行
                if isinstance(first_value, dict) and len(first_value) > 0:
                    file_handle.write(' ' * indent + '- ' + first_key + ':\n')
                    write_yaml_with_indent(first_value, file_handle, indent + 4, inline_keys)
                elif isinstance(first_value, list) and len(first_value) > 0:
                    file_handle.write(' ' * indent + '- ' + first_key + ':\n')
                    write_yaml_with_indent(first_value, file_handle, indent + 4, inline_keys)
                else:
                    # 简单类型，写在同一行
                    formatted_value = format_yaml_value(first_value)
                    file_handle.write(' ' * indent + '- ' + first_key + ': ' + formatted_value + '\n')

                # 处理剩余的键值对
                for key in keys[1:]:
                    value = item[key]
                    if value is None:
                        continue
                    if isinstance(value, dict) and len(value) == 0:
                        continue
                    if isinstance(value, list) and len(value) == 0:
                        continue

                    # 判断是否需要换行
                    if isinstance(value, dict) and len(value) > 0:
                        file_handle.write(' ' * (indent + 2) + key + ':\n')
                        write_yaml_with_indent(value, file_handle, indent + 4, inline_keys)
                    elif isinstance(value, list) and len(value) > 0:
                        file_handle.write(' ' * (indent + 2) + key + ':\n')
                        write_yaml_with_indent(value, file_handle, indent + 4, inline_keys)
                    else:
                        formatted_v = format_yaml_value(value)
                        file_handle.write(' ' * (indent + 2) + key + ': ' + formatted_v + '\n')
            else:
                formatted = format_yaml_value(item)
                file_handle.write(' ' * indent + '- ' + formatted + '\n')

    else:
        # 基础类型
        formatted = format_yaml_value(data)
        file_handle.write(' ' + formatted + '\n')


def clean_yaml_file(input_path: str, output_path: str = None) -> str:
    """
    清理 YAML 文件

    Args:
        input_path: 输入文件路径
        output_path: 输出文件路径，如果为 None 则覆盖原文件

    Returns:
        清理后的 YAML 字符串
    """
    # 读取 YAML
    with open(input_path, 'r', encoding='utf-8') as f:
        data = yaml.safe_load(f)

    # 清理数据
    cleaned_data = clean_dict(data)

    # 使用自定义写入保持缩进
    import io
    buffer = io.StringIO()
    write_yaml_with_indent(cleaned_data, buffer)
    result = buffer.getvalue()

    # 如果没有指定输出路径，返回字符串
    if output_path:
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(result)
        return ""

    return result


def main():
    """主函数"""
    if len(sys.argv) < 2:
        print("Usage: python clean_yaml.py <input_yaml> [output_yaml]", file=sys.stderr)
        sys.exit(1)

    input_path = sys.argv[1]
    output_path = sys.argv[2] if len(sys.argv) > 2 else None

    try:
        result = clean_yaml_file(input_path, output_path)
        if result:
            print(result)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
