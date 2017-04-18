import sys
from PyQt5 import QtCore
from PyQt5.QtWidgets import QApplication, QStyleFactory
from deriva_io.deriva_upload import DerivaUpload
from deriva_qt.upload_gui.ui import upload_window


def launch(uploader, config_file=None, credential_file=None, window_title=None):
    try:
        if not isinstance(uploader, DerivaUpload):
            raise ValueError("DerivaUpload instance required")
        QApplication.setDesktopSettingsAware(False)
        QApplication.setStyle(QStyleFactory.create("Fusion"))
        app = QApplication(sys.argv)
        app.setAttribute(QtCore.Qt.AA_UseHighDpiPixmaps)
        window = upload_window.MainWindow(uploader, config_file, credential_file, window_title)
        window.show()
        ret = app.exec_()
        return ret
    except Exception as e:
        print(e)

