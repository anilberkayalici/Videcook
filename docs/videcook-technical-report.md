# Videcook — Kapsamlı Teknik Rapor (AI Asistanı İçin)

## Genel Bakış

**Videcook**, `yt-dlp + FFmpeg + Groq Whisper` kullanarak YouTube ve diğer sitelerden video/ses/thumbnail/altyazı indirmeyi, altyazı format dönüşümü yapmayı ve temalı bir arayüzde yönetmeyi sağlayan çok platformlu bir masaüstü uygulamasıdır.

- **Dil:** Python 3.11+
- **Arayüz:** PySide6 (Qt 6.11)
- **Paketleme:** PyInstaller (Windows portable .exe, Linux AppImage, macOS .app/DMG)
- **Test:** pytest + pytest-qt (194 test, hepsi geçiyor)
- **Lint:** ruff
- **Sürüm:** 0.4.0
- **Lisans:** MIT

## Mimari Katmanlar

```
videcook/
  core/          # İş mantığı, Qt bağımsız, test edilebilir
  services/      # Harici araçlar (yt-dlp, ffmpeg, Groq API)
  ui/            # PySide6 arayüz (sayfalar, worker thread'ler, tema)
  utils/         # Dil yönetimi (i18n), tercihler, hata çevirisi
  main.py        # Giriş noktası
  app.py         # QApplication bootstrap
  paths.py       # Dosya yolu yardımcıları (frozen/dev)
```

### Bağımlılık zinciri

```
ui/ → core/ + services/ + utils/
services/ → core/ + paths.py
core/ → sadece stdlib (models hariç)
utils/ → paths.py
```

## Tüm Özellikler ve Teknik Detaylar

### 1. Video İndirme (`download_page.py` + `command_builder.py`)

**Arayüz elemanları:**
- URL input (placeholder: `https://...`)
- Video/Ses toggle (segment button)
- Kalite dropdown: En iyi kalite, 1080p, 720p, 480p
- "Üyelere Özel Video" toggle (cookie dosyası için)
- Cookie dosyası seçici (sadece `.txt`, uzantı kontrolü)
- Çıktı klasörü seçici (son seçim hatırlanır)
- Embed thumbnail checkbox (sadece ses modunda)
- İlerleme çubuğu + durum etiketi
- İşlem günlüğü (son 500 satır, monospace)

**Teknik akış:**
1. URL doğrulanır (`validate_url` — http/https başlamalı)
2. Playlist tespiti (`detect_playlist_intent` — URL'de `list=` parametresi)
3. Binary check (`check_binaries` — yt-dlp.exe + ffmpeg.exe PATH veya bin/ kontrolü)
4. Tercihler kaydedilir (son kalite, ses formatı, çıktı klasörü)
5. `DownloadRequest` oluşturulur
6. `DownloadWorker` (QObject + QThread) arka planda çalışır:
   - `build_ytdlp_command()` ile komut oluşturulur — **asla shell string değil**, arg list
   - `subprocess.Popen` ile çalıştırılır
   - `stream_lines()` ile stdout satır satır okunur
   - `parse_progress_line()` ile progress parse edilir
   - İptal: `process.terminate()` + `_cancelled` flag
   - Bittiğinde cookie yolu bellekten silinir

**Format seçici (`quality.py`):**
```python
QualityOption.BEST: "bv*[vcodec^=avc1]+ba/b[vcodec^=avc1]/bv*+ba/b"
```
Her zaman H.264 (avc1) codec'ini tercih eder. 1080p altı YouTube H.264 verir → Doğrudan Audition/Reaper'da çalışır.

### 2. H.264 Uyumluluk Modu (`command_builder.py`)

**Sorun:** YouTube 1080p üstünü VP9/AV1 codec'inde sunar. Adobe Audition ve Reaper VP9/AV1'i MP4 içinde çözemez → siyah ekran.

**Çözüm:** `force_h264_transcode` flag'i (Ayarlar'da toggle, varsayılan AÇIK). Açık olduğunda postprocessor args eklenir:
```python
_H264_TRANSCODE_ARGS = "ffmpeg:-c:v libx264 -preset medium -crf 20 -c:a copy"
```
- Video: libx264 ile yeniden kodlanır (CRF 20 = görsel kalite)
- Ses: kopyalanır, kalite kaybı olmaz
- 1080p ve altı: YouTube zaten H.264 verir → hızlı mod (transcode gereksiz)
- 1440p/4K: VP9/AV1 alınır, H.264'e dönüştürülür → yavaş ama Audition'da çalışır

### 3. Ses İndirme (`command_builder.py` `_build_audio_command`)

**AudioFormat enum:** MP3, Opus, AAC, FLAC, WAV (M4A kaldırıldı — AAC'nin doğal konteyneri M4A olduğu için mükerrerdi)

**Varsayılan:** WAV (dublajcılar için sıkıştırılmamış)
**Sıralama:** WAV > MP3 > Opus > AAC (M4A) > FLAC

**Teknik:**
```python
args = [ytdlp, "--ffmpeg-location", ffmpeg_dir, "-x", "--audio-format", fmt, "--audio-quality", "0", "-P", out_dir, "--newline"]
```
- `-x`: ses çıkart
- `--audio-format wav`: WAV container, PCM codec
- `--audio-quality 0`: en yüksek kalite
- Embed thumbnail: `--embed-thumbnail --embed-metadata`

### 4. Thumbnail İndirme (`thumbnail.py` + `download_page.py`)

**Toggle:** "Sadece Thumbnail İndir" (üyelere özel toggle'ın altında)
**Boyutlar:** 1280x720 (MaxRes), 640x480 (SD), 480x360 (HQ), 320x180 (MQ), 120x90 (Default)

**Video ID extraction:** 7 farklı YouTube URL formatı (watch, youtu.be, shorts, embed, v, live, music)

**Teknik akış:**
1. URL'den video ID parse (`extract_video_id` — regex) — 11 karakter alfanumerik
2. `fetch_metadata()` → yt-dlp `--dump-json` ile video başlığı (dosya adı için)
3. `download_thumbnail()` → `https://img.youtube.com/vi/{ID}/{size}.jpg`
4. 404 fallback: istenen boyut yoksa sırayla küçük boyutlar denenir
5. JPEG magic byte kontrolü (geçersiz veri reddedilir)
6. Dosya adı: `{title} - {size}.jpg`
7. Backend: `ThumbnailDownloadWorker` (QObject + QThread)

**Güvenlik notları:** API key yok, public endpoint, rate limit yok.

### 5. Altyazı Oluşturma (Groq Whisper)

**Sayfa:** Altyazı sekmesi
**Servisler:** `groq_transcription.py` + `subtitle_pipeline.py` + `subtitle_worker.py`

**Akış:**
1. Ses dosyası seçilir (mp3, m4a, wav, ogg, flac, webm)
2. SRT çıktı yolu belirlenir
3. Groq API anahtarı Ayarlar'dan okunur (güvenli depolama — DPAPI/Linux chmod)
4. `SubtitlePipeline`: FFmpeg ile sesi chunk'lara böler, Groq Whisper'a gönderir
5. Sonuç İngilizce `.srt` dosyasına yazılır

### 6. SRT Altyazı Dönüştürme (`subtitle_formatter.py`)

**Sayfa:** Çeviri sekmesi (yeni!)
**Kaynak:** TypeScript Çeviri-Uygulaması projesinden port edildi

**Pipeline:**
```
parse_srt → normalize_cues → detect_sequence_markers → format_subtitles → stringify_formatted_lines
```

**Çıktı formatı:**
```
MM.SS - (Karakter İsmi) - Diyalog metni
MM.SS - (Ayşe + Mehmet) - Çoklu konuşmacı
MM.SS - MM.SS - Opening        # sequence marker
MM.SS - (Karakter) - (nara)   # efekt satırı
```

**Özellikler:**
- SRT timecode parse (HH:MM:SS,mmm)
- Speaker extraction (regex: `Speaker: text` veya `Speaker + Speaker: text`)
- Opening/Ending tespiti (75-150s sessizlik aralığı, pozisyon)
- Cümle başı büyük harf normalizasyonu (Türkçe)
- Bozuk satır atlama + uyarı verme
- UTF-8, UTF-8-BOM, CP1254 encoding desteği
- Çıktı: kopyala veya `.txt` kaydet

**Locale stringleri:** `nav.translate`, `translate.*` (12 yeni anahtar, TR + EN)

### 7. Binary Yönetimi (`binary_locator.py` + `binary_downloader.py`)

**Binary'ler:** yt-dlp, ffmpeg, ffprobe

**Arama sırası:**
1. Sistem PATH (`shutil.which`)
2. `bin/` klasörü (uygulama dizini)
3. Kullanıcı veri dizini (indirilen binary'ler)

**Setup Wizard (`setup_wizard.py`):** İlk çalıştırmada eksik binary'leri otomatik indirir:
- yt-dlp: GitHub releases → `yt-dlp.exe`
- FFmpeg+FFprobe: BtbN/FFmpeg-Builds → zip'ten çıkartılır
- Progress bar + kaynak onayı

**Update Checker (`update_checker.py`):** Ayarlar'dan yt-dlp sürümünü kontrol eder, GitHub API ile karşılaştırır, `yt-dlp -U` ile günceller.

### 8. Tema Sistemi (`theme.py`)

**6 tema:** Wine (varsayılan), Dracula, Nord, Gruvbox, Solarized, Monokai

**Mimari:**
- Her tema 50+ renk değişkeninden oluşan bir `dict`
- Ortak QSS template — `{{bg}}`, `{{accent}}` gibi placeholder'lar
- `build_stylesheet(theme_key)` → tam QSS string
- `apply_theme(app, theme_key)` → anında uygular

**UI:** Ayarlar'da 6 yuvarlak renk swatch'ı (44×44px, diagonal gradient). Tıklayınca anında tema değişir, tercihlere kaydedilir. Swatch'lar `QPushButton` ile `border-radius: 22px` ve `qlineargradient` kullanır.

### 9. Güvenli Depolama (`secure_store.py`)

- **Windows:** DPAPI (CryptProtectData/CryptUnprotectData)
- **Linux:** chmod 600 + base64 encoding
- **Kullanım:** Groq API anahtarı için

### 10. Dil ve Tercihler (`i18n.py` + `preferences.py`)

**Diller:** Türkçe (varsayılan), İngilizce — TR/EN toggle (header'da)
**JSON tabanlı:** `locales/tr.json` (196 anahtar), `locales/en.json` (196 anahtar)

**Tercihler (`videcook_prefs.json`):**
```python
@dataclass
class UserPreferences:
    language: str = "tr"
    last_output_folder: str = ""
    last_quality: str = "quality.best"
    last_audio_format: str = "audio_format.wav"
    embed_thumbnail: bool = True
    advanced_args: str = ""
    h264_compat_mode: bool = True
    theme: str = "wine"
    format_cache: dict[str, str] = field(default_factory=dict)  # max 32 entries
```
Geriye uyumlu — eksik anahtarlar varsayılan değerle doldurulur.

### 11. Gezinme (`main_window.py`)

**Sidebar:** İndir → Altyazı → Çeviri → Ayarlar → Nasıl Kullanılır
**Header:** Uygulama başlığı + slogan + TR/EN toggle
**Stacked widget:** 6 sayfa (setup dahil)
**Metadata:** Versiyon numarası sidebar footer'da

### 12. Yardım Sayfası (`help_page.py`)

4 tab: Video İndirme, Ses İndirme, Altyazı, Çeviri
Her tab: numaralı adımlar (7/7/7/5) + uyarı kutusu

### 13. Hata Yönetimi (`error_parser.py`)

yt-dlp hata çıktısını parse eder, kullanıcı dostu mesajlara çevirir:
- HTTP 403, 404, 429
- Video unavailable/private/members-only
- Ağ hatası, SSL, rate limit
- Cookie geçersiz/süresi dolmuş

### 14. Playlist Desteği (`playlist.py`)

URL'de `list=` parametresi tespiti. Dialog: "Bu videoyu indir" / "Tüm playlist'i indir"

### 15. Cookie Güvenliği

- Cookie dosyası içeriği **asla okunmaz**
- Cookie dosya yolu **oturumlar arası saklanmaz**
- Log'da sadece dosya adı gösterilir, tam yol asla
- İndirme sonrası (başarı/hata/iptal) bellekten temizlenir

### 16. Gelişmiş yt-dlp Argümanları

Ayarlar'da `--limit-rate 5M --sleep-interval 3` gibi ek flag'ler. `shlex.split()` ile parse edilir, tırnaklı değerler desteklenir. Her indirme komutuna eklenir.

### 17. Thumbnail Preview Worker (`thumbnail_worker.py`)

`ThumbnailPreviewWorker` (kullanılmıyor — preview kaldırıldı):
- MaxRes thumbnail'i önizleme için çeker
- İptal edilebilir

`ThumbnailDownloadWorker` (aktif):
- yt-dlp metadata + urllib thumbnail indirme
- Progress sinyalleri, log, finished

### 18. Test Suite

**194 test, 194 passing** — test dosyaları:

| Test Dosyası | Kapsam |
|---|---|
| `test_binary_locator.py` | Binary bulma mantığı |
| `test_command_builder.py` | yt-dlp komut oluşturma (video, ses, H.264, audio format) |
| `test_download_page_layout.py` | UI geometrisi, widget varlığı |
| `test_download_process.py` | subprocess yönetimi |
| `test_download_worker_smoke.py` | Worker yapısı |
| `test_groq_transcription.py` | Groq API |
| `test_i18n.py` | Dil yönetimi |
| `test_paths.py` | Dosya yolu mantığı |
| `test_playlist.py` | Playlist tespiti |
| `test_preferences.py` | Tercih okuma/yazma, geriye uyumluluk |
| `test_progress_parser.py` | yt-dlp çıktı parse |
| `test_settings_page_layout.py` | Ayarlar UI, H.264 toggle |
| `test_subtitle_formatter.py` | SRT format dönüşümü (8 fixture seti) |
| `test_subtitle_pipeline.py` | Altyazı pipeline |
| `test_subtitles.py` | Altyazı core |
| `test_thumbnail.py` | Thumbnail parse, URL, indirme (mock, 52 test) |
| `test_ui_smoke.py` | Temel UI testi |
| `test_validators.py` | URL/cookie/klasör doğrulama |

### 19. Derleme ve Dağıtım

**Windows:** `scripts/build_portable.bat` → `dist/Videcook/` → ZIP (207 MB)
**Linux:** `scripts/build_linux.sh` → AppImage (appimagetool)
**macOS:** `.github/workflows/build-macos.yml` → DMG (create-dmg + GitHub Actions)

**Spec dosyası (`Videcook.spec`):** Cross-platform — platforma göre binary uzantısı, ikon formatı, macOS Info.plist otomatik ayarlanır.

### 20. Veri Akışı (Özet)

```
Kullanıcı → DownloadPage → DownloadRequest → command_builder
                                            ↓
                                     yt-dlp subprocess
                                            ↓
                                   progress_parser → UI signals
                                            ↓
                                     Dosya diske yazılır
```

```
Kullanıcı → SubtitlePage → Groq API → .srt dosyası
                            ↓
                    Çeviri sayfası → subtitle_formatter → .txt dosyası
```

```
Kullanıcı → Thumbnail toggle → extract_video_id
                                    ↓
                            yt-dlp metadata
                                    ↓
                         img.youtube.com → .jpg dosyası
```

## Değiştirilmemesi Gereken Hassas Noktalar

- **Cookie güvenlik katmanı:** İçerik okunmaz, yol saklanmaz, log'da redacted
- **Shell injection koruması:** Tüm komutlar arg list, `shell=False`
- **Thread yönetimi:** DownloadWorker, ThumbnailDownloadWorker — UI thread bloklanmaz
- **Sinyal bağlantı sırası:** `finished → on_finished → quit → deleteLater` zinciri bozulursa çökme olur
- **AudioFormat.WAV varsayılan:** Dublajcı workflow için kritik
- **H.264 format seçici:** `vcodec^=avc1` tercihi Audition uyumluluğu için zorunlu

## Backward Compatibility

- Eski `videcook_prefs.json` dosyaları yeni sürümde sorunsuz açılır (eksik alanlar varsayılanla doldurulur)
- `AudioFormat.M4A` enum değeri kaldırıldı ama eski prefs dosyasında `last_audio_format: "audio_format.m4a"` varsa, dropdown'da eşleşmez → ilk seçenek (WAV) seçilir
