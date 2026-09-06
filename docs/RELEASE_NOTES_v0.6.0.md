# 🚀 Videcook v0.6.0 — Sürüm Notları (Release Notes)

Videcook'un en kapsamlı ve en güçlü güncellemesi olan **v0.6.0** yayında! Bu sürümle birlikte Videcook, standart bir indirici olmaktan çıkıp tam teşekküllü bir **multimedya ve canlı ses işleme stüdyosu** haline geldi.

---

## 🎛️ 1. Canlı Stüdyo Ton (Pitch) & BPM Ayarlayıcı (Gerçek Zamanlı DSP Motoru)
- **Spotify C++ `pedalboard` & WASAPI Mimarisi:** Parça çalarken anında transpoze yapın ve hızını (BPM) değiştirin; sıfır gecikme ve anlık tepki.
- **🎯 Akıllı Harmonik Eşleme (Smart Camelot Key Match):** Referans parçanın tonunu otomatik analiz eder, Camelot çarkı kurallarına göre en uyumlu yarı ton farkını (-12 ile +12) milisaniyeler içinde hesaplayıp uygular.
- **⚡ Müzikal Oktav Duyarlı BPM Eşleme (Optimal Tempo Match):** Örneğin 73.6 BPM'lik bir vokal ile 171 BPM'lik bir drill beat eşlenirken parçayı aşırı hızlandırıp bozmak yerine, müzikal olarak kusursuz olan **Half-Time (85.5 BPM / +16.2%)** hızını akıllıca seçer.
- **🎧 İkiz Referans Oynatıcı (Emerald Twin Player):** Referans parçayı dinleyebilmek için bağımsız zümrüt yeşili dalga boyu oynatıcısı, bağımsız ses ayarı ve karşılıklı akıllı susturma (A/B dinleme testi).
- **🔊 16K Overlap-Add Hann Filtresi & True Peak Limiter:** Düşük bas frekanslarında dahi faz çatlamasını (pıtırtı seslerini) tamamen yok eden 16.384 örnek blok boyutu ve çıkışta patlamayı önleyen -0.2 dBFS stüdyo sınırlayıcısı ile stüdyo kalitesinde ses çıktısı.
- **📐 880px Geniş Stüdyo Konsolu:** Yan yana yerleştirilmiş Pitch ve BPM panelleri, interaktif tıklanabilir dalga boyları ve ekran altına sabitlenmiş `Yeni Haliyle Kaydet` butonu.

---

## 🎬 2. Yapay Zeka Video Düzenleyici (AI Editor)
- **Akıllı Sahne ve Klip Yönetimi:** FFmpeg ve MoviePy 2.0 tabanlı video kesme, klip birleştirme.
- **Arkaplan Müziği ve Ses Dengeleme:** Dinamik ses kısma (ducking) ve dengeli arka plan müziği miksleme.

---

## 🌍 3. Akıllı Altyazı & Çeviri Merkezi (Subtitle Translate Hub)
- **Groq Whisper Entegrasyonu:** Konuşmaları saniyeler içinde yazıya dökerek İngilizce ve Türkçe `.srt` ve `.vtt` formatlarında altyazı üretimi.
- **Güvenli Depolama:** API anahtarları Windows üzerinde DPAPI (CryptProtectData), Linux üzerinde `chmod 600` ile korunur.

---

## 🔄 4. Evrensel Medya & Belge Dönüştürücü (Converter)
- **Geniş Format Desteği:** MP4, MKV, AVI, MOV, WebM, MP3, WAV, FLAC, AAC, OPUS arasında kayıpsız ve hızlı FFmpeg dönüştürme.
- **Belge ve PDF Desteği:** Çok amaçlı dönüştürme araçları.

---

## 🚀 5. AI Çözünürlük Yükseltme (Upscayl / Super Resolution)
- **NCNN AI Modelleri:** Fotoğraf ve videolarda 2x/4x netleştirme ve yapay zeka destekli çözünürlük yükseltme.

---

## 📜 6. İndirilenler & Geçmiş (History Hub)
- Tamamlanan tüm indirme, dönüştürme ve düzenleme işlemlerinin listelendiği, tek tıkla dosyaya veya klasöre erişim sağlayan geçmiş ekranı.

---

## 🔧 Diğer Düzeltmeler ve İyileştirmeler
- **İki Dilli Arayüz:** Türkçe ve İngilizce dil desteği (otomatik kalıcılık).
- **Yüksek Çözünürlük Desteği:** 4K, 1080p, 60fps video indirme ve kayıpsız FLAC/WAV ses ayrıştırma.
- **Bellek ve Süreç Temizliği:** Arka planda çalışan alt süreçlerin (zombie processes) ve geçici dosyaların anında temizlenmesi.
