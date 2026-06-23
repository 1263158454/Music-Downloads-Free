# 音频完整性校验 — 实现参考

## 原理

下载完成后用 `ffprobe` 提取音频实际时长，与 API 返回的预期时长对比。

## 阈值

| 条件 | 判定 | 说明 |
|------|------|------|
| 实际 < 30s | 不完整 | 试听片段/空白文件 |
| 实际/预期 < 50% | 不完整 | QQ 音乐预览截断 |
| 实际 >= 预期 × 90% | 完整 | 正常文件 |
| 无预期时长 | 仅判断 > 30s | 无参考值 |

## ffprobe 调用

```python
import subprocess, json

def get_duration(filepath: str) -> float:
    cmd = ['ffprobe', '-v', 'quiet', '-print_format', 'json',
           '-show_format', filepath]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
    data = json.loads(result.stdout)
    return float(data['format']['duration'])
```

## 多源重试流程

```
搜索 → 下载 → ffprobe 校验
  ↓ 不完整(<50%)
删除不完整文件 → 下一个搜索结果
  ↓ 全部失败
切换下一个源(QQ→网易云→酷狗→酷我→咪咕)
  ↓ 全部失败
标记为不完整
```

## 实践发现

- QQ 音乐预览片段 = 1:00 (mp3) 或 0:30 (m4a)
- 第三方 API 返回的"完整版"可能是预览的 1:00 截断
- 网易云 FLAC 通常真实完整（文件大小 10x+ 于预览版）
- `(Only one for me) - 960KB` = 预览, `(没有你不行) Live - 3.1MB` = 完整
