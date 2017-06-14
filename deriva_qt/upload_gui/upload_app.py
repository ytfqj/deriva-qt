import sys
import urllib.parse
import traceback
from PyQt5 import QtCore
from PyQt5.QtWidgets import QApplication, QStyleFactory
from deriva_common.base_cli import BaseCLI
from deriva_io.deriva_upload import DerivaUpload
from deriva_qt.upload_gui.ui import upload_window


class DerivaUploadGUI(BaseCLI):
    def __init__(self, uploader, description, epilog, cookie_persistence=True):
        BaseCLI.__init__(self, description, epilog)
        self.uploader = uploader
        self.cookie_persistence = cookie_persistence

    @staticmethod
    def upload_gui(uploader,
                   config_file=None,
                   credential_file=None,
                   hostname=None,
                   window_title=None,
                   cookie_persistence=True):

        if not issubclass(uploader, DerivaUpload):
            raise TypeError("DerivaUpload subclass required")

        server = None
        if hostname:
            server = dict()
            if hostname.startswith("http"):
                url = urllib.parse.urlparse(hostname)
                server["protocol"] = url.scheme
                server["host"] = url.netloc
            else:
                server["protocol"] = "https"
                server["host"] = hostname

        QApplication.setDesktopSettingsAware(False)
        QApplication.setStyle(QStyleFactory.create("Fusion"))
        app = QApplication(sys.argv)
        app.setAttribute(QtCore.Qt.AA_UseHighDpiPixmaps)
        window = upload_window.MainWindow(uploader(config_file, credential_file, server),
                                          window_title=window_title,
                                          cookie_persistence=cookie_persistence)
        del uploader
        window.show()
        ret = app.exec_()

        return ret

    def main(self):
        sys.stderr.write("\n")
        args = self.parse_cli()
        try:
            self.upload_gui(self.uploader,
                            config_file=args.config_file,
                            credential_file=args.credential_file,
                            hostname=args.host,
                            window_title=self.parser.description,
                            cookie_persistence=self.cookie_persistence)

        except:
            traceback.print_exc()
            return 1
        finally:
            sys.stderr.write("\n\n")
        return 0
