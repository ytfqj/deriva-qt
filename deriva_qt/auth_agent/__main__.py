import sys
from PyQt5 import QtCore
from PyQt5.QtWidgets import QApplication, QStyleFactory
from deriva_common.base_cli import BaseCLI
from deriva_qt.auth_agent.ui.auth_window import AuthWindow


def main():
    try:
        QApplication.setDesktopSettingsAware(False)
        QApplication.setStyle(QStyleFactory.create("Fusion"))
        app = QApplication(sys.argv)
        app.setAttribute(QtCore.Qt.AA_UseHighDpiPixmaps)
        app.setAttribute(QtCore.Qt.AA_EnableHighDpiScaling)

        cli = BaseCLI("DERIVA Authentication Agent",
                      "For more information see: https://github.com/informatics-isi-edu/deriva-qt")
        cli.parser.add_argument(
            "--no-persistence", action="store_true",
            help="Disable cookie and local storage persistence for QtWebEngine.")
        args = cli.parse_cli()
        authWindow = AuthWindow(args.config_file, args.credential_file, is_persistent=not args.no_persistence)
        authWindow.show()
        authWindow.login()
        ret = app.exec_()
        return ret
    except Exception as e:
        print(e)

if __name__ == '__main__':
    sys.exit(main())
