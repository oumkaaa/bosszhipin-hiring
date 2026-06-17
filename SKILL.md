---
name: boss-hr-recruiter
description: >
  Boss直聘招聘助手（Python版）。完全基于boss-agent-cli，支持自动化招聘流程：
  筛选+打招呼 → 判断回复 → 简历处理+目标判断。
  定时触发模式：外部App每2小时触发一次skill，单次运行完成三个阶段。
  解决了原opencli版本的GBK编码问题和Python集成困难。
  
metadata:
  requires:
    bins: ["python3", "boss-agent-cli"]
  version: "1.0.0"
---

# Boss直聘招聘助手（Python版）

## 一、架构说明

**改造背景：** 从 boss-hiring-v2（基于 opencli TypeScript）迁移到 boss-hr-recruiter（完全 Python 实现，基于 boss-agent-cli）

**核心优势：**
- ✅ 编码问题彻底解决（GBK乱码问题消除）
- ✅ Python原生，可直接 import 库
- ✅ 性能更高（无subprocess开销）
- ✅ 类型安全，IDE友好
- ✅ 代码质量继承boss-agent-cli（1400+测试）

**运行模式：**
```
外部App触发（每2小时）
  ↓
单次运行（一个Python进程）
  ├─ Phase 1：筛选 + 打招呼
  ├─ Phase 2：判断回复是否达标
  └─ Phase 3：简历处理 + 目标判断
  ↓
退出，等待下次触发
```

三个阶段共享同一份 `candidates.json` 状态文件，阶段间以 JSON 格式通信。

---

## 二、前置条件

### 2.1 系统要求

| 依赖 | 检查命令 | 说明 |
|------|----------|------|
| Python 3.10+ | `python --version` | 必须 |
| boss-agent-cli | `boss --version` | 必须，>=1.13.1 |
| 完整认证状态 | `boss status --live` | 需已登录zhipin.com |
| Chrome（可选） | CDP端口9222 | 仅hr reply/request-resume需要 |

### 2.2 环境变量

```bash
# Windows 强烈建议设置（避免GBK编码问题）
set PYTHONIOENCODING=utf-8

# Linux/macOS
export PYTHONIOENCODING=utf-8
```

---

## 三、安装

### 3.1 安装依赖

```bash
pip install -r requirements.txt
```

### 3.2 认证登录

```bash
# 首次登录
boss login

# 如果需要Chrome自动化（hr reply, hr request-resume）
boss login --cdp

# 验证登录状态
boss status --live
```

### 3.3 初始化运行时目录

```bash
# 创建运行时目录
mkdir -p D:/boss-hiring-runtime/my-job

# 初始化配置（见第四节）
```

---

## 四、Phase 1：新建任务（Intake）

### 4.1 配置表单

创建 `$RUNTIME_DIR/run-context.json`：

```json
{
  "task_name": "国际公域-ai产品经理实习生",
  "job_name": "ai产品经理",
  "job_id": "543926518",
  "job_id_status": "resolved",
  "resume_target": 20,
  "task_deadline": "2026-06-19T12:00:00+08:00",
  "task_status": "active",
  
  "first_round_message": "你好！看到你的简历，觉得和我们岗位很匹配，请问能实习多久，多久能到岗，一周能到岗几天呢",
  "second_round_message": "感谢回复！你的实习时间和我们完全匹配，方便发一份最新简历吗？",
  "follow_up_message": "感谢回复！还想确认一下：最早到岗时间、每周可投入天数、可持续时长分别是多少？",
  "reject_message": "感谢您的回复！您目前的实习安排和我们的需求有些差距，希望未来有机会合作"
}
```

### 4.2 筛选规则

创建 `$RUNTIME_DIR/screen-rules.json`：

```json
{
  "min_grad_year": 2026,
  "valid_degrees": ["本科", "硕士", "博士"],
  "exclude_keywords": ["专升本", "成人教育", "自考", "电大", "函授"],
  
  "max_arrival_weeks": 2,
  "min_days_per_week": 4,
  "min_duration_months": 3,
  
  "business_include_rules": ["AI产品", "产品经理", "互联网"],
  "business_exclude_rules": ["纯销售", "纯客服"]
}
```

### 4.3 初始化候选人列表

创建 `$RUNTIME_DIR/candidates.json`：

```json
{
  "version": "boss-hiring-v2",
  "candidates": []
}
```

---

## 五、Phase 1：筛选 + 打招呼（双源并行）

**改进说明（2026-06-17）：** Phase 1 现支持两个数据源的并行处理。`boss hr candidates` 已验证可完全替代 `recommend` 命令，迁移覆盖率从 70% 提升至 80%。

### 5.1 并行获取两个来源

同时执行以下两条命令（内部异步并行）：

```bash
# 来源1：新招呼列表（候选人主动沟通）
boss hr chat --label-id 1

# 来源2：推荐牛人列表（系统推荐给招聘者）
boss hr candidates --job-id <job_id> --page 1-3
```

返回合并后的候选人列表。

### 5.2 配额分配

合并后按来源分配配额：

```
target_count = 10 人  (可配置)
├─ 新招呼：5 人（50%）— 按得分排序
└─ 推荐：5 人（50%）— 按活跃度排序
```

配额分配确保两个来源都有机会被处理，避免某个来源被完全忽略。

### 5.3 逐人筛选

对每个候选人执行：

1. **获取简历**
   - 新招呼：`boss hr resume <security_id> --job-id <job_id> --raw`
   - 推荐：从 geekCard 直接提取（高效，无额外API调用）

2. **基础筛选**
   - 学历：本科及以上
   - 届别：2026届及以后
   - 排除关键词：专升本、成人教育等

3. **业务规则评分**
   - 匹配全部包含规则 → 100%
   - 匹配部分规则 → 50-99%（按比例）
   - 无负面项但无经历 → 60%
   - 默认 → 75%

### 5.4 发送打招呼消息

符合度 ≥75% 的候选人自动发送（无需人工确认）：

```bash
# 两个来源的候选人都使用同一条消息
boss hr reply <friend_id> "你好！看到你的简历..."
```

**风控规则：**
- 每批最多 10 人（可配置 `greet_batch_size`）
- 每批后休息 1 分钟
- 每次运行最多 10 批

**audit trail：** candidates.json 中 `source` 字段记录来源（'chat' | 'recommend'）

---

## 七、Phase 2：判断回复是否达标

### 7.1 获取待判断候选人

```
boss hr chatmsg <friend_id>
```

获取聊天记录，检查是否有新回复。

### 7.2 解析回复信息

使用 regex 提取：
- `arrival_weeks`：最晚到岗周数
- `days_per_week`：每周天数
- `duration_months`：实习时长（月）

### 7.3 三分支路由

| 情况 | 处理 | 状态转移 |
|------|------|----------|
| 达标（3个信息完整且符合要求） | 推进二轮 | 首轮沟通 → 二轮沟通 |
| 信息不完整（首次） | 追问一次 | 首轮沟通 → 首轮沟通追加提问 |
| 信息不完整（追问后仍不全） | 婉拒并淘汰 | 首轮沟通追加提问 → FAILED |
| 明确不达标 | 婉拒并淘汰 | 首轮沟通 → FAILED |

**风控规则：** 同Phase 1

---

## 八、Phase 3：简历处理 + 目标判断

### 8.1 索要简历

状态为 `二轮沟通` 的候选人发送索要简历消息：

```
boss hr reply <friend_id> "感谢回复！你的实习时间和我们完全匹配，方便发一份最新简历吗？"
```

### 8.2 接收简历

监控聊天记录，检查是否收到简历：

```
boss hr chatmsg <friend_id>
```

检查消息中是否包含 `aid=38`（候选人已接受简历申请）。

如果收到，状态转为 `简历已获取`。

### 8.3 超时处理

等待简历超过 48 小时仍未收到 → 状态转为 FAILED

### 8.4 判断任务完成

统计 `status='简历已获取'` 的候选人数：

- 如果 ≥ `resume_target` → 任务完成，`task_status` 更新为 `completed`
- 如果当前时间 > `task_deadline` → 任务过期，`task_status` 更新为 `expired`
- 否则继续等待下次运行

**这是全流程唯一写 `task_status` 的地方**

---

## 九、候选人状态机

```
NEW
  ├─ 首轮沟通（发出首轮消息）
  └─ FAILED（初筛不通过）

首轮沟通
  ├─ 首轮沟通追加提问（信息不完整，追问）
  ├─ 二轮沟通（达标）
  └─ FAILED（不达标）

首轮沟通追加提问
  ├─ 二轮沟通（追问后达标）
  └─ FAILED（追问后仍不达标）

二轮沟通
  └─ 等待简历（发出索要简历消息）

等待简历
  ├─ 简历已获取（收到简历）
  └─ FAILED（超时未收到）

简历已获取 / FAILED（终态）
```

---

## 十、风控规则

| 规则 | 值 | 说明 |
|------|-----|------|
| 每批发送上限 | 10 条 | send / reply |
| 每批后强制休息 | 1 分钟 | - |
| 每次运行最多批次 | 10 批 | 最多100条/次运行 |
| 等待简历超时 | 48 小时 | 未收到 → FAILED |
| Cookie 过期（code 7/37） | 立即停止 | 等待人工重新登录 |

---

## 十一、运行方式

### 11.1 命令行运行

```bash
python -m boss_hr_recruiter.main /path/to/runtime_dir
```

### 11.2 定时触发

使用外部调度工具（如 Anthropic Routines、cron 等）每 2 小时触发一次。

示例（cron）：
```bash
0 */2 * * * python -m boss_hr_recruiter.main /path/to/runtime_dir
```

---

## 十二、故障排查

### 问题 1：GBK 编码错误

**表现：** `boss hr resume` 返回 NETWORK_ERROR，中文乱码

**解决：** 这是原opencli版本的问题，新版本已彻底解决（Python原生UTF-8）

### 问题 2：Cookie 过期

**表现：** 返回错误 code 7 或 37，或提示"登录失效"

**解决：**
```bash
boss login
# 或通过Chrome重新登录
boss login --cdp
```

然后等待下次定时触发（2小时后）自动恢复。

### 问题 3：CDP Chrome 连接

**表现：** "RECRUITER_CHAT_TAB_REQUIRED"

**解决：**
1. 启动Chrome：`--remote-debugging-port=9222`
2. 打开聊天页面：https://www.zhipin.com/web/chat/index
3. 重试命令

### 问题 4：简历数据解析失败

**原因：** JSON格式变化或API升级

**解决：** 检查 `$RUNTIME_DIR/logs/` 中的详细日志

---

## 十三、与 opencli 版本的区别

| 功能 | opencli版 | Python版 | 说明 |
|------|:-------:|:------:|------|
| GBK编码问题 | ❌ 存在 | ✅ 已解决 | Python原生UTF-8 |
| Python集成 | ❌ 需subprocess | ✅ 直接import | 性能更高 |
| 工程质量 | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ | 继承boss-agent-cli |
| 社区支持 | ⭐⭐ | ⭐⭐⭐⭐⭐ | 活跃维护 |
| 多平台支持 | 仅Boss | 支持多平台 | 可扩展 |

---

## 十四、数据兼容性

新版本与 opencli 版本的 `candidates.json` 格式完全兼容，可无缝迁移：

```bash
# 将旧版本的runtime_dir直接用于新版本
python -m boss_hr_recruiter.main /path/to/old_runtime_dir
```

---

## 十五、完整运行流程示例

```bash
# 1. 安装
pip install -r requirements.txt

# 2. 认证
boss login

# 3. 初始化运行时目录
mkdir -p D:/boss-hiring-runtime/ai-product-intern
# 创建 run-context.json / screen-rules.json / candidates.json

# 4. 首次运行
python -m boss_hr_recruiter.main D:/boss-hiring-runtime/ai-product-intern

# 5. 查看日志
cat D:/boss-hiring-runtime/ai-product-intern/logs/main-20260617.log

# 6. 设置定时运行（每2小时）
# Linux: crontab -e
# Windows: 任务计划程序或其他调度工具
```

---

## 十六、常见问题

**Q: 如何修改筛选规则？**
A: 编辑 `$RUNTIME_DIR/screen-rules.json` 中的参数，重新运行 skill 即可应用。

**Q: 如何手动停止任务？**
A: 修改 `run-context.json` 中的 `task_status` 为 `manual_stopped`。

**Q: 候选人没有回复怎么办？**
A: skill 会每次运行检查一遍，如果仍无回复就继续等待，不会自动淘汰。

**Q: 能否支持多个招聘职位同时进行？**
A: 当前不支持。可创建多个 `$RUNTIME_DIR` 目录，分别管理不同职位。

---

## 十七、更新日志

### v1.0.0 (2026-06-17)

- ✅ 首个稳定版本
- ✅ Python完全实现，解决GBK编码问题
- ✅ 三阶段完整实现
- ✅ 风控规则落地
- ✅ 详细文档和故障排查
