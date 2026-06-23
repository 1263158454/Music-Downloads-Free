# 网易云歌单 API V3 — 使用说明

## API 端点

```
GET https://music.163.com/api/v3/playlist/detail?id={playlist_id}
Headers:
  User-Agent: Mozilla/5.0 ...
  Referer: https://music.163.com/
```

## 字段映射（V3 vs 旧版）

| 字段 | V3 字段 | 旧版字段 | 说明 |
|------|---------|---------|------|
| 播放列表 | `data.playlist` | `data.result` | 根对象名变了 |
| 歌曲名 | `track.name` | 同左 | 不变 |
| 歌手 | `track.ar[].name` | `track.artists[].name` | `ar` = artists 缩写 |
| 时长(ms) | `track.dt` | `track.duration` | `dt` = duration 缩写 |

## 代码中兼容写法

```python
result = data.get('playlist') or data.get('result', {})
tracks = result.get('tracks', [])

for track in tracks:
    raw_artists = track.get('ar') or track.get('artists', [])
    artists = ','.join(a['name'] for a in raw_artists)
    duration_ms = track.get('dt') or track.get('duration', 0)
```

## 已知限制

- 频繁调用返回 `code: -447`（服务器繁忙），间隔 > 10s 可缓解
- `duration` 在旧版 API 是毫秒，V3 中 `dt` 也是毫秒
- 首次成功调用后短时间内的重复调用会触发限流
- 备用端点（较旧，可能下线）: `https://music.163.com/api/playlist/detail?id={id}`
