#!/usr/bin/env python3
"""
调试验证脚本，找出 simple_test_errors.yaml 错误丢失的原因
"""

import os
import sys
import metamodel_validator as mv

# 创建元元模型解析器
meta_meta_model = mv.MetaMetaModelParser()
result = meta_meta_model.parse('../test_data/metametamodel.yml')
print(f"元元模型解析成功: {result}")

if result:
    # 创建验证器
    validator = mv.MetaModelValidator(meta_meta_model)
    
    # 测试1: 模拟脚本调用的方式（只验证特定文件）
    print("\n=== 测试1: 模拟脚本调用方式 ===")
    
    # 获取所有元模型文件
    meta_model_files = []
    for root, dirs, files in os.walk(TEST_DATA_DIR):
        for file in files:
            if file.endswith(('.yml', '.yaml')):
                file_path = os.path.join(root, file)
                meta_model_files.append(file_path)
    
    print(f"找到 {len(meta_model_files)} 个文件")
    
    # 只验证继承和引用错误文件（模拟脚本当前行为）
    target_files = [
        os.path.join(TEST_DATA_DIR, 'test_inheritance_errors.yaml'),
        os.path.join(TEST_DATA_DIR, 'test_reference_errors.yaml')
    ]
    
    # 注意：test_data/simple_test_errors.yaml 不在 target_files 中！
    errors1 = validator.validate_meta_model_files(target_files, TEST_DATA_DIR)
    print(f"验证指定文件后找到 {len(errors1)} 个错误")
    
    # 测试2: 包含 simple_test_errors.yaml
    print("\n=== 测试2: 包含 simple_test_errors.yaml ===")
    target_files2 = target_files + [
        os.path.join(TEST_DATA_DIR, 'simple_test_errors.yaml')]
    
    errors2 = validator.validate_meta_model_files(target_files2, TEST_DATA_DIR)
    print(f"验证包含 simple_test_errors.yaml 的文件后找到 {len(errors2)} 个错误")
    
    # 测试3: 验证所有文件
    print("\n=== 测试3: 验证所有文件 ===")
    errors3 = validator.validate_meta_model_files(meta_model_files, TEST_DATA_DIR)
    print(f"验证所有文件后找到 {len(errors3)} 个错误")
    
    # 比较差异
    print("\n=== 错误计数对比 ===")
    print(f"只验证继承/引用文件: {len(errors1)} 个错误")
    print(f"+ simple_test_errors.yaml: {len(errors2)} 个错误") 
    print(f"+ 所有文件: {len(errors3)} 个错误")
    print(f"单独 simple_test_errors.yaml 的错误数: {len(errors2) - len(errors1)}")
    
    # 输出 simple_test_errors.yaml 的具体错误
    if len(errors2) > len(errors1):
        print("\n=== simple_test_errors.yaml 的错误 ===")
        for error in errors2[len(errors1):]:
            print(f"[{error.severity.name}] {error.file}: {error.message}")
            if error.field_path:
                print(f"  Field: {error.field_path}")