#!/usr/bin/env python3
"""
StarRocks 表定义 YAML 转建表 SQL 工具

输入: 建模平台生成的表定义 YAML 字符串
输出: StarRocks 建表 SQL 语句

支持: 主键表(PRIMARY)、明细表(DUPLICATE)
不支持: 聚合模型、向量化引擎、复杂类型(ARRAY/MAP/STRUCT)
"""

import logging
import sys
from typing import Any, Dict, List, Optional
import yaml

# 配置 logging
logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s: %(message)s'
)
logger = logging.getLogger(__name__)


def parse_column_type(column_type: Dict[str, Any]) -> str:
    """
    解析字段类型，生成 SQL 中的类型定义

    支持: TINYINT, SMALLINT, INT, BIGINT, LARGEINT, FLOAT, DOUBLE,
          DECIMAL, DATE, DATETIME, CHAR, VARCHAR, STRING, BOOLEAN, VARBINARY, JSON
    不支持: ARRAY, MAP, STRUCT
    """
    field_type = column_type.get("fieldType", "INT")

    # DECIMAL 类型需要 precision 和 scale
    if field_type == "DECIMAL":
        decimal_para = column_type.get("decimalPara", {})
        precision = decimal_para.get("precision", 10)
        scale = decimal_para.get("scale", 2)
        return f"DECIMAL({precision}, {scale})"

    # VARCHAR 类型需要最大长度
    if field_type == "VARCHAR":
        var_char_len = column_type.get("varCharLen", 255)
        return f"VARCHAR({var_char_len})"

    # CHAR 类型需要长度
    if field_type == "CHAR":
        char_len = column_type.get("charLen", 1)
        return f"CHAR({char_len})"

    # VARBINARY 类型需要最大长度
    if field_type == "VARBINARY":
        var_bin_len = column_type.get("varBinLen", 255)
        return f"VARBINARY({var_bin_len})"

    # ARRAY, MAP, STRUCT 暂不支持
    if field_type in ("ARRAY", "MAP", "STRUCT"):
        raise ValueError(f"暂不支持复杂类型: {field_type}")

    return field_type


def parse_columns(columns: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    解析列定义列表
    返回: 包含解析后信息的列列表
    """
    result = []
    for col in columns:
        col_name = col.get("columnName", "")
        column_type = col.get("columnType", {})

        # 解析类型
        sql_type = parse_column_type(column_type)

        # 是否可为空
        is_nullable = col.get("isNullable", True)

        # 默认值
        default_value = col.get("defaultValue", "")
        default_sql = ""
        if default_value:
            # 如果是字符串类型，加引号
            if sql_type in ("VARCHAR", "CHAR", "STRING", "JSON"):
                default_sql = f" DEFAULT '{default_value}'"
            else:
                default_sql = f" DEFAULT {default_value}"

        # 描述/注释
        description = col.get("description", "")
        comment_sql = f" COMMENT '{description}'" if description else ""

        # 标记字段角色
        is_primary_key = col.get("isPrimaryKey", False)
        is_partition_key = col.get("isPartitionKey", False)
        is_hash_distributed_key = col.get("isHashDistributedKey", False)
        is_order_key = col.get("isOrderKey", False)

        result.append({
            "column_name": col_name,
            "sql_type": sql_type,
            "is_nullable": is_nullable,
            "default_sql": default_sql,
            "comment_sql": comment_sql,
            "is_primary_key": is_primary_key,
            "is_partition_key": is_partition_key,
            "is_hash_distributed_key": is_hash_distributed_key,
            "is_order_key": is_order_key,
        })

    return result


def generate_column_definitions(parsed_columns: List[Dict[str, Any]]) -> str:
    """生成列定义 SQL"""
    column_defs = []
    for col in parsed_columns:
        # StarRocks: 只有 NOT NULL 才需要显式写，NULL 可以省略
        null_str = "NOT NULL" if not col["is_nullable"] else ""
        col_def = f"    {col['column_name']} {col['sql_type']} {null_str}{col['default_sql']}{col['comment_sql']}"
        column_defs.append(col_def)
    return ",\n".join(column_defs)


def generate_primary_key_sql(table_type: str, parsed_columns: List[Dict[str, Any]]) -> Optional[str]:
    """生成 PRIMARY KEY 子句"""
    if table_type == "PRIMARY":
        pk_columns = [col["column_name"] for col in parsed_columns if col["is_primary_key"]]
        if pk_columns:
            return f"PRIMARY KEY ({', '.join(pk_columns)})"
    return None


def generate_partition_by_sql(parsed_columns: List[Dict[str, Any]]) -> Optional[str]:
    """生成 PARTITION BY RANGE 子句"""
    partition_key_columns = [col["column_name"] for col in parsed_columns if col["is_partition_key"]]
    if partition_key_columns:
        return f"PARTITION BY RANGE({', '.join(partition_key_columns)}) ()"
    return None


def generate_distributed_by_sql(parsed_columns: List[Dict[str, Any]]) -> Optional[str]:
    """生成 DISTRIBUTED BY HASH 子句"""
    distributed_key_columns = [col["column_name"] for col in parsed_columns if col["is_hash_distributed_key"]]
    if distributed_key_columns:
        return f"DISTRIBUTED BY HASH({', '.join(distributed_key_columns)})"
    return None


def generate_order_by_sql(parsed_columns: List[Dict[str, Any]]) -> Optional[str]:
    """生成 ORDER BY 子句"""
    order_key_columns = [col["column_name"] for col in parsed_columns if col["is_order_key"]]
    if order_key_columns:
        return f"ORDER BY ({', '.join(order_key_columns)})"
    return None


def validate_primary_key_order(table_type: str, parsed_columns: List[Dict[str, Any]], table_name: str) -> None:
    """校验主键表的列定义顺序：主键列必须在最前面"""
    if table_type == "PRIMARY":
        pk_columns = [col["column_name"] for col in parsed_columns if col["is_primary_key"]]
        if pk_columns:
            first_n_columns = [col["column_name"] for col in parsed_columns[:len(pk_columns)]]
            if first_n_columns != pk_columns:
                raise ValueError(
                    f"主键表 '{table_name}' 的列定义顺序错误：主键列 {pk_columns} 必须放在列定义的最前面。"
                    f"当前前列定义顺序: {[col['column_name'] for col in parsed_columns]}"
                )


def generate_create_table_sql(yaml_str: str) -> str:
    """
    根据表定义 YAML 生成建表 SQL

    Args:
        yaml_str: 表定义 YAML 字符串

    Returns:
        StarRocks 建表 SQL 语句
    """
    # 解析 YAML
    data = yaml.safe_load(yaml_str)

    if not data:
        raise ValueError("YAML 内容为空")

    # 获取表基本信息
    table = data.get("table", "")
    table_type = data.get("tableType", "DUPLICATE")
    columns = data.get("columns", [])
    sql_fragement = data.get("sqlFragement", "")

    if not table:
        raise ValueError("表名不能为空")

    # 解析列定义
    parsed_columns = parse_columns(columns)

    # 校验主键表列顺序
    validate_primary_key_order(table_type, parsed_columns, table)

    # 构建 SQL
    sql_parts = []

    # 1. CREATE TABLE 语句 + 列定义
    column_defs = generate_column_definitions(parsed_columns)
    sql_parts.append(f"CREATE TABLE {table} (\n    {column_defs}\n)")

    # 2. PRIMARY KEY (主键表)
    pk_sql = generate_primary_key_sql(table_type, parsed_columns)
    if pk_sql:
        sql_parts.append(pk_sql)

    # 3. PARTITION BY RANGE (分区键)
    partition_sql = generate_partition_by_sql(parsed_columns)
    if partition_sql:
        sql_parts.append(partition_sql)

    # 4. DISTRIBUTED BY HASH (分桶键)
    distributed_sql = generate_distributed_by_sql(parsed_columns)
    if distributed_sql:
        sql_parts.append(distributed_sql)

    # 5. ORDER BY (排序键)
    order_sql = generate_order_by_sql(parsed_columns)
    if order_sql:
        sql_parts.append(order_sql)

    # 6. PROPERTIES (sqlFragement)
    if sql_fragement:
        sql_fragement = sql_fragement.strip()
        if sql_fragement:
            sql_parts.append(sql_fragement)

    # 加上分号
    sql_parts[-1] = sql_parts[-1].rstrip().rstrip(",") + ";"

    return "\n".join(sql_parts)


def main():
    """主函数：从 --model-yaml-path 或 stdin 读取 YAML。"""
    import argparse

    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--model-yaml-path", default="")
    parser.add_argument("--field-name", default="")
    parser.add_argument("--model-zip", dest="model_zip_path", default="")
    args, extras = parser.parse_known_args()

    yaml_str = ""
    if args.model_yaml_path:
        with open(args.model_yaml_path, encoding="utf-8") as f:
            yaml_str = f.read()
    elif extras and not extras[0].startswith("-"):
        with open(extras[0], encoding="utf-8") as f:
            yaml_str = f.read()
    else:
        yaml_str = sys.stdin.read()

    if not yaml_str.strip():
        logger.error("Usage: python starrocks_sql_generator.py --model-yaml-path <yaml_file>")
        logger.error("Or: cat <yaml_file> | python starrocks_sql_generator.py")
        sys.exit(1)

    try:
        sql = generate_create_table_sql(yaml_str)
        print(sql)
    except Exception as e:
        logger.error(f"{e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
