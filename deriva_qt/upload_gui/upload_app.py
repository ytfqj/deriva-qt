import sys
import traceback
from PyQt5 import QtCore
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import QApplication, QStyleFactory, QMessageBox
from deriva_common import format_exception
from deriva_common.base_cli import BaseCLI
from deriva_io.deriva_upload import DerivaUpload
from deriva_io.generic_uploader import GenericUploader, DESC, INFO
from deriva_qt.upload_gui.ui import upload_window


class DerivaUploadGUI(BaseCLI):
    def __init__(self, uploader, description, epilog, cookie_persistence=True, window_icon=":/images/upload.png"):
        BaseCLI.__init__(self, description, epilog)
        self.uploader = uploader
        self.cookie_persistence = cookie_persistence
        self.window_icon = window_icon

    @staticmethod
    def upload_gui(uploader,
                   config_file=None,
                   credential_file=None,
                   hostname=None,
                   window_title=None,
                   window_icon=None,
                   cookie_persistence=True):

        if not issubclass(uploader, DerivaUpload):
            raise TypeError("DerivaUpload subclass required")

        QApplication.setDesktopSettingsAware(False)
        QApplication.setStyle(QStyleFactory.create("Fusion"))
        app = QApplication(sys.argv)
        if window_icon:
            app.setWindowIcon(QIcon(window_icon))
        app.setAttribute(QtCore.Qt.AA_UseHighDpiPixmaps)
        window = upload_window.MainWindow(uploader,
                                          config_file,
                                          credential_file,
                                          hostname,
                                          window_title=window_title,
                                          cookie_persistence=cookie_persistence)
        window.show()
        ret = app.exec_()

        return ret

    @staticmethod
    def excepthook(etype, value, tb):
        traceback.print_tb(tb)
        sys.stderr.write(format_exception(value))
        msg = QMessageBox()
        msg.setText(str(value))
        msg.setStandardButtons(QMessageBox.Close)
        msg.setWindowTitle("Unhandled Exception: %s" % etype.__name__)
        msg.setIcon(QMessageBox.Critical)
        msg.setDetailedText('\n'.join(traceback.format_exception(etype, value, tb)))
        msg.exec_()

    def main(self):
        sys.excepthook = DerivaUploadGUI.excepthook
        sys.stderr.write("\n")
        args = self.parse_cli()
        try:
            self.upload_gui(self.uploader,
                            config_file=args.config_file,
                            credential_file=args.credential_file,
                            hostname=args.host,
                            window_title=self.parser.description,
                            window_icon=self.window_icon,
                            cookie_persistence=self.cookie_persistence)
        finally:
            sys.stderr.write("\n\n")
        return 0


if __name__ == '__main__':
    gui = DerivaUploadGUI(GenericUploader, DESC, INFO)
    sys.exit(gui.main())
