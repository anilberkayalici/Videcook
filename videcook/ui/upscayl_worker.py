import os
import shutil
import subprocess
import urllib.request
import zipfile
from pathlib import Path
from PySide6.QtCore import QObject, Signal, Slot
from videcook.utils.i18n import LanguageManager

class UpscaylWorker(QObject):
    progress_changed = Signal(int)
    status_changed = Signal(str)
    finished = Signal(bool, str, str)  # success, message, output_path
    
    def __init__(self, input_path: str, output_dir: str, model: int, scale: int, i18n: LanguageManager):
        super().__init__()
        self._input_path = Path(input_path)
        self._output_dir = Path(output_dir)
        self._model = model
        self._scale = scale
        self._i18n = i18n
        self._is_cancelled = False
        self._process = None
        
    def cancel(self):
        self._is_cancelled = True
        if self._process:
            try:
                self._process.kill()
            except Exception:
                pass
                
    def _run_cmd(self, cmd, progress_offset, progress_scale):
        startupinfo = None
        if os.name == 'nt':
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            
        self._process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            startupinfo=startupinfo,
            encoding='utf-8',
            errors='replace'
        )
        
        for line in self._process.stdout:
            if self._is_cancelled:
                self._process.kill()
                break
            if "%" in line:
                try:
                    parts = line.strip().split('%')[0].split()
                    val = float(parts[-1])
                    overall_progress = int(progress_offset + (val * progress_scale / 100))
                    self.progress_changed.emit(overall_progress)
                except:
                    pass
                    
        self._process.wait()
        return self._process.returncode

    @Slot()
    def run(self):
        try:
            bin_dir = Path.home() / ".videcook" / "bin" / "upscayl"
            exe_path = bin_dir / "realesrgan-ncnn-vulkan.exe"
            
            if not exe_path.exists():
                self.status_changed.emit("Yapay zeka motoru ve modeller indiriliyor (Sadece bir defa)...")
                bin_dir.mkdir(parents=True, exist_ok=True)
                
                url = "https://github.com/xinntao/Real-ESRGAN/releases/download/v0.2.5.0/realesrgan-ncnn-vulkan-20220424-windows.zip"
                zip_path = bin_dir / "realesrgan.zip"
                
                def reporthook(blocknum, blocksize, totalsize):
                    if self._is_cancelled:
                        raise Exception("Cancelled")
                    if totalsize > 0:
                        percent = int(blocknum * blocksize * 100 / totalsize)
                        if percent > 100: percent = 100
                        self.progress_changed.emit(percent)
                        
                urllib.request.urlretrieve(url, zip_path, reporthook)
                
                self.status_changed.emit("Kurulum yapılıyor...")
                self.progress_changed.emit(0)
                
                with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                    zip_ref.extractall(bin_dir)
                    
                zip_path.unlink()

            if not exe_path.exists():
                self.finished.emit(False, "Motor kurulumu başarısız oldu.", "")
                return

            if self._is_cancelled:
                self.finished.emit(False, "İşlem iptal edildi.", "")
                return
                
            self.status_changed.emit("Görsel netleştiriliyor...")
            self.progress_changed.emit(0)
            
            out_filename = f"{self._input_path.stem}_upscaled{self._input_path.suffix}"
            out_path = self._output_dir / out_filename
            
            model_map = {
                0: "realesrgan-x4plus",
                1: "ultrasharp",
                2: "realesrgan-x4plus-anime",
                3: "remacri"
            }
            model_name = model_map.get(self._model, "realesrgan-x4plus")
            
            # Check if custom model exists, otherwise fallback to standard
            # (realesrgan-x4plus is bundled with the executable)
            models_dir = exe_path.parent / "models"
            if model_name not in ("realesrgan-x4plus", "realesrgan-x4plus-anime"):
                if not (models_dir / f"{model_name}.bin").exists() and not (models_dir / f"{model_name}-4x.bin").exists():
                    model_name = "realesrgan-x4plus"
            
            is_double_pass = (self._scale == 2)
            
            if not is_double_pass:
                scale_factor = 2 if self._scale == 0 else 4
                cmd = [
                    str(exe_path),
                    "-i", str(self._input_path),
                    "-o", str(out_path),
                    "-n", model_name,
                    "-s", str(scale_factor)
                ]
                ret = self._run_cmd(cmd, 0, 100)
                
                if self._is_cancelled:
                    if out_path.exists(): out_path.unlink()
                    self.finished.emit(False, "İşlem iptal edildi.", "")
                    return
                if ret != 0:
                    self.finished.emit(False, f"İşlem başarısız (Hata Kodu: {ret})", "")
                    return
            else:
                # 8x Double Pass
                temp_path = self._output_dir / f"{self._input_path.stem}_temp_4x{self._input_path.suffix}"
                
                # Pass 1: 4x
                self.status_changed.emit("Görsel netleştiriliyor... (Aşama 1/2)")
                cmd1 = [
                    str(exe_path),
                    "-i", str(self._input_path),
                    "-o", str(temp_path),
                    "-n", model_name,
                    "-s", "4"
                ]
                ret1 = self._run_cmd(cmd1, 0, 50)
                
                if self._is_cancelled or ret1 != 0:
                    if temp_path.exists(): temp_path.unlink()
                    if self._is_cancelled:
                        self.finished.emit(False, "İşlem iptal edildi.", "")
                    else:
                        self.finished.emit(False, f"Aşama 1 başarısız (Hata Kodu: {ret1})", "")
                    return
                    
                # Pass 2: 2x on top of 4x = 8x
                self.status_changed.emit("Görsel netleştiriliyor... (Aşama 2/2)")
                cmd2 = [
                    str(exe_path),
                    "-i", str(temp_path),
                    "-o", str(out_path),
                    "-n", model_name,
                    "-s", "2"
                ]
                ret2 = self._run_cmd(cmd2, 50, 50)
                
                if temp_path.exists():
                    temp_path.unlink()
                    
                if self._is_cancelled or ret2 != 0:
                    if out_path.exists(): out_path.unlink()
                    if self._is_cancelled:
                        self.finished.emit(False, "İşlem iptal edildi.", "")
                    else:
                        self.finished.emit(False, f"Aşama 2 başarısız (Hata Kodu: {ret2})", "")
                    return
                
            self.progress_changed.emit(100)
            self.finished.emit(True, "Başarılı", str(out_path))
            
        except Exception as e:
            self.finished.emit(False, str(e), "")
