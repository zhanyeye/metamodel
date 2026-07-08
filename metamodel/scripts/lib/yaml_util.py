这段代码是干啥的？
"""
yaml_util - YAML 文件处理工具

基于 ruamel.yaml 的 YAML 读写工具，支持：
- 多行字符串自动使用 |- 格式
- 保留原始引号风格
- 保持缩进格式

输入:
    - data: 要序列化的 dict 或其他对象
    - file_path: 可选，输出文件路径

输出:
    - 如果指定 file_path，写入文件
    - 否则返回 YAML 字符串
"""

import copy
from io import StringIO

from ruamel.yaml import YAML
from ruamel.yaml.scalarstring import LiteralScalarString


class YamlUtil:
    """
    YAML 处理工具类

    特性:
        - 多行字符串自动使用 |- 格式
        - 保留原始引号风格
        - 保持缩进格式 (mapping=2, sequence=4, offset=2)
    """

    def __init__(self):
        self.yaml = YAML()
        self.yaml.preserve_quotes = True
        self.yaml.indent(mapping=2, sequence=4, offset=2)

    def dump(self, data):
        """
        序列化 YAML

        Args:
            data: 要序列化的数据（dict 或其他）

        Returns:
            如果未指定 file_path，返回 YAML 字符串
        """
        data_copy = copy.deepcopy(data)
        self._convert_multiline_strings(data_copy)
        buf = StringIO()
        self.yaml.dump(data_copy, buf)
        return buf.getvalue()

    def load(self, file_path):
        """
        加载 YAML 文件

        Args:
            file_path: YAML 文件路径

        Returns:
            解析后的 dict 对象
        """
        with open(file_path, 'r', encoding='utf-8') as f:
            return self.yaml.load(f)

    def _convert_multiline_strings(self, obj):
        """
        递归将包含换行符的字符串转换为 LiteralScalarString

        Args:
            obj: dict 或 list 对象，会被原地修改
        """
        if isinstance(obj, dict):
            self._process_dict(obj)
        elif isinstance(obj, list):
            self._process_list(obj)

    def _process_dict(self, d):
        for k, v in d.items():
            if isinstance(v, str) and '\n' in v:
                d[k] = LiteralScalarString(v)
            elif isinstance(v, (dict, list)):
                self._convert_multiline_strings(v)

    def _process_list(self, lst):
        for i, item in enumerate(lst):
            if isinstance(item, str) and '\n' in item:
                lst[i] = LiteralScalarString(item)
            elif isinstance(item, (dict, list)):
                self._convert_multiline_strings(item)
