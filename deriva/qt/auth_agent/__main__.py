import sys
import traceback
from PyQt5 import QtCore
from PyQt5.QtWidgets import QApplication, QStyleFactory, QMessageBox
from deriva.core import read_config, format_exception, BaseCLI
from deriva.qt import AuthWindow, __version__ as VERSION


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


def main():
    sys.excepthook = excepthook

    QApplication.setDesktopSettingsAware(False)
    QApplication.setStyle(QStyleFactory.create("Fusion"))
    app = QApplication(sys.argv)
    app.setAttribute(QtCore.Qt.AA_UseHighDpiPixmaps)
    sys.stderr.write("\n")
    cli = BaseCLI("DERIVA Authentication Agent",
                  "For more information see: https://github.com/informatics-isi-edu/deriva-qt", VERSION)
    cli.parser.add_argument(
        "--cookie-persistence", action="store_true",
        help="Enable cookie and local storage persistence for QtWebEngine.")
    args = cli.parse_cli()
    config = read_config(args.config_file, create_default=False) if args.config_file else None
    authWindow = AuthWindow(config, args.credential_file, cookie_persistence=args.cookie_persistence)
    authWindow.show()
    ret = app.exec_()
    return ret


if __name__ == '__main__':
    sys.exit(main())
