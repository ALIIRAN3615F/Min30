#!/usr/bin/env python3
import os
import sys
import subprocess
import re
import urllib.parse
import random
import shutil
import time
from pathlib import Path

RANDOM_WORDS = ["alpha", "beta", "gamma", "delta", "epsilon", "zeta", "theta", "kappa", "lambda", "sigma", "omega", "nova", "star", "moon", "sun", "sky", "cloud", "river", "ocean", "mountain"]
SPLIT_MB = 95
SPLIT_BYTES = SPLIT_MB * 1024 * 1024

def sanitize_name(name):
    return re.sub(r'-+', '-', name.replace(' ', '-').replace('　', '-'))

def urlencode(s):
    return urllib.parse.quote(s, safe='')

def get_random_word():
    return f"{random.choice(RANDOM_WORDS)}_{random.randint(0, 9999)}"

def get_unique_folder(base_path, backup_dir, name):
    if not os.path.isdir(f"{base_path}/{name}") and not os.path.isdir(f"{backup_dir}/{name}"):
        return name
    suffix = get_random_word()
    while os.path.isdir(f"{base_path}/{name}_{suffix}") or os.path.isdir(f"{backup_dir}/{name}_{suffix}"):
        suffix = get_random_word()
    return f"{name}_{suffix}"

def normalize_youtube_url(url):
    match = re.search(r'youtu\.be/([a-zA-Z0-9_-]+)', url)
    if match:
        vid = match.group(1).split('?')[0]
        return f"https://www.youtube.com/watch?v={vid}"
    return url

def get_format(quality):
    formats = {
        "audio": "bestaudio/bestaudio*/best",
        "best": "bv*+ba/b",
        "2160": "bestvideo[height>=2000][height<=2160]+bestaudio/bestvideo[height<=2160]+bestaudio/best",
        "4k": "bestvideo[height>=2000][height<=2160]+bestaudio/bestvideo[height<=2160]+bestaudio/best",
        "1440": "bestvideo[height>=1400][height<=1440]+bestaudio/bestvideo[height<=1440]+bestaudio/best",
        "2k": "bestvideo[height>=1400][height<=1440]+bestaudio/bestvideo[height<=1440]+bestaudio/best",
        "1080": "bestvideo[height>=1000][height<=1080]+bestaudio/bestvideo[height<=1080]+bestaudio/best",
        "720": "bestvideo[height>=700][height<=720]+bestaudio/bestvideo[height<=720]+bestaudio/best",
        "480": "bestvideo[height>=450][height<=480]+bestaudio/bestvideo[height<=480]+bestaudio/best",
    }
    return formats.get(quality, formats["best"])

def get_common_args(quality, tmp_dir):
    base = [
        "--write-thumbnail", "--convert-thumbnails", "jpg",
        "--no-cache-dir", "--output", f"{tmp_dir}/%(title)s.%(ext)s",
        "--no-part", "--no-playlist", "--retries", "5",
        "--fragment-retries", "5", "--no-check-certificates",
        "--concurrent-fragments", "8", "--buffer-size", "16K",
        "--http-chunk-size", "10M", "--progress", "--newline"
    ]
    if quality == "audio":
        return ["--extract-audio", "--audio-format", "mp3", "--audio-quality", "0"] + base
    elif quality == "best":
        return ["--merge-output-format", "mp4"] + base
    else:
        return ["--merge-output-format", "mp4"] + base

def download_video(method, url, tmp_dir, fmt, quality):
    common = get_common_args(quality, tmp_dir)
    proxy = ["--proxy", "socks5://127.0.0.1:1080"]
    ua_chrome = ["--user-agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"]
    ua_android = ["--user-agent", "Mozilla/5.0 (Linux; Android 12; SM-S906N Build/QP1A.190711.020) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/112.0.0.0 Mobile Safari/537.36"]
    sort_opt = ["--format-sort", "res,vcodec:h264"] if quality != "audio" else []

    methods = {
        1: ["yt-dlp"] + proxy + ["--format", fmt] + sort_opt + common + ["--extractor-args", "youtube:player_client=web", "--js-runtimes", "deno", "--remote-components", "ejs:github"] + ua_chrome + ["--add-header", "Accept-Language:en-US,en;q=0.9", url],
        2: ["yt-dlp"] + proxy + ["--format", fmt] + sort_opt + common + ["--extractor-args", "youtube:player_client=web", "--js-runtimes", "deno", "--remote-components", "ejs:npm"] + ua_chrome + ["--add-header", "Accept-Language:en-US,en;q=0.9", url],
        3: ["yt-dlp"] + proxy + ["--format", fmt] + sort_opt + common + ["--extractor-args", "youtube:player_client=web,mweb,android_vr", "--js-runtimes", "deno", "--remote-components", "ejs:github", url],
        4: ["yt-dlp"] + proxy + ["--format", fmt] + sort_opt + common + ["--extractor-args", "youtube:player_client=mweb", url],
        5: ["yt-dlp"] + proxy + ["--format", fmt] + sort_opt + common + ["--extractor-args", "youtube:player_client=android_vr", url],
        6: ["yt-dlp", "--format", fmt] + sort_opt + common + ["--extractor-args", "youtube:player_client=web", "--js-runtimes", "deno", "--remote-components", "ejs:github", url],
        7: ["yt-dlp", "--format", fmt] + sort_opt + common + ["--extractor-args", "youtube:player_client=mweb", url],
        8: ["yt-dlp"] + proxy + ["--format", fmt] + sort_opt + common + ["--extractor-args", "youtube:player_client=android"] + ua_android + [url],
    }
    print(f"Trying download method {method}...")
    try:
        result = subprocess.run(methods[method], check=False)
        return result.returncode == 0
    except Exception as e:
        print(f"Error: {e}")
        return False

def get_video_height(filepath):
    try:
        result = subprocess.run(
            ['ffprobe', '-v', 'error', '-select_streams', 'v:0', '-show_entries', 'stream=height', '-of', 'csv=p=0', filepath],
            capture_output=True, text=True
        )
        return int(result.stdout.strip())
    except:
        return None

def create_readme(folder_path, filename, url, quality, parts_info, has_password, is_split):
    readme = f"# {filename}\n\n"
    if os.path.exists(f"{folder_path}/thumbnail.jpg"):
        readme += '<div align="center">\n  <picture>\n    <img src="thumbnail.jpg" width="250" />\n  </picture>\n</div>\n\n<br>\n\n'
    readme += "---\n\n## Video Information\n\n| Property | Value |\n|----------|-------|\n"
    readme += f"| **Video Name** | `{filename}` |\n"
    readme += f"| **Original Link** | [YouTube Video]({url}) |\n"
    readme += f"| **Total Size** | **{parts_info['count']} {'parts' if is_split else 'file'}** - **{parts_info['size_mb']} MB** |\n"
    readme += f"| **Quality** | **{quality}** |\n"
    readme += "| **Status** | **Complete (100%)** |\n"
    readme += f"| **Password Protected** | **{'YES' if has_password else 'NO'}** |\n\n"
    readme += "---\n\n## Download Links\n\n"
    if is_split:
        readme += f"> Download **all parts**, then open `{parts_info['main_zip']}` — the other parts are found automatically.\n\n"
    readme += "| # | File | Link |\n|---|------|------|\n"
    for i, link in enumerate(parts_info['links'], 1):
        readme += f"| {i} | `{link['name']}` | [Download]({link['url']}) |\n"
    readme += "\n---\n\n## How to Extract\n\n"
    if has_password:
        readme += "| OS | Steps |\n|----|-------|\n"
        readme += f"| **Windows** | Right-click `{parts_info['main_zip']}` → *Extract Here* (needs 7-Zip or WinRAR) → enter password |\n"
        readme += "| **Mac** | Open with Keka → enter password |\n"
        readme += f"| **Linux** | `unzip {parts_info['main_zip']}` or right-click → Extract → enter password |\n"
        readme += f"| **Android** | Use ZArchiver → tap `{parts_info['main_zip']}` → enter password |\n"
    elif is_split:
        readme += "| OS | Steps |\n|----|-------|\n"
        readme += f"| **Windows** | Double-click `{parts_info['main_zip']}` — opens in Explorer, WinRAR, or 7-Zip |\n"
        readme += f"| **Mac** | Double-click `{parts_info['main_zip']}` — extracts with Archive Utility |\n"
        readme += f"| **Linux** | `unzip {parts_info['main_zip']}` or right-click → Extract Here |\n"
        readme += f"| **Android** | Tap `{parts_info['main_zip']}` in file manager or use ZArchiver |\n"
    else:
        readme += "Ready to use — no extraction needed!\n"
    readme += "\n---\n\n*This tool created by [avasam.ir](https://avasam.ir)*\n"
    with open(f"{folder_path}/README.md", 'w', encoding='utf-8') as f:
        f.write(readme)

def process_video(url, quality, password, backup_dir, repo_owner, repo_name, branch, url_index):
    url = normalize_youtube_url(url)
    print(f"Processing URL {url_index}: {url}")
    tmp_dir = f"tmp_downloads_{url_index}"
    os.makedirs(tmp_dir, exist_ok=True)
    fmt = get_format(quality)

    success = False
    best_height = 0
    best_method = None

    for method in range(1, 9):
        if download_video(method, url, tmp_dir, fmt, quality):
            quality_ok = True
            current_height = 0
            for f in Path(tmp_dir).glob("*.mp4"):
                h = get_video_height(str(f))
                if h:
                    current_height = max(current_height, h)
                    if quality == "best":
                        if h < 720 and method < 8:
                            print(f"Method {method} delivered {h}p — trying next method for better quality...")
                            quality_ok = False
                            f.unlink()
                    elif quality != "audio":
                        if h < int(quality) - 150:
                            print(f"Method {method} delivered {h}p instead of {quality}p — rejecting...")
                            quality_ok = False
                            f.unlink()
            if quality_ok:
                if quality == "best" and current_height > best_height:
                    best_height = current_height
                    best_method = method
                success = True
                print(f"Download successful with method {method}! ({current_height}p)")
                break
        print(f"Method {method} failed, waiting 3 seconds...")
        time.sleep(3)

    if not success:
        print(f"All download methods failed for URL: {url}")
        shutil.rmtree(tmp_dir, ignore_errors=True)
        return None

    for p in Path(tmp_dir).glob("*.part"):
        p.unlink()

    video_info = []
    for filepath in Path(tmp_dir).iterdir():
        if filepath.suffix in ['.jpg', '.webp']:
            continue
        if not filepath.is_file():
            continue

        size = filepath.stat().st_size
        filename_no_ext = sanitize_name(filepath.stem)
        ext = filepath.suffix[1:]
        final_folder = get_unique_folder("videos", backup_dir, filename_no_ext)
        folder_path = f"{backup_dir}/{final_folder}"
        os.makedirs(folder_path, exist_ok=True)

        thumbs = list(Path(tmp_dir).glob("*.jpg"))
        if thumbs:
            shutil.copy(thumbs[0], f"{folder_path}/thumbnail.jpg")

        folder_encoded = urlencode(final_folder)

        if size > SPLIT_BYTES:
            archive_base = f"{folder_path}/{final_folder}"
            if password:
                subprocess.run(["rar", "a", "-m0", f"-v{SPLIT_MB}m", f"-hp{password}", f"{archive_base}.rar", str(filepath)])
            else:
                subprocess.run(["rar", "a", "-m0", f"-v{SPLIT_MB}m", f"{archive_base}.rar", str(filepath)])

            parts = sorted(list(Path(folder_path).glob("*.rar")) + list(Path(folder_path).glob("*.r[0-9][0-9]")))
            total_size = sum(p.stat().st_size for p in parts)
            links = []
            for p in parts:
                pname = p.name
                penc = urlencode(pname)
                links.append({'name': pname, 'url': f"https://raw.githubusercontent.com/{repo_owner}/{repo_name}/{branch}/videos/{folder_encoded}/{penc}"})

            create_readme(folder_path, filename_no_ext, url, quality, {
                'count': len(parts), 'size_mb': f"{total_size/1024/1024:.2f}",
                'main_zip': f"{final_folder}.rar", 'links': links
            }, bool(password), True)
        else:
            if password:
                subprocess.run(["rar", "a", "-m0", f"-hp{password}", f"{folder_path}/{final_folder}.rar", str(filepath)])
                file_enc = urlencode(f"{final_folder}.rar")
                links = [{'name': f"{final_folder}.rar", 'url': f"https://raw.githubusercontent.com/{repo_owner}/{repo_name}/{branch}/videos/{folder_encoded}/{file_enc}"}]
                create_readme(folder_path, filename_no_ext, url, quality, {
                    'count': 1, 'size_mb': f"{size/1024/1024:.2f}",
                    'main_zip': f"{final_folder}.rar", 'links': links
                }, True, False)
            else:
                shutil.copy(filepath, f"{folder_path}/{final_folder}.{ext}")
                file_enc = urlencode(f"{final_folder}.{ext}")
                links = [{'name': f"{final_folder}.{ext}", 'url': f"https://raw.githubusercontent.com/{repo_owner}/{repo_name}/{branch}/videos/{folder_encoded}/{file_enc}"}]
                create_readme(folder_path, filename_no_ext, url, quality, {
                    'count': 1, 'size_mb': f"{size/1024/1024:.2f}",
                    'main_zip': None, 'links': links
                }, False, False)

        video_info.append({'original': filename_no_ext, 'folder': final_folder})

    shutil.rmtree(tmp_dir, ignore_errors=True)
    return video_info


def check_fa_subs(subtitle_dir):
    """Check if any Persian subtitle files exist"""
    # Only match exact language code patterns like .fa. or .fa-IR.
    exact_patterns = ["*.fa.vtt", "*.fa.srt", "*.fa-IR.vtt", "*.fa-IR.srt",
                      "*.Persian.vtt", "*.Persian.srt"]
    for pattern in exact_patterns:
        found = list(Path(subtitle_dir).glob(pattern))
        if found:
            return True
    # Regex check: must have .fa. or .fa- as a language tag (not just any 'fa' substring)
    fa_re = re.compile(r'\.(fa|fa-IR|Persian)\.(vtt|srt)$', re.IGNORECASE)
    for f in Path(subtitle_dir).iterdir():
        if f.is_file() and fa_re.search(f.name):
            return True
    return False


def check_en_subs(subtitle_dir):
    """Check if any English subtitle files exist"""
    patterns = ["*.en.vtt", "*.en.srt", "*.en-US.vtt", "*.en-US.srt"]
    for pattern in patterns:
        if list(Path(subtitle_dir).glob(pattern)):
            return True
    return False


def run_sub_command(cmd, subtitle_dir, label=""):
    """Run a subtitle download command and return True if subs were downloaded"""
    print(f"  → {label}")
    try:
        result = subprocess.run(cmd, check=False, capture_output=False)
    except Exception as e:
        print(f"    Error: {e}")
        return False
    subs = list(Path(subtitle_dir).glob("*.vtt")) + list(Path(subtitle_dir).glob("*.srt"))
    return len(subs) > 0


def download_subtitles(url, folder_path, folder_name, repo_owner, repo_name, branch):
    subtitle_dir = f"{folder_path}/subtitle"
    os.makedirs(subtitle_dir, exist_ok=True)
    out_tmpl = f"{subtitle_dir}/%(title)s"

    proxy = ["--proxy", "socks5://127.0.0.1:1080"]
    common = [
        "--sub-format", "vtt/srt/best",
        "--convert-subs", "vtt",
        "--skip-download",
        "--no-playlist",
        "--no-check-certificates",
        "--output", out_tmpl
    ]

    # ── ALL subtitle methods to try ──────────────────────────────────────────
    # Each entry: (label, command_list)
    sub_methods = [

        # ── MANUAL SUBS fa+en ────────────────────────────────────────────────
        ("manual fa+en | web+deno+github | proxy",
         ["yt-dlp"] + proxy +
         ["--extractor-args", "youtube:player_client=web",
          "--js-runtimes", "deno", "--remote-components", "ejs:github",
          "--write-sub", "--sub-langs", "fa,fa-IR,en,en-US"] +
         common + [url]),

        ("manual fa+en | web+deno+npm | proxy",
         ["yt-dlp"] + proxy +
         ["--extractor-args", "youtube:player_client=web",
          "--js-runtimes", "deno", "--remote-components", "ejs:npm",
          "--write-sub", "--sub-langs", "fa,fa-IR,en,en-US"] +
         common + [url]),

        ("manual fa+en | web+mweb+android_vr+deno | proxy",
         ["yt-dlp"] + proxy +
         ["--extractor-args", "youtube:player_client=web,mweb,android_vr",
          "--js-runtimes", "deno", "--remote-components", "ejs:github",
          "--write-sub", "--sub-langs", "fa,fa-IR,en,en-US"] +
         common + [url]),

        ("manual fa+en | mweb | proxy",
         ["yt-dlp"] + proxy +
         ["--extractor-args", "youtube:player_client=mweb",
          "--write-sub", "--sub-langs", "fa,fa-IR,en,en-US"] +
         common + [url]),

        ("manual fa+en | android_vr | proxy",
         ["yt-dlp"] + proxy +
         ["--extractor-args", "youtube:player_client=android_vr",
          "--write-sub", "--sub-langs", "fa,fa-IR,en,en-US"] +
         common + [url]),

        ("manual fa+en | android | proxy",
         ["yt-dlp"] + proxy +
         ["--extractor-args", "youtube:player_client=android",
          "--write-sub", "--sub-langs", "fa,fa-IR,en,en-US"] +
         common + [url]),

        ("manual fa+en | web+deno+github | no-proxy",
         ["yt-dlp"] +
         ["--extractor-args", "youtube:player_client=web",
          "--js-runtimes", "deno", "--remote-components", "ejs:github",
          "--write-sub", "--sub-langs", "fa,fa-IR,en,en-US"] +
         common + [url]),

        ("manual fa+en | mweb | no-proxy",
         ["yt-dlp"] +
         ["--extractor-args", "youtube:player_client=mweb",
          "--write-sub", "--sub-langs", "fa,fa-IR,en,en-US"] +
         common + [url]),

        # ── AUTO-GENERATED SUBS fa+en ────────────────────────────────────────
        ("auto fa+en | web+deno+github | proxy",
         ["yt-dlp"] + proxy +
         ["--extractor-args", "youtube:player_client=web",
          "--js-runtimes", "deno", "--remote-components", "ejs:github",
          "--write-auto-sub", "--sub-langs", "fa,fa-IR,en,en-US"] +
         common + [url]),

        ("auto fa+en | web+deno+npm | proxy",
         ["yt-dlp"] + proxy +
         ["--extractor-args", "youtube:player_client=web",
          "--js-runtimes", "deno", "--remote-components", "ejs:npm",
          "--write-auto-sub", "--sub-langs", "fa,fa-IR,en,en-US"] +
         common + [url]),

        ("auto fa+en | web+mweb+android_vr+deno | proxy",
         ["yt-dlp"] + proxy +
         ["--extractor-args", "youtube:player_client=web,mweb,android_vr",
          "--js-runtimes", "deno", "--remote-components", "ejs:github",
          "--write-auto-sub", "--sub-langs", "fa,fa-IR,en,en-US"] +
         common + [url]),

        ("auto fa+en | mweb | proxy",
         ["yt-dlp"] + proxy +
         ["--extractor-args", "youtube:player_client=mweb",
          "--write-auto-sub", "--sub-langs", "fa,fa-IR,en,en-US"] +
         common + [url]),

        ("auto fa+en | android_vr | proxy",
         ["yt-dlp"] + proxy +
         ["--extractor-args", "youtube:player_client=android_vr",
          "--write-auto-sub", "--sub-langs", "fa,fa-IR,en,en-US"] +
         common + [url]),

        ("auto fa+en | android | proxy",
         ["yt-dlp"] + proxy +
         ["--extractor-args", "youtube:player_client=android",
          "--write-auto-sub", "--sub-langs", "fa,fa-IR,en,en-US"] +
         common + [url]),

        ("auto fa+en | web+deno+github | no-proxy",
         ["yt-dlp"] +
         ["--extractor-args", "youtube:player_client=web",
          "--js-runtimes", "deno", "--remote-components", "ejs:github",
          "--write-auto-sub", "--sub-langs", "fa,fa-IR,en,en-US"] +
         common + [url]),

        ("auto fa+en | mweb | no-proxy",
         ["yt-dlp"] +
         ["--extractor-args", "youtube:player_client=mweb",
          "--write-auto-sub", "--sub-langs", "fa,fa-IR,en,en-US"] +
         common + [url]),

        # ── MANUAL+AUTO COMBINED fa+en ───────────────────────────────────────
        ("manual+auto fa+en | web+mweb+android_vr | proxy",
         ["yt-dlp"] + proxy +
         ["--extractor-args", "youtube:player_client=web,mweb,android_vr",
          "--js-runtimes", "deno", "--remote-components", "ejs:github",
          "--write-sub", "--write-auto-sub", "--sub-langs", "fa,fa-IR,en,en-US"] +
         common + [url]),

        ("manual+auto fa+en | android_vr | proxy",
         ["yt-dlp"] + proxy +
         ["--extractor-args", "youtube:player_client=android_vr",
          "--write-sub", "--write-auto-sub", "--sub-langs", "fa,fa-IR,en,en-US"] +
         common + [url]),

        ("manual+auto fa+en | android | proxy",
         ["yt-dlp"] + proxy +
         ["--extractor-args", "youtube:player_client=android",
          "--write-sub", "--write-auto-sub", "--sub-langs", "fa,fa-IR,en,en-US"] +
         common + [url]),

        ("manual+auto fa+en | mweb | no-proxy",
         ["yt-dlp"] +
         ["--extractor-args", "youtube:player_client=mweb",
          "--write-sub", "--write-auto-sub", "--sub-langs", "fa,fa-IR,en,en-US"] +
         common + [url]),

        # ── ALL SUBS fallback ────────────────────────────────────────────────
        ("all-subs | web+deno+github | proxy",
         ["yt-dlp"] + proxy +
         ["--extractor-args", "youtube:player_client=web",
          "--js-runtimes", "deno", "--remote-components", "ejs:github",
          "--write-sub", "--write-auto-sub", "--all-subs"] +
         common + [url]),

        ("all-subs | android_vr | proxy",
         ["yt-dlp"] + proxy +
         ["--extractor-args", "youtube:player_client=android_vr",
          "--write-sub", "--write-auto-sub", "--all-subs"] +
         common + [url]),
    ]

    print(f"\n{'='*60}")
    print(f"🔠 Starting subtitle download for: {url}")
    print(f"{'='*60}")

    fa_found = False
    en_found = False

    for i, (label, cmd) in enumerate(sub_methods, 1):
        # If we already have both fa and en, we're done
        if fa_found and en_found:
            print(f"\n✅ Both fa and en subtitles found — stopping.")
            break

        # If fa is found but en is missing, skip fa-only retries and keep going for en
        print(f"\n[Method {i}/{len(sub_methods)}] {label}")

        run_sub_command(cmd, subtitle_dir, label)
        time.sleep(1)

        fa_now = check_fa_subs(subtitle_dir)
        en_now = check_en_subs(subtitle_dir)

        if fa_now and not fa_found:
            print(f"    ✅ Persian (fa) subtitle found!")
            fa_found = True
        if en_now and not en_found:
            print(f"    ✅ English (en) subtitle found!")
            en_found = True

        if not fa_now and not en_now:
            print(f"    ❌ No new subtitles found with this method.")

    # ── Summary ──────────────────────────────────────────────────────────────
    print(f"\n{'='*60}")
    print(f"📝 Subtitle download summary:")
    print(f"   Persian (fa): {'✅ Found' if fa_found else '❌ Not found (may not exist on YouTube)'}")
    print(f"   English (en): {'✅ Found' if en_found else '❌ Not found'}")

    all_subs = list(Path(subtitle_dir).glob("*.vtt")) + list(Path(subtitle_dir).glob("*.srt"))
    if not all_subs:
        print(f"   No subtitles downloaded — skipping zip.")
        print(f"{'='*60}\n")
        shutil.rmtree(subtitle_dir, ignore_errors=True)
        return

    print(f"   Total files: {len(all_subs)}")
    for s in all_subs:
        print(f"     - {s.name}")
    print(f"{'='*60}\n")

    # ── Zip subtitles ─────────────────────────────────────────────────────────
    zip_path = f"{folder_path}/subtitle.zip"
    subprocess.run(["zip", "-j", zip_path] + [str(s) for s in all_subs], check=False)
    shutil.rmtree(subtitle_dir, ignore_errors=True)

    folder_enc = urlencode(folder_name)
    sub_link = f"https://raw.githubusercontent.com/{repo_owner}/{repo_name}/{branch}/videos/{folder_enc}/subtitle.zip"
    readme_path = f"{folder_path}/README.md"
    if os.path.exists(readme_path):
        with open(readme_path, 'r') as f:
            content = f.read()
        sub_section = f"\n---\n\n## Subtitles\n\n| # | File | Link |\n|---|------|------|\n| 1 | `subtitle.zip` | [Download]({sub_link}) |\n\n> Contains all available subtitle languages.\n"
        if "## Download Link" in content:
            content = content.replace("## Download Link", sub_section + "\n## Download Link")
        else:
            content += sub_section
        with open(readme_path, 'w') as f:
            f.write(content)


def main():
    urls = os.environ.get('YT_URLS', '').split()
    quality = os.environ.get('YT_QUALITY', 'best')
    password = os.environ.get('YT_PASSWORD', '')
    download_subs = os.environ.get('DOWNLOAD_SUBS', 'false').lower() == 'true'
    repo_owner = os.environ.get('REPO_OWNER_ENV', '')
    repo_name = os.environ.get('REPO_NAME_ENV', '')
    branch = os.environ.get('BRANCH_ENV', '')

    backup_dir = f"/tmp/video_backup_{os.getpid()}"
    os.makedirs(backup_dir, exist_ok=True)
    os.makedirs("videos", exist_ok=True)

    all_info = []
    for i, url in enumerate(urls, 1):
        info = process_video(url, quality, password, backup_dir, repo_owner, repo_name, branch, i)
        if info:
            all_info.extend([(v, url) for v in info])

    if download_subs:
        for info, url in all_info:
            folder_path = f"{backup_dir}/{info['folder']}"
            download_subtitles(url, folder_path, info['folder'], repo_owner, repo_name, branch)

    with open('/tmp/backup_dir_path.txt', 'w') as f:
        f.write(backup_dir)
    with open('/tmp/video_info.txt', 'w') as f:
        for info, _ in all_info:
            f.write(f"{info['original']}|{info['folder']}\n")
    with open('/tmp/yt_urls.txt', 'w') as f:
        for url in urls:
            f.write(url + '\n')
    with open('/tmp/env_vars.txt', 'w') as f:
        f.write(f"REPO_OWNER_ENV={repo_owner}\n")
        f.write(f"REPO_NAME_ENV={repo_name}\n")
        f.write(f"BRANCH_ENV={branch}\n")

    print(f"Processed {len(all_info)} videos")

if __name__ == "__main__":
    main()
