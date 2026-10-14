"""Explicit Qt deployment policy for the English-only Windows Widgets client.

Qt PDF preview is direct QPdfDocument/QPdfView, not the QImage PDF plugin.
Keep native Windows/offscreen platforms, the Windows style, standard raster/SVG
icons, network/TLS integrations, and the OpenGL fallback pending wider testing.
"""
PLUGIN_FILES={
    'platforms':{'qwindows.dll','qoffscreen.dll'},
    'styles':{'qmodernwindowsstyle.dll'},
    'imageformats':{'qgif.dll','qico.dll','qjpeg.dll','qsvg.dll'},
    'iconengines':{'qsvgicon.dll'},
    'networkinformation':{'qnetworklistmanager.dll'},
    'tls':{'qcertonlybackend.dll','qopensslbackend.dll','qschannelbackend.dll'},
}


def keep_binary(row):
    name=row[0].replace('\\','/').lower()
    if ('platforminputcontexts/' in name or '/qt6virtualkeyboard' in name
            or '/qt6qml' in name or '/qt6quick' in name):return False
    marker='pyside6/plugins/'
    if marker in name:
        relative=name.split(marker,1)[1].split('/')
        return len(relative)==2 and relative[1] in PLUGIN_FILES.get(relative[0],set())
    return True


def keep_data(row):
    name=row[0].replace('\\','/').lower()
    return not ('pyside6/translations/' in name or (name.startswith('pyside6/') and name.endswith('.qm')))


def verify_payload(bundle):
    """Reject stale resources or a new hook collection outside the reviewed policy."""
    root=bundle/'_internal/PySide6'
    for path in root.rglob('*'):
        if not path.is_file():continue
        relative='PySide6/'+path.relative_to(root).as_posix()
        allowed=keep_binary((relative,)) if path.suffix.lower()=='.dll' else keep_data((relative,))
        if not allowed:raise RuntimeError('Qt deployment policy violation: '+relative)
    for required in ('Qt6Pdf.dll','Qt6PdfWidgets.dll','opengl32sw.dll','plugins/platforms/qwindows.dll',
                     'plugins/platforms/qoffscreen.dll','plugins/styles/qmodernwindowsstyle.dll'):
        if not (root/required).is_file():raise RuntimeError('Required Qt functionality missing: '+required)
