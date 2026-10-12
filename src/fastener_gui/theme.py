"""Consistent contrast regardless of the Windows light/dark system preference."""
from PySide6.QtGui import QColor, QPalette


def apply_theme(app):
    app.setStyle('Fusion')
    palette=QPalette()
    colors={
        QPalette.ColorRole.Window:'#f3f5f7', QPalette.ColorRole.WindowText:'#20323e',
        QPalette.ColorRole.Base:'#ffffff', QPalette.ColorRole.AlternateBase:'#eef3f6',
        QPalette.ColorRole.Text:'#20323e', QPalette.ColorRole.Button:'#e9eef2',
        QPalette.ColorRole.ButtonText:'#20323e', QPalette.ColorRole.BrightText:'#ffffff',
        QPalette.ColorRole.Highlight:'#176278', QPalette.ColorRole.HighlightedText:'#ffffff',
        QPalette.ColorRole.ToolTipBase:'#fff8e5', QPalette.ColorRole.ToolTipText:'#20323e',
        QPalette.ColorRole.PlaceholderText:'#61717c',
    }
    for role,color in colors.items():palette.setColor(role,QColor(color))
    for role in (QPalette.ColorRole.WindowText,QPalette.ColorRole.Text,QPalette.ColorRole.ButtonText):
        palette.setColor(QPalette.ColorGroup.Disabled,role,QColor('#71818b'))
    app.setPalette(palette)
