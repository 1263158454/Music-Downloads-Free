#!/home/admin/.venv/bin/python
"""
Music Downloader — 多源搜索下载歌曲 (mp3 320k)
支持: search / download / download-idx / download-playlist / check-playlist
"""
import sys, os, re, time, json, subprocess, urllib.request, urllib.parse

sys.path.insert(0, '/home/admin/Downloads/musicdl')
from musicdl.modules import BuildMusicClient, LoggerHandle

WORK_DIR = '/home/admin/Music'
RETRY_COUNT = 2       # QQ搜索重试3次，保证主源覆盖
RETRY_DELAY = 3

# 多源链: 主源QQ保持全深度，其他源快速试一轮
SOURCE_CHAIN = [
    ('QQMusicClient',      'QQ音乐',   60,  True),   # 主源，给足时间搜全
    ('NeteaseMusicClient', '网易云',   45,  False),  # 备源1
    ('KugouMusicClient',   '酷狗',     30,  False),  # 备源2
    ('KuwoMusicClient',    '酷我',     20,  False),  # 备源3 (快速)
    ('MiguMusicClient',    '咪咕',     15,  False),  # 备源4 (快速)
]

BASE_CFG = {
    'auto_set_proxies': False, 'max_retries': 1, 'maintain_session': False,
    'disable_print': True, 'search_size_per_page': 5,  # 搜5条，给够候选
    'strict_limit_search_size_per_page': True,
    'quark_parser_config': {}, 'freeproxy_settings': None,
    'enable_download_curl_cffi': False, 'enable_parse_curl_cffi': False,
    'enable_search_curl_cffi': False,
    'default_search_cookies': {}, 'default_download_cookies': {},
    'default_parse_cookies': {},
}

MIN_VALID_DURATION_S = 30
MIN_DURATION_RATIO = 0.50


# ─── 工具函数 ───

def search_with_retry(client, keyword):
    for attempt in range(RETRY_COUNT + 1):
        try:
            results = client.search(keyword)
            if results:
                return results
        except Exception:
            pass
        if attempt < RETRY_COUNT:
            time.sleep(RETRY_DELAY)
    return []


def create_client(source_type='QQMusicClient', work_dir=None):
    cfg = dict(BASE_CFG)
    cfg['type'] = source_type
    cfg['logger_handle'] = LoggerHandle()
    cfg['work_dir'] = work_dir or WORK_DIR
    return BuildMusicClient(module_cfg=cfg)


def _get_audio_duration(filepath: str) -> float:
    try:
        r = subprocess.run(['ffprobe', '-v', 'quiet', '-print_format', 'json',
                            '-show_format', filepath],
                           capture_output=True, text=True, timeout=10)
        return float(json.loads(r.stdout).get('format', {}).get('duration', 0))
    except Exception:
        return 0.0


def _format_duration(seconds: float) -> str:
    m, s = divmod(int(seconds), 60)
    return f"{m}:{s:02d}"


def check_audio_integrity(filepath: str, expected_duration_ms: int = 0) -> dict:
    actual = _get_audio_duration(filepath)
    expected_s = expected_duration_ms / 1000.0 if expected_duration_ms > 0 else 0
    if actual <= 0:
        return {'actual': 0, 'expected': expected_s, 'status': 'unknown', 'label': '未知'}
    if expected_s > 0:
        ratio = actual / expected_s
        if actual < MIN_VALID_DURATION_S or ratio < MIN_DURATION_RATIO:
            return {'actual': actual, 'expected': expected_s, 'status': 'short', 'label': '不完整'}
        return {'actual': actual, 'expected': expected_s, 'status': 'ok', 'label': '完整'}
    if actual < MIN_VALID_DURATION_S:
        return {'actual': actual, 'expected': 0, 'status': 'short', 'label': '不完整'}
    return {'actual': actual, 'expected': 0, 'status': 'ok', 'label': '完整(无参考)'}


def _match_singer(results, artists_str: str):
    al = [a.strip().lower() for a in artists_str.split(',')]
    m, u = [], []
    for s in results:
        sl = (s.singers or "").lower()
        (m if any(a in sl for a in al) else u).append(s)
    return m + u


def _netease_api_get(url: str) -> dict:
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Referer': 'https://music.163.com/',
    }
    with urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=15) as resp:
        return json.loads(resp.read())


def _sanitize_folder(name: str) -> str:
    return re.sub(r'[<>:"/\\|?*]', '_', name).strip()[:100]



def _rename_file_suffix(path: str) -> str:
    """Strip random media ID suffix from filename.
    'xxx - 001YvwLN0Gj9fc.m4a' -> 'xxx.m4a'
    'xxx - 29819059.mp3'     -> 'xxx.mp3'
    """
    d, basename = os.path.dirname(path), os.path.basename(path)
    stem, ext = os.path.splitext(basename)
    new_stem = re.sub(r' - [A-Za-z0-9]+(\s*\(1\))?$', '', stem).strip()
    if new_stem == stem:
        return path
    new_path = os.path.join(d, new_stem + ext)
    c = 1
    while os.path.exists(new_path):
        new_path = os.path.join(d, f'{new_stem}_{c}{ext}')
        c += 1
    try:
        os.rename(path, new_path)
        return new_path
    except Exception:
        return path


def _clean_song_path(filepath: str) -> str:
    """Rename song file + matching .lrc to remove random suffix."""
    new_fp = _rename_file_suffix(filepath)
    old_lrc = os.path.splitext(filepath)[0] + '.lrc'
    if os.path.exists(old_lrc):
        new_lrc = os.path.splitext(new_fp)[0] + '.lrc'
        if new_lrc != old_lrc and not os.path.exists(new_lrc):
            try:
                os.rename(old_lrc, new_lrc)
            except Exception:
                pass
    return new_fp

def _parse_playlist_id(url: str) -> str:
    m = re.search(r'id=(\d+)', url)
    if m:
        return m.group(1)
    m = re.search(r'/playlist[=/](\d+)', url)
    return m.group(1) if m else url.strip()


# ─── 多源下载核心 ───

def _try_source(client_type, client_label, keyword, artists_str,
                expected_duration_ms, output_dir):
    """尝试从一个源搜索+下载，成功后返回结果dict"""
    client = create_client(client_type, work_dir=output_dir)
    results = search_with_retry(client, keyword)
    if not results:
        return None

    ordered = _match_singer(results, artists_str) if artists_str else results

    for idx, s in enumerate(ordered[:3]):
        print(f"    🔄 [{client_label} #{idx+1}] {s.song_name} — {s.singers}")
        try:
            dl = client.download([s])
        except Exception as e:
            print(f"      ⚠️ 异常: {str(e)[:60]}")
            continue

        if not dl:
            print(f"      ⚠️ 返回空")
            continue

        s2 = dl[0]
        fpath = s2.save_path
        if not fpath or not os.path.exists(fpath):
            print(f"      ⚠️ 文件不存在")
            continue

        integrity = check_audio_integrity(fpath, expected_duration_ms)

        if integrity['status'] == 'ok':
            dur = _format_duration(integrity['actual'])
            if integrity['expected'] > 0:
                dur += f"/{_format_duration(integrity['expected'])}"
            # Strip random suffix from filename
            cleaned = _clean_song_path(fpath)
            if cleaned != fpath:
                fpath = cleaned
            print(f"      ✅ 完整! {dur}")
            return {
                'path': fpath, 'integrity': integrity,
                'downloaded': True, 'source': client_label,
                'file_size': os.path.getsize(fpath),
            }

        dur = f"实际{_format_duration(integrity['actual'])}"
        if integrity['expected'] > 0:
            dur += f" 预期{_format_duration(integrity['expected'])}"
        print(f"      ⚠️ {dur}")
        try:
            os.remove(fpath)
            lrc = os.path.splitext(fpath)[0] + '.lrc'
            if os.path.exists(lrc):
                os.remove(lrc)
        except Exception:
            pass

    return None


def _multi_source_download(keyword, artists_str, expected_duration_ms, output_dir):
    """跨源链搜索+下载"""
    for client_type, label, _, do_match in SOURCE_CHAIN:
        src_artists = artists_str if do_match else ""
        print(f"    📡 [{label}] 搜索中...")
        result = _try_source(client_type, label, keyword, src_artists,
                             expected_duration_ms, output_dir)
        if result:
            return result
    return {'path': None, 'integrity': None, 'downloaded': False, 'source': '全部失败'}


# ─── 命令: search ───

def cmd_search(args):
    keyword = ' '.join(args)
    if not keyword:
        print("用法: music.py search <关键词>")
        return

    print(f"\n🔍 跨源搜索: {keyword}\n")
    for client_type, label, _, _ in SOURCE_CHAIN:
        client = create_client(client_type)
        results = search_with_retry(client, keyword)
        if results:
            print(f"  [{label}] {len(results)} 条:")
            for s in results[:3]:
                print(f"    {s.song_name} — {s.singers} [{s.ext or '?'}] {s.file_size or '?'}")
        else:
            print(f"  [{label}] 无结果")
        print()


# ─── 命令: download ───

def cmd_download(args):
    keyword = ' '.join(args)
    if not keyword:
        print("用法: music.py download <关键词>")
        return

    result = _multi_source_download(keyword, "", 0, WORK_DIR)
    if result['downloaded']:
        integ = result['integrity']
        print(f"\n✅ 下载成功 [{result['source']}]")
        print(f"   保存: {result['path']}")
        print(f"   时长: {_format_duration(integ['actual'])}"
              f"{'/' + _format_duration(integ['expected']) if integ['expected'] > 0 else ''}")
    else:
        print(f"\n❌ 所有 {len(SOURCE_CHAIN)} 个源均无法下载完整版本")


# ─── 命令: download-idx ───

def cmd_download_idx(args):
    if len(args) < 2:
        print("用法: music.py download-idx <序号> <关键词>")
        return
    try:
        idx = int(args[0]) - 1
    except ValueError:
        print("序号必须是数字")
        return
    keyword = ' '.join(args[1:])
    result = _multi_source_download(keyword, "", 0, WORK_DIR)
    if result['downloaded']:
        print(f"✅ [{result['source']}] {result['path']}")
    else:
        print(f"❌ 所有 {len(SOURCE_CHAIN)} 个源均无法下载完整版本")


# ─── 命令: download-playlist ───

def cmd_download_playlist(args):
    if not args:
        print("用法: music.py download-playlist <歌单URL>")
        return

    url = args[0].strip()
    playlist_id = _parse_playlist_id(url)
    print(f"📋 歌单ID: {playlist_id}")

    print("📡 获取歌单信息中...")
    try:
        api_url = f'https://music.163.com/api/v3/playlist/detail?id={playlist_id}'
        data = _netease_api_get(api_url)
    except Exception as e:
        print(f"❌ 获取歌单失败: {e}")
        return

    result = data.get('playlist') or data.get('result', {})
    playlist_name = result.get('name', f'playlist_{playlist_id}')
    tracks = result.get('tracks', [])
    if not tracks:
        print("❌ 歌单中没有歌曲")
        return

    folder_name = _sanitize_folder(playlist_name)
    output_dir = os.path.join(WORK_DIR, folder_name)
    os.makedirs(output_dir, exist_ok=True)

    print(f"🎵 {playlist_name} ({len(tracks)} 首)")
    print(f"📁 保存: {output_dir}/")

    success, incomplete, failed, results_log = 0, 0, 0, []

    for i, track in enumerate(tracks, 1):
        raw_artists = track.get('ar') or track.get('artists', [])
        song_name = track.get('name', '')
        artists = ','.join(a['name'] for a in raw_artists)
        expected_duration = track.get('dt') or track.get('duration', 0)
        keyword = f"{song_name} {artists}"

        print(f"\n  [{i}/{len(tracks)}] {song_name} — {artists}")
        if expected_duration:
            print(f"      预期: {_format_duration(expected_duration / 1000)}")

        dl_result = _multi_source_download(keyword, artists, expected_duration, output_dir)

        if dl_result['downloaded']:
            integ = dl_result['integrity']
            src = dl_result['source']
            actual = integ['actual']
            expected = integ['expected']
            fsize = dl_result.get('file_size', 0)

            if integ['status'] == 'ok':
                success += 1
                label = '✅ 完整'
            else:
                incomplete += 1
                label = '⚠️ 不完整'

            dur = _format_duration(actual)
            if expected > 0:
                dur += f"/{_format_duration(expected)}"
            print(f"    {label} [{src}] {dur} | {fsize // 1024} KB")
            results_log.append((song_name, artists, actual, expected, f'{label} [{src}] {dur}'))
        else:
            print(f"    ❌ 全部 {len(SOURCE_CHAIN)} 个源均失败")
            failed += 1
            results_log.append((song_name, artists, 0, expected_duration / 1000, '❌ 失败'))

    total = len(tracks)
    print(f"\n{'='*65}")
    print(f"  📊 下载报告: {playlist_name}")
    print(f"{'='*65}")
    print(f"  路径: {output_dir}/")
    print(f"  总计: {total}  |  ✅ 完整: {success}  |  ⚠️ 不完整: {incomplete}  |  ❌ 失败: {failed}")
    print(f"  ── 明细 ──")
    for song, artist, actual, expected, status in results_log:
        label = status[:4]
        rest = status[4:]
        print(f"  {label} {rest:>30}  {song}")
        if artist:
            print(f"  {'':>36}{artist}")
    print(f"{'='*65}")


# ─── 命令: check-playlist ───

def cmd_check_playlist(args):
    if not args:
        print("用法: music.py check-playlist <路径> [--playlist-url <URL>]")
        return

    path = os.path.expanduser(args[0])
    playlist_url = None
    if '--playlist-url' in args:
        idx = args.index('--playlist-url')
        if idx + 1 < len(args):
            playlist_url = args[idx + 1]

    if not os.path.exists(path):
        print(f"❌ 路径不存在: {path}")
        return

    if os.path.isfile(path):
        result = check_audio_integrity(path)
        print(f"\n  文件: {os.path.basename(path)}")
        print(f"  状态: {result['label']}")
        if result['actual']:
            print(f"  时长: {_format_duration(result['actual'])}")
        return

    audio_exts = {'.mp3', '.m4a', '.flac', '.ogg', '.wav', '.aac'}
    files = sorted([os.path.join(path, f) for f in os.listdir(path)
                    if os.path.splitext(f)[1].lower() in audio_exts])
    if not files:
        print("⚠️ 未找到音频文件")
        return

    playlist_name = os.path.basename(os.path.normpath(path))

    expected_durations = {}
    if playlist_url:
        try:
            pid = _parse_playlist_id(playlist_url)
            data = _netease_api_get(f'https://music.163.com/api/v3/playlist/detail?id={pid}')
            pl = data.get('playlist') or data.get('result', {})
            for t in pl.get('tracks', []):
                raw_a = t.get('ar') or t.get('artists', [])
                artists = ','.join(a['name'] for a in raw_a)
                dur = t.get('dt') or t.get('duration', 0)
                expected_durations[(t['name'], artists)] = dur / 1000
            print(f"📡 {len(expected_durations)} 首预期时长")
        except Exception as e:
            print(f"⚠️ 加载歌单数据失败: {e}")

    ok, short, unknown, results = 0, 0, 0, []
    remaining = {os.path.basename(f): f for f in files}

    for (sname, artist), expected_s in expected_durations.items():
        best = None
        chars = [c for c in sname[:8] if c.isalpha() or ord(c) > 127]
        for fname in list(remaining.keys()):
            cnt = sum(1 for c in chars if c in fname)
            if cnt >= max(2, len(chars) // 2):
                if not best or cnt > best[1]:
                    best = (fname, cnt)
        if best:
            fpath = remaining.pop(best[0])
        elif remaining:
            fname = next(iter(remaining))
            fpath = remaining.pop(fname)
        else:
            results.append((sname, artist, 0, expected_s, '❌  文件缺失'))
            short += 1
            continue

        actual_s = _get_audio_duration(fpath)
        if actual_s <= 0:
            results.append((sname, artist, 0, expected_s, '❓  无法读取'))
            unknown += 1
            continue

        actual_str = _format_duration(actual_s)
        expected_str = _format_duration(expected_s) if expected_s > 0 else '?'
        ratio = actual_s / expected_s if expected_s > 0 else 1
        if actual_s < MIN_VALID_DURATION_S or (expected_s > 0 and ratio < MIN_DURATION_RATIO):
            results.append((sname, artist, actual_s, expected_s,
                           f'⚠️  {actual_str:>5}/{expected_str:<5}'))
            short += 1
        else:
            results.append((sname, artist, actual_s, expected_s,
                           f'✅  {actual_str:>5}/{expected_str:<5}'))
            ok += 1

    for fname, fpath in remaining.items():
        actual_s = _get_audio_duration(fpath)
        actual_str = _format_duration(actual_s) if actual_s > 0 else '??:??'
        lab = '⚠️' if actual_s < MIN_VALID_DURATION_S else '❓'
        results.append((f'(多余) {fname[:40]}', '', actual_s, 0,
                       f'{lab}  {actual_str:>5}/?'))
        short += 1 if actual_s < MIN_VALID_DURATION_S else 0

    print(f"\n{'='*65}")
    print(f"  📊 完整性检测: {playlist_name}")
    print(f"{'='*65}")
    print(f"  总计: {len(files)}  |  ✅ {ok}  |  ⚠️ {short}  |  ❓ {unknown}")
    for sname, artist, actual, expected, line in results:
        print(f"  {line}  {sname}")
        if artist:
            print(f"  {'':>26}{artist}")
    print(f"{'='*65}")


# ─── 命令: rename (批量清理文件名后缀) ───

def cmd_rename(args):
    """遍历目录，清理所有音乐文件的随机ID后缀"""
    target = args[0] if args else WORK_DIR
    target = os.path.expanduser(target)
    if not os.path.exists(target):
        print(f"❌ 路径不存在: {target}")
        return

    audio_exts = {'.mp3', '.m4a', '.flac', '.ogg', '.wav', '.aac', '.opus'}
    renamed, removed = 0, 0

    if os.path.isfile(target):
        files = [target]
    else:
        files = []
        for root, dirs, fnames in os.walk(target):
            for f in fnames:
                if os.path.splitext(f)[1].lower() in audio_exts:
                    files.append(os.path.join(root, f))

    # Phase 1: delete (1) duplicates and _1 duplicates first
    for fpath in sorted(files):
        base = os.path.basename(fpath)
        dup = False
        if ' (1).' in base:
            main_path = os.path.join(os.path.dirname(fpath), base.replace(' (1).', '.'))
            dup = os.path.exists(main_path)
        elif '_1.' in base:
            main_path = os.path.join(os.path.dirname(fpath), base.replace('_1.', '.'))
            dup = os.path.exists(main_path)
        if dup:
            try:
                os.remove(fpath)
                removed += 1
                print(f"  Deleted dup: {base}")
                lrc = os.path.splitext(fpath)[0] + '.lrc'
                if os.path.exists(lrc):
                    os.remove(lrc)
            except Exception:
                pass

    # Phase 2: rename remaining files, strip suffix
    remaining = []
    for root, dirs, fnames in os.walk(target):
        for f in fnames:
            if os.path.splitext(f)[1].lower() in audio_exts:
                remaining.append(os.path.join(root, f))

    for fpath in sorted(remaining):
        new_fp = _clean_song_path(fpath)
        if new_fp != fpath:
            renamed += 1
            print(f"  Renamed: {os.path.basename(fpath)} -> {os.path.basename(new_fp)}")

    print(f"\n📊 清理完成: {renamed} 已重命名, {removed} 重复已删除")

# ─── 入口 ───

def main():
    if len(sys.argv) < 2:
        print("用法:"); print("  music.py search <关键词>")
        print("  music.py download <关键词>"); print("  music.py download-idx <N> <关键词>")
        print("  music.py download-playlist <URL>")
        print("  music.py check-playlist <路径> [--playlist-url <URL>]")
        print("  music.py rename [路径]   -- 清理文件名中的随机ID后缀")
        return

    cmd, args = sys.argv[1], sys.argv[2:]
    if cmd == 'search':
        cmd_search(args)
    elif cmd == 'download':
        cmd_download(args)
    elif cmd in ('download-idx', 'download_idx'):
        cmd_download_idx(args)
    elif cmd in ('download-playlist', 'download_playlist', 'playlist'):
        cmd_download_playlist(args)
    elif cmd in ('check-playlist', 'check_playlist', 'check'):
        cmd_check_playlist(args)
    elif cmd == 'rename':
        cmd_rename(args)
    else:
        print(f"未知命令: {cmd}")

if __name__ == '__main__':
    main()
