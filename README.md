# UDA Metamodel

UDA 元模型独立代码仓，包含：

- `metamodel/` — M2 元模型定义（YAML、脚本、校验工具）
- `metametamodel/` — M3 元元模型类型系统定义

后端服务通过 Git 拉取本仓库各分支，在 `metamodel/` 子目录下读取运行时元模型文件。

## 发布

将本目录作为独立 Git 仓库发布到 GitHub 后，在后端设置环境变量：

- `METAMODEL_REPO_URL` — 本仓库 Git URL
- `METAMODEL_REPO_TOKEN` — 私有仓库访问 Token（可选）
