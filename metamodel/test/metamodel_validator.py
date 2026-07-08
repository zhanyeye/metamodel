#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
元模型验证脚本
用于验证元模型是否符合元元模型定义的规范

使用方法:
    python metamodel_validator.py \
        --meta-model-dir metamodel/metamodel \
        --meta-meta-model metamodel/metametamodel/metametamodel.yml \
        [--output-format json|text] \
        [--strict-level error|warning|info]
"""

import argparse
import logging
import os
import re
import sys
from dataclasses import dataclass
from enum import Enum, auto
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Union

import json
import yaml


class ValidationSeverity(Enum):
    """验证严重程度"""
    ERROR = auto()
    WARNING = auto()
    INFO = auto()


@dataclass
class ValidationError:
    """验证错误类"""
    severity: ValidationSeverity
    file: str
    message: str
    field_path: str = ""
    line_number: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            'severity': self.severity.name,
            'file': self.file,
            'message': self.message,
            'field_path': self.field_path,
            'line_number': self.line_number
        }


@dataclass
class FieldDefinition:
    """字段定义类"""
    name: str
    field_type: str
    properties: Dict[str, Any]
    
    def get_property(self, prop_name: str, default: Any = None) -> Any:
        """获取属性值"""
        return self.properties.get(prop_name, default)


@dataclass
class MetaModelDefinition:
    """元模型定义类"""
    model_type: str
    version: str
    description: str
    extends: Optional[str] = None
    fields: List[FieldDefinition] = None
    
    def get_field_by_name(self, field_name: str) -> Optional[FieldDefinition]:
        """根据字段名获取字段定义"""
        if self.fields:
            for field in self.fields:
                if field.name == field_name:
                    return field
        return None


class MetaMetaModelParser:
    """元元模型解析器"""
    
    def __init__(self):
        self.field_types: Dict[str, Dict[str, Any]] = {}
        self.inheritance_graph: Dict[str, List[str]] = {}
    
    def parse(self, meta_meta_model_path: str) -> bool:
        """解析元元模型文件"""
        try:
            with open(meta_meta_model_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            data = yaml.safe_load(content)
            
            # 解析字段类型定义
            for field_type_def in data.get('metaMetaTypes', []):
                field_type_name = field_type_def['fieldType']
                self.field_types[field_type_name] = field_type_def
                
                # 构建继承图
                extends = field_type_def.get('extends')
                if extends:
                    if extends not in self.inheritance_graph:
                        self.inheritance_graph[extends] = []
                    self.inheritance_graph[extends].append(field_type_name)
            
            return True
            
        except Exception as e:
            logging.error(f"Error parsing meta meta model: {e}")
            return False
    
    def get_field_type_definition(self, field_type: str) -> Optional[Dict[str, Any]]:
        """获取字段类型定义"""
        # 如果字段类型不是基础类型，沿着继承链查找基类定义
        while field_type in self.inheritance_graph:
            if field_type in self.field_types:
                return self.field_types[field_type]
            # 找到继承链的基类
            extends = self.field_types.get(field_type, {}).get('extends')
            if extends:
                field_type = extends
            else:
                break
        
        return self.field_types.get(field_type)
    
    def get_all_inherited_properties(self, field_type: str) -> Dict[str, Dict[str, Any]]:
        """获取字段类型及其所有继承的属性定义"""
        properties = {}
        visited = set()
        
        def _collect_properties(ft: str):
            if ft in visited:
                return
            visited.add(ft)
            
            field_def = self.get_field_type_definition(ft)
            if field_def and 'infos' in field_def:
                for prop in field_def['infos']:
                    properties[prop['name']] = prop
            
            # 递归收集父类属性
            extends = self.field_types.get(ft, {}).get('extends')
            if extends:
                _collect_properties(extends)
        
        _collect_properties(field_type)
        return properties


class ReferenceResolver:
    """引用解析器"""
    
    def __init__(self):
        self.cache: Dict[str, Any] = {}
        self.resolved_references: Dict[str, bool] = {}

    @staticmethod
    def _get_mapped_field_type(self, field_type: str) -> str:
        """映射字段类型"""
        type_mapping = {
            'ComplexField': 'ComplexType',
            'StringField': 'StringField',
            'IntegerField': 'IntegerField',
            'BooleanField': 'BooleanField',
            'ArrayField': 'ArrayField',
            'IdField': 'IdField',
            'EnumField': 'EnumField',
            'ReferenceField': 'ReferenceField'
        }
        return type_mapping.get(field_type, field_type)

    def resolve_reference(self, current_file: str, ref_value: Any,
                      file_cache: Dict[str, Dict[str, Any]],
                      meta_model_dir: str) -> Any:
        """在内存中解析引用，展开引用内容"""
        if isinstance(ref_value, str) and ref_value.startswith('$ref:'):
            ref_path = ref_value.replace('$ref:', '').strip().strip('"\'')
            return self._resolve_ref_path(current_file, ref_path, file_cache, meta_model_dir)
        elif isinstance(ref_value, str) and ref_value.startswith('#/components/'):
            # 处理简化的引用格式
            ref_path = ref_value
            return self._resolve_ref_path(current_file, ref_path, file_cache, meta_model_dir)
        return None
    
    def _resolve_ref_path(self, current_file: str, ref_path: str,
                      file_cache: Dict[str, Dict[str, Any]],
                      meta_model_dir: str) -> Any:
        """根据引用路径解析引用"""
        # 处理同文件引用
        if ref_path.startswith('#/'):
            return self._resolve_local_ref(current_file, ref_path[2:], file_cache)
        
        # 处理跨文件引用
        if '/' in ref_path and not ref_path.startswith('#/'):
            return self._resolve_cross_file_ref(current_file, ref_path, file_cache, meta_model_dir)
        
        return None
    
    def _resolve_local_ref(self, file_path: str, ref_path: str, file_cache: Dict[str, Dict[str, Any]]) -> Any:
        """解析本地引用（同文件内）"""
        file_key = file_path
        if file_key not in file_cache:
            return None
            
        data = file_cache[file_key]
        parts = ref_path.split('/')
        
        current = data
        for part in parts:
            if isinstance(current, dict) and part in current:
                current = current[part]
            elif isinstance(current, list) and part.isdigit():
                current = current[int(part)]
            else:
                return None
        
        # 如果是组件定义，将其转换为字段定义格式
        if isinstance(current, dict) and 'type' in current:
            return self._convert_component_to_field(current, resolve_inner_refs=False)
        
        return current
    
    def _resolve_cross_file_ref(self, current_file: str, ref_path: str,
                           file_cache: Dict[str, Dict[str, Any]],
                           meta_model_dir: str) -> Any:
        """解析跨文件引用"""
        if '/' not in ref_path:
            return None
        
        file_part, ref_part = ref_path.split('/', 1)
        
        # 1. 首先尝试同目录下的文件
        resolved = self._try_resolve_in_current_dir(current_file, file_part, ref_part, file_cache)
        if resolved:
            return resolved
        
        # 2. 在整个元模型目录下查找
        return self._try_resolve_in_meta_model_dir(meta_model_dir, file_part, ref_part, file_cache)
    
    def _try_resolve_in_current_dir(self, current_file: str, file_part: str,
                               ref_part: str, file_cache: Dict[str, Dict[str, Any]]) -> Any:
        """尝试在同目录中解析引用"""
        current_dir = os.path.dirname(current_file)
        target_files = [current_dir + '/' + file_part + '.yaml', current_dir + '/' + file_part + '.yml']
        
        for target in target_files:
            if target in file_cache:
                resolved = self._resolve_local_ref(target, ref_part, file_cache)
                if resolved:
                    return resolved
        return None
    
    def _try_resolve_in_meta_model_dir(self, meta_model_dir: str, file_part: str,
                                  ref_part: str, file_cache: Dict[str, Dict[str, Any]]) -> Any:
        """在整个元模型目录中解析引用"""
        valid_filenames = [file_part + '.yaml', file_part + '.yml']
        
        for root, dirs, files in os.walk(meta_model_dir):
            for filename in files:
                if filename in valid_filenames:
                    target_path = os.path.join(root, filename)
                    if target_path in file_cache:
                        resolved = self._resolve_local_ref(target_path, ref_part, file_cache)
                        if resolved:
                            return resolved
        return None
    
    def _handle_array_items_property(self, value: Dict[str, Any], properties: Dict[str, Any]):
        """处理数组items属性"""
        if isinstance(value, dict) and 'type' in value:
            if '$ref' in value:
                # 这里需要回传给文件解析器处理
                properties['items'] = value
            else:
                properties['items'] = self._convert_component_to_field(value)
    
    def _process_component_properties(self, component_data: Dict[str, Any], resolve_inner_refs: bool) -> Dict[str, Any]:
        """处理组件属性"""
        properties = {}
        
        if resolve_inner_refs:
            for key, value in component_data.items():
                if key == 'type':
                    continue
                if key == 'items':
                    self._handle_array_items_property(value, properties)
                else:
                    properties[key] = value
        else:
            # 直接转换属性
            properties = component_data.copy()
            properties.pop('type', None)
        
        return properties
    
    def _convert_component_to_field(self, component_data: Dict[str, Any],
                               resolve_inner_refs: bool = True) -> FieldDefinition:
        """将组件定义转换为字段定义格式"""
        field_type = self._get_mapped_field_type(component_data.get('type'))
        properties = self._process_component_properties(component_data, resolve_inner_refs)
        
        return FieldDefinition(
            name="component_field",
            field_type=field_type,
            properties=properties
        )


class MetaModelParser:
    """元模型解析器"""
    
    def __init__(self, meta_meta_model: MetaMetaModelParser, meta_model_dir: str):
        self.meta_meta_model = meta_meta_model
        self.reference_resolver = ReferenceResolver()
        self.file_cache: Dict[str, Dict[str, Any]] = {}
        self.meta_model_dir = meta_model_dir
    
    def parse_file(self, file_path: str) -> List[MetaModelDefinition]:
        """解析元模型文件"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 缓存文件内容以支持跨文件引用
            self.file_cache[file_path] = yaml.safe_load(content)
            
            # 解析模型定义
            data = self.file_cache[file_path]
            models = []
            
            if 'models' in data:
                for model_data in data['models']:
                    model = self._parse_model_definition(model_data, file_path)
                    models.append(model)
            
            return models
            
        except Exception as e:
            logging.error(f"Error parsing meta model file {file_path}: {e}")
            return []
    
    def parse_component(self, file_path: str, component_name: str) -> Dict[str, Any]:
        """解析组件引用（保留兼容性）"""
        key = f"{file_path}#{component_name}"
        
        if key in self.reference_resolver.cache:
            return self.reference_resolver.cache[key]
        
        try:
            if file_path not in self.file_cache:
                with open(file_path, 'r', encoding='utf-8') as f:
                    self.file_cache[file_path] = yaml.safe_load(f.read())
            
            data = self.file_cache[file_path]
            
            if 'components' in data and component_name in data['components']:
                component_data = data['components'][component_name]
                self.reference_resolver.cache[key] = component_data
                return component_data
            else:
                return {}
                
        except Exception as e:
            logging.error(f"Error parsing component {component_name} from {file_path}: {e}")
            return {}

    def _parse_model_definition(self, model_data: Dict[str, Any], file_path: str) -> MetaModelDefinition:
        """解析单个元模型定义"""
        model_type = model_data.get('modelType')
        version = model_data.get('version', '1.0.0')
        description = model_data.get('description', '')
        extends = model_data.get('extends')

        fields = []
        if 'fields' in model_data:
            for field_data in model_data['fields']:
                field_def = self._parse_field_definition(field_data, file_path)
                fields.append(field_def)

        return MetaModelDefinition(
            model_type=model_type,
            version=version,
            description=description,
            extends=extends,
            fields=fields
        )

    def _check_field_properties(self, field_data: Dict[str, Any], file_path: str):
        """检查字段属性，在解析阶段发现问题"""
        if not hasattr(self, 'errors'):
            self.errors = []

        name = field_data.get('name')
        field_type = field_data.get('type')

        if field_type:
            field_type_def = self.meta_meta_model.get_field_type_definition(field_type)
            if field_type_def:
                self._check_unsupported_properties(field_data, field_type, field_type_def,
                                                 name, file_path)

            self._check_stringfield_example(field_data, name, file_path)

    def _check_unsupported_properties(self, field_data: Dict[str, Any], field_type: str,
                                    field_type_def: Dict[str, Any], name: str, file_path: str):
        """检查不支持的属性"""
        valid_properties = set(field_type_def.get('properties', {}).keys())
        current_properties = set(field_data.keys()) - {'name', 'type', '$ref'}

        for prop in current_properties:
            if prop not in valid_properties:
                self.errors.append(ValidationError(
                    severity=ValidationSeverity.ERROR,
                    file=file_path,
                    message=f"Unsupported property '{prop}' for field type '{field_type}'",
                    field_path=f"{name}.{prop}" if name else f"model.fields.{name}.{prop}"
                ))

    def _check_stringfield_example(self, field_data: Dict[str, Any], name: str, file_path: str):
        """检查StringField的example类型"""
        field_type = field_data.get('type')
        if field_type == 'StringField' and 'example' in field_data:
            example_value = field_data['example']
            if not isinstance(example_value, str):
                self.errors.append(ValidationError(
                    severity=ValidationSeverity.ERROR,
                    file=file_path,
                    message=f"Expected string, got {type(example_value).__name__}",
                    field_path=f"{name}.example" if name else f"model.fields.{name}.example"
                ))

    def _parse_field_definition(self, field_data: Dict[str, Any], file_path: str) -> FieldDefinition:
        """解析字段定义，包括引用展开"""
        name = field_data.get('name')
        field_type = field_data.get('type')

        # 首先检查原始字段的错误（避免使用$ref时这些信息丢失）
        self._check_field_properties(field_data, file_path)

        # 处理 $ref 引用
        if '$ref' in field_data:
            ref_value = field_data['$ref']
            resolved_field = self.reference_resolver.resolve_reference(
                    file_path, ref_value, self.file_cache, self.meta_model_dir)

            if resolved_field:
                # 如果是引用的字段，需要修改字段名以匹配原始字段名
                if '.' in resolved_field.name:
                    resolved_field = FieldDefinition(
                        name=name,
                        field_type=resolved_field.field_type,
                        properties=resolved_field.properties
                    )

                # 合并原始数据中的其他属性
                resolve_properties = {k: v for k, v in field_data.items() if k not in ['$ref', 'name']}
                merged_properties = {**resolved_field.properties, **resolve_properties}

                return FieldDefinition(
                    name=name,
                    field_type=resolved_field.field_type,
                    properties=merged_properties
                )
            else:
                # 如果解析失败，回退到直接定义而不指定类型
                field_type = None
        else:
            # 普通字段定义
            field_type = field_data.get('type')

        properties = {k: v for k, v in field_data.items() if k not in ['name', 'type', '$ref']}

        return FieldDefinition(
            name=name,
            field_type=field_type,
            properties=properties
        )

class MetaModelValidator:
    """元模型验证器"""
    
    def __init__(self, meta_meta_model: MetaMetaModelParser, meta_model_dir: str = None):
        self.meta_meta_model = meta_meta_model
        self.errors: List[ValidationError] = []
        self.meta_model_dir = meta_model_dir
        self.parser = MetaModelParser(meta_meta_model, meta_model_dir) if meta_model_dir else None
    
    @staticmethod
    def _collect_meta_model_files(file_paths: List[str], meta_model_dir: str) -> List[str]:
        """收集所有相关的元模型文件"""
        if file_paths:
            return file_paths.copy()
        
        all_meta_model_files = []
        for root, dirs, files in os.walk(meta_model_dir):
            for file in files:
                if file.endswith(('.yml', '.yaml')):
                    file_path = os.path.join(root, file)
                    all_meta_model_files.append(file_path)
        return all_meta_model_files

    @staticmethod
    def _get_models_from_file(file_path: str, all_models: List) -> List:
        """从解析的模型中获取属于特定文件的模型"""
        file_models = []
        for model in all_models:
            if MetaModelValidator._is_model_from_file(model, file_path):
                file_models.append(model)
        return file_models

    @staticmethod
    def _validate_number_property(field: FieldDefinition, prop_name: str,
                                 prop_value: Union[int, float], prop_def: Dict[str, Any], file_path: str):
        """验证数字类型属性"""
        MetaModelValidator._validate_range_property(field, prop_name, prop_value, prop_def, file_path, "number")

    @staticmethod
    def _is_model_from_file(self, model, file_path: str) -> bool:
        """检查模型是否来自特定文件"""
        is_source_match = hasattr(model, 'source_file') and model.source_file == file_path
        is_type_match = model.model_type + '.yaml' == os.path.basename(file_path)
        is_basematch = model.model_type == os.path.splitext(os.path.basename(file_path))[0]

        return is_source_match or is_type_match or is_basematch

    @staticmethod
    def _validate_type(self, value: Any, expected_type: str) -> Optional[str]:
        """验证类型"""
        if expected_type is None:
            return None

        type_mapping = {
            'string': str,
            'integer': int,
            'number': (int, float),
            'boolean': bool,
            'array': list
        }

        actual_type = type(value)
        expected_python_type = type_mapping.get(expected_type)

        if expected_python_type is not None:
            if not isinstance(value, expected_python_type):
                return f"Expected {expected_type}, got {actual_type.__name__}"

        return None

    def validate_meta_model_files(self, file_paths: List[str], meta_model_dir: str) -> List[ValidationError]:
        """验证多个元模型文件（支持跨文件引用）"""
        original_errors = getattr(self, 'errors', None)
        self.errors = []

        all_meta_model_files = MetaModelValidator._collect_meta_model_files(file_paths, meta_model_dir)
        all_models = self._parse_all_files(all_meta_model_files, meta_model_dir)

        self._validate_specified_files(file_paths, all_models)

        all_errors = self.errors
        if original_errors:
            all_errors = original_errors + all_errors

        return all_errors

    def validate_meta_model_file(self, file_path: str) -> List[ValidationError]:
        """验证单个元模型文件（保持兼容性）"""
        return self.validate_meta_model_files([file_path], os.path.dirname(file_path))

    def _parse_all_files(self, all_meta_model_files: List[str], meta_model_dir: str) -> List:
        """解析所有元模型文件，建立文件缓存"""
        self.parser = MetaModelParser(self.meta_meta_model, meta_model_dir)
        self.parser.errors = []
        
        all_models = []
        for file_path in all_meta_model_files:
            models = self.parser.parse_file(file_path)
            all_models.extend(models)
        
        # 收集解析时的错误
        parse_errors = self.parser.errors if hasattr(self.parser, 'errors') else []
        self.errors = parse_errors + self.errors
        
        return all_models
    
    def _validate_specified_files(self, file_paths: List[str], all_models: List):
        """验证指定的文件路径是否解析成功"""
        for file_path in file_paths:
            file_models = MetaModelValidator._get_models_from_file(file_path, all_models)
            for model in file_models:
                self._validate_model_definition(model, os.path.relpath(model.model_type + '.yaml'))

    def _validate_model_definition(self, model: MetaModelDefinition, file_path: str):
        """验证元模型定义"""
        # 验证继承关系
        if model.extends:
            self._validate_inheritance(model, file_path)
        
        # 验证字段定义
        for field in model.fields:
            self._validate_field_definition(field, model, file_path)
    
    def _validate_inheritance(self, model: MetaModelDefinition, file_path: str):
        """验证继承关系"""
        # 检查父模型是否存在
        # 这里需要实现一个查找机制，由于时间限制，暂时跳过
        pass
    
    def _validate_field_definition(self, field: FieldDefinition, model: MetaModelDefinition, file_path: str):
        """验证字段定义"""
        # 检查字段类型是否在元元模型中定义
        field_type_def = self.meta_meta_model.get_field_type_definition(field.field_type)
        if not field_type_def:
            self.errors.append(ValidationError(
                severity=ValidationSeverity.ERROR,
                file=file_path,
                message=f"Unknown field type '{field.field_type}'",
                field_path=f"{model.model_type}.fields.{field.name}"
            ))
            return
        
        # 获取该字段类型支持的所有属性
        supported_properties = self.meta_meta_model.get_all_inherited_properties(field.field_type)
        
        # 检查每个属性是否合法
        for prop_name, prop_value in field.properties.items():
            if prop_name not in supported_properties:
                self.errors.append(ValidationError(
                    severity=ValidationSeverity.ERROR,
                    file=file_path,
                    message=f"Unsupported property '{prop_name}' for field type '{field.field_type}'",
                    field_path=f"{model.model_type}.fields.{field.name}"
                ))
                continue
            
            # 验证属性值
            self._validate_property(field, prop_name, prop_value, supported_properties, file_path)
    
    def _validate_property(self, field: FieldDefinition, prop_name: str, prop_value: Any, 
                          supported_properties: Dict[str, Dict[str, Any]], file_path: str):
        """验证属性值"""
        prop_def = supported_properties[prop_name]
        expected_type = prop_def.get('type')
        
        # 类型验证
        type_error = self._validate_type(prop_value, expected_type)
        if type_error:
            self.errors.append(ValidationError(
                severity=ValidationSeverity.ERROR,
                file=file_path,
                message=type_error,
                field_path=f"{field.name}.{prop_name}"
            ))
            return
        
        # 特定类型的验证
        if expected_type == 'string':
            self._validate_string_property(field, prop_name, prop_value, prop_def, file_path)
        elif expected_type == 'integer':
            self._validate_integer_property(field, prop_name, prop_value, prop_def, file_path)
        elif expected_type == 'number':
            MetaModelValidator._validate_number_property(field, prop_name, prop_value, prop_def, file_path)
        elif expected_type == 'boolean':
            self._validate_boolean_property(field, prop_name, prop_value, prop_def, file_path)
        elif expected_type == 'array':
            self._validate_array_property(field, prop_name, prop_value, prop_def, file_path)
        elif expected_type == 'enum':
            self._validate_enum_property(field, prop_name, prop_value, prop_def, file_path)
    
    def _validate_string_property(self, field: FieldDefinition, prop_name: str, 
                                 prop_value: str, prop_def: Dict[str, Any], file_path: str):
        """验证字符串类型属性"""
        # 验证正则表达式
        pattern = prop_def.get('pattern')
        if pattern and isinstance(prop_value, str):
            if not re.match(pattern, prop_value):
                self.errors.append(ValidationError(
                    severity=ValidationSeverity.ERROR,
                    file=file_path,
                    message=f"Property '{prop_name}' value '{prop_value}' does not match pattern '{pattern}'",
                    field_path=f"{field.name}.{prop_name}"
                ))
        
        # 验证最大长度
        if prop_def.get('maxLength') and isinstance(prop_value, str):
            if len(prop_value) > prop_def['maxLength']:
                self.errors.append(ValidationError(
                    severity=ValidationSeverity.ERROR,
                    file=file_path,
                    message=f"Property '{prop_name}' value exceeds maximum length "
                      f"{prop_def['maxLength']}",
                    field_path=f"{field.name}.{prop_name}"
                ))
        
        # 验证最小长度
        if prop_def.get('minLength') and isinstance(prop_value, str):
            if len(prop_value) < prop_def['minLength']:
                self.errors.append(ValidationError(
                    severity=ValidationSeverity.ERROR,
                    file=file_path,
                    message=f"Property '{prop_name}' value is shorter than minimum length "
                      f"{prop_def['minLength']}",
                    field_path=f"{field.name}.{prop_name}"
                ))
    
    def _validate_range_property(self, field: FieldDefinition, prop_name: str, 
                            prop_value: Union[int, float], prop_def: Dict[str, Any], 
                            file_path: str, property_type: str):
        """验证范围属性（用于整数和数字类型）"""
        prop_value_num = float(prop_value)
        
        # 验证最小值
        if prop_def.get('minimum') is not None:
            if prop_value_num < prop_def['minimum']:
                self.errors.append(ValidationError(
                    severity=ValidationSeverity.ERROR,
                    file=file_path,
                    message=(f"Property '{prop_name}' value {property_type} "
                      f"{prop_value_num} is less than minimum {prop_def['minimum']}"),
                    field_path=f"{field.name}.{prop_name}"
                ))
        
        # 验证最大值
        if prop_def.get('maximum') is not None:
            if prop_value_num > prop_def['maximum']:
                self.errors.append(ValidationError(
                    severity=ValidationSeverity.ERROR,
                    file=file_path,
                    message=(f"Property '{prop_name}' value {property_type} "
                      f"{prop_value_num} is greater than maximum {prop_def['maximum']}"),
                    field_path=f"{field.name}.{prop_name}"
                ))
    
    def _validate_integer_property(self, field: FieldDefinition, prop_name: str, 
                                  prop_value: int, prop_def: Dict[str, Any], file_path: str):
        """验证整数类型属性"""
        self._validate_range_property(field, prop_name, prop_value, prop_def, file_path, "integer")
    
    def _validate_boolean_property(self, field: FieldDefinition, prop_name: str, 
                                  prop_value: bool, prop_def: Dict[str, Any], file_path: str):
        """验证布尔类型属性"""
        pass
    
    def _validate_array_property(self, field: FieldDefinition, prop_name: str, 
                                prop_value: List[Any], prop_def: Dict[str, Any], file_path: str):
        """验证数组类型属性"""
        # 验证最小元素数
        if prop_def.get('minItems') is not None:
            if len(prop_value) < prop_def['minItems']:
                self.errors.append(ValidationError(
                    severity=ValidationSeverity.ERROR,
                    file=file_path,
                    message=(f"Property '{prop_name}' array has {len(prop_value)} elements, "
                      f"less than minimum {prop_def['minItems']}"),
                    field_path=f"{field.name}.{prop_name}"
                ))
        
        # 验证最大元素数
        if prop_def.get('maxItems') is not None:
            if len(prop_value) > prop_def['maxItems']:
                self.errors.append(ValidationError(
                    severity=ValidationSeverity.ERROR,
                    file=file_path,
                    message=(f"Property '{prop_name}' array has {len(prop_value)} elements, "
                      f"more than maximum {prop_def['maxItems']}"),
                    field_path=f"{field.name}.{prop_name}"
                ))
    
    def _validate_enum_property(self, field: FieldDefinition, prop_name: str, 
                               prop_value: Any, prop_def: Dict[str, Any], file_path: str):
        """验证枚举类型属性"""
        enum_values = prop_def.get('enum', [])
        if prop_value not in enum_values:
            self.errors.append(ValidationError(
                severity=ValidationSeverity.ERROR,
                file=file_path,
                message=f"Property '{prop_name}' value '{prop_value}' is not in allowed enum values: {enum_values}",
                field_path=f"{field.name}.{prop_name}"
            ))


def parse_arguments():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(description='元模型验证工具')
    parser.add_argument('--meta-model-dir', required=True, help='元模型目录')
    parser.add_argument('--meta-meta-model', required=True, help='元元模型文件路径')
    parser.add_argument('--output-format', choices=['text', 'json'], default='test', 
                       help='输出格式')
    parser.add_argument('--strict-level', choices=['error', 'warning', 'info'], 
                       default='error', help='严格程度')
    parser.add_argument('--test-mode', action='store_true', 
                       help='测试模式：只验证测试数据目录')
    return parser.parse_args()


def validate_file_paths(args):
    """验证文件路径是否存在"""
    if not os.path.exists(args.meta_meta_model):
        logging.error(f"Error: Meta meta model file not found: {args.meta_meta_model}")
        sys.exit(1)
    
    if not os.path.exists(args.meta_model_dir):
        logging.error(f"Error: Meta model directory not found: {args.meta_model_dir}")
        sys.exit(1)


def setup_test_mode(args):
    """设置测试模式"""
    if not args.test_mode:
        return
    
    # 如果当前目录下有test_data目录，使用它
    current_test_data_dir = os.path.join(os.path.dirname(args.meta_model_dir), 'test', 
                                       'test_data')
    # 或者如果传入了的meta_model_dir下有test_data子目录
    test_data_dir = os.path.join(args.meta_model_dir, 'test_data')
    
    # 优先使用当前目录下的test_data目录，这对于从test目录运行的情况
    if os.path.exists('./test_data'):
        args.meta_model_dir = './test_data'
    elif os.path.exists(current_test_data_dir):
        args.meta_model_dir = current_test_data_dir
    elif os.path.exists(test_data_dir):
        args.meta_model_dir = test_data_dir
    else:
        logging.error(f"测试数据目录不存在")
        logging.error("应该在测试数据目录下创建包含错误的测试文件")
        sys.exit(1)
    
    # 设置测试特定的输出格式
    if args.output_format == 'test':
        args.output_format = 'text'


def find_meta_model_files(meta_model_dir):
    """查找所有元模型文件"""
    meta_model_files = []
    for root, dirs, files in os.walk(meta_model_dir):
        for file in files:
            if file.endswith(('.yml', '.yaml')):
                file_path = os.path.join(root, file)
                meta_model_files.append(file_path)
    return meta_model_files


def main():
    """主函数"""
    args = parse_arguments()
    
    # 验证文件路径
    validate_file_paths(args)
    
    # 处理测试模式
    setup_test_mode(args)
    
    # 解析元元模型
    meta_meta_model_parser = MetaMetaModelParser()
    if not meta_meta_model_parser.parse(args.meta_meta_model):
        logging.error(f"Error: Failed to parse meta meta model: {args.meta_meta_model}")
        sys.exit(1)
    
    # 执行验证
    validator = MetaModelValidator(meta_meta_model_parser)
    
    # 查找所有元模型文件
    meta_model_files = find_meta_model_files(args.meta_model_dir)
    
    # 验证所有元模型文件（支持跨文件引用展开）
    all_errors = validator.validate_meta_model_files(meta_model_files, args.meta_model_dir)
    
    # 输出结果
    if args.output_format == 'json':
        output = [error.to_dict() for error in all_errors]
        try:
            logging.error(json.dumps(output, indent=2, ensure_ascii=False))
        except UnicodeError:
            # 如果UTF-8输出有问题，尝试简单的JSON输出
            logging.error(json.dumps(output, indent=2, ensure_ascii=True))
    else:
        for error in all_errors:
            logging.error(f"[{error.severity.name}] {error.file}: {error.message}")
            if error.field_path:
                logging.error(f"  Field: {error.field_path}")
            logging.error()
    
    # 设置退出码
    if any(error.severity == ValidationSeverity.ERROR for error in all_errors):
        sys.exit(1)
    else:
        sys.exit(0)


if __name__ == '__main__':
    main()