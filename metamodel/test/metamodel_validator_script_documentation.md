# 元模型验证脚本更新文档

## 概述
本文档记录了用于更新和维护元模型验证脚本所需的关键信息。如果当前会话被清理，需要提供以下信息才能正确更新脚本。

## 基本概念

### 什么是元数据（Metadata）？
元数据是"关于数据的数据"，描述数据的基本信息。例如：
- 文件属性：创建时间、文件大小
- 数据库表结构：字段名、数据类型、约束
- API接口定义：请求参数、响应格式

### 什么是元模型（Metamodel）？
元模型是"描述模型的模型"，定义了如何构建和描述业务模型。在这个项目中：

#### 元模型的作用：
- 定义各种计算任务、存储表、消息队列等业务实体的"数据结构模板"
- 规定每个实体应该包含哪些字段、字段类型、约束条件
- 提供统一的数据建模规范

#### 元模型示例：FlinkSQLJob
```yaml
models:
  - modelType: "FlinkSQLJob"
    extends: "ComputeNode"
    fields:
      - name: id
        type: IdField
        required: true
        generated: true
      
      - name: name  
        type: StringField
        required: true
        pattern: "^[a-zA-Z0-9_-]+$"
        unique: true
      
      - name: description
        type: StringField
        maxLength: 500
        required: false
      
      - name: inputs
        type: ArrayField
        required: true
        minItems: 1
        # 引用定义在其他文件中的输入组件
        $ref: "#/components/inputs"
```

### 什么是元元模型（Metametamodel）？
元元模型是"描述元模型的模型"，定义了元模型本身的构建规则。

#### 元元模型的作用：
- 定义元模型中可以使用的字段类型（如 StringField、IntegerField 等）
- 规定每种字段类型支持的属性
- 定义验证规则和约束条件

#### 元元模型示例：StringField 定义
```yaml
fieldTypes:
  StringField:
    properties:
      type:
        type: string
        required: true
        enum: ["StringField"]
      
      name:
        type: string  
        required: true
        
      description:
        type: string
        required: false
        maxLength: 500
        
      required:
        type: boolean
        required: false
        default: false
        
      maxLength:
        type: integer
        required: false
        minimum: 1
        
      pattern:
        type: string
        required: false
        description: "正则表达式验证模式"
        
      example:
        type: string  
        required: false
        description: "示例值"
```

### 两者的关系：三层架构

```
┌─────────────────────────────┐
│     实例数据 (Instance)      │  ← 实际的业务数据
├─────────────────────────────┤
│     元模型 (Metamodel)       │  ← 数据结构定义 (flink_sql_job.yaml)
├─────────────────────────────┤  
│     元元模型 (Metametamodel) │  ← 类型系统定义 (metametamodel.yml)
└─────────────────────────────┘
```

**实例应用：**
```
实际业务数据：
{
  "id": "flink_001",
  "name": "daily-stats", 
  "description": "每日统计任务"
}

对应的是元模型定义的字段类型和约束
```

## 脚本检查的具体项目

脚本会执行以下验证检查：

### 1. 字段类型验证
**检查内容**：字段类型是否在元元模型中定义
- ✅ `type: StringField` - 字符串字段（有效）
- ❌ `type: UnknownField` - 未知字段类型（报错）
- ✅ `type: IdField` - ID字段继承自BaseField（有效）

### 2. 字段属性验证
**检查内容**：字段属性是否符合类型定义
- ✅ `StringField.required: boolean` - 布尔值（有效）
- ❌ `StringField.required: "true"` - 字符串（报错，类型不符）
- ✅ `StringField.maxLength: 500` - 整数（有效）
- ❌ `StringField.maxLength: "500"` - 字符串（报错，类型不符）
- ❌ `StringField.customProperty: value` - 未定义属性（报错）
- ✅ `StringField.example: "test"` - 字符串示例值（有效）
- ❌ `StringField.example: 123` - 非字符串示例值（报错）

### 3. 必填字段验证  
**检查内容**：必填字段是否缺失（注意继承场景）
- ✅ 父模型定义的必填字段在子模型中存在（有效）
- ❌ 父模型定义的必填字段在子模型中缺失（报错）

**示例场景**：
```yaml
# ComputeNode 父模型
models:
  - modelType: ComputeNode
    fields:
      - name: name
        type: StringField
        required: true
      
      - name: inputs  
        type: ArrayField
        required: true  # 是必填字段

# FlinkSQLJob 子模型  
models:
  - modelType: FlinkSQLJob
    extends: ComputeNode
    fields:
      - name: name
        type: StringField
        required: true
      # ❌ 缺失了必填的 inputs 字段（报错）
```

### 4. 引用格式验证
**检查内容**：`$ref` 引用格式是否正确
- ✅ `$ref: "#/components/inputs"` - 本地引用（有效）
- ✅ `$ref: "other_file.yaml#/components/inputs"` - 跨文件引用（有效）
- ❌ `$ref: "invalid_reference"` - 无法解析的引用（报错）

### 5. 数值范围验证
**检查内容**：数值类型的范围约束
- ✅ `minimum: 1, maximum: 100` - 在范围内（有效）
- ❌ `minimum: 1, value: 0` - 小于最小值（报错）
- ✅ `minItems: 1, maxItems: 50` - 数组长度在范围内（有效）
- ❌ `minItems: 1, array: []` - 数组为空违反最小长度（报错）

### 6. 正则表达式验证
**检查内容**：字符串类型的模式匹配
- ✅ `pattern: "^[a-zA-Z0-9_-]+$"`, value: "valid-name"` - 匹配模式（有效）
- ❌ `pattern: "^[a-zA-Z0-9_-]+$"`, value: "invalid@name"` - 不匹配模式（报错）

### 7. 枚举值验证
**检查内容**：字段值是否在允许的枚举范围内
- ✅ `enum: ["online", "offline"]`, value: "online"` - 在枚举中（有效）
- ❌ `enum: ["online", "offline"]`, value: "unknown"` - 不在枚举中（报错）

### 8. 继承关系验证
**检查内容**：模型继承关系的正确性
- ✅ `extends: "ComputeNode"` - 继承自已定义的模型（有效）
- ❌ `extends: "NonExistentModel"` - 继承不存在的模型（报错）

### 9. 特殊处理验证
**检查内容**：专门字段的特殊逻辑
- **IdField**: 验证 `generated: true` 和 `template` 属性
- **ReferenceField**: 验证 `refModelAllowed` 引用模型是否存在
- **ComplexType**: 验证内部 `fields` 结构的完整性
- **ArrayField**: 验证 `items` 字段的类型定义

### 10. 引用展开验证  
**检查内容**：引用展开后的字段定义是否有效
- ✅ 引用成功展开，字段属性正确（有效）
- ❌ 引用解析失败，字段类型为None（报错）
- ✅ 引用成功，并正确合并了原始属性（有效）
- ❌ 引用导致属性冲突或覆盖错误（报错）

## 核心架构信息

### 1. 元模型验证流程
1. **解析阶段**：读取并解析所有元模型文件（YAML格式）
2. **引用展开**：在内存中解析和展开 `$ref` 引用
3. **类型检查**：基于元元模型定义验证字段类型
4. **属性验证**：检查字段属性是否被支持
5. **继承验证**：验证模型继承关系和必填字段
6. **错误报告**：收集并输出验证错误

### 2. 关键类和方法

#### MetaModelParser 类
- **作用**：解析元模型文件，建立字段定义
- **关键方法**：
  - `parse_file(file_path)` - 解析单个元模型文件
  - `_parse_field_definition(field_data, file_path)` - 解析字段定义（包括引用展开）
  - `_check_field_properties(field_data, file_path)` - 检查字段属性（新增）

#### MetaMetaModelParser 类  
- **作用**：解析元元模型定义，提供类型规范
- **关键方法**：
  - `parse(meta_meta_model_file)` - 解析元元模型文件
  - `get_field_type_definition(field_type)` - 获取字段类型定义

#### ReferenceResolver 类
- **作用**：处理引用解析，支持跨文件引用
- **关键方法**：
  - `resolve_reference(current_file, ref_value, file_cache, meta_model_dir)` - 解析引用
  - `_resolve_ref_path(current_file, ref_path, file_cache, meta_model_dir)` - 根据路径解析引用
  - `_resolve_local_ref(file_path, ref_path, file_cache)` - 解析本地引用
  - `_resolve_cross_file_ref(current_file, ref_path, file_cache, meta_model_dir)` - 解析跨文件引用
  - `_convert_component_to_field(component_def)` - 将组件转换为字段定义

#### MetaModelValidator 类
- **作用**：执行验证逻辑，收集错误
- **关键方法**：
  - `validate_meta_model_files(file_paths, meta_model_dir)` - 验证多个元模型文件
  - `_validate_model_definition(model, file_path)` - 验证模型定义
  - `_validate_field_definition(field, model, file_path)` - 验证字段定义
  - `_validate_inheritance(model, file_path)` - 验证继承关系

### 3. 数据结构

#### FieldDefinition 类
```python
{
    'name': str,           # 字段名
    'field_type': str,     # 字段类型
    'properties': dict      # 字段属性
}
```

#### MetaModelDefinition 类
```python
{
    'model_type': str,     # 模型类型
    'version': str,        # 版本
    'description': str,    # 描述
    'extends': str,        # 继自的模型
    'fields': list         # 字段定义列表
}
```

## 新增字段类型的更新指南

### 1. 元元模型更新
需要提供的信息：
- **新类型名称**：字段类型的名称（如 "BooleanField", "DateField" 等）
- **属性定义**：新类型支持的属性及类型要求
- **继承关系**：是否继承自其他类型（可选）
- **默认值**：属性的默认值（可选）
- **验证规则**：属性的验证要求（如正则表达式、数值范围等）

**示例格式**：
```yaml
# 在 metametamodel.yml 中新增
CustomField:
  extends: BaseField
  properties:
    customProp:
      type: string
      required: false
      description: "自定义属性"
    minValue:
      type: number
      required: false
      minimum: 0
```

### 2. 脚本更新需求
需要确认以下方面：

#### 必要的代码更新：
- **验证逻辑**：是否需要在 `_check_field_properties` 中添加新类型的属性验证
- **引用解析**：新类型是否需要特殊的引用处理
- **默认值处理**：新类型的属性是否有特殊默认值逻辑
- **转换逻辑**：引用到字段定义的转换是否有特殊要求

#### 可优化的内容：
- **错误信息**：是否需要更精确的错误消息
- **类型转换**：新类型的值转换和处理
- **性能优化**：新类型是否影响解析性能

## 引用系统更新指南

### 1. 引用格式变更
需要提供的信息：
- **新的引用格式**：除了 `$ref: 和 `#/components/` 外，是否有新的引用格式
- **复杂的引用路径**：引用路径是否变得更复杂
- **命名空间支持**：是否引入命名空间概念

### 2. 解析逻辑更新
需要确认的变更：
- **跨文件引用**：引用解析逻辑是否需要调整
- **递归引用**：是否需要处理更深层的递归引用
- **错误处理**：引用失败时的错误处理是否需要改进

## 继承系统更新指南

### 1. 继承机制变更
需要提供的信息：
- **继承规则变化**：显式继承是否变为隐式继承，或反之
- **字段传播**：父模型字段如何传播到子模型
- **覆盖规则**：子模型覆盖父模型字段的规则

### 2. 验证逻辑更新
需要确认的变更：
- **必填字段检查**：继承的必填字段验证逻辑
- **属性合并**：父子模型属性合并规则
- **循环检测**：继承循环的检测和处理

## 错误报告系统更新指南

### 1. 错误类型变更
需要提供的信息：
- **新增错误严重级别**：除了 ERROR、WARNING、INFO 外的新级别
- **错误分类**：是否需要新的错误分类（如引用错误、类型错误、属性错误等）
- **错误上下文**：是否需要更详细的错误上下文信息

### 2. 输出格式更新
需要确认的变更：
- **新的输出格式**：除了 JSON、TEXT 外的新格式
- **国际化支持**：是否需要多语言错误消息
- **详细信息**：是否需要堆栈跟踪、原始数据等信息

## 特殊处理逻辑更新指南

### 1. 特殊类型处理
需要提供的信息：
- **自定义字段类型**：需要自定义处理逻辑的复杂类型
- **转换规则**：类型之间转换的规则和边界条件
- **验证规则**：需要特殊验证逻辑的类型

### 2. 边界条件处理
需要确认的变更：
- **空值处理**：各种类型的空值和默认值处理
- **嵌套结构**：复杂嵌套结构的解析和验证
- **循环引用**：处理模型和字段的循环引用

## 测试用例更新指南

### 1. 测试场景扩展
需要提供的测试用例：
- **有效的使用示例**：正确使用新增功能的示例
- **错误的测试案例**：各种错误情况的测试用例
- **边界测试**：边界条件和异常情况的测试
- **性能测试**：涉及性能相关功能的测试

### 2. 验证要点
需要确保的验证点：
- **功能正确性**：新增功能按预期工作
- **向后兼容**：不影响现有功能
- **错误处理**：错误情况被正确处理
- **性能要求**：满足性能要求

## 版本兼容性

### 1. 向后兼容
需要确保：
- **旧版本元模型**：仍然能被正确验证
- **旧版本引用格式**：仍然能被正确解析
- **错误消息格式**：保持一致或提供明确的迁移指南

### 2. 迁移指南
需要提供：
- **升级步骤**：从旧版本升级到新版本的步骤
- **配置变更**：需要修改的配置文件或设置
- **已知问题**：升级过程中可能遇到的问题和解决方案

## 总结

要成功更新元模型验证脚本，需要提供以下关键信息：
1. **元元模型的变更详情**
2. **新增类型的完整定义和行为**
3. **验证逻辑的具体要求**
4. **引用系统的变更规则**
5. **继承机制的变更详情**
6. **错误处理的改进要求**
7. **性能和兼容性要求**
8. **测试用例和验证场景**

有了这些信息，我就能准确地更新和维护元模型验证脚本，确保其能够正确验证新的元模型定义。