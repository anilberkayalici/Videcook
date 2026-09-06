"""Qt worker for fetching video metadata + available formats in ONE call.

Uses yt-dlp --dump-json to grab the full JSON info for a URL, then emits:
- Video metadata (title, channel, duration, filesize, thumbnail)
- Available video format options (e.g. 4K, 2K, 1080p, 720p, 480p, etc.)
- Thumbnail image bytes

Also features instant high-resolution thumbnail pre-fetching for YouTube URLs.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import urllib.error
import urllib.request
from urllib.parse import unquote, urlparse
from pathlib import Path
from dataclasses import dataclass, field

from PySide6.QtCore import QObject, Signal, Slot
from videcook.core.thumbnail import extract_video_id


STANDARD_HEIGHTS = [4320, 2160, 1440, 1080, 720, 480, 360, 240, 144]


@dataclass
class VideoFormatOption:
    """A selectable resolution option in the quality dropdown."""

    label: str
    quality_value: str
    std_height: int = 0
    filesize_approx: int = 0


@dataclass
class VideoInfo:
    """Structured video metadata for the UI."""

    title: str = ""
    channel: str = ""
    duration_seconds: int = 0
    filesize_approx: int = 0  # bytes
    description: str = ""
    email: str = ""
    instagram_handles: list[str] = field(default_factory=list)
    social_links: list[dict[str, str]] = field(default_factory=list)
    thumbnail_url: str = ""
    webpage_url: str = ""
    formats: list[VideoFormatOption] = field(default_factory=list)


class VideoInfoWorker(QObject):
    """Fetch video metadata + formats + thumbnail bytes off the UI thread."""

    # Emitted with the parsed VideoInfo (includes .formats list)
    info_ready = Signal(object)
    # Emitted with raw thumbnail JPEG bytes
    thumbnail_ready = Signal(bytes)
    # Emitted when the fetch fails
    info_failed = Signal(str)

    def __init__(
        self,
        url: str,
        ytdlp_path: Path,
        timeout: float = 15.0,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._url = url
        self._ytdlp_path = ytdlp_path
        self._timeout = timeout
        self._cancelled = False

    @Slot()
    def run(self) -> None:
        if self._cancelled or not self._url:
            self.info_failed.emit("URL boş")
            return

        if not self._ytdlp_path.is_file():
            self.info_failed.emit("yt-dlp bulunamadı")
            return

        # 1. FAST PATH: If YouTube URL, instantly pre-fetch 16:9 HD thumbnail in ~50ms from CDN
        yt_id = extract_video_id(self._url)
        if yt_id and not self._cancelled:
            self._fetch_fast_youtube_thumbnail(yt_id)

        if self._cancelled:
            return

        # 2. FULL METADATA + FORMATS FETCH via yt-dlp --dump-json
        args: list[str] = [
            str(self._ytdlp_path),
            "--no-playlist",
            "--encoding", "utf-8",
            "--extractor-args", "youtube:player_client=visionos,android,mweb",
            "--user-agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
            "--dump-json",
            "--no-warnings",
            "--no-progress",
            "--skip-download",
            self._url,
        ]
        env = os.environ.copy()
        env["PYTHONIOENCODING"] = "utf-8"
        env["PYTHONUTF8"] = "1"

        kwargs: dict = {
            "stdout": subprocess.PIPE,
            "stderr": subprocess.PIPE,
            "text": True,
            "encoding": "utf-8",
            "errors": "replace",
            "env": env,
        }
        if os.name == "nt":
            kwargs["creationflags"] = 0x08000000  # CREATE_NO_WINDOW

        proc = subprocess.Popen(args, **kwargs)  # noqa: S603
        try:
            stdout, _ = proc.communicate(timeout=self._timeout)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.communicate(timeout=2)
            if not self._cancelled:
                self.info_failed.emit("Zaman aşımı")
            return
        except Exception as exc:
            if not self._cancelled:
                self.info_failed.emit(str(exc))
            return

        if self._cancelled:
            return

        if proc.returncode != 0 or not stdout:
            self.info_failed.emit("Video bilgisi alınamadı")
            return

        lines = [l.strip() for l in stdout.splitlines() if l.strip().startswith("{")]
        if not lines:
            self.info_failed.emit("Geçersiz yanıt")
            return

        try:
            data = json.loads(lines[0])
        except json.JSONDecodeError:
            self.info_failed.emit("JSON ayrıştırılamadı")
            return

        if self._cancelled:
            return

        # Extract metadata + formats from JSON
        raw_title = (data.get("title") or "").strip()
        cleaned_title = self._clean_title(raw_title, self._url)

        raw_channel = (data.get("channel") or data.get("uploader") or "").strip()
        cleaned_channel = self._clean_channel(raw_channel, self._url)

        desc = (data.get("description") or "").strip()
        channel_desc = (data.get("channel_description") or data.get("uploader_description") or "").strip()
        channel_url = (data.get("channel_url") or "").strip()
        combined_text = f"{desc}\n{channel_desc}\n{channel_url}"

        extracted_emails = self._extract_emails(combined_text)
        email_str = ", ".join(extracted_emails) if extracted_emails else ""

        extracted_insta = self._extract_instagram_handles(combined_text)
        social_links = self._extract_social_links(combined_text)

        info = VideoInfo(
            title=cleaned_title,
            channel=cleaned_channel,
            duration_seconds=int(data.get("duration") or 0),
            filesize_approx=self._estimate_filesize(data),
            description=desc,
            email=email_str,
            instagram_handles=extracted_insta,
            social_links=social_links,
            thumbnail_url=(data.get("thumbnail") or "").strip(),
            webpage_url=(data.get("webpage_url") or self._url).strip(),
            formats=self._extract_formats(data),
        )

        self.info_ready.emit(info)

        # 3. High quality thumbnail fetch (maxres / full quality from metadata)
        if info.thumbnail_url and not self._cancelled:
            self._fetch_thumbnail(info.thumbnail_url)

    def _extract_emails(self, text: str) -> list[str]:
        """Extract valid email addresses from text."""
        if not text:
            return []
        pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
        matches = re.findall(pattern, text)
        seen = set()
        result = []
        for email in matches:
            email_clean = email.strip('.').lower()
            if email_clean not in seen and not email_clean.endswith(('.png', '.jpg', '.jpeg', '.webp', '.gif', '.svg', '.mp4', '.mkv')):
                seen.add(email_clean)
                result.append(email_clean)
        return result

    def _extract_instagram_handles(self, text: str) -> list[str]:
        """Extract Instagram handles / URLs from text."""
        if not text:
            return []
        
        handles = []
        seen = set()

        # 1. Direct Instagram URLs: instagram.com/username or instagr.am/username
        url_pattern = r'(?:https?://)?(?:www\.)?(?:instagram\.com|instagr\.am)/([a-zA-Z0-9_.]+)'
        url_matches = re.findall(url_pattern, text, flags=re.IGNORECASE)
        for m in url_matches:
            handle = m.strip('/. ').lower()
            ignore_list = {'p', 'reel', 'reels', 'stories', 'explore', 'tv', 'direct', 'accounts', 'developer', 'about', 'privacy', 'terms'}
            if handle and handle not in ignore_list and handle not in seen:
                seen.add(handle)
                handles.append(handle)

        # 2. Text patterns: Instagram: @handle, IG: @handle, Insta: @handle
        text_pattern = r'(?:instagram|ig|insta)\s*[:=]\s*@?([a-zA-Z0-9_.]+)'
        text_matches = re.findall(text_pattern, text, flags=re.IGNORECASE)
        for m in text_matches:
            handle = m.strip('/. ').lower()
            ignore_list = {'p', 'reel', 'reels', 'stories', 'explore', 'tv', 'direct', 'accounts', 'developer', 'about'}
            if handle and len(handle) >= 3 and handle not in ignore_list and handle not in seen:
                seen.add(handle)
                handles.append(handle)

        return handles

    def _extract_social_links(self, text: str) -> list[dict[str, str]]:
        """Extract all social media & contact links (Email, Instagram, TikTok, Discord, Twitter/X, Twitch, Patreon, Linktree, Websites)."""
        if not text:
            return []

        results: list[dict[str, str]] = []
        seen_urls = set()

        def add_link(platform: str, label: str, url: str):
            clean_url = url.strip().rstrip('.,;()[]')
            if clean_url and clean_url.lower() not in seen_urls:
                seen_urls.add(clean_url.lower())
                results.append({"platform": platform, "label": label, "url": clean_url})

        # 1. Emails
        email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
        for email in re.findall(email_pattern, text):
            clean_email = email.strip('.').lower()
            if not clean_email.endswith(('.png', '.jpg', '.jpeg', '.webp', '.gif', '.svg', '.mp4', '.mkv')):
                add_link("email", f"📧 {clean_email}", f"mailto:{clean_email}")

        # 2. Discord
        discord_pattern = r'(?:https?://)?(?:www\.)?(?:discord\.gg|discord\.com/invite)/([a-zA-Z0-9_-]+)'
        for code in re.findall(discord_pattern, text, flags=re.IGNORECASE):
            add_link("discord", f"💬 Discord ({code})", f"https://discord.gg/{code}")

        # 3. Instagram
        insta_pattern = r'(?:https?://)?(?:www\.)?(?:instagram\.com|instagr\.am)/([a-zA-Z0-9_.]+)'
        for handle in re.findall(insta_pattern, text, flags=re.IGNORECASE):
            h = handle.strip('/. ').lower()
            ignore = {'p', 'reel', 'reels', 'stories', 'explore', 'tv', 'direct', 'accounts', 'developer', 'about', 'privacy', 'terms'}
            if h and h not in ignore:
                add_link("instagram", f"📸 Instagram (@{h})", f"https://instagram.com/{h}")

        insta_text_pattern = r'(?:instagram|ig|insta)\s*[:=]\s*@?([a-zA-Z0-9_.]+)'
        for handle in re.findall(insta_text_pattern, text, flags=re.IGNORECASE):
            h = handle.strip('/. ').lower()
            ignore = {'p', 'reel', 'reels', 'stories', 'explore', 'tv', 'direct', 'accounts', 'developer', 'about'}
            if h and len(h) >= 3 and h not in ignore:
                add_link("instagram", f"📸 Instagram (@{h})", f"https://instagram.com/{h}")

        # 4. TikTok
        tiktok_pattern = r'(?:https?://)?(?:www\.)?(?:tiktok\.com/@([a-zA-Z0-9_.]+)|vm\.tiktok\.com/([a-zA-Z0-9_.]+))'
        for handle1, handle2 in re.findall(tiktok_pattern, text, flags=re.IGNORECASE):
            h = (handle1 or handle2).strip('/. ').lower()
            if h:
                add_link("tiktok", f"🎵 TikTok (@{h})", f"https://tiktok.com/@{h}" if handle1 else f"https://vm.tiktok.com/{h}")

        tiktok_text_pattern = r'(?:tiktok|tt)\s*[:=]\s*@?([a-zA-Z0-9_.]+)'
        for handle in re.findall(tiktok_text_pattern, text, flags=re.IGNORECASE):
            h = handle.strip('/. ').lower()
            if h and len(h) >= 3:
                add_link("tiktok", f"🎵 TikTok (@{h})", f"https://tiktok.com/@{h}")

        # 5. Twitter / X
        twitter_pattern = r'(?:https?://)?(?:www\.)?(?:twitter\.com|x\.com)/([a-zA-Z0-9_]+)'
        for handle in re.findall(twitter_pattern, text, flags=re.IGNORECASE):
            h = handle.strip('/. ').lower()
            ignore = {'intent', 'share', 'search', 'home', 'explore', 'notifications', 'messages', 'i', 'tos', 'privacy'}
            if h and h not in ignore:
                add_link("twitter", f"𝕏 Twitter (@{h})", f"https://x.com/{h}")

        # 6. Twitch
        twitch_pattern = r'(?:https?://)?(?:www\.)?twitch\.tv/([a-zA-Z0-9_]+)'
        for handle in re.findall(twitch_pattern, text, flags=re.IGNORECASE):
            h = handle.strip('/. ').lower()
            ignore = {'directory', 'videos', 'clips', 'downloads', 'jobs', 'press', 'p'}
            if h and h not in ignore:
                add_link("twitch", f"👾 Twitch ({h})", f"https://twitch.tv/{h}")

        # 7. Other Links
        generic_url_pattern = r'https?://[^\s<>"{}|\\^`]+'
        for raw_url in re.findall(generic_url_pattern, text):
            clean_url = raw_url.rstrip('.,;()[]')
            lower_url = clean_url.lower()
            skip_domains = ['youtube.com', 'youtu.be', 'ytimg.com', 'googlevideo.com', 'google.com/maps', 'amazon.com', 'wildberries.ru', 'ozon.ru']
            if not any(domain in lower_url for domain in skip_domains) and clean_url.lower() not in seen_urls:
                if 'patreon.com' in lower_url:
                    add_link("patreon", f"🧡 Patreon", clean_url)
                elif 'linktr.ee' in lower_url:
                    add_link("linktree", f"🔗 Linktree", clean_url)
                elif 'buymeacoffee.com' in lower_url:
                    add_link("buymeacoffee", f"☕ BuyMeACoffee", clean_url)
                elif not any(p in lower_url for p in ['instagram.com', 'tiktok.com', 'discord.gg', 'discord.com', 'twitter.com', 'x.com', 'twitch.tv']):
                    domain_name = clean_url.split('://')[-1].split('/')[0].replace('www.', '')
                    add_link("website", f"🌐 {domain_name}", clean_url)

        return results

    def _clean_title(self, raw_title: str, url: str) -> str:
        """Clean generic / manifest titles into human-readable media titles."""
        generic_names = {"master", "index", "video", "playlist", "manifest", "stream", "hls", "audio", "output"}
        cleaned = (raw_title or "").strip()
        if not cleaned or cleaned.lower() in generic_names or cleaned.lower().startswith("master."):
            try:
                path = unquote(urlparse(url).path)
                parts = [
                    p for p in path.split("/")
                    if p and p.lower() not in generic_names and not p.lower().endswith((".txt", ".m3u8", ".mpd", ".html", ".php"))
                ]
                if parts:
                    candidate = parts[-1]
                    candidate = re.sub(r"\.(mp4|mkv|webm|avi|flv)$", "", candidate, flags=re.IGNORECASE)
                    candidate = re.sub(r"[-_.]+", " ", candidate)
                    candidate = re.sub(r"\s+", " ", candidate).strip()
                    if candidate:
                        return candidate.title()
            except Exception:
                pass
        return cleaned or "Video"

    def _clean_channel(self, raw_channel: str, url: str) -> str:
        """Extract a sensible source / channel label."""
        if raw_channel:
            return raw_channel
        try:
            domain = urlparse(url).netloc
            return domain.replace("www.", "") or "Web"
        except Exception:
            return "Web"

    def _fetch_fast_youtube_thumbnail(self, yt_id: str) -> None:
        """Try high quality 16:9 thumbnail endpoints first."""
        candidates = [
            f"https://i.ytimg.com/vi/{yt_id}/maxresdefault.jpg",
            f"https://i.ytimg.com/vi/{yt_id}/hq720.jpg",
            f"https://i.ytimg.com/vi/{yt_id}/sddefault.jpg",
            f"https://i.ytimg.com/vi/{yt_id}/hqdefault.jpg",
        ]
        for url in candidates:
            if self._cancelled:
                return
            try:
                req = urllib.request.Request(url, method="GET")
                req.add_header("User-Agent", "Videcook/0.2")
                with urllib.request.urlopen(req, timeout=4) as resp:
                    if resp.status == 200:
                        data = resp.read()
                        if data and not self._cancelled:
                            self.thumbnail_ready.emit(data)
                            return
            except Exception:
                continue

    def _extract_formats(self, data: dict) -> list[VideoFormatOption]:
        """Extract available video format options with standard labels and accurate size estimates."""
        formats = data.get("formats", [])
        dur = int(data.get("duration") or 0)

        # Determine best audio stream size to combine with video-only streams
        best_audio_size = 0
        for f in formats:
            vcodec = f.get("vcodec", "none")
            acodec = f.get("acodec", "none")
            s = f.get("filesize") or f.get("filesize_approx") or 0
            if (vcodec == "none" or vcodec == "images") and acodec != "none":
                best_audio_size = max(best_audio_size, int(s))
        if best_audio_size == 0 and dur > 0:
            best_audio_size = int(dur * 160_000 / 8)

        format_dict: dict[str, VideoFormatOption] = {}

        for f in formats:
            vcodec = f.get("vcodec")
            if not vcodec or vcodec == "none" or vcodec == "images":
                continue

            h = f.get("height") or 0
            w = f.get("width") or 0
            note = (f.get("format_note") or "").strip()

            std_h = self._get_standard_height(h, w, note)
            if std_h <= 0:
                continue

            # Label generation
            if std_h >= 4320:
                label = f"8K ({std_h}p)"
            elif std_h >= 2160:
                label = f"4K ({std_h}p)"
            elif std_h >= 1440:
                label = f"2K ({std_h}p)"
            else:
                label = f"{std_h}p"

            q_val = str(h if h > 0 else std_h)
            v_size = f.get("filesize") or f.get("filesize_approx") or 0
            if v_size == 0 and dur > 0:
                bitrate_bps = {
                    4320: 25_000_000,
                    2160: 12_000_000,
                    1440: 6_000_000,
                    1080: 3_200_000,
                    720: 1_600_000,
                    480: 800_000,
                    360: 450_000,
                    240: 220_000,
                    144: 100_000,
                }.get(std_h, std_h * 2000)
                v_size = int(dur * bitrate_bps / 8)

            total_size = v_size + best_audio_size

            if label not in format_dict or std_h > format_dict[label].std_height or total_size > format_dict[label].filesize_approx:
                format_dict[label] = VideoFormatOption(
                    label=label,
                    quality_value=q_val,
                    std_height=std_h,
                    filesize_approx=total_size,
                )

        sorted_options = sorted(format_dict.values(), key=lambda opt: opt.std_height, reverse=True)
        return sorted_options

    def _get_standard_height(self, h: int, w: int, note: str) -> int:
        """Map format note, width and height to standard resolution buckets."""
        m = re.search(r"(\d+)p", note or "")
        if m:
            val = int(m.group(1))
            if val in STANDARD_HEIGHTS:
                return val

        dim = max(h, w)
        if dim >= 3800:
            return 2160
        if dim >= 2500:
            return 1440
        if dim >= 1850:
            return 1080
        if dim >= 1200:
            return 720
        if dim >= 800:
            return 480
        if dim >= 600:
            return 360
        if dim >= 400:
            return 240
        if dim >= 200:
            return 144
        return h

    def _estimate_filesize(self, data: dict) -> int:
        """Estimate total download size from format data."""
        fs = data.get("filesize_approx") or data.get("filesize") or 0
        if fs:
            return int(fs)

        formats = data.get("formats", [])
        best_video_size = 0
        best_audio_size = 0
        for f in formats:
            vcodec = f.get("vcodec", "none")
            acodec = f.get("acodec", "none")
            size = f.get("filesize") or f.get("filesize_approx") or 0
            if vcodec != "none" and vcodec != "images":
                best_video_size = max(best_video_size, int(size))
            elif acodec != "none":
                best_audio_size = max(best_audio_size, int(size))

        return best_video_size + best_audio_size

    def _fetch_thumbnail(self, url: str) -> None:
        """Download thumbnail bytes and emit them."""
        try:
            req = urllib.request.Request(url, method="GET")
            req.add_header(
                "User-Agent",
                "Videcook/0.2 (https://github.com/anilberkayalici/Videcook)",
            )
            with urllib.request.urlopen(req, timeout=6) as resp:
                data = resp.read()
            if not self._cancelled and data:
                self.thumbnail_ready.emit(data)
        except Exception:
            pass

    def cancel(self) -> None:
        self._cancelled = True
