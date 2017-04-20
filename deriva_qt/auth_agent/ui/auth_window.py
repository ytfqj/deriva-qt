from PyQt5.QtCore import Qt, QEvent, QMetaObject, pyqtSlot
from PyQt5.QtWidgets import QWidget, QMainWindow, QMessageBox, QStatusBar, QVBoxLayout, QSystemTrayIcon, QStyle, qApp
from deriva_common import DEFAULT_CONFIG_FILE, DEFAULT_CREDENTIAL_FILE
from .auth_widget import AuthWidget


class AuthWindow(QMainWindow):

    config_file = None
    credential_file = None
    is_child_window = False
    is_persistent = False
    authentication_success_callback = None

    def __init__(self,
                 config_file=DEFAULT_CONFIG_FILE,
                 credential_file=DEFAULT_CREDENTIAL_FILE,
                 authentication_success_callback=None,
                 is_child_window=False,
                 is_persistent=False):
        super(AuthWindow, self).__init__()
        self.config_file = config_file
        self.credential_file = credential_file
        self.is_child_window = is_child_window
        self.is_persistent = is_persistent
        self.authentication_success_callback = \
            self.successCallback if not authentication_success_callback else authentication_success_callback
        if not self.is_child_window and self.credential_file is None:
            self.credential_file = DEFAULT_CREDENTIAL_FILE
        self.ui = AuthWindowUI(self)
        if not is_child_window:
            self.systemTrayIcon = QSystemTrayIcon(self)
            self.systemTrayIcon.setIcon(qApp.style().standardIcon(QStyle.SP_TitleBarMenuButton))
            self.systemTrayIcon.setVisible(True)
            self.systemTrayIcon.activated.connect(self.on_systemTrayIcon_activated)

    def authenticated(self):
        return self.ui.authWidget.authenticated

    def login(self):
        self.ui.authWidget.login()

    def logout(self):
        self.ui.authWidget.logout()

    def successCallback(self, **kwargs):
        if self.is_child_window:
            self.hide()
        else:
            self.setWindowState(Qt.WindowMinimized)

    @pyqtSlot(QSystemTrayIcon.ActivationReason)
    def on_systemTrayIcon_activated(self, reason):
        if reason == QSystemTrayIcon.DoubleClick or reason == QSystemTrayIcon.Trigger:
            if self.isHidden():
                self.show()
                self.setWindowState(self.windowState() & ~Qt.WindowMinimized | Qt.WindowActive)
                self.activateWindow()
            else:
                self.hide()

    def changeEvent(self, event):
        if event.type() == QEvent.WindowStateChange:
            if self.windowState() & Qt.WindowMinimized:
                event.ignore()
                self.hide()
                if not self.is_child_window:
                    self.systemTrayIcon.showMessage('DERIVA Authentication Agent', 'Running in the background.')
                return

        super(AuthWindow, self).changeEvent(event)

    def closeEvent(self, event):
        if not self.is_child_window:
            self.systemTrayIcon.hide()
            if not self.ui.authWidget.authenticated:
                return
            msg = QMessageBox()
            msg.setIcon(QMessageBox.Warning)
            msg.setWindowTitle("Confirm Action")
            msg.setText("Are you sure you wish to exit?")
            msg.setDetailedText("If you close the application, your credentials will not be automatically refreshed "
                                "and will be invalidated once the credential expiration time is reached.")
            msg.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
            ret = msg.exec_()
            if ret == QMessageBox.No:
                event.ignore()


class AuthWindowUI(object):

    def __init__(self, MainWin):
        super(AuthWindow).__init__()

        # Main Window
        MainWin.setObjectName("AuthWindow")
        MainWin.setWindowTitle(MainWin.tr("DERIVA Authentication Agent"))
        # MainWin.setWindowIcon(QIcon(":/images/bag.png"))
        MainWin.resize(1024, 745)
        self.centralWidget = QWidget(MainWin)
        self.centralWidget.setObjectName("centralWidget")
        MainWin.setCentralWidget(self.centralWidget)
        self.verticalLayout = QVBoxLayout(self.centralWidget)
        self.verticalLayout.setContentsMargins(11, 11, 11, 11)
        self.verticalLayout.setSpacing(6)
        self.verticalLayout.setObjectName("verticalLayout")
        self.authWidget = AuthWidget(MainWin.config_file, MainWin.credential_file, MainWin.is_persistent)
        self.authWidget.setSuccessCallback(MainWin.authentication_success_callback)
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
