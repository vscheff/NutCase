"""Internal native GUI worker; the public CLI remains generate_drawing.py."""
import os
import sys
import faulthandler
faulthandler.enable()
import _bootstrap
from fastener_paths import native_runtime_home
os.environ.setdefault("QT_QPA_PLATFORM","offscreen")
os.environ["FREECAD_USER_HOME"]=str(native_runtime_home())
from fastener_drawing.finishing import finish
if __name__=="__main__":finish(sys.argv[1])
