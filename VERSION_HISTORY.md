# 稳定版本历史

## v1.0.1 - 话术库命中修复稳定版

### 更新日期
2026-05-23

### 修改文件
- `intercept_bot_local.py`
- `web_service.py`

---

### 更新内容

#### 1. 评论截流优先使用话术库

**问题**: 识别到 A/B/C/D 标签后，生成结果仍可能随机使用通用话术，导致主回复和备选话术与客户评论不匹配。

**修改内容**:
- 评论截流命中 A/B/C/D 标签后，优先从对应标签的话术库输出主话术。
- 备选话术改为从同一个标签的话术库中选择，避免混入无关通用鼓励话术。
- 增加简单情绪分支识别，优先匹配 `罪恶感循环`、`自我厌弃`、`耗竭感`、`自我否定` 等既有话术分支。

#### 2. 找搭子场景稳定命中

**问题**: 评论如 `saw ur comment about wanting a weight loss buddy! same here` 没有对应到“找搭子截流”，而是输出无关通用话术。

**修改内容**:
- 新增找搭子场景模板 `C：找搭子截流`。
- 增加 `weight loss buddy`、`accountability partner`、`need motivation`、`try together`、`一起减肥`、`互相监督` 等关键词识别。
- 命中找搭子场景时，主话术直接使用场景 C 话术，备选话术也保持找搭子方向。

#### 3. 输入框清除按钮

**修改内容**:
- 评论截流页的“帖子内容”和“评论内容”输入框新增 `清除` 按钮。
- DM 对话页当前输入框新增 `清除` 按钮。
- 清除评论内容时同步隐藏旧生成结果，避免误读旧内容。

### 验证结果

- `python3 -m py_compile web_service.py intercept_bot_local.py` 通过。
- `weight loss buddy` 示例可稳定返回 `C：找搭子截流`。
- 甜品、情绪暴食等已覆盖标签优先使用对应话术库和同标签备选话术。

---

## v1.0.0 - 初版稳定版本

## 更新日期
2026-05-23

## 修改文件
- `intercept_bot_local.py`
- `web_service.py`

---

## 更新内容

### 1. 模型加载优化

**问题**: 每次启动都尝试联网下载模型，连接失败报错
**修复位置**: `intercept_bot_local.py` - `_load_model()` 函数 (第 136 行左右)

**修改内容**:
- 移除 Hugging Face 镜像源配置
- 直接使用本地缓存路径
- 简化模型加载流程，移除不兼容的 Flash Attention

**本地模型路径**:
```
/Users/yuesen/.cache/huggingface/hub/models--Qwen--Qwen2-1.5B-Chat/snapshots/ba1cf1846d7df0a0591d6c00649f57e798519da8
```

---

### 2. 评论截流页面重构

**问题**: 备选话术与主回复几乎一样，缺乏多样性
**修复位置**: `intercept_bot_local.py` - `intercept()` 函数 (第 630 行左右)

**修改内容**:
- 完全重写话术生成逻辑
- 预定义 5 个完全不同的话术角度
- 每次随机打乱，选出 3 条（主回复 + 2备选）

**话术角度**:
1. **理解共情型** - "Hey girl! I totally get where you're coming from..."
2. **实用建议型** - "Hi there! Something that really made a difference..."
3. **积极鼓励型** - "Hey! Don't be too hard on yourself!"
4. **姐妹分享型** - "Hey sister! I feel you so much on this!"
5. **轻松幽默型** - "Hey! You know what? We've all been there!"

---

### 3. DM页面修复

**问题列表**:
- 用户消息和回复位置颠倒
- 缺少每条消息的中文翻译
- 气泡文字颜色可读性差

**修复位置**: `web_service.py` - HTML & CSS 模板

**修改内容**:
- CSS 调整消息对齐方式
- 新增 `/api/translate` 接口
- 气泡文字颜色优化（紫色气泡白色文字，白色气泡黑色文字）

---

### 4. 翻译优化

**问题**: 使用简单字典翻译，效果差且不全
**修复位置**: `intercept_bot_local.py` - `_simple_translate()` 函数 (第 569 行左右)

**修改内容**:
- 移除单词/短语字典翻译
- 使用 Qwen 模型直接翻译
- 更准确、更自然

---

### 5. 服务启动优化

**问题**: 模型加载滞后，第一次请求响应慢
**修复位置**: `web_service.py` (第 660-665 行)

**修改内容**:
- 服务启动时预加载 bot 实例
- 提前调用 `_load_model()`
- 用户第一次请求即可快速响应

---

## Git 提交记录
- **Commit ID**: `e0cc323`
- **提交信息**: "初版稳定版本发布"

## GitHub 仓库
https://github.com/lbbin1988/talktool-lossweight-dev

---

## 测试建议
1. 启动服务: `python web_service.py`
2. 打开浏览器访问: http://localhost:5005
3. 测试评论截流页面，确认三条话术完全不同
4. 测试DM页面，确认消息位置和翻译正常
5. 多次点击生成，验证随机多样性
