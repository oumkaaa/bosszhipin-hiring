# Boss直聘招聘助手 - Python版（boss-hr-recruiter）

完全基于 `boss-agent-cli` 的自动化招聘工具，支持三阶段流程：筛选+打招呼 → 判断回复 → 简历处理+目标判断。

## 核心特性

- ✅ **解决编码问题**：GBK乱码问题彻底消除（Python原生UTF-8）
- ✅ **Python原生**：直接import库，无subprocess开销
- ✅ **工程质量**：继承boss-agent-cli的1400+测试
- ✅ **完全自动化**：支持定时触发，无需人工干预
- ✅ **状态机严谨**：完整的候选人生命周期管理
- ✅ **风控完备**：速率限制、超时处理、错误恢复

## 快速开始

### 安装

```bash
pip install -r requirements.txt
boss login
```

### 初始化运行时目录

```bash
mkdir -p D:/boss-hiring-runtime/my-job
# 创建 run-context.json / screen-rules.json / candidates.json
```

### 运行

**Windows (推荐)**:
```bash
.\run.ps1 "D:\boss-hiring-runtime\my-job"
```

**Linux/macOS**:
```bash
bash run.sh /path/to/runtime/my-job
```

**直接运行** (不用启动脚本):
```bash
python -m boss_hr_recruiter.main D:/boss-hiring-runtime/my-job
```

启动脚本会自动：
- 设置 UTF-8 编码
- 初始化运行时目录
- 显示彩色日志输出

### 定时触发

```bash
# 每2小时运行一次
0 */2 * * * python -m boss_hr_recruiter.main /path/to/runtime_dir
```

## 目录结构

```
boss-hr-recruiter/
├── boss_hr_recruiter/
│   ├── __init__.py
│   ├── main.py                 # 主入口（三阶段orchestrator）
│   ├── phase1/
│   │   ├── __init__.py
│   │   ├── models.py          # 数据模型
│   │   └── screening.py       # 简历筛选和评分
│   ├── phase2/
│   │   ├── __init__.py
│   │   └── reply_parser.py    # 回复解析
│   ├── phase3/
│   │   ├── __init__.py
│   │   └── goal_judge.py      # 目标判断
│   └── utils/
│       ├── __init__.py
│       ├── errors.py          # 自定义异常
│       ├── config.py          # 配置加载
│       ├── logger.py          # 日志系统
│       ├── auth.py            # 认证管理
│       └── storage.py         # 数据存储
├── SKILL.md                    # Skill定义和使用说明
├── README.md                   # 本文件
├── requirements.txt            # 依赖
├── .env.example               # 环境变量示例
├── tests/                     # 测试代码
└── docs/                      # 补充文档
    ├── MIGRATION.md           # 迁移指南
    ├── TROUBLESHOOTING.md     # 故障排查
    └── API_REFERENCE.md       # API参考
```

## 与 opencli 版本的区别

| 特性 | opencli版 | Python版 |
|------|:-------:|:------:|
| GBK编码问题 | ❌ | ✅ |
| Python集成 | ❌ | ✅ |
| 工程质量 | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| 社区支持 | ⭐⭐ | ⭐⭐⭐⭐⭐ |

## 文档

- **SKILL.md**：完整的使用说明，包含前置条件、各阶段详解、故障排查
- **docs/MIGRATION.md**：从 opencli 版本迁移的指南
- **docs/TROUBLESHOOTING.md**：常见问题和解决方案
- **docs/API_REFERENCE.md**：boss-agent-cli API参考

## 环境要求

- Python 3.10+
- boss-agent-cli >= 1.13.1
- 完整的Boss直聘登录状态

## 配置

编辑 `$RUNTIME_DIR/run-context.json` 和 `screen-rules.json` 来配置：
- 招聘职位信息
- 消息模板
- 筛选条件
- 业务规则

详见 SKILL.md 的第四节。

## 许可证

MIT

## 常见问题

**Q: 如何修改筛选规则？**
编辑 `screen-rules.json`，重新运行即可。

**Q: 支持多个职位吗？**
当前不支持。可创建多个 `$RUNTIME_DIR` 分别管理。

**Q: 如何手动停止任务？**
修改 `run-context.json` 中的 `task_status` 为 `manual_stopped`。

更多问题见 SKILL.md 第十六节。

## 反馈与贡献

欢迎提交问题和拉取请求！
