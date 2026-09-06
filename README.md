# Videcook — v0.6.0

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Platform](https://img.shields.io/badge/platform-Windows%20%7C%20Linux%20%7C%20macOS-lightgrey.svg)]()
[![Release](https://img.shields.io/github/v/release/anilberkayalici/Videcook?color=purple)](https://github.com/anilberkayalici/Videcook/releases)

---

**TR:** **Videcook**, yt-dlp + FFmpeg gücüyle yüksek kaliteli video/ses indirme, Spotify C++ `pedalboard` DSP motoru ile **canlı stüdyo kalitesinde Ton (Pitch) & BPM ayarlama ve akıllı beat eşleme**, Groq Whisper ile otomatik altyazı ve çeviri, MoviePy tabanlı AI video kurgulama, format dönüştürme ve çözünürlük yükseltme yapabilen modern, hepsi-bir-arada masaüstü stüdyosudur.

**EN:** **Videcook** is an all-in-one cross-platform multimedia studio featuring yt-dlp + FFmpeg downloading, real-time zero-latency **Pitch & BPM shifting with smart harmonic beat matching** powered by Spotify C++ `pedalboard` DSP, AI-powered subtitle generation & translation via Groq Whisper, MoviePy video editing, format conversion, and upscale tools.

---

## 🌟 v0.6.0 Öne Çıkan Yenilikler / What's New in v0.6.0

### 🎛️ 1. Gerçek Zamanlı Stüdyo Ton (Pitch) & BPM Motoru (Real-time DSP Studio)
- **Spotify C++ `pedalboard` & WASAPI Entegrasyonu:** Müzik çalarken anında transpoze yapın, şarkının hızını (BPM) değiştirin — sıfır gecikme, sıfır takılma.
- **Akıllı Harmonik Eşleme (Smart Camelot Key Match):** Referans parçanın müzikal tonunu analiz eder; Camelot çarkına göre en uyumlu yarı ton farkını (-12 ile +12) otomatik hesaplar.
- **Müzikal Oktav Duyarlı BPM Eşleme (Optimal Tempo Match):** Örneğin 73.6 BPM'lik bir vokali 171 BPM'lik bir drill beat'e uydururken aşırı hızlandırmak yerine, müzikal olarak kusursuz olan **Half-Time (85.5 BPM / +16.2%)** hızını akıllıca önerir.
- **İkiz Referans Oynatıcı (Emerald Twin Player):** Referans parçayı dinleyebilmeniz için bağımsız zümrüt yeşili dalga boyu oynatıcısı, bağımsız ses kontrolü ve karşılıklı akıllı susturma (A/B dinleme testi).
- **16K Overlap-Add Hann Filtresi & -0.2 dBFS Stüdyo Sınırlayıcı (True Peak Limiter):** Düşük bas frekanslarında dahi faz çatlamasını (pıtırtı/çatırtı seslerini) ortadan kaldıran 16.384 örnek blok boyutu ve çıkışta patlamayı önleyen stüdyo sınırlayıcısı ile kristal netliğinde dışa aktarım.
- **880px Geniş Stüdyo Konsolu:** Yan yana yerleştirilmiş Pitch ve BPM panelleri, interaktif tıklanabilir dalga boyları ve ekran altına sabitlenmiş `Yeni Haliyle Kaydet` butonu.

### 🎬 2. Yapay Zeka Video Düzenleyici (AI Video Editor)
- FFmpeg ve MoviePy 2.0 tabanlı video kesme, klip birleştirme.
- Otomatik ses seviyesi dengeleme ve arkaplan müziği (ducking / background music mix).

### 🌍 3. Altyazı & Çeviri Merkezi (Subtitle Translate Hub)
- Groq Whisper ile saniyeler içinde konuşmadan İngilizce veya Türkçe `.srt` ve `.vtt` altyazı üretimi.
- Güvenli API anahtarı yönetimi (Windows DPAPI / Linux chmod 600).

### 🔄 4. Evrensel Medya & Belge Dönüştürücü (Converter)
- MP4, MKV, AVI, MOV, WebM, MP3, WAV, FLAC, AAC, OPUS formatları arasında kayıpsız dönüştürme.
- PDF ve belge formatları desteği.

### 🚀 5. AI Çözünürlük Yükseltme (Upscayl / Super Resolution)
- NCNN AI modelleriyle fotoğraflar ve video karelerinde 2x/4x netleştirme ve kalite artırma.

### 📜 6. İndirilenler & Geçmiş (History)
- Tamamlanan tüm indirme, dönüştürme ve düzenleme işlemlerinin listelendiği, tek tıkla dosya veya klasöre erişim sağlayan geçmiş ekranı.

---

## 💻 Desteklenen İşletim Sistemleri / Supported Platforms

- **Windows:** Windows 10 / 11 (64-bit) — Kurulum gerektirmeyen taşınabilir (Portable) ZIP
- **Linux:** x86_64 AppImage
- **macOS:** Apple Silicon / Intel DMG

---

## 🛠️ Kurulum & Geliştirme (Setup & Development)

### Gereksinimler (Prerequisites)
- Python 3.11 veya üzeri
- Git
- Windows, Linux veya macOS

### Kaynak Koddan Çalıştırma

```bash
# 1. Depoyu klonlayın
git clone https://github.com/anilberkayalici/Videcook.git
cd Videcook

# 2. Bağımlılıkları yükleyin
python -m pip install --upgrade pip
pip install -r requirements.txt

# 3. Gerekli motorları indirin (yt-dlp, FFmpeg)
python scripts/download_binaries.py --all

# 4. Uygulamayı başlatın
python -m videcook.main
```

---

## 🧪 Testler (Automated Tests)

Uygulama kapsamlı birim ve UI duman (smoke) testleri ile korunmaktadır:

```bash
# Tüm testleri çalıştırın
pytest

# Sadece Ton & BPM stüdyo testlerini çalıştırın
pytest tests/test_pitch_tempo.py

# Arayüz duman testlerini çalıştırın
pytest tests/test_ui_smoke.py
```

---

## 📦 Taşınabilir Windows Paketi Oluşturma (Portable Build)

Bağımsız, kurulum gerektirmeyen bir `.exe` klasörü oluşturmak için:

```cmd
scripts\build_portable.bat
```

İşlem tamamlandığında `dist\Videcook\Videcook.exe` dosyası hazır hale gelir. `dist\Videcook` klasörünü ZIP yaparak dilediğiniz bilgisayarda doğrudan çalıştırabilirsiniz.

---

## 🔒 Güvenlik & Gizlilik İlkeleri (Privacy & Safety)

1. **Çerez Güvenliği (Cookie Safety):** `cookies.txt` dosyalarının içeriği asla okunmaz, saklanmaz veya sunuculara iletilmez. Yalnızca dosya adı arayüzde gösterilir.
2. **API Anahtarı Güvenliği:** Groq API anahtarları Windows üzerinde **DPAPI** (CryptProtectData) ile şifrelenir; Linux üzerinde `chmod 600` ile korunur.
3. **Kalıntısız Temizlik:** İptal edilen indirme ve dönüştürme işlemlerinde geçici dosyalar ve arka plan işlemleri (zombie processes) anında temizlenir.

---

## 📄 Lisans (License)

Bu proje [MIT Lisansı](LICENSE) ile lisanslanmıştır. Kullanılan üçüncü taraf araçların (yt-dlp, FFmpeg, Spotify Pedalboard) lisansları için [THIRD_PARTY_LICENSES.md](THIRD_PARTY_LICENSES.md) dosyasına bakabilirsiniz.
