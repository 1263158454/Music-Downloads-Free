---
name: music-downloader
title: Music Downloader — 多源搜索下载歌曲（mp3 320k）
description: 基于 musicdl 多源（QQ/网易云/酷狗/酷我/咪咕）搜索并下载歌曲，默认 mp3 320kbps 格式+完整性校验+文件名自动清理，保存到指定目录（首次安装需问询路径），包含完整安装说明/校验流程/Agent边界约束
---

# Music Downloader Skill

基于 **musicdl 多源链** 的歌曲下载工具。默认下载 **mp3 320kbps**，按源优先级依次尝试：
**QQ音乐 → 网易云 → 酷狗 → 酷我 → 咪咕**，每步 ffprobe 完整性校验。
下载成功后 **自动清理文件名** 中的随机 mediaID 后缀。

---

## 1. 安装说明

### 1.1 前置依赖

| 依赖 | 版本要求 | 用途 |
|:---|:---:|:---|
| Python | ≥ 3.8 | 运行脚本（推荐 3.11） |
| ffprobe / ffmpeg | 任意版本 | 音频完整性校验 |
| pip / uv | — | 安装 Python 依赖 |
| git | — | 拉取 musicdl 库（可选） |

### 1.2 安装步骤

```bash
# 1. 安装 ffmpeg（如未安装）
sudo apt install ffmpeg -y
# 或
brew install ffmpeg

# 2. 克隆 musicdl 到本地
git clone https://github.com/CharlesPikachu/musicdl.git /path/to/musicdl
# 或从压缩包解压到指定路径

# 3. 安装 musicdl 依赖
cd /path/to/musicdl
pip install -r requirements.txt
# 或使用 uv（更快）：
uv pip install -r requirements.txt

# 4. 将 skill 解压/复制到 skills 目录
# （假设 Hermes Agent 的 skills 目录）
cp -r music-downloader/ ~/.hermes/skills/media/

# 5. 修改 scripts/music.py 中的 sys.path 指向你的 musicdl 路径
# 第 8 行：sys.path.insert(0, '/path/to/musicdl')

# 6. 确保 music.py 有执行权限
chmod +x scripts/music.py
```

> **musicdl GitHub**: [https://github.com/CharlesPikachu/musicdl](https://github.com/CharlesPikachu/musicdl)
>
> musicdl 是此 skill 的核心依赖，提供了 QQ音乐、网易云、酷狗、酷我、咪咕等国内音乐平台的搜索与下载 API。

### 1.3 首次安装路径设置

首次使用此 skill 时，**必须向用户问询单首歌曲的下载路径**，例如：

> "请告诉我单首歌曲的下载保存路径（默认: /home/admin/Music）："

获取路径后在 `scripts/music.py` 中修改第 11 行的 `WORK_DIR` 变量：

```python
WORK_DIR = '/home/admin/Music'   # ← 改为用户指定的路径
```

歌单下载默认在 `WORK_DIR` 下创建 `<歌单名>/` 子文件夹，无需额外配置。

### 1.4 码率优先级配置（可选）

默认码率优先级为 **MP3 320k → 标准 → FLAC**，此配置需要修改 musicdl 库源码。
如用户首次使用时不特别说明，**不执行此修改**，保留 musicdl 默认码率逻辑。
只有在用户明确要求后才进行修改，修改记录见 `references/musicdl-modifications.md`。

---

## 2. 文件结构

```text
music-downloader/
├── SKILL.md                           ← 本文件（技能说明）
├── scripts/
│   ├── music.py                       ← 主执行脚本（搜索/下载/歌单/校验/清理）
│   └── music_ssl.py                   ← SSL 降级 wrapper（仅当系统 CA 证书过旧时使用）
├── references/
│   ├── musicdl-modifications.md       ← musicdl 各源码率修改记录
│   ├── netease-playlist-api.md        ← 网易云歌单 API 文档
│   ├── audio-integrity-check.md       ← 完整性校验逻辑细节
│   └── multi-source-architecture.md   ← 多源链架构设计文档
```

**`scripts/music.py` 支持的 8 个命令：**

| 命令 | 功能 |
|:---|:---|
| `search <关键词>` | 跨 5 个源搜索歌曲 |
| `check-duplicate <关键词>` | 三重匹配检测重复（歌名+歌手+时长），输出 JSON 供 agent 决策 |
| `download <关键词> [--action skip\|overwrite\|coexist]` | 带重复检测的下载（默认 coexist） |
| `download-idx <N> <关键词> [--action skip\|overwrite\|coexist]` | 指定序号下载，带重复检测 |
| `download-playlist <URL> [--action skip\|overwrite\|coexist]` | 下载歌单（逐首检测重复 + 支持批量策略） |
| `check-playlist <路径>` | 完整性检测（对比预期时长） |
| `rename [路径]` | 批量清理文件名（去随机ID + 删重复） |

> **`scripts/music_ssl.py`** — 与 `music.py` 命令完全相同的 SSL 降级 wrapper，仅在系统 CA 证书过旧导致 `SSL: CERTIFICATE_VERIFY_FAILED` 时使用。调用方式：`python music_ssl.py <命令>`（代替 `python music.py <命令>`）。注意：此 wrapper **不能绕过主动网络拦截**（如 URL过滤、P2P流媒体屏蔽），它只解决被拦截服务器的证书链不完整问题。

---

## 3. 触发词

当用户说出以下短语时，自动执行对应命令：

### 🎵 搜索歌曲

| 用户说 | 执行 |
|:---|:---|
| "搜歌 <关键词>" / "搜索歌曲 <关键词>" | `search <关键词>` |
| "搜一下 <关键词>" / "帮我搜首歌 <关键词>" | `search <关键词>` |
| "有什么歌可以推荐" / "搜索 <关键词>" | `search <关键词>` |

### ⬇️ 下载单首歌曲

| 用户说 | 执行 |
|:---|:---|
| "下载歌曲 <关键词>" / "下歌 <关键词>" | `download <关键词>` |
| "下载 <歌手>的<歌名>" / "帮我把<歌名>下载下来" | `download <歌手> <歌名>` |
| "下第N首 <关键词>" / "下载第N个结果" | `download-idx <N> <关键词>` |
| "帮我下个歌 <关键词>" / "下载一首歌 <关键词>" | `download <关键词>` |

### 📋 下载歌单

| 用户说 | 执行 |
|:---|:---|
| "下载歌单 <URL>" / "下载这个歌单 <URL>" | `download-playlist <URL>` |
| "把歌单下下来" / "帮我下个歌单 <URL>" | `download-playlist <URL>` |
| "保存这个歌单" / "歌单下载" + URL | `download-playlist <URL>` |

### 🔍 完整性检测

| 用户说 | 执行 |
|:---|:---|
| "检查歌单 <路径>" / "检测完整性 <路径>" | `check-playlist <路径>` |
| "检查下歌单有没有不完整的" | `check-playlist <路径>` |

### 🧹 文件名清理

| 用户说 | 执行 |
|:---|:---|
| "清理歌单文件名" / "整理下载目录" | `rename [路径]` |
| "把文件名整理一下" / "去重" | `rename [路径]` |

### ⚙️ 重复检测

| 用户说 | 执行 |
|:---|:---|
| "检测重复 <关键词>" / "检查重复 <关键词>" | `check-duplicate <关键词>` |
| "看看有没有重复" / "已经下过了吗 <关键词>" | `check-duplicate <关键词>` |

### ⚙️ 配置管理

| 用户说 | 执行 |
|:---|:---|
| "更改下载路径" | 问询新路径，更新 `WORK_DIR` |
| "查看下载路径" | 输出当前 `WORK_DIR` |
| "更改码率偏好" | 问询偏好，选择是否修改 musicdl 源码 |

---

## 4. 多源链架构

```
QQ音乐 (主源, search_size_per_page=5, RETRY_COUNT=2)  ← 保持全搜索深度
  ↓ 最多试3个搜索结果, 歌手优先排序
  ↓ ffprobe 校验通过 → 清理文件名 → 返回
  ↓ 全部失败
网易云 (备源1, 超时45s) → 失败 → 酷狗(30s) → 失败 → 酷我(20s) → 失败 → 咪咕(15s)
  ↓ 全部失败 → 标记为不完整
```

**关键设计原则**：永远不要为了加备源而削弱主源的搜索强度。备源通常只补回极少量歌曲（实测约10%），但主源的搜索深度直接影响90%歌曲的下载成功率。

musicdl 注册了 50+ 个 Client，但国内网络环境下只有上述 5 个源可用。其余（Spotify/Apple Music/YouTube/Deezer/Tidal/Amazon/Qobuz/SoundCloud 等）均因 GFW 阻断或国内无内容而不可达。

---

## 5. 使用方法

```bash
# 跨源搜索
python scripts/music.py search 晴天 周杰伦

# 单首下载（自动尝试所有源直到找到完整版 + 清理文件名）
python scripts/music.py download 晴天 周杰伦

# 下载指定序号（从 1 开始）
python scripts/music.py download-idx 2 晴天 周杰伦

# 下载歌单全部歌曲（保存到 <WORK_DIR>/<歌单名>/）
python scripts/music.py download-playlist "https://y.music.163.com/m/playlist?id=..."

# 完整性检测
python scripts/music.py check-playlist "/path/to/歌单文件夹/" --playlist-url "..."

# 清理文件名（去掉随机ID后缀 + 删除重复）
python scripts/music.py rename "/path/to/歌单文件夹/"
# 不加路径 = 递归处理整个 WORK_DIR
python scripts/music.py rename
```

---

## 6. 安装完成校验

安装完成后，按以下步骤执行校验，确保 skill 正常工作。

> **`scripts/music_ssl.py`** — 与 `music.py` 命令完全相同的 SSL 降级 wrapper，仅在系统 CA 证书过旧导致 `SSL: CERTIFICATE_VERIFY_FAILED` 时使用。调用方式：`python music_ssl.py <命令>`（代替 `python music.py <命令>`）。注意：此 wrapper **不能绕过主动网络拦截**（如 URL过滤、P2P流媒体屏蔽），它只解决被拦截服务器的证书链不完整问题。

### 6.1 文件完整性校验

确认以下文件存在且可执行：

```bash
# 检查主脚本
ls -la scripts/music.py
# 应输出: -rwx... music.py（有执行权限）

# 检查引用文档
ls references/
# 应包含: musicdl-modifications.md  netease-playlist-api.md
#         audio-integrity-check.md  multi-source-architecture.md
```

### 6.2 语法校验

```bash
python -m py_compile scripts/music.py
# 无输出 = 语法通过 ✅
```

### 6.3 单首歌曲下载校验

```bash
python scripts/music.py download 周杰伦的晴天
```

**预期结果：**
- 搜索日志显示 5 个源依次尝试
- 至少一个源返回完整版本（时长 ≥ 30s）
- 文件名不含随机ID后缀（如 `周杰伦的晴天.mp3` 而非 `周杰伦的晴天 - 00XXX.mp3`）
- 输出 ✅ 完整 + 时长标记

### 6.4 歌单下载校验

```bash
python scripts/music.py download-playlist \
  "https://y.music.163.com/m/playlist?id=7958405730&userid=472346207&creatorId=472346207"
```

**预期结果：**
- 成功读取歌单歌曲列表
- 在 `WORK_DIR` 下创建歌单名子文件夹
- 每首歌显示预期时长与实际时长对比
- 下载报告显示：完整数 + 不完整数 + 失败数
- 文件名均不含随机ID后缀

### 6.5 校验通过标准

| 检查项 | 通过标准 |
|:---|:---|
| 文件完整性 | 6 个必要文件全部存在 |
| 语法校验 | `py_compile` 无报错 |
| 单首下载 | 至少下载成功 1 首完整歌曲 |
| 歌单下载 | 歌单全部歌曲成功下载（允许少量因版权/网络原因失败） |
| 文件名 | 无随机ID后缀残留 |

### 6.6 校验报告模板

校验完成后，需整理成以下格式报告给用户：

```
━━━ Music Downloader 安装校验报告 ━━━

📦 文件完整性: ✅ (6/6)
   scripts/music.py           ✅
   references/*.md (4个)      ✅
   SKILL.md                   ✅

🧪 语法校验: ✅

🎵 单首下载测试:
   测试歌曲: 周杰伦的晴天
   结果: ✅ 完整 [来源] 时长 X:XX
   文件路径: /path/to/歌曲文件.mp3
   文件大小: X.X MB

📋 歌单下载测试:
   测试歌单: 7958405730
   歌曲总数: N
   完整: N | 不完整: N | 失败: N
   来源分布: QQ N | 网易云 N | 其他 N
   总大小: XX MB
   文件名清理: ✅

📝 使用说明:
   - 搜索歌曲 → "搜歌 <关键词>"
   - 下载歌曲 → "下载歌曲 <关键词>"
   - 下载歌单 → "下载歌单 <URL>"
   - 检查完整性 → "检查歌单 <路径>"
   - 清理文件名 → "清理歌单文件名"

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

---

## 7. Agent 边界约束

此 skill 的 agent（AI 代理）在处理与 music-downloader 相关的任务时，必须遵守以下约束：

### ✅ 允许做的事

- 使用 `scripts/music.py` 的 8 个命令（search / download / download-idx / download-playlist / check-playlist / check-duplicate / rename）
- 读取和引用 `references/` 下的文档
- 根据用户要求修改 `WORK_DIR` 路径（仅改 `scripts/music.py` 第 11 行）
- 根据用户明确要求修改 musicdl 源码的码率优先级（前提是先在 `references/musicdl-modifications.md` 检查已有修改记录）
- 第一次使用此 skill 时问询下载路径
- 向用户提供使用帮助和校验报告

### ❌ 严格禁止做的事

- **禁止修改 `scripts/music.py` 的执行逻辑**（搜索逻辑、下载流程、多源链顺序、完整性校验、文件名清理等核心功能）——除非用户明确要求
- **禁止擅自修改 musicdl 库源码**（`/path/to/musicdl/musicdl/modules/sources/` 下的各源文件）——码率优先级修改只在用户要求时才执行，且必须先查看 `references/musicdl-modifications.md`
- **禁止擅自添加/删除/重排多源链中的源**——`SOURCE_CHAIN` 的配置经过了验证，擅自改动可能降低成功率
- **禁止猜测或编造命令**——所有操作必须使用 `scripts/music.py` 的 6 个命令之一
- **禁止绕过 `scripts/music.py` 直接调用 musicdl API**——配置已写在脚本中，直接调 API 会走默认无损优先的旧逻辑
- **禁止在未问询用户的情况下更改下载路径或码率配置**
- **禁止自动执行安装完成校验**——校验步骤需要向用户说明并征得同意后再执行（"已就绪，需要我运行安装校验吗？"）
- **禁止将 skill 的错误归因于外部网络/API 时误导用户**——如果下载失败，明确区分：网络问题（GFW/超时）、源无版权（找不到歌曲）、文件不完整（被拒绝）

### ⚠️ 特别提醒

- musicdl 的第三方解析器域名（如 `cenguigui.cn`、`haitangw.net`、`rrvenn.cn` 等）可能间歇性不可用，这是正常的 API 波动，不是脚本错误
- **任何对 `scripts/music.py` 或 musicdl 源码的修改都必须先向用户报告方案（文字计划），获得确认后再执行**
- 单首下载和歌单下载共用同一套核心逻辑（`_multi_source_download` → `_try_source`），不要尝试分开修改

---

## 8. 完整性校验

每首歌下载后自动执行 `ffprobe` 检测：
- 获取实际音频时长
- 对比网易云 API 返回的预期时长（歌单下载时）
- 判定：实际/预期 < 50% 或 < 30s → 不完整，自动尝试下一源/下一结果
- 无预期时长（单曲下载时）：仅用 30s 阈值简单判断

---

## 9. 文件名自动清理

下载成功后自动调用 `_clean_song_path()` 去除随机ID后缀：

| 原文件名 | 清理后 |
|---|---|
| `白猫海贼船 - 001YvwLN0Gj9fc.m4a` | `白猫海贼船.m4a` |
| `Love is You - 1340165691.mp3` | `Love is You.mp3` |
| `He_Starlight - 29819059.lrc` | `He_Starlight.lrc` |

后缀是 QQ 音乐的 mediaID（字母数字混合）或网易云的 songID（纯数字），musicdl 下载时保留在文件名中用于区分同名文件。清理只在 **下载完成并确认完整性后** 进行，不影响下载过程。

---

## 10. 重复检测机制（v2.0）

### 10.1 三重匹配策略

| 维度 | 匹配条件 | 权重 |
|:---|:---|:---:|
| 🏷️ **歌名** | 归一化后字符串相似度 ≥ 0.3 才纳入候选 | 基础 |
| 👤 **歌手** | 歌手关键词出现在文件名中 | +0.3 |
| ⏱ **时长** | 实际时长与预期时长偏差 ≤ ±15% | +0.3 |

### 10.2 置信度判定

| 条件 | 置信度 | 建议行为 |
|:---|:---:|:---|
| 歌名≥80% **且** 歌手匹配 **且** 时长匹配 | high | **skip** 自动跳过 |
| 歌名≥80% **且** 时长匹配 | high | **skip** 自动跳过 |
| 歌名≥60% **且** 时长匹配 | medium | **skip** 可跳过 |
| 歌名≥60% **但** 时长不匹配 | low | **ask** 需确认 |
| 歌名≥80% **但** 时长不匹配 | low | **ask** 需确认 |
| 其他 | medium | **download** 直接下 |

### 10.3 决策参数 `--action`

| 参数 | 效果 |
|:---|:---|
| `--action skip` | 检测到重复直接跳过，保留原文件 |
| `--action overwrite` | 检测到重复先删除旧文件，再下载新文件 |
| `--action coexist`（默认） | 检测到重复也正常下载，musicdl 自动追加 ` (1)` 后缀并存 |

### 10.4 歌单批量决策

下载歌单时，每首歌遇到重复都会输出 JSON 供 agent 决策。`--action` 参数一旦设置，**对该歌单剩余所有歌曲均生效**（无需逐首确认）。

### 10.5 Agent 决策流程

```
用户请求 → agent 调用 check-duplicate
  ├─ 建议 skip → 直接跳过（通知用户）
  ├─ 建议 download → 直接下载
  └─ 建议 ask → agent 向用户展示 match 信息（歌名/歌手/时长对比）
                  └─ 用户选择 skip/overwrite/coexist
                      └─ agent 用 --action 参数重调 download 命令
```

---

## 11. 配置说明

| 配置项 | 值 |
|:---|:---|
| **保存目录** | 首次安装时由用户指定（默认为 `/home/admin/Music/`） |
| **单首下载路径** | `WORK_DIR/`（根目录） |
| **歌单下载路径** | `WORK_DIR/<歌单名>/`（子文件夹） |
| **码率优先级** | MP3 320k → 标准 → FLAC（需修改 musicdl 源码，默认不启用） |
| **主源搜索** | `search_size_per_page=5, max_retries=1, RETRY_COUNT=2` |
| **多源超时** | QQ 60s, 网易云 45s, 酷狗 30s, 酷我 20s, 咪咕 15s |
| **Python 路径** | `scripts/music.py` 自带 shebang，如有需要覆盖为 `python3 scripts/music.py` |
| **musicdl 路径** | 在 `scripts/music.py` 第 8 行配置 |

---

## 12. 常见坑点

### ⚠️ 不要削弱主源搜索参数
当需要添加备源时，**不要为了给备源省时间而降低主源的搜索深度**（RETRY_COUNT、search_size_per_page）。主源如果因为参数缩水漏掉了本来能搜到的歌，所有备源加起来也补不回来。

### ⚠️ QQ 音乐 API 网络波动
`c.y.qq.com` 和 `u.y.qq.com` 有被 GFW 阻断的风险。如果搜索返回空，先 curl 测试：
```bash
curl -s 'https://c.y.qq.com/splcloud/fcgi-bin/smartbox_new.fcg?key=晴天&format=json' | head -c 200
```
空响应 → 网络问题，换个网络环境或稍后再试。脚本已内置 2 次重试 + 3s 间隔。

### ⚠️ 外国歌可能没有 MP3
QQ 音乐对外国歌（如 Taylor Swift）的授权可能仅包含 AAC/M4A 格式。此时自动降级为 m4a（C600 192k AAC ≈ MP3 320k 听感）。中文歌通常正常返回 mp3。

### ⚠️ 搜索引擎不支持歌手匹配
仅 QQ 音乐源支持歌手匹配（在搜索结果中优先排同名歌手版本）。其他源的搜索结果由 API 决定顺序，无法按歌手重排。

### ⚠️ 码率优先级必须改库源码，不止脚本层
musicdl 各源在 `_parse` 方法内部遍历自己的 quality 列表并返回第一个可用的。**脚本层无法干预码率选择。** 详情见 `references/musicdl-modifications.md`。

### ⚠️ 重新跑测试会累积 `(1)` 重复文件
musicdl 下载同名文件时自动追加 ` (1)` 后缀。每次重新下载歌单都会产生一批 `(1)` 副本。运行 `rename` 命令即可一键清理 + 重命名。

### ⚠️ 不要直接调 `musicdl.MusicClient()` 下载
配置已写在 `music.py` 脚本中。如果用高层 API：`musicdl.MusicClient()`，默认 work_dir 仍是 `musicdl_outputs`，且走原版无损优先的解析逻辑。

### ⚠️ 网易云音乐 API 在中国企业/校园网中常被拦截
`music.163.com` 的 API 在中国大陆的企业/校园网络中经常被 **URL过滤（P2P流媒体）** 规则拦截。表现行为：

- **Python 报错**: `SSL: CERTIFICATE_VERIFY_FAILED` — 不是真的证书问题，是网络中间人返回了自签名拦截页
- **curl 响应**: 返回 `URL过滤` HTML 页面（`http://172.18.88.12/disable/disable.htm?url_type=P2P流媒体/网易云音乐`）
- **间歇性**: 拦截不是 100% 的，有时能通有时不能

**处理方案（按优先级）：**
1. **重试** — 拦截通常是间歇性的，等几秒重试可能就通了
2. **更换网络环境** — 断开公司 VPN 或换手机热点即可绕开
3. **使用 proxy** — 设置 `http_proxy`/`https_proxy` 环境变量指向可用的代理服务器
4. **安装 certifi**（推荐）— 如果报错是 `unable to get local issuer certificate`（非拦截页），说明系统 CA 证书过旧。安装 `certifi` 可获得最新的 CA 证书包：
   ```bash
   pip install certifi
   # 或
   uv pip install certifi --python 3.11
   ```
   这解决的是 Python 使用系统旧 CA 包导致无法验证 SSL 证书的问题。musicdl 的依赖（requests/httpx）会自动使用 certifi。
5. **SSL 降级 wrapper**（不推荐）— 仅在无法安装 certifi 时备用。项目附带了 `scripts/music_ssl.py`，其使用 `ssl._create_unverified_context` 绕过证书校验。注意：**如果被网络主动拦截（返回 URL过滤页面），降级 SSL 也只能看到拦截页面**，不能真正解决问题。

> 区分：`unable to get local issuer certificate` = CA 证书过旧（装 certifi 解决）；收到 URL过滤 HTML = 网络拦截（换网络环境解决）。两者经常混淆，务必先检查 curl 实际返回内容再决策。

### ⚠️ `rename` 命令采用两阶段清理，解决 `_1` 后缀残留
`cmd_rename` 分两阶段执行：
1. **Phase 1**: 删除 ` (1).` 和 `_1.` 重复文件（如果主文件存在）——前者来自 musicdl 自动编号（多次下载同首歌），后者来自清理工具早期 bug（清理顺序错误导致主文件被重命名为 `_1`）
2. **Phase 2**: 重命名剩余文件，去掉随机ID后缀

早期版本存在 bug：先处理 `(1)` 文件（重命名为干净名），导致非 `(1)` 文件重命名时冲突变成 `_1`。当前版本已修复为先删重复再重命名。如果用户报告有 `_1` 文件，运行 `rename` 即可一键清理。
