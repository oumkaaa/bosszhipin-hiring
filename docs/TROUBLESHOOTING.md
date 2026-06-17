# 故障排查（Troubleshooting）

## 1. GBK编码问题

### 问题表现
- 中文字符显示为乱码（如 `˶ʿ` 代替 `硕士`）
- 简历数据解析失败
- `NETWORK_ERROR` 返回

### 原因分析
这是原 opencli 版本的已知问题。在 Windows 上，subprocess 调用产生的 stdout 使用 GBK 编码，当简历包含 GBK 无法表示的 Unicode 字符（如 `•` bullet）时，CLI 进程内部直接崩溃。

### 解决方案
**Python版本已彻底解决**（继承 boss-agent-cli）：
- ✅ 直接 import Python 库，不走 subprocess
- ✅ 所有数据在进程内流转（UTF-8）
- ✅ 无编码转换

设置环境变量确保安全：
```bash
set PYTHONIOENCODING=utf-8
```

---

## 2. Cookie过期（登录失效）

### 问题表现
```json
{
  "error": {
    "code": 7,  // 或 37
    "message": "Cookie已过期"
  }
}
```

### 解决步骤
1. **立即停止** skill 运行（无需重试）
2. **重新登录**
   ```bash
   boss login
   ```
3. **等待下次触发**（2小时后自动恢复）

### 详细登录流程
```bash
# 方式1：扫码登录
boss login

# 方式2：Chrome自动登录（推荐CDP使用）
boss login --cdp

# 验证登录状态
boss status --live
```

---

## 3. CDP Chrome连接问题

### 问题表现
```json
{
  "error": {
    "code": "RECRUITER_CHAT_TAB_REQUIRED",
    "message": "please open https://www.zhipin.com/web/chat/index in your Chrome (CDP-attached)"
  }
}
```

### 受影响的操作
- `hr reply` — 发送消息
- `hr request-resume` — 请求简历

### 解决步骤

#### Step 1: 启动Chrome（CDP模式）
```bash
# Windows
"C:\Program Files\Google\Chrome\Application\chrome.exe" ^
  --remote-debugging-port=9222 ^
  --user-data-dir=C:\Users\<username>\AppData\Local\Google\Chrome\User Data

# macOS
/Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome \
  --remote-debugging-port=9222 \
  --user-data-dir=/Users/<username>/Library/Application\ Support/Google/Chrome
```

#### Step 2: 验证CDP连接
```bash
# 检查9222端口是否打开
curl http://localhost:9222/json/version

# 应该返回Chrome版本信息
```

#### Step 3: 打开聊天页面
在Chrome中打开：
```
https://www.zhipin.com/web/chat/index
```

#### Step 4: 重试命令
```bash
boss hr reply <friend_id> "消息内容"
```

---

## 4. 简历数据解析失败

### 问题表现
```
ERROR: 筛选 张三 时出错: KeyError: 'degreeCategory'
```

### 原因分析
- API 返回格式变化
- 简历字段缺失或结构改变
- JSON 格式错误

### 调试步骤
1. **查看日志**
   ```bash
   tail -f D:/boss-hiring-runtime/my-job/logs/phase1-*.log
   ```

2. **获取原始JSON**
   ```bash
   boss hr resume <security_id> --job-id <job_id> --raw
   ```

3. **检查数据结构**
   查看 JSON 中的路径：
   ```
   data.zpData.geekDetailInfo.geekBaseInfo.degreeCategory
   ```

4. **更新解析逻辑**
   修改 `phase1/screening.py` 中的 `parse_resume_json()` 函数

---

## 5. 任务无法启动

### 问题表现
```
ConfigError: run-context.json 不存在
```

### 解决
创建必需的配置文件：
```bash
mkdir -p D:/boss-hiring-runtime/my-job
touch run-context.json screen-rules.json candidates.json
```

参考 SKILL.md 第四节的配置模板。

---

## 6. 候选人列表为空

### 问题表现
```
阶段一完成：打招呼发送：0 人
```

### 可能原因

| 原因 | 检查方法 |
|------|----------|
| 没有新招呼 | `boss hr chat --label-id 1` |
| 全部被筛选掉 | 检查 `screen-rules.json` |
| API问题 | 检查日志中的错误 |

### 调试
```bash
# 手动获取新招呼
boss hr chat --label-id 1

# 检查某个候选人的简历
boss hr resume <security_id> --job-id <job_id> --raw
```

---

## 7. 简历接收失败

### 问题表现
```
RECRUITER_CHAT_TAB_REQUIRED: ExchangeResume confirm button not found
```

### 原因
CDP 页面中候选人对话未正确渲染。

### 解决
1. 确保 CDP Chrome 仍在运行
2. 刷新 https://www.zhipin.com/web/chat/index
3. 重试命令

---

## 8. 内存泄漏

### 问题表现
```
长时间运行后，内存占用不断增长
```

### 调试
```bash
# 监控进程内存
watch -n 1 'ps aux | grep python | grep boss_hr_recruiter'
```

### 解决
- 检查循环中是否有未释放的连接
- 确保异步操作正确关闭
- 查看日志中的警告信息

---

## 9. 网络超时

### 问题表现
```
TimeoutError: Request timeout
```

### 原因
- 网络延迟
- API 服务器响应缓慢
- 代理配置问题

### 解决
```bash
# 增加超时时间（编辑 config.py）
REQUEST_TIMEOUT = 30  # 默认 10 秒

# 检查网络连接
boss status --live

# 重试
python -m boss_hr_recruiter.main <runtime_dir>
```

---

## 10. 状态转移失败

### 问题表现
```
候选人状态未按预期转移
```

### 调试
```bash
# 查看当前状态
cat D:/boss-hiring-runtime/my-job/candidates.json | grep status

# 检查日志
tail -f D:/boss-hiring-runtime/my-job/logs/*.log
```

### 常见原因
- 收到的消息格式与预期不符
- 回复解析逻辑失败
- 数据存储时出错

---

## 日志位置

所有日志存储在：
```
$RUNTIME_DIR/logs/
├── main-YYYYMMDD.log
├── phase1-YYYYMMDD.log
├── phase2-YYYYMMDD.log
└── phase3-YYYYMMDD.log
```

查看实时日志：
```bash
tail -f D:/boss-hiring-runtime/my-job/logs/*.log
```

---

## 获取帮助

1. **查看完整日志** — 最详细的信息来源
2. **查看 SKILL.md** — 功能说明和使用指南
3. **查看源代码** — 逻辑实现细节
4. **查看 boss-agent-cli 文档** — 底层API说明

---

## 常见问题速查

| 症状 | 可能原因 | 解决方案 |
|------|---------|---------|
| 中文乱码 | GBK编码 | Python版本已解决 |
| Cookie失效 | 需要重新登录 | `boss login` |
| 无法发送消息 | CDP未连接 | 启动Chrome，打开聊天页面 |
| 候选人为空 | 无新招呼或全被筛选 | 检查筛选规则或招呼列表 |
| 内存泄漏 | 连接未释放 | 查看日志，检查连接处理 |
