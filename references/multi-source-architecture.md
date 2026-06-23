# 多源链架构设计

## 源列表 (按优先级)

| 优先级 | 源 | 超时 | 歌手匹配 | 特点 |
|--------|----|------|---------|------|
| 1 | QQMusicClient (QQ音乐) | 60s | ✅ 是 | 主源, 中文覆盖率最高, mp3 320k |
| 2 | NeteaseMusicClient (网易云) | 45s | ❌ | FLAC 多, 补 QQ 无版权/只有预览的歌 |
| 3 | KugouMusicClient (酷狗) | 30s | ❌ | 韩日歌较全 |
| 4 | KuwoMusicClient (酷我) | 20s | ❌ | 快速兜底 |
| 5 | MiguMusicClient (咪咕) | 15s | ❌ | 最后尝试 |

## 为什么只有5个源

musicdl 注册了50+个 MusicClient，但中国网络环境下只有上述5个可用：

- **被GFW阻断**: YouTube, Spotify, Apple Music, Deezer, Tidal, SoundCloud, Qobuz, Amazon 等全部 connect timeout
- **国内无内容/不同品类**: Ximalaya(喜马拉雅)/Qingting(蜻蜓)/Lizhi(荔枝) = 播客电台, Bilibili = 视频
- **翻唱/小众**: 5sing(FiveSingMusicClient), Gequbao, Gequhai 等搜索结果少且质量低
- **测试不可达/失效**: Joox(Buguyy/Fangpi/HTQYY 等) 连不上或返回空

将慢/无效源加入链中只会让下载时间成倍增长，而对成功率几乎无贡献。

## 搜索参数设计

```python
RETRY_COUNT = 2         # 每个源搜索重试3次(1原始+2重试)
search_size_per_page = 5 # 每页5条结果
max_retries_in_dl = 1    # 下载重试1次
```

这些参数对QQ音乐最敏感——减少搜索深度会导致原本能搜到的歌被漏掉。

## 关键设计原则

**永远不要为了加备源而削弱主源的搜索强度。**

实测数据:
- QQ音乐单独: 可覆盖约 90% 歌曲的完整版本
- 各备源合计: 可额外补回约 10% 的歌曲
- 但如果QQ音乐搜索参数被削弱导致漏掉 10%: 备源补回的 +10% 和漏掉的 -10% 抵消, 成功率不变
- 如果QQ音乐搜索参数被削弱导致漏掉 20%: 总体成功率下降

所以正确的策略是: **QQ保持全搜索深度 → 其他源轻量兜底**。

## 完整性校验阈值

```python
MIN_VALID_DURATION_S = 30   # 小于30秒视为试听片段
MIN_DURATION_RATIO = 0.50   # 实际/预期 < 50% 视为不完整
```

QQ音乐第三方API对VIP/海外歌曲经常返回1分钟试听片段。完整性校验通过ffprobe获取实际时长，与网易云API提供的预期时长对比，<50%则自动尝试下一源。

## 网易云歌单API

端点: `https://music.163.com/api/v3/playlist/detail?id={playlist_id}`

注: 旧版 `api/playlist/detail` 已返回 code=-447(需登录), 新版 V3 API 无需cookie。

字段映射:
| V3字段 | 旧版字段 | 说明 |
|--------|---------|------|
| `ar` | `artists` | 歌手列表(数组, 每个有name) |
| `dt` | `duration` | 时长(毫秒) |
| `playlist` | `result` | 根对象 |
