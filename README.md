# 🎵 Music Downloader

基于 **musicdl** 多源链的歌曲下载工具。自动从 **QQ音乐 → 网易云 → 酷狗 → 酷我 → 咪咕** 依次搜索，下载完整歌曲并清理文件名。

## ✨ 功能

| 命令 | 功能 |
|:---|:---|
| `search <关键词>` | 跨 5 个音乐源搜索歌曲 |
| `check-duplicate <关键词>` | 检测本地是否已有该歌曲（歌名+歌手+时长三重匹配） |
| `download <关键词> [--action skip\|overwrite\|coexist]` | 单首下载（重复检测 + 多源链 + 完整性校验） |
| `download-idx <N> <关键词> [--action skip\|overwrite\|coexist]` | 搜索结果中指定序号下载 |
| `download-playlist <URL> [--action skip\|overwrite\|coexist]` | 下载网易云歌单（逐首检测重复 + 批量策略） |
| `check-playlist <路径>` | 完整性检测 |
| `rename [路径]` | 批量清理文件名（去随机ID + 删重复） |

## 🔄 重复检测机制

三重匹配策略，避免重复下载：

| 维度 | 匹配条件 |
|:---|:---|
| 🏷️ **歌名** | 归一化后字符串相似度 ≥ 0.8 |
| 👤 **歌手** | 歌手关键词出现在文件名中 |
| ⏱ **时长** | 实际时长与预期偏差 ≤ ±15% |

**置信度高** → 自动跳过；**拿捏不准** → 输出结构化信息供用户决策。

支持 `--action` 参数指定重复处理策略：

| 参数 | 效果 |
|:---|:---|
| `--action skip` | 跳过，保留原文件 |
| `--action overwrite` | 删除旧文件，下载新文件 |
| `--action coexist` | 并存（自动加 (1) 后缀） |

歌单下载时，`--action` 对剩余所有歌曲批量生效，无需逐首确认。

## 🚀 快速开始

### 前置依赖

- Python ≥ 3.8（推荐 3.11）
- ffmpeg / ffprobe（音频校验用）
- [musicdl](https://github.com/CharlesPikachu/musicdl)

### 安装

```bash
# 1. 安装 ffmpeg
sudo apt install ffmpeg -y

# 2. 克隆 musicdl
git clone https://github.com/CharlesPikachu/musicdl.git /path/to/musicdl
cd /path/to/musicdl && pip install -r requirements.txt

# 3. 下载本技能
git clone https://github.com/1263158454/Music-Downloads-Free.git
cd Music-Downloads-Free

# 4. 修改 scripts/music.py 第 8 行的 musicdl 路径
#    将 '/home/admin/Downloads/musicdl' 改为你的 musicdl 路径

# 5. 修改 scripts/music.py 第 11 行的下载保存路径（可选）
#    WORK_DIR = '/home/admin/Music'
```

### 使用

```bash
# 搜索歌曲
python scripts/music.py search 晴天 周杰伦

# 预检是否已存在
python scripts/music.py check-duplicate 晴天 周杰伦

# 下载单首（自动跳过已存在的）
python scripts/music.py download 晴天 周杰伦 --action skip

# 覆盖已有的
python scripts/music.py download 晴天 周杰伦 --action overwrite

# 下载歌单（重复的跳过）
python scripts/music.py download-playlist "https://music.163.com/playlist?id=xxx" --action skip

# 清理文件名
python scripts/music.py rename /path/to/music/folder
```

## 🔧 多源链架构

```
QQ音乐 (主源) → 网易云 → 酷狗 → 酷我 → 咪咕
每步 ffprobe 完整性校验（拒绝 <30s 试听版）
下载后自动清理文件名中的随机ID后缀
```

## ⚙️ 码率优先级

默认：**MP3 320k（高品质）→ 标准 → FLAC（无损）**

> 码率优先级需要修改 musicdl 库源码中的 quality 列表，详情见 `references/musicdl-modifications.md`。如有需要请按说明操作。

## 📁 目录结构

```
Music-Downloads-Free/
├── SKILL.md                        ← 完整技能文档（含安装/校验/Agent约束/重复检测机制）
├── README.md                       ← 本文件
├── scripts/
│   ├── music.py                    ← 主脚本（8个命令）
│   └── music_ssl.py               ← SSL 降级 wrapper（CA证书过旧时备用）
└── references/
    ├── musicdl-modifications.md    ← 码率修改记录
    ├── netease-playlist-api.md     ← 歌单API文档
    ├── audio-integrity-check.md    ← 完整性校验逻辑
    └── multi-source-architecture.md ← 多源链架构设计
```

## 📄 开源

本项目基于 musicdl 开发，感谢 [CharlesPikachu/musicdl](https://github.com/CharlesPikachu/musicdl) 提供的底层支持。
