# Third-Party Licenses

Videcook bundles or interfaces with the following third-party software.
Full license texts should be included in the release distribution.

---

## yt-dlp

- **Project:** https://github.com/yt-dlp/yt-dlp
- **License:** [The Unlicense](https://unlicense.org/)
- **Usage:** Core download engine invoked as a subprocess.
- **Note:** The pre-built `yt-dlp.exe` available from the yt-dlp GitHub
  releases is distributed under the Unlicense. If you build yt-dlp yourself
  or use a different distribution, verify the license terms of that build.

---

## FFmpeg / FFprobe

- **Project:** https://ffmpeg.org/
- **License:** LGPLv2.1+ / GPLv2+ (depending on build configuration)
- **Usage:** Media processing (format conversion, muxing) invoked as
  subprocesses.
- **Note:** The pre-built Windows binaries recommended by Videcook come from
  [BtbN/FFmpeg-Builds](https://github.com/BtbN/FFmpeg-Builds) which are
  built with GPL components enabled. The GPL applies to FFmpeg when
  configured with `--enable-gpl`. Users intending to distribute Videcook
  commercially should verify that the specific FFmpeg build they bundle is
  compatible with their intended use and licensing obligations. Building a
  custom LGPL-only FFmpeg binary is possible if GPL components are omitted.

---

## Qt / PySide6

- **Project:** https://www.qt.io/
- **License:** LGPLv3 / GPLv3 / Qt Commercial License
- **Usage:** GUI framework used by Videcook via the `PySide6-Essentials`
  Python package. PySide6 is the official LGPL-licensed Python binding for Qt.
- **Note:** Videcook uses `PySide6-Essentials` (LGPL). If you distribute
  Videcook, you must comply with the LGPL obligations for Qt. See the
  [Qt Licensing](https://www.qt.io/licensing/) page for details.

---

## Python

- **Project:** https://www.python.org/
- **License:** Python Software Foundation License (PSF)
- **Usage:** Runtime platform for Videcook.

---

*Videcook itself does not include the source code or compiled binaries of
these tools in its git repository. Users are responsible for obtaining
binaries from official sources and verifying license compatibility before
distribution.*
