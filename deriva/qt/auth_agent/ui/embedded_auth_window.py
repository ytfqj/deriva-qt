from PyQt5.QtCore import Qt, QEvent, QMetaObject
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import QWidget, QMainWindow, QStatusBar, QVBoxLayout
from deriva.qt import __version__ as VERSION
from deriva.qt.auth_agent.ui.auth_widget import AuthWidget
from deriva.qt.auth_agent.resources import resources


class EmbeddedAuthWindow(QMainWindow):

    def __init__(self,
                 config,
                 credential_file=None,
                 cookie_persistence=False,
                 authentication_success_callback=None):
        super(EmbeddedAuthWindow, self).__init__()
        success_callback = \
            self.successCallback if not authentication_success_callback else authentication_success_callback
        self.ui = EmbeddedAuthWindowUI(self, config, credential_file, cookie_persistence, success_callback)
        self.cookie_persistence = cookie_persistence

    def authenticated(self):
        return self.ui.authWidget.authenticated()

    def login(self):
        self.ui.authWidget.login()

    def logout(self, delete_cookies=False):
        self.ui.authWidget.logout(delete_cookies)

    def successCallback(self, **kwargs):
        host = kwargs.get("host")
        if host:
            self.statusBar().showMessage("Authenticated: %s" % host)
        self.hide()

    def changeEvent(self, event):
        if event.type() == QEvent.WindowStateChange:
            if self.windowState() & Qt.WindowMinimized:
                event.ignore()
                self.hide()
                return

        super(EmbeddedAuthWindow, self).changeEvent(event)

    def closeEvent(self, event):
        self.logout()


class EmbeddedAuthWindowUI(object):

    def __init__(self, MainWin, config, credential_file, cookie_persistence, success_callback):

        # Main Window
        MainWin.setObjectName("EmbeddedAuthWindow")
        MainWin.setWindowIcon(QIcon(":/images/keys.png"))
        MainWin.setWindowTitle(MainWin.tr("DERIVA Authentication Agent %s" % VERSION))
        MainWin.resize(1024, 745)
        self.centralWidget = QWidget(MainWin)
        self.centralWidget.setObjectName("centralWidget")
        MainWin.setCentralWidget(self.centralWidget)
        self.verticalLayout = QVBoxLayout(self.centralWidget)
        self.verticalLayout.setContentsMargins(11, 11, 11, 11)
        self.verticalLayout.setSpacing(6)
        self.verticalLayout.setObjectName("verticalLayout")
        self.authWidget = AuthWidget(MainWin, config, credential_file, cookie_persistence)
        self.authWidget.setSuccessCallback(success_callback)
        self.authWidget.setObjectName("authWidget")
        self.verticalLayout.addWidget(self.authWidget)

        # Status Bar

        self.statusBar = QStatusBar(MainWin)
        self.statusBar.setToolTip("")
        self.statusBar.setStatusTip("")
        self.statusBar.setObjectName("statusBar")
        MainWin.setStatusBar(self.statusBar)

        # finalize UI setup
        QMetaObject.connectSlotsByName(MainWin)
