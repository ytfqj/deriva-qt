import sys
import traceback

from PyQt5 import QtCore
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import QApplication, QStyleFactory, QMessageBox
from deriva.core import format_exception, BaseCLI
from deriva.transfer import DerivaUpload
from deriva.qt import UploadWindow


class DerivaUploadGUI(BaseCLI):
    def __init__(self, uploader, description, epilog, cookie_persistence=True, window_icon=":/images/upload.png"):

        if not issubclass(uploader, DerivaUpload):
            raise TypeError("DerivaUpload subclass required")

        BaseCLI.__init__(self, description, epilog, uploader.getVersion())
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

        QApplication.setDesktopSettingsAware(False)
        QApplication.setStyle(QStyleFactory.create("Fusion"))
        app = QApplication(sys.argv)
        if window_icon:
            app.setWindowIcon(QIcon(window_icon))
        app.setAttribute(QtCore.Qt.AA_UseHighDpiPixmaps)
        window = UploadWindow(uploader,
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
        self.parser.add_argument(
            "--no-persistence", action="store_true",
            help="Disable cookie and local storage persistence for QtWebEngine.")
        args = self.parse_cli()
        self.cookie_persistence = not args.no_persistence
        try:
            self.upload_gui(self.uploader,
                            config_file=args.config_file,
                            credential_file=args.credential_file,
                            hostname=args.host,
                            window_title="%s %s" % (self.parser.description, self.uploader.getVersion()),
                            window_icon=self.window_icon,
                            cookie_persistence=self.cookie_persistence)
        finally:
            sys.stderr.write("\n\n")
        return 0
