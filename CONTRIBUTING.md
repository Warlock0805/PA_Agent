# 参与贡献

感谢你对 PA Agent 的关注。本项目欢迎 Issue 与 Pull Request。

智能体或自动化贡献开始前先读 [`AGENTS.md`](AGENTS.md)，实施与授权流程见
[`docs/WORKFLOW.md`](docs/WORKFLOW.md)，完整验证矩阵见
[`docs/TESTING.md`](docs/TESTING.md)。

## 开发环境

1. Windows 10/11，Python 3.11+
2. 安装 MetaTrader 5 并登录（用于真实 K 线联调）
3. 克隆仓库后：

   ```cmd
   python -m venv .venv
   .venv\Scripts\activate
   pip install -e ".[dev]"
   copy config\settings.example.json config\settings.json
   ```

4. 在 GUI **设置** 中配置 API Key，或仅跑不依赖网络的测试。

## 提交代码前

```cmd
.\.venv\Scripts\python.exe -m pytest -m "not live and not e2e" -q
.\.venv\Scripts\python.exe -m ruff check pa_agent tests
powershell -NoProfile -ExecutionPolicy Bypass -File tools\check_project_harness.ps1
```

（若已安装 `black`，可按团队习惯格式化。）

## 请勿提交

- `config/settings.json`、`config/exception_state.json`
- `logs/`、`records/pending/`、`experience/` 下的运行数据
- 任何 API Key、`.env`、私钥文件

启用本地 pre-commit 钩子：

```powershell
powershell -ExecutionPolicy Bypass -File tools\setup_git_secrets.ps1
```

## Pull Request 建议

- 一个 PR 聚焦一类改动（功能 / 修复 / 文档）
- 说明动机与测试方式
- 若改 JSON schema、提示词或路由，请补充或更新 `tests/` 中相关用例

## 问题反馈

- Bug：附上日志片段（`logs/pa_agent.log`）、复现步骤、品种/周期
- 功能建议：说明使用场景与期望行为

讨论与交流也可加入 README 中的 QQ 群。
