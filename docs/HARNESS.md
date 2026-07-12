# Harness Engineering

## 目标

本 Harness 帮助智能体在明确授权内可靠修改 PA Agent，并通过可复现证据纠正错误。仓库中的代码、Prompt、测试和版本化文档是事实源；聊天摘要和个人记忆不能覆盖用户最新要求。

## 组件

### Guides

- `AGENTS.md`：短入口地图、硬边界和暂停条件。
- `docs/WORKFLOW.md`：任务从就绪到交接的流程。
- `docs/TESTING.md`：真实验证命令与风险分层。
- `.github/ISSUE_TEMPLATE/agent-task.yml`：目标、范围、授权和验收规格。
- `.github/pull_request_template.md`：证据、风险和外部影响审查。

### Sensors

- `tools/check_project_harness.ps1`：入口、链接、命令、eval、忽略规则和敏感路径漂移检查。
- `.githooks/pre-commit`：阻止密钥、设置、日志和记录误提交。
- `.github/workflows/ci.yml`：在 Windows 环境运行安装、Harness 检查和离线冒烟。
- `tests/`：行为正确性与回归背压。
- `docs/harness/evals.jsonl`：代表性任务与授权场景。

## 风险与配对

| 风险 | Guide | Sensor |
|---|---|---|
| 误改无关模块 | AGENTS 范围规则、Issue 模板 | PR diff 清单、Harness 授权检查项 |
| 模型/API 路由回归 | TESTING 映射 | client/provider route 测试 |
| Prompt/JSON 语义漂移 | WORKFLOW 与 Prompt 路由入口 | assembler/validator/normalizer 测试 |
| 密钥或记录泄漏 | AGENTS、SECURITY | pre-commit、ignore/tracked 检查 |
| live 操作越权 | 外部影响闸门 | eval 场景与人工批准证据 |
| 文档命令漂移 | 单一 TESTING 入口 | `check_project_harness.ps1` |

## Harness 深度

当前采用标准深度，不默认启用 subagent、昂贵评测或高权限工具。只有任务可独立并行、共享状态明确且要求证据合并时，才使用 subagent；普通单文件修改由单一智能体完成。

## Subagent 合约

如任务明确要求使用 subagent，父任务必须向 child 提供：

- 目标、完成条件和非目标。
- cwd、分支/worktree、权限和可用工具。
- 允许修改的精确文件及冲突策略。
- 必读上下文，而不是假设 child 拥有完整对话。
- 必须回传的 diff、命令输出、失败和不确定项。

父任务必须独立读取 diff 并重跑验证；“已完成”不是证据。

## Eval 回收

`docs/harness/evals.jsonl` 保存小型代表任务集。新增以下事件时应追加 case：

- 用户纠正了范围或授权理解。
- 发生密钥/运行时数据误提交风险。
- 相同 bug 或错误命令重复出现。
- 模型、Prompt、工具或 Harness 更新后出现行为回归。

case 使用稳定场景，不保存真实密钥、账号、行情或临时提交号。

## 治理

- Harness 变更与业务功能分开提交，便于独立审查。
- 入口文件保持简短；细节只在一个权威文档维护。
- CI 与本地检查调用同一个 `tools/check_project_harness.ps1`，避免规则分叉。
- 每次 Harness 试跑后，只把可复用缺口回写为规则、模板、测试、eval 或传感器。
