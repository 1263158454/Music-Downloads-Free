# musicdl 各源码率修改记录

对 `/home/admin/Downloads/musicdl/musicdl/` 中各源文件的定制修改。

## 修改动机

将所有源从 **FLAC 无损优先** 改为 **MP3 320k（高品质）→ 标准 → 无损** 的码率优先级。用户明确偏好：高品质 mp3 优先于无损 FLAC。

## 核心原则

**不要在 music.py 脚本层做码率排序——必须改 musicdl 库源码本身。** 
musicdl 各源的 `_parse` 方法内部遍历自己的 quality 列表并返回第一个可用的，所以脚本层无法干预。要改码率顺序，必须改库里的 `MUSIC_QUALITIES`、`SORTED_QUALITIES` 或对应的 br/quality 列表。

---

## QQ 音乐 (`qqutils.py` + `qq.py`)

### `qqutils.py` — 码率等级精简

**SongFileType.SORTED_QUALITIES**
- 移除 FLAC：`AI00.flac`, `Q000.flac`, `Q001.flac`, `F000.flac`
- 移除 OGG：`O801.ogg`, `O800.ogg`, `O600.ogg`, `O400.ogg`
- 保留：`M800.mp3`(320k), `M500.mp3`(128k), `C600.m4a`(192k AAC), `C400.m4a`(128k AAC), `C200.m4a`(64k AAC)

**EncryptedSongFileType.SORTED_QUALITIES**
- 移除 mflac：`AIM0.mflac`, `Q0M0.mflac`, `Q0M1.mflac`, `F0M0.mflac`
- 保留：`O801.mgg`, `O800.mgg`, `O6M0.mgg`, `O4M0.mgg`

### `qq.py` — 第三方解析器精简

移除不稳定解析器（l1/l2/l4），只保留 l3（MP3/M4A 专用），顺序：

| 解析器 | 平均耗时 | 特点 |
|:---|:---:|:---|
| `cyapi` | ~2.7s | 返回 mp3 320k 最快 |
| `tangapi` | ~1.3s | 最快但默认返回 m4a |
| `lxmusicapi` | ~3.9s | 兜底 |

`nkiapi`（`api.nki.pw`）被移除 — 固定超时 10s。

### `qq.py` — `_parsewithtangapi` 品质顺序调整

```python
# 之前: sq → pq → accom → hq → url → standard → fq
# 之后: hq → pq → accom → sq → url → standard → fq
```

先试 `song_play_url_hq`（MP3 320k 或 AAC 256k），跳过 `song_play_url_sq`（FLAC）。

### `qq.py` — 官方 API 跳过优化

- 第三方已返回 **mp3** → 直接返回，不调官方 API
- 第三方返回 **m4a** → 尝试官方 M800（MP3 320k）一次，超时 5s
- M800 失败 → 回退第三方 m4a 结果

### `qq.py` — lossless 标志强制 False

```python
# 之前: False if self.default_cookies or request_overrides.get('cookies') else True
# 之后: False
```

移除 song_info_flac.largerthan 覆盖逻辑。

---

## 网易云 (`neteaseutils.py`)

**MUSIC_QUALITIES** 整体重排，将 `exhigh`(320k) 提到第一位：

```python
# 原始 (musicdl 默认): ['jymaster', 'dolby', 'sky', 'jyeffect', 'hires', 'exhigh', 'standard', 'lossless']
# 当前:           ['exhigh', 'standard', 'lossless', 'jymaster', 'dolby', 'sky', 'jyeffect', 'hires']
```

**关键**：`exhigh` 必须排在 `lossless`、`hires`、`jymaster` 等所有高清格式之前，否则 API 会先返回 FLAC/母带。

---

## 酷狗 (`kugou.py`)

共 4 处修改（按行号）：

| API / 位置 | 行号 | 之前 | 之后 |
|------------|:----:|:----|:----|
| `_parsewithcggapi` | 59 | `['lossless', 'exhigh', 'standard']` | `['exhigh', 'standard', 'lossless']` |
| `_parsewithhaitangwapi` | 80 | `['hires', 'lossless', 'exhigh']` | `['exhigh', 'standard', 'lossless']` |
| `_parsewithliuyunidcapi` | 102 | `['clear', 'atmos', 'flac24bit', 'flac', '320k', '128k'][:-1]` → `['128k']` | `['320k', '128k', 'flac', 'flac24bit', 'clear', 'atmos'][:-2]` → `['320k']` |
| `_parsewith317akapi` | 125 | `['6', '5', '4', '3', '2', '1']` (6=FLAC) | `['5', '4', '3', '2', '1', '6']` (5=320k) |

---

## 酷我 (`kuwo.py`)

共 5 处修改（按行号）：

| API / 位置 | 行号 | 之前 | 之后 |
|------------|:----:|:----|:----|
| 类属性 `QUALITIES` | 36 | `[(22000, 'flac'), (320, 'mp3')]` | `[(320, 'mp3'), (22000, 'flac')]` |
| 类属性 `ENC_MUSIC_QUALITIES` | 37 | `[(4000, '4000kflac'), (2000, '2000kflac'), (320, '320kmp3'), (192, '192kmp3'), (128, '128kmp3')]` | `[(320, '320kmp3'), (192, '192kmp3'), (128, '128kmp3'), (4000, '4000kflac'), (2000, '2000kflac')]` |
| `_parsewithyyy001api` | 113 | `["ff", "p", "h"]` (ff=FLAC, p=播放/低质, h=高音质) | `["h", "p", "ff"]` |
| `_parsewithnxinxzapi` | 169 | `['lossless', 'exhigh', 'standard']` | `['exhigh', 'standard', 'lossless']` |
| `_parsewithhaitangwapi` + 备用 | 189, 209 | `['master', 'atmos_plus', 'atmos', 'flac', '320k']` → `['flac']` | `['atmos_plus', 'atmos', 'flac', '320k', 'master']` → `['320k']` |

---

## 咪咕 (`migu.py`)

**`_parsewithofficialapiv1`** (line 76)：排序 key 从按文件大小降序改为按格式优先级：

```python
# 之前: FLAC(文件大) 优先
key=lambda x: int(safe_obtain_filesize_func(x)), reverse=True

# 之后: HQ/PQ(mp3/320k) 优先于 SQ/ZQ(FLAC)
key=lambda x: (0 if x.get('formatType') in ('HQ', 'PQ') else 1, -(int(safe_obtain_filesize_func(x)) or 0))
```

---

## `base.py` — 保存路径简化

```python
# 之前: {work_dir}/{source}/{timestamp} {keyword}/
# 之后: {work_dir}/
```

所有歌曲直接平铺到 `/home/admin/Music/`，不再按源和时间建子目录。

---

## 验证方法

下载后用 `ffprobe` 检查文件大小可判断码率：
- **~3-12MB 每歌/每3-5分钟** → MP3 320k ✅
- **~1-3MB 每歌/每3-5分钟** → 低码率 MP3（源无高品质版本）
- **~100MB+ 每歌** → FLAC（说明某个源的 quality 列表漏改了，需要检查）

完整歌单下载后对比日志中的文件大小即可验证码率优先级是否生效。

---

## 已知限制

- **外国歌曲**（Taylor Swift 等）在某些源可能只有 AAC/M4A，自动降级为 m4a
- **小众/日韩歌曲**在酷狗/酷我/咪咕的覆盖率低，搜不到正常，不影响 QQ/网易云
- **网络依赖**：部分第三方解析器域名（cenguigui.cn、haitangw.net 等）可能间歇性不可用
