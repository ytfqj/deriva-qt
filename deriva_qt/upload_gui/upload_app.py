import os
import sys
from PyQt5 import QtCore
from PyQt5.QtWidgets import QApplication, QStyleFactory
from deriva_common import read_config, copy_config, read_credential, format_exception
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

        if not (config_file and os.path.isfile(config_file)):
            config_file = uploader.getDeployedConfigFilePath(uploader)
            if not (config_file and os.path.isfile(config_file)):
                copy_config(uploader.getDefaultConfigFilePath(uploader), config_file)
        config = read_config(config_file)
        if hostname:
            config['server']['host'] = hostname
        credential = read_credential(credential_file) if credential_file else None

        try:
            QApplication.setDesktopSettingsAware(False)
            QApplication.setStyle(QStyleFactory.create("Fusion"))
            app = QApplication(sys.argv)
            app.setAttribute(QtCore.Qt.AA_UseHighDpiPixmaps)
            window = upload_window.MainWindow(uploader.getInstance(config, credential),
                                              window_title=window_title,
                                              cookie_persistence=cookie_persistence)
            del uploader
            window.show()
            ret = app.exec_()
            return ret
        except Exception as e:
            print(e)

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

        except Exception as e:
            sys.stderr.write(format_exception(e))
            return 1
        finally:
            sys.stderr.write("\n\n")
        return 0
