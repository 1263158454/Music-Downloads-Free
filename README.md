# 🎵 Music Downloader

基于 **musicdl** 多源链的歌曲下载工具。自动从 **QQ音乐 → 网易云 → 酷狗 → 酷我 → 咪咕** 依次搜索，下载完整歌曲并清理文件名。

## ✨ 功能

| 命令 | 功能 |
|:---|:---|
| `search <关键词>` | 跨 5 个音乐源搜索歌曲 |
| `download <关键词>` | 单首下载（多源链 + 完整性校验 + 文件名自动清理） |
| `download-idx <N> <关键词>` | 搜索结果中指定序号下载 |
| `download-playlist <URL>` | 下载网易云歌单全部歌曲 |
| `check-playlist <路径>` | 完整性检测 |
| `rename [路径]` | 批量清理文件名（去随机ID + 删重复） |

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

# 下载单首
python scripts/music.py download 晴天 周杰伦

# 下载歌单
python scripts/music.py download-playlist "https://music.163.com/playlist?id=xxx"

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
├── SKILL.md                        ← 完整技能文档（含安装/校验/Agent约束）
├── scripts/
│   └── music.py                    ← 主脚本（6个命令）
└── references/
    ├── musicdl-modifications.md    ← 码率修改记录
    ├── netease-playlist-api.md     ← 歌单API文档
    ├── audio-integrity-check.md    ← 完整性校验逻辑
    └── multi-source-architecture.md ← 多源链架构设计
```

## 📄 开源

本项目基于 musicdl 开发，感谢 [CharlesPikachu/musicdl](https://github.com/CharlesPikachu/musicdl) 提供的底层支持。
