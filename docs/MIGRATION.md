# 从 boss-hiring-v2 迁移到 boss-hr-recruiter

## 为什么迁移？

| 问题 | boss-hiring-v2 | boss-hr-recruiter |
|------|:-------------:|:---------------:|
| GBK编码乱码 | ❌ | ✅ |
| TypeScript vs Python | ❌ 割裂 | ✅ 统一 |
| 工程质量 | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| AI Agent集成 | ❌ | ✅ |
| 社区支持 | ⭐⭐ | ⭐⭐⭐⭐⭐ |

## 数据兼容性

好消息：`candidates.json` 格式完全兼容！

```bash
# 直接迁移即可
cp -r D:/boss-hiring-runtime/old_job D:/boss-hiring-runtime/new_job
python -m boss_hr_recruiter.main D:/boss-hiring-runtime/new_job
```

## 命令映射

### 招聘者命令

| 功能 | opencli 版 | Python 版 | 状态 |
|------|-----------|---------|------|
| 获取新招呼 | `opencli boss chatlist --job-id` | `boss hr chat --label-id 1` | ✅ |
| **获取推荐牛人** | **`opencli boss recommend`** | **`boss hr candidates --job-id`** | **✅ 可替代**（2026-06-17验证） |
| 获取简历 | `opencli boss resume <uid>` | `boss hr resume --raw` | ✅ |
| 发送消息 | `opencli boss send <uid> msg` | `boss hr reply <uid> msg` | ✅ |
| 获取聊天 | `opencli boss chatmsg <uid>` | `boss hr chatmsg <uid>` | ✅ |
| 请求简历 | `opencli boss accept-resume <uid>` | `boss hr request-resume <uid>` | ✅ |
| 标记 | `opencli boss mark <uid>` | `boss mark` | ✅ |

**⚠️ 关键修正（2026-06-17）**
- **原认为**：`recommend` 无替代方案
- **实际验证**：`boss hr candidates --job-id <jobId>` 返回完整 JSON 结构（geekCard），包含 name、degree、school、workYear 等所有筛选所需字段，**可直接替代**
- **改进**：Phase 1 现支持双源并行处理（新招呼 + 推荐），迁移覆盖率 70% → 80%

### 推荐牛人（geekCard）字段映射

```json
// boss hr candidates 返回的结构
{
  "geekCard": {
    "name": "王**",                  // 脱敏姓名
    "highestDegreeName": "硕士",     // 学历（对应 degree）
    "workYear": "应届",              // 工作年限描述
    "eduSchool": "清华大学",         // 学校
    "eduMajor": "计算机",            // 专业
    "activeDesc": "刚刚活跃",        // 活跃度（用于排序）
    "encryptGeekId": "XXX"           // 用于后续操作
  }
}
```

### 关键字段差异

| 概念 | opencli | boss-agent-cli |
|------|---------|----------------|
| 新招呼候选人ID | `uid` | `friendId` |
| 推荐候选人ID | N/A | `encryptGeekId` |
| 简历格式 | YAML文本 | JSON（--raw） |
| 推荐牛人格式 | YAML | JSON geekCard（无需额外API） |
| 职位ID | `encrypt_job_id` | `encryptJobId` |
| 来源标签 | N/A | `source`: 'chat' \| 'recommend' |

## 逐步迁移

### 第1阶段：并行运行（0-1周）
- ✅ 保持 boss-hiring-v2 运行
- ✅ 部署 boss-hr-recruiter
- ✅ 在测试职位上验证

### 第2阶段：验证稳定性（1-2周）
- ✅ 观察 Python 版本的表现
- ✅ 对比结果
- ✅ 修复发现的问题

### 第3阶段：全量迁移（2+周）
- ✅ 切换所有职位到 Python 版本
- ✅ 归档 boss-hiring-v2

## 故障排查

**GBK编码错误**
- 原因：opencli 版本的已知问题
- 状态：Python 版本已解决

**简历数据不完整**
- 原因：某些API字段缺失
- 解决：使用 `--raw` 标志，自定义JSON解析

**CDP连接问题**
- 原因：Chrome自动化要求
- 解决：启动Chrome，打开聊天页面

## 常见问题

**Q: 新版本的简历解析准确度如何？**
A: 与 opencli 版本相同，使用 regex 和业务规则。

**Q: 能否同时运行两个版本？**
A: 可以，但要使用不同的 `$RUNTIME_DIR`，避免 candidates.json 竞态。

**Q: 旧版本的候选人数据会丢失吗？**
A: 不会。JSON 格式兼容，直接拷贝目录即可。

**Q: 如何回滚到 opencli 版本？**
A: 由于数据格式相同，可直接切换回 opencli 版本继续运行。
