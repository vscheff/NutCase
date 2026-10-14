"""Application palettes and the Windows app-theme preference."""
import sys

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QIcon, QPainter, QPalette, QPixmap


THEME_CHOICES = ('Light Mode', 'Dark Mode', 'System Default')


def resolve_theme(preference, app):
    if preference in THEME_CHOICES[:2]:
        return preference
    if sys.platform == 'win32':
        import winreg
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                    r'Software\Microsoft\Windows\CurrentVersion\Themes\Personalize') as key:
                value, _ = winreg.QueryValueEx(key, 'AppsUseLightTheme')
            return 'Dark Mode' if value == 0 else 'Light Mode'
        except OSError:
            pass
    return 'Dark Mode' if app.styleHints().colorScheme() == Qt.ColorScheme.Dark else 'Light Mode'


def settings_icon(dark=False):
    gear = QPixmap(32, 32)
    gear.fill(Qt.GlobalColor.transparent)
    painter = QPainter(gear)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(QColor('#f0f3f5' if dark else '#000000'))
    for angle in range(0, 360, 45):
        painter.save()
        painter.translate(16, 16)
        painter.rotate(angle)
        painter.drawRoundedRect(-3, -15, 6, 10, 1, 1)
        painter.restore()
    painter.drawEllipse(6, 6, 20, 20)
    painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_Clear)
    painter.drawEllipse(12, 12, 8, 8)
    painter.end()
    return QIcon(gear)


def apply_theme(app, preference='System Default'):
    mode = resolve_theme(preference, app)
    dark = mode == 'Dark Mode'
    if app.style().objectName().lower() != 'fusion':
        app.setStyle('Fusion')
    colors = ({
        'window':'#1c2025', 'text':'#e5ebef', 'base':'#252b32', 'alternate':'#2c343d',
        'button':'#303943', 'disabled':'#82909b', 'highlight':'#247d95',
        'placeholder':'#9caab5', 'tooltip':'#303943', 'border':'#48535f',
        'heading':'#d7eaf3', 'notice_text':'#f4d49c', 'notice':'#403526',
        'hover':'#36424e', 'pressed':'#435362', 'primary':'#247d95', 'primary_disabled':'#43545e',
    } if dark else {
        'window':'#f3f5f7', 'text':'#20323e', 'base':'#ffffff', 'alternate':'#eef3f6',
        'button':'#e9eef2', 'disabled':'#71818b', 'highlight':'#176278',
        'placeholder':'#61717c', 'tooltip':'#fff8e5', 'border':'#c9d1d8',
        'heading':'#173447', 'notice_text':'#754c09', 'notice':'#fff1cf',
        'hover':'#e5ebef', 'pressed':'#d6e0e5', 'primary':'#176278', 'primary_disabled':'#a5b4bc',
    })
    palette = QPalette()
    roles = {
        'Window':'window', 'WindowText':'text', 'Base':'base', 'AlternateBase':'alternate',
        'Text':'text', 'Button':'button', 'ButtonText':'text', 'Highlight':'highlight',
        'ToolTipBase':'tooltip', 'ToolTipText':'text', 'PlaceholderText':'placeholder',
    }
    for role, name in roles.items():
        palette.setColor(getattr(QPalette.ColorRole, role), QColor(colors[name]))
    for role in ('BrightText', 'HighlightedText'):
        palette.setColor(getattr(QPalette.ColorRole, role), QColor('#ffffff'))
    for role in ('WindowText', 'Text', 'ButtonText'):
        palette.setColor(QPalette.ColorGroup.Disabled, getattr(QPalette.ColorRole, role), QColor(colors['disabled']))
    if dark:
        for role, color in (('Light','#56616d'), ('Midlight','#3f4a56'), ('Mid','#39434d'),
                            ('Dark','#12161a'), ('Shadow','#090c0f')):
            palette.setColor(getattr(QPalette.ColorRole, role), QColor(color))
    app.setPalette(palette)
    app.setStyleSheet('''
        QMainWindow, QDialog { background: %(window)s; }
        QWidget { font-family: Segoe UI; font-size: 10pt; }
        QLabel#Heading { font-size: 20pt; font-weight: 600; color: %(heading)s; }
        QLabel#Notice { color: %(notice_text)s; padding: 6px; background: %(notice)s; border-radius: 4px; }
        QGroupBox { font-weight: 600; border: 1px solid %(border)s; border-radius: 5px; margin-top: 10px; padding-top: 8px; }
        QGroupBox::title { subcontrol-origin: margin; left: 9px; }
        QLineEdit,QComboBox,QSpinBox { min-height: 26px; }
        QPushButton { padding: 6px 9px; }
        QPushButton#Primary { background: %(primary)s; color: white; font-weight: 600; }
        QPushButton#Primary:disabled { background: %(primary_disabled)s; }
        QToolButton#RuntimeSettings { border: none; border-radius: 20px; background: transparent; }
        QToolButton#RuntimeSettings:hover { background: %(hover)s; }
        QToolButton#RuntimeSettings:pressed { background: %(pressed)s; }
        QTabWidget::pane { border: 1px solid %(border)s; background: %(base)s; }
        QHeaderView::section { padding: 6px; background: %(hover)s; }
    ''' % colors)
    return mode
