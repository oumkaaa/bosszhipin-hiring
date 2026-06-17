# Boss 直聘招聘助手 v1.2.1

完全自动化的 Boss 直聘招聘流程管理系统。基于 Python + boss-agent-cli，支持从候选人获取、智能筛选、实时互动到简历收集的完整自动化。

**Current Version**: v1.2.1 (Production Ready)  
**Status**: ✅ Fully Implemented & Tested

---

## 核心功能

### 三阶段自动化流程

#### Phase 1：候选人获取 + 筛选 + 打招呼 ✅
- 并行获取两个来源：新招呼列表 + 推荐牛人
- 智能去重和配额分配（50/50 比例）
- 基于学历、毕业年份、关键词的自动筛选
- 业务规则评分（0-100分）
- 真实发送打招呼消息
- **状态转移**: `NEW` → `首轮沟通` / `FAILED`

#### Phase 2：回复判断 + 智能追问 ✅
- 实时拉取候选人最新消息
- 智能解析：到岗时间、周天数、实习时长
- 三分支路由：
  - **达标** → 推进 `二轮沟通`
  - **信息不完整** → 发送追问消息
  - **不达标** → 发送礼貌拒绝
- **状态转移**: `首轮沟通` → `二轮沟通` / `首轮沟通追加提问` / `FAILED`

#### Phase 3：简历索要 + 收集 + 目标判断 ✅
- 实时请求候选人分享简历
- 检查消息中的简历附件状态
- 追踪简历收集进度
- 自动判断任务完成：`active` → `completed` / `expired`
- **状态转移**: `二轮沟通` → `等待简历` → `简历已获取`

---

## 技术特点

| 特性 | 说明 |
|------|------|
| **编码完美** | 原生 Python UTF-8，GBK 乱码问题彻底解决 |
| **架构优雅** | 统一的 AgentCliAdapter，所有 Boss API 调用集中管理 |
| **审计完整** | 每次 API 调用结果都记录到 candidates.json |
| **安全第一** | Dry-run 模式默认启用，显式 allow_send=true 才能发送 |
| **高可靠** | 单个候选人失败不影响其他，完整错误恢复 |
| **工程质量** | 类型安全、IDE 友好、继承 boss-agent-cli 的 1400+ 测试 |

---

## 快速开始

### 前置要求

```bash
# Python 3.10+
python --version

# boss-agent-cli >= 1.13.1
boss --version

# 已登录 Boss 直聘
boss status --live
```

### 安装

```bash
# 克隆仓库
git clone https://github.com/oumkaaa/bosszhipin-hiring.git
cd bosszhipin-hiring

# 安装依赖
pip install -r requirements.txt

# 验证环境
python verify_setup.py
```

### 初始化运行时目录

```bash
# 创建目录
mkdir -p /path/to/runtime/my-job

# 复制配置文件（参考 SKILL.md）
# 需要创建：
# - run-context.json (任务配置)
# - screen-rules.json (筛选规则)
# - candidates.json (初始化空列表)
```

### 运行

#### 安全模式（推荐首次）

```bash
# Windows
.\run.ps1 "D:\path\to\runtime\my-job"

# Linux/macOS
bash run.sh /path/to/runtime/my-job

# 或直接 Python
python -m boss_hr_recruiter /path/to/runtime/my-job --dry-run
```

所有消息操作都是模拟的（日志显示 `[DRY-RUN]`）。

#### 生产模式

编辑 `run-context.json`：

```json
{
  "allow_send": true,
  "dry_run": false
}
```

然后运行：

```bash
python -m boss_hr_recruiter /path/to/runtime/my-job
```

#### 单阶段运行

```bash
# 只运行 Phase 1（获取和打招呼）
python -m boss_hr_recruiter /path/to/runtime/my-job --phase 1

# 只运行 Phase 2（判断回复）
python -m boss_hr_recruiter /path/to/runtime/my-job --phase 2

# 只运行 Phase 3（简历处理）
python -m boss_hr_recruiter /path/to/runtime/my-job --phase 3
```

### 定时触发（Cron）

```bash
# 每 2 小时运行一次
0 */2 * * * cd /path/to/boss-hr-recruiter && python -m boss_hr_recruiter /path/to/runtime/my-job

# Windows Task Scheduler
# New-ScheduledTask -Action ... (参考 SKILL.md)
```

---

## 项目结构

```
boss-hr-recruiter/
├── boss_hr_recruiter/
│   ├── __main__.py              # CLI 入口（带 --phase, --dry-run 支持）
│   ├── main.py                  # 三阶段 orchestrator
│   ├── adapters/
│   │   └── agentcli.py          # 统一 boss-agent-cli 接口 [新]
│   ├── phase1/
│   │   ├── sources.py           # 并行获取候选人（双源）
│   │   ├── screening.py         # 简历筛选和评分
│   │   ├── allocator.py         # 配额分配
│   │   └── models.py            # 数据模型
│   ├── phase2/
│   │   └── reply_parser.py      # 回复解析和达标判断
│   ├── phase3/
│   │   └── goal_judge.py        # 目标完成判断
│   └── utils/
│       ├── config.py            # 配置加载
│       ├── storage.py           # candidates.json 读写
│       ├── logger.py            # 结构化日志
│       ├── auth.py              # 认证管理
│       ├── errors.py            # 自定义异常
│       └── models.py            # schema 规范化
├── run.ps1 / run.sh             # 启动脚本
├── verify_setup.py              # 环境验证工具
├── requirements.txt             # 依赖清单
├── SKILL.md                     # 完整使用文档
├── TEST_REPORT.md               # 验证报告
├── README.md                    # 本文件
└── docs/
    ├── MIGRATION.md             # opencli 版本迁移指南
    └── TROUBLESHOOTING.md       # 常见问题和解决方案
```

---

## 配置说明

### run-context.json（任务配置）

```json
{
  "task_name": "AI产品经理实习生",
  "job_name": "AI产品经理",
  "job_id": "543926518",
  "resume_target": 20,
  "task_deadline": "2026-06-30T18:00:00+08:00",
  "task_status": "active",
  
  "first_round_message": "看到你的简历很不错...",
  "second_round_message": "感谢回复！请发一份最新简历...",
  "follow_up_message": "还想确认一下...",
  "reject_message": "感谢回复，希望未来有机会合作",
  
  "dry_run": true,
  "allow_send": false,
  "greet_batch_size": 4
}
```

### screen-rules.json（筛选规则）

```json
{
  "min_grad_year": 2026,
  "valid_degrees": ["本科", "硕士", "博士"],
  "exclude_keywords": ["专升本", "成人教育", "自考"],
  "business_include_rules": ["AI产品", "产品经理"],
  "business_exclude_rules": ["纯销售", "纯客服"],
  "max_arrival_weeks": 2,
  "min_days_per_week": 4,
  "min_duration_months": 3
}
```

详见 SKILL.md 的第四节。

---

## 候选人生命周期

```
NEW
  ├─ 首轮沟通（已发送打招呼）
  │   ├─ 二轮沟通（回复达标）
  │   │   ├─ 等待简历（已请求）
  │   │   │   ├─ 简历已获取 ✅（终态）
  │   │   │   └─ FAILED（等待超期）
  │   │   └─ FAILED（不达标）
  │   ├─ 首轮沟通追加提问（回复不完整）
  │   │   ├─ 二轮沟通（追问后达标）
  │   │   └─ FAILED（追问后仍不达标）
  │   └─ FAILED（明确不达标）
  └─ FAILED（初筛不通过）
```

**任务状态**:
- `active`: 运行中
- `completed`: 简历数 >= 目标
- `expired`: 超过截止时间
- `manual_stopped`: 人工停止

---

## 环境要求

| 项目 | 要求 |
|------|------|
| Python | >= 3.10 |
| boss-agent-cli | >= 1.13.1 |
| 操作系统 | Windows 7+ / macOS 10.13+ / Ubuntu 16.04+ |
| 网络 | 能访问 Boss 直聘（zhipin.com） |
| 浏览器 | Chrome（用于 CDP 连接，可选） |

---

## 常见问题

**Q: 如何在多个职位间切换？**  
创建多个 `$RUNTIME_DIR`，每个目录配置不同的 `run-context.json`。

**Q: 支持修改筛选规则吗？**  
支持。编辑 `screen-rules.json` 后重新运行，新规则立即生效。

**Q: 如何暂停或停止任务？**  
修改 `run-context.json` 中的 `task_status` 为 `manual_stopped`，重新运行时会跳过。

**Q: 显示 Cookie 过期怎么办？**  
运行 `boss login --cdp` 重新登录，或清除 ~/.boss-agent 目录后重新登录。

**Q: 如何验证是否正确配置？**  
运行 `python verify_setup.py` 进行 7 项检查。

更多问题见 [TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md)。

---

## 与 v1.1（opencli 版本）的对比

| 维度 | opencli 版本 | Python 版本（v1.2.1） |
|------|:----------:|:-------------------:|
| **GBK 编码问题** | ❌ 存在 | ✅ 完全解决 |
| **Python 集成** | ❌ Subprocess 调用 | ✅ 直接 import |
| **Phase 1** | ✅ 完整 | ✅ 完整 |
| **Phase 2** | ⚠️ 模拟 | ✅ **真实** |
| **Phase 3** | ⚠️ 模拟 | ✅ **真实** |
| **审计日志** | ⭐⭐ | ✅ **完整** |
| **类型安全** | ⭐⭐ | ✅ **IDE 友好** |
| **工程质量** | ⭐⭐⭐ | ✅ **⭐⭐⭐⭐⭐** |

---

## 文档

- **[SKILL.md](SKILL.md)** — 完整功能文档、配置指南、故障排查
- **[TEST_REPORT.md](TEST_REPORT.md)** — v1.2.1 验证报告
- **[docs/TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md)** — 常见问题解决方案
- **[docs/MIGRATION.md](docs/MIGRATION.md)** — 从 opencli 版本迁移指南

---

## 架构亮点

### AgentCliAdapter（新增）
统一所有 boss-agent-cli SDK 调用的接口，集中处理：
- 错误检查和 Cookie 过期处理
- Dry-run 模式支持
- 完整的日志记录
- 返回值一致性

### candidates.json 审计日志
每次 API 调用都记录 `last_agentcli_result`：
```json
{
  "last_agentcli_result": {
    "code": 0,
    "action": "send_message",
    "timestamp": "2026-06-17T20:10:00+08:00",
    "message_type": "greeting"
  }
}
```

---

## 安全与可靠性

- ✅ **Dry-run 默认启用** — 模拟所有发送操作
- ✅ **显式允许发送** — 需要 `allow_send=true` 才真实发送
- ✅ **Auth 前置检查** — 任何阶段前都验证登录状态
- ✅ **完整错误恢复** — 单个候选人失败不影响其他
- ✅ **原子写入** — candidates.json 采用原子更新

---

## 贡献

欢迎提交 Issue 和 Pull Request！

---

## 许可证

MIT License - 详见 [LICENSE](LICENSE)

---

**v1.2.1 生产就绪** ✅
