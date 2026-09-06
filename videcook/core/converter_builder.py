import json
import os
import subprocess
from pathlib import Path
from dataclasses import dataclass
from typing import Optional


def probe_audio_channels(file_path: Path, ffprobe_path: Path | None = None) -> tuple[int, str]:
    """Probe audio channels and channel layout of a media file using ffprobe.
    
    Returns:
        tuple[int, str]: (channels, channel_layout) e.g. (6, "5.1(side)") or (2, "stereo") or (0, "")
    """
    if ffprobe_path is None:
        try:
            from videcook.services.binary_locator import check_binaries
            status = check_binaries()
            ffprobe_path = status.ffprobe_path
        except Exception:
            ffprobe_path = None
    
    if not ffprobe_path or not ffprobe_path.is_file() or not file_path.is_file():
        return (0, "")
    
    try:
        cmd = [
            str(ffprobe_path),
            "-v", "error",
            "-select_streams", "a:0",
            "-show_entries", "stream=channels,channel_layout",
            "-of", "json",
            str(file_path)
        ]
        kwargs = {
            "stdout": subprocess.PIPE,
            "stderr": subprocess.PIPE,
            "text": True,
            "encoding": "utf-8",
            "errors": "replace"
        }
        if os.name == "nt":
            kwargs["creationflags"] = 0x08000000  # CREATE_NO_WINDOW
            
        p = subprocess.run(cmd, timeout=4, **kwargs)
        if p.returncode == 0 and p.stdout:
            data = json.loads(p.stdout)
            streams = data.get("streams", [])
            if streams:
                channels = int(streams[0].get("channels") or 0)
                layout = str(streams[0].get("channel_layout") or "")
                return (channels, layout)
    except Exception:
        pass
    return (0, "")


def get_channel_suffixes(channels: int, layout: str = "") -> list[str]:
    """Return channel label suffixes (e.g. ['FL', 'FR', 'FC', 'LFE', 'SL', 'SR']) for given channel count and layout."""
    layout_lower = layout.lower()
    if channels == 6 or "5.1" in layout_lower:
        return ["FL", "FR", "FC", "LFE", "SL", "SR"]
    elif channels == 8 or "7.1" in layout_lower:
        return ["FL", "FR", "FC", "LFE", "BL", "BR", "SL", "SR"]
    elif channels == 2:
        return ["FL", "FR"]
    elif channels == 1:
        return ["FC"]
    return [f"Ch{i+1}" for i in range(max(1, channels))]


@dataclass
class ConverterRequest:
    input_file: Path
    output_file: Path
    split_channels: bool = False
    
@dataclass
class CommandBuildResult:
    args: list[str]
    redacted_display: str

def build_ffmpeg_command(request: ConverterRequest, ffmpeg_path: Path) -> CommandBuildResult:
    """Build the FFmpeg command for conversion."""
    if not ffmpeg_path.exists():
        raise FileNotFoundError(f"FFmpeg not found: {ffmpeg_path}")
        
    in_ext = request.input_file.suffix.lower()
    out_ext = request.output_file.suffix.lower()
    
    args = [
        str(ffmpeg_path),
        "-y", # overwrite output
        "-v", "error", # minimal logs unless error
        "-progress", "pipe:1", # pipe progress to stdout for parsing
        "-i", str(request.input_file)
    ]
    
    AUDIO_EXTS = {".mp3", ".wav", ".flac", ".ogg", ".m4a", ".aac", ".ac3", ".eac3", ".opus"}
    
    if request.split_channels:
        ffprobe_exe = ffmpeg_path.parent / ("ffprobe.exe" if os.name == "nt" else "ffprobe")
        channels, layout = probe_audio_channels(request.input_file, ffprobe_path=ffprobe_exe)
        if channels <= 0:
            if "7.1" in str(request.input_file).lower() or "7.1" in layout.lower():
                channels = 8
                layout = "7.1"
            else:
                channels = 6
                layout = "5.1"
            
        suffixes = get_channel_suffixes(channels, layout)
        base_stem = request.output_file.stem
        output_dir = request.output_file.parent
        
        filter_parts = [f"[0:a:0]asplit={channels}" + "".join([f"[a{i}]" for i in range(channels)])]
        for i in range(channels):
            filter_parts.append(f"[a{i}]pan=1c|c0=c{i}[out{i}]")
            
        args.extend(["-filter_complex", ";".join(filter_parts)])
        
        if out_ext == ".ac3":
            codec_args = ["-c:a", "ac3", "-b:a", "192k"]
        elif out_ext == ".wav":
            codec_args = ["-c:a", "pcm_s16le"]
        elif out_ext == ".flac":
            codec_args = ["-c:a", "flac"]
        elif out_ext in [".aac", ".m4a"]:
            codec_args = ["-c:a", "aac", "-b:a", "192k"]
        elif out_ext == ".eac3":
            codec_args = ["-c:a", "eac3", "-b:a", "192k"]
        elif out_ext == ".opus":
            codec_args = ["-c:a", "libopus", "-b:a", "160k"]
        elif out_ext == ".ogg":
            codec_args = ["-c:a", "libvorbis", "-q:a", "6"]
        elif out_ext == ".mp3":
            codec_args = ["-c:a", "libmp3lame", "-b:a", "192k"]
        else:
            codec_args = ["-c:a", "pcm_s16le"]
            
        for i, suf in enumerate(suffixes):
            channel_output = output_dir / f"{base_stem}_{suf}{out_ext}"
            args.extend(["-map", f"[out{i}]"])
            args.extend(codec_args)
            args.append(str(channel_output))
            
        redacted_display = f"ffmpeg -i {request.input_file.name} -> {channels} ayrı kanal dosyası ({out_ext})"
        return CommandBuildResult(args=args, redacted_display=redacted_display)

    # Special cases for single file
    if out_ext == ".ico":
        # Scale to standard icon size
        args.extend(["-vf", "scale=256:256:force_original_aspect_ratio=decrease,pad=256:256:(ow-iw)/2:(oh-ih)/2"])
    elif out_ext in AUDIO_EXTS:
        # Extract / convert audio
        args.extend(["-vn"])
        if out_ext == ".ac3":
            args.extend(["-c:a", "ac3", "-b:a", "640k"])
        elif out_ext == ".wav":
            args.extend(["-c:a", "pcm_s16le"])
        elif out_ext == ".flac":
            args.extend(["-c:a", "flac"])
        elif out_ext in [".aac", ".m4a"]:
            args.extend(["-c:a", "aac", "-b:a", "640k"])
        elif out_ext == ".eac3":
            args.extend(["-c:a", "eac3", "-b:a", "768k"])
        elif out_ext == ".opus":
            args.extend(["-c:a", "libopus", "-b:a", "450k"])
        elif out_ext == ".ogg":
            args.extend(["-c:a", "libvorbis", "-q:a", "6"])
        elif out_ext == ".mp3":
            args.extend(["-c:a", "libmp3lame", "-b:a", "320k"])
        
    # Mapping metadata is generally a good idea, but simple is better here
    args.append(str(request.output_file))
    
    redacted_display = f"ffmpeg -i {request.input_file.name} -> {request.output_file.name}"
    
    return CommandBuildResult(args=args, redacted_display=redacted_display)

