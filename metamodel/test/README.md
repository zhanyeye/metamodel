# 元模型验证工具

## 目录结构

```
metamodel/
├── app/              # 真实元模型
├── atomic/
├── base_cfg/
├── collector/
├── comm/
├── compute/
├── pub_def/
├── storage/
└── test/                    # 验证工具目录
    ├── metamodel_validator.py     # 主验证脚本
    ├── metamodel_validator_script_documentation.md  # 详细文档
    ├── README.md                  # 本说明文档
    └── test_data/               # 专门用于测试验证脚本的错误数据
        ├── test_inheritance_errors.yaml
        ├── test_reference_errors.yaml
        └── simple_test_errors.yaml
```

## 使用方法

### 测试模式 - 验证错误检测功能
```bash
cd metamodel/test
python metamodel_validator.py \
  --test-mode \
  --meta-meta-model metametamodel/metametamodel.yml \
  --meta-model-dir ../ \
  --output-format text
```

或使用JSON格式：
```bash
cd metamodel/test
python metamodel_validator.py \
  --test-mode \
  --meta-meta-model metametamodel/metametamodel.yml \
  --meta-model-dir ../ \
  --output-format json
```

### 正常模式 - 验证真实元模型
```bash
python test/metamodel_validator.py \
  --meta-meta-model metametamodel/metametamodel.yml \
  --meta-model-dir path/to/meta_models \
  --output-format text
```

## 测试数据说明

`test/test_data/` 目录包含专门设计的测试文件，用于验证脚本的错误检测能力：

- `test_inheritance_errors.yaml` - 继承相关错误
- `test_reference_errors.yaml` - 引用相关错误  
- `simple_test_errors.yaml` - 基础字段类型错误

## 注意事项

1. 元元模型文件应该从外部传入，不给内嵌副本
2. 测试数据与真实元模型分离
3. 所有错误案例都有详细的注释说明
