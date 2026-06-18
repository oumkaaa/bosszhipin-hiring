# Boss 直聘招聘助手 v1.2.1

基于 boss-agent-cli 的自动化招聘工具。完整实现三阶段流程：候选人筛选 → 回复判断 → 简历收集。

## 快速开始

```bash
# 安装
pip install -r requirements.txt
boss login

# 验证环境
python verify_setup.py

# 干运行（推荐首次）
python -m boss_hr_recruiter /path/to/runtime --dry-run

# 真实运行（修改配置后）
python -m boss_hr_recruiter /path/to/runtime --live
```

## 核心功能

| Phase | 功能 | 状态 |
|-------|------|------|
| **1** | 双源候选人获取 → 筛选 → 打招呼 | ✅ |
| **2** | 消息获取 → 回复解析 → 追问/拒绝 | ✅ |
| **3** | 简历请求 → 收据检查 → 目标判断 | ✅ |

## 项目结构

```
boss-hr-recruiter/
├── boss_hr_recruiter/
│   ├── adapters/agentcli.py      # 统一 API 接口
│   ├── phase1/                   # 候选人筛选
│   ├── phase2/                   # 回复判断
│   ├── phase3/                   # 简历处理
│   └── utils/                    # 工具和存储
├── run.ps1 / run.sh              # 启动脚本
├── verify_setup.py               # 环境检查
├── SKILL.md                      # 完整文档
└── requirements.txt
```

## 配置

创建 `run-context.json` 和 `screen-rules.json`：

```json
{
  "task_name": "职位名",
  "job_id": "职位ID",
  "resume_target": 20,
  "task_deadline": "2026-06-30T18:00:00+08:00",
  "dry_run": true,
  "allow_send": false,
  "greet_batch_size": 4
}
```

详见 SKILL.md。

## 候选人状态

```
NEW → 首轮沟通 → 二轮沟通 → 等待简历 → 简历已获取
    → FAILED
```

## 环境要求

- Python 3.10+
- boss-agent-cli >= 1.13.1
- 已登录 Boss 直聘

## 定时运行

```bash
# Cron
0 */2 * * * python -m boss_hr_recruiter /path/to/runtime --live

# Windows Task Scheduler
# 参考 SKILL.md
```

## 特点

- 解决 GBK 编码问题（原生 Python UTF-8）
- 直接调用 boss-agent-cli 库（无 subprocess）
- Dry-run 默认安全（需显式 allow_send=true）
- 完整审计日志（last_agentcli_result）
- 单个失败不影响其他候选人

## 文档

- [SKILL.md](SKILL.md) - 完整功能和配置说明
- [TEST_REPORT.md](TEST_REPORT.md) - 验证报告
- [docs/TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md) - 常见问题

## 许可证

MIT
