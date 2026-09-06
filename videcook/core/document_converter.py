import os
from pathlib import Path
from typing import Callable

def convert_document(input_path: Path, output_path: Path, progress_cb: Callable[[int], None], check_cancelled: Callable[[], bool]) -> bool:
    in_ext = input_path.suffix.lower()
    out_ext = output_path.suffix.lower()
    
    # 1. PDF to DOCX
    if in_ext == '.pdf' and out_ext == '.docx':
        try:
            from pdf2docx import Converter
        except ImportError:
            raise Exception("pdf2docx kütüphanesi yüklü değil.")
        
        progress_cb(10)
        if check_cancelled(): return False
        
        cv = Converter(str(input_path))
        progress_cb(40)
        
        if check_cancelled():
            cv.close()
            return False
            
        cv.convert(str(output_path), start=0, end=None)
        progress_cb(90)
        cv.close()
        
        if check_cancelled(): return False
        return True
        
    # 2. DOCX / PPTX / XLSX to PDF (using MS Office COM)
    elif out_ext == '.pdf' and in_ext in ['.docx', '.pptx', '.xlsx']:
        try:
            import win32com.client
            import pythoncom
        except ImportError:
            raise Exception("pywin32 (Microsoft Office otomasyonu) kütüphanesi yüklü değil.")
            
        pythoncom.CoInitialize()
        progress_cb(20)
        if check_cancelled(): return False
        
        app = None
        doc = None
        try:
            if in_ext == '.docx':
                app = win32com.client.Dispatch("Word.Application")
                app.Visible = False
                progress_cb(40)
                doc = app.Documents.Open(str(input_path.resolve()))
                if check_cancelled(): return False
                doc.SaveAs(str(output_path.resolve()), FileFormat=17) # 17 = wdFormatPDF
                
            elif in_ext == '.pptx':
                app = win32com.client.Dispatch("PowerPoint.Application")
                # PowerPoint requires Window to be visible or with specific flags sometimes, but usually headless works if minimal
                app.DisplayAlerts = False
                progress_cb(40)
                doc = app.Presentations.Open(str(input_path.resolve()), WithWindow=False)
                if check_cancelled(): return False
                doc.SaveAs(str(output_path.resolve()), 32) # 32 = ppSaveAsPDF
                
            elif in_ext == '.xlsx':
                app = win32com.client.Dispatch("Excel.Application")
                app.Visible = False
                app.DisplayAlerts = False
                progress_cb(40)
                doc = app.Workbooks.Open(str(input_path.resolve()))
                if check_cancelled(): return False
                doc.ExportAsFixedFormat(0, str(output_path.resolve())) # 0 = xlTypePDF
                
        except Exception as e:
            raise Exception(f"Microsoft Office entegrasyon hatası: {str(e)}\nBilgisayarda lisanslı Office kurulu olduğundan emin olun.")
        finally:
            if doc:
                try:
                    doc.Close()
                except:
                    pass
            if app:
                try:
                    app.Quit()
                except:
                    pass
            pythoncom.CoUninitialize()
            
        progress_cb(90)
        if check_cancelled(): return False
        return True
        
    else:
        raise Exception(f"Desteklenmeyen belge dönüştürme formatı: {in_ext} -> {out_ext}")
