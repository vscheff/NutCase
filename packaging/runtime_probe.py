"""Frozen-candidate evidence for locale, Qt fallback and linked image codecs."""
import ctypes
import importlib
import json
import os
import sys
from pathlib import Path


def modules():
    if sys.platform!='win32':return []
    psapi=ctypes.WinDLL('psapi');kernel=ctypes.WinDLL('kernel32')
    kernel.GetCurrentProcess.restype=ctypes.c_void_p
    process=kernel.GetCurrentProcess();handles=(ctypes.c_void_p*2048)();needed=ctypes.c_ulong()
    psapi.EnumProcessModules.argtypes=[ctypes.c_void_p,ctypes.c_void_p,ctypes.c_ulong,ctypes.c_void_p]
    psapi.GetModuleFileNameExW.argtypes=[ctypes.c_void_p,ctypes.c_void_p,ctypes.c_wchar_p,ctypes.c_ulong]
    if not psapi.EnumProcessModules(process,handles,ctypes.sizeof(handles),ctypes.byref(needed)):
        raise ctypes.WinError()
    result=[]
    for handle in handles[:needed.value//ctypes.sizeof(ctypes.c_void_p)]:
        buffer=ctypes.create_unicode_buffer(32768)
        if psapi.GetModuleFileNameExW(process,handle,buffer,len(buffer)):result.append(buffer.value)
    return sorted(result)


def run(app,window,report):
    from PySide6.QtCore import QCoreApplication,QLocale,QLibraryInfo,QSize
    from PySide6.QtGui import QImageReader,QOpenGLContext,QOffscreenSurface
    from PySide6.QtWidgets import QDialogButtonBox
    from PySide6.QtPdf import QPdfDocument
    from pypdf import PdfWriter
    base=Path(sys._MEIPASS)/'PySide6'
    if list((base/'translations').glob('*.qm')):raise AssertionError('Translation catalogs unexpectedly bundled')
    locales=[]
    for name in ('en_US','de_DE','fr_FR','ja_JP'):
        QLocale.setDefault(QLocale(name))
        buttons=QDialogButtonBox(QDialogButtonBox.StandardButton.Cancel)
        button=buttons.button(QDialogButtonBox.StandardButton.Cancel)
        # Source text falls back to English when no translator is installed.
        text=QCoreApplication.translate('QDialogButtonBox','Cancel')
        if text!='Cancel':raise AssertionError('Unexpected translator/catalog use: '+name)
        locales.append({'locale':name,'qt_translation':text,'button':button.text()})
    QLocale.setDefault(QLocale('en_US'))
    source=report.with_suffix('.fixture.pdf');source.parent.mkdir(parents=True,exist_ok=True)
    writer=PdfWriter();writer.add_blank_page(width=612,height=792);writer.write(source)
    if not window.preview.load(source):raise AssertionError('Qt preview failed')
    app.processEvents()
    image=window.preview.document.render(0,QSize(612,792))
    if image.isNull() or window.preview.document.status()!=QPdfDocument.Status.Ready:
        raise AssertionError('Native Qt PDF rendering failed')
    window.preview.view.grab().save(str(report.with_suffix('.png')))
    before=modules()
    # Explicit context creation exercises QT_OPENGL=software/desktop separately
    # from the raster Widgets/PDF path. Failure is evidence, never hidden fallback.
    surface=QOffscreenSurface();surface.create();context=QOpenGLContext()
    created=context.create();current=context.makeCurrent(surface) if created else False
    if current:context.doneCurrent()
    after=modules()
    from PIL import features
    codecs={}
    for name in features.get_supported():
        try:codecs[name]={'enabled':features.check(name),'version':features.version(name)}
        except (ValueError,ImportError):pass
    native=[]
    for name in ('_imaging','_imagingcms','_imagingmath','_imagingtk','_webp','_avif','_imagingft'):
        try:
            module=importlib.import_module('PIL.'+name)
            versions={k:str(v() if k=='codec_versions' else v) for k,v in vars(module).items() if 'version' in k.lower()}
            native.append({'module':name,'file':module.__file__,'versions':versions})
        except ImportError as error:
            native.append({'module':name,'physical_files':[str(p) for p in (Path(sys._MEIPASS)/'PIL').glob(name+'.*.pyd')],
                           'import_error':str(error)})
    result={'status':'passed','frozen':True,'platform':app.platformName(),'qt_build':QLibraryInfo.build(),
        'locale_checks':locales,'catalog_count':0,'supported_image_formats':[bytes(x).decode() for x in QImageReader.supportedImageFormats()],
        'qt_pdf_render':'passed','qt_opengl_requested':os.environ.get('QT_OPENGL','auto'),
        'opengl_context_created':created,'opengl_make_current':current,
        'remote_session':bool(ctypes.windll.user32.GetSystemMetrics(0x1000)),'clean_vm':False,
        'modules_during_raster_pdf':before,'modules_after_context_probe':after,'pillow_features':codecs,'pillow_extensions':native,
        'limitations':['Development host; no Remote Desktop/VM hardware coverage','Offscreen tests do not prove every interactive desktop behavior']}
    report.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print('Frozen Qt locale/PDF/codec probe passed; context:',created,current,flush=True)
    return result
