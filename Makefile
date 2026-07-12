.PHONY: run test lint check-harness setup-secrets

# 启动 GUI
run:
	python -m pa_agent.main

# 运行测试
test:
	pytest -m "not live and not e2e" -q

# 代码检查
lint:
	ruff check . && black --check .

# 检查智能体入口、验证命令、eval 与敏感路径漂移
check-harness:
	powershell -NoProfile -ExecutionPolicy Bypass -File tools/check_project_harness.ps1

# 启用 pre-commit，防止 settings / 日志 / 记录被提交
setup-secrets:
	powershell -ExecutionPolicy Bypass -File tools/setup_git_secrets.ps1
