"""Internal native GUI worker; the public CLI remains generate_drawing.py."""
import os
import sys
import faulthandler
faulthandler.enable()
from _bootstrap import PROJECT_ROOT as root
os.environ.setdefault("QT_QPA_PLATFORM","offscreen")
os.environ["FREECAD_USER_HOME"]=str(root/"tmp/freecad-runtime")
from fastener_drawing.finishing import finish
if __name__=="__main__":finish(sys.argv[1])
