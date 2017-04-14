from PyQt5.QtCore import Qt, QEvent, QMetaObject, pyqtSlot
from PyQt5.QtWidgets import QWidget, QMainWindow, QStatusBar, QVBoxLayout, QSystemTrayIcon, QStyle, qApp
from deriva_common import DEFAULT_CONFIG_FILE, DEFAULT_CREDENTIAL_FILE
from .auth_widget import AuthWidget


class AuthWindow(QMainWindow):
    def __init__(self, config_file=DEFAULT_CONFIG_FILE, credential_file=DEFAULT_CREDENTIAL_FILE):
        super(AuthWindow, self).__init__()
        self.ui = AuthWindowUI(self, config_file, credential_file)
        self.systemTrayIcon = QSystemTrayIcon(self)
        self.systemTrayIcon.setIcon(qApp.style().standardIcon(QStyle.SP_TitleBarMenuButton))
        self.systemTrayIcon.setVisible(True)
        self.systemTrayIcon.activated.connect(self.on_systemTrayIcon_activated)

    def successCallback(self, **kwargs):
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
                self.systemTrayIcon.showMessage('DERIVA Authentication Agent', 'Running in the background.')
                return

        super(AuthWindow, self).changeEvent(event)

    def closeEvent(self, event):
        self.systemTrayIcon.hide()


class AuthWindowUI(object):

    def __init__(self, MainWin, config_file, credential_file):
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
        self.authWidget = AuthWidget(config_file, credential_file)
        self.authWidget.setSuccessCallback(MainWin.successCallback)
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
