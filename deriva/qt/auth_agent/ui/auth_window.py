import logging
import sys

from pkg_resources import parse_version
from PyQt5.QtCore import Qt, QEvent, QMetaObject, pyqtSlot, qVersion
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import QWidget, QMainWindow, QMessageBox, QStatusBar, QVBoxLayout, QSystemTrayIcon, QStyle, qApp, \
    QTabWidget, QAction, QToolBar, QSizePolicy, QHBoxLayout, QLabel, QComboBox, QSplitter
from deriva.core import read_config, write_config, DEFAULT_CREDENTIAL_FILE
from deriva.qt import QPlainTextEditLogger, __version__ as VERSION
from deriva.qt.auth_agent.ui.auth_widget import AuthWidget, DEFAULT_CONFIG, DEFAULT_CONFIG_FILE
from deriva.qt.auth_agent.resources import resources


class AuthWindow(QMainWindow):

    window_title = 'DERIVA Authentication Agent %s' % VERSION

    def __init__(self,
                 config,
                 credential_file=None,
                 cookie_persistence=False,
                 authentication_success_callback=None):
        super(AuthWindow, self).__init__()
        self.config = config
        self.credential_file = credential_file if credential_file else DEFAULT_CREDENTIAL_FILE
        self.cookie_persistence = cookie_persistence
        self.authentication_success_callback = \
            self.successCallback if not authentication_success_callback else authentication_success_callback

        self.window_icon = QIcon(":/images/keys.png")
        qApp.setWindowIcon(QIcon(self.window_icon))
        self.systemTrayIcon = QSystemTrayIcon(self)
        self.systemTrayIcon.setIcon(self.window_icon)
        self.systemTrayIcon.setVisible(True)
        self.systemTrayIcon.activated.connect(self.on_systemTrayIcon_activated)

        if not self.config:
            self.config = read_config(DEFAULT_CONFIG_FILE, create_default=True, default=DEFAULT_CONFIG)
        self.ui = AuthWindowUI(self)
        self.hide()
        self.populateServerList()
        self.show()
        self.on_actionLogin_triggered()
        qApp.aboutToQuit.connect(self.logout)

    def authenticated(self):
        authenticated = False
        for i in range(self.ui.tabWidget.count()):
            widget = self.ui.tabWidget.widget(i)
            if isinstance(widget, AuthWidget):
                if widget.authenticated():
                    authenticated = True
        return authenticated

    def logout(self):
        for i in range(self.ui.tabWidget.count()):
            widget = self.ui.tabWidget.widget(i)
            if isinstance(widget, AuthWidget):
                widget.logout()

    def successCallback(self, **kwargs):
        host = kwargs.get("host")
        if host:
            self.statusBar().showMessage("Authenticated: %s" % host)
        self.ui.actionShowToken.setEnabled(True)
        self.updateSystrayTooltip()

    def populateServerList(self):
        for server in self.config.get("servers", []):
            if not server:
                continue
            host = server.get("host")
            if host:
                self.ui.serverComboBox.addItem(host, server)

    def getConfiguredServers(self):
        servers = list()
        for x in range(self.ui.serverComboBox.count()):
            servers.append(self.ui.serverComboBox.itemData(x, Qt.UserRole))
        self.config["servers"] = servers
        return self.config

    def getAuthenticatedServers(self):
        servers = list()
        for i in range(self.ui.tabWidget.count()):
            widget = self.ui.tabWidget.widget(i)
            if isinstance(widget, AuthWidget):
                if widget.authenticated():
                    servers.append(self.ui.tabWidget.tabText(i))
        return servers

    def addAuthTab(self, config, credential_file, cookie_persistence, success_callback):
        authWidget = AuthWidget(self, config, credential_file, cookie_persistence)
        authWidget.setSuccessCallback(success_callback)
        authWidget.setObjectName("authWidget")
        index = self.ui.tabWidget.addTab(authWidget, authWidget.auth_url.host())
        return index

    def updateSystrayTooltip(self):
        tooltip = "DERIVA Authenticated:\n%s" % "\n".join(self.getAuthenticatedServers())
        self.systemTrayIcon.setToolTip(tooltip)

    @pyqtSlot(int)
    def onTabChanged(self, index):
        host = self.ui.tabWidget.tabText(index)
        cur = self.ui.serverComboBox.currentIndex()
        ind = self.ui.serverComboBox.findText(host, Qt.MatchFixedString)
        if (ind != -1) and (ind != cur):
            self.ui.serverComboBox.setCurrentIndex(ind)
        widget = self.ui.tabWidget.widget(index)
        authenticated = False
        if isinstance(widget, AuthWidget):
            if widget.authenticated():
                authenticated = True
        if host and authenticated:
            self.statusBar().showMessage("Authenticated: %s" % host)
            self.ui.actionShowToken.setEnabled(True)
        else:
            self.ui.actionShowToken.setEnabled(False)
            self.statusBar().clearMessage()

    @pyqtSlot(int)
    def onTabClosed(self, index):
        widget = self.ui.tabWidget.widget(index)
        if isinstance(widget, AuthWidget):
            widget.logout()
            del widget
        self.ui.tabWidget.removeTab(index)
        self.updateSystrayTooltip()

    @pyqtSlot(int)
    def onServerListChanged(self, item):
        if self.isHidden():
            return

        host = self.ui.serverComboBox.itemText(item)
        for i in range(self.ui.tabWidget.count()):
            if host == self.ui.tabWidget.tabText(i):
                self.ui.tabWidget.setCurrentIndex(i)
                return

    @pyqtSlot()
    def on_actionAdd_triggered(self):
        host = self.ui.serverComboBox.currentText()
        if not host:
            return
        index = self.ui.serverComboBox.findText(host, Qt.MatchFixedString)
        if index != -1:
            for i in range(self.ui.tabWidget.count()):
                if host == self.ui.tabWidget.tabText(i):
                    self.ui.tabWidget.setCurrentIndex(i)
                    return

        server = {"host": host, "protocol": "https"}
        if index == -1:
            self.ui.serverComboBox.addItem(host, server)
        else:
            self.ui.serverComboBox.setItemData(index, server)
        index = self.addAuthTab(server,
                                self.credential_file,
                                self.cookie_persistence,
                                self.authentication_success_callback)
        self.ui.tabWidget.setTabEnabled(index, False)
        widget = self.ui.tabWidget.widget(index)
        if isinstance(widget, AuthWidget):
            widget.login()
        self.ui.tabWidget.setTabEnabled(index, True)
        self.ui.tabWidget.setCurrentIndex(index)

        config = self.getConfiguredServers()
        write_config(DEFAULT_CONFIG_FILE, config)

    @pyqtSlot()
    def on_actionRemove_triggered(self):
        host = self.ui.serverComboBox.currentText()
        index = self.ui.serverComboBox.currentIndex()
        self.ui.serverComboBox.removeItem(index)
        for i in range(self.ui.tabWidget.count()):
            if host == self.ui.tabWidget.tabText(i):
                widget = self.ui.tabWidget.widget(i)
                if isinstance(widget, AuthWidget):
                    widget.logout()
                    del widget
                self.ui.tabWidget.removeTab(i)

        config = self.getConfiguredServers()
        write_config(DEFAULT_CONFIG_FILE, config)

    @pyqtSlot()
    def on_actionShowToken_triggered(self):
        token = None
        widget = self.ui.tabWidget.currentWidget()
        if isinstance(widget, AuthWidget):
            token = widget.token
        if not token:
            return
        host = self.ui.serverComboBox.currentText()

        msg = QMessageBox()
        msg.setIcon(QMessageBox.Information)
        msg.setWindowTitle("Display Authentication Token: %s" % host)
        msg.setText("Click \"Show Details...\" to reveal your bearer token for host: [%s]\n\n"
                    "This bearer token can be used to authenticate with DERIVA services on this host until the "
                    "credential lifetime expires." % host)
        msg.setDetailedText(token)
        msg.setStandardButtons(QMessageBox.Close)
        msg.exec_()

    @pyqtSlot()
    def on_actionLogin_triggered(self):
        index = self.ui.serverComboBox.currentIndex()
        if index == -1:
            return
        host = self.ui.serverComboBox.itemText(index)
        for i in range(self.ui.tabWidget.count()):
            if host == self.ui.tabWidget.tabText(i):
                widget = self.ui.tabWidget.widget(i)
                if isinstance(widget, AuthWidget):
                    widget.login()
                    return

        server = self.ui.serverComboBox.itemData(index, Qt.UserRole)
        index = self.addAuthTab(server,
                                self.credential_file,
                                self.cookie_persistence,
                                self.authentication_success_callback)
        self.ui.tabWidget.setTabEnabled(index, False)
        widget = self.ui.tabWidget.widget(index)
        if isinstance(widget, AuthWidget):
            widget.login()
        self.ui.tabWidget.setTabEnabled(index, True)
        self.ui.tabWidget.setCurrentIndex(index)

    @pyqtSlot()
    def on_actionLogout_triggered(self):
        host = self.ui.serverComboBox.currentText()
        for i in range(self.ui.tabWidget.count()):
            if host == self.ui.tabWidget.tabText(i):
                widget = self.ui.tabWidget.widget(i)
                if isinstance(widget, AuthWidget):
                    widget.logout()
                    del widget
                self.ui.tabWidget.removeTab(i)
        self.updateSystrayTooltip()

    @pyqtSlot()
    def on_actionExit_triggered(self):
        self.close()

    @pyqtSlot(str)
    def updateLog(self, text):
        self.ui.logTextBrowser.widget.appendPlainText(text)

    @pyqtSlot(QSystemTrayIcon.ActivationReason)
    def on_systemTrayIcon_activated(self, reason):
        if reason == QSystemTrayIcon.DoubleClick or reason == QSystemTrayIcon.Trigger:
            if self.isHidden() or self.isMinimized():
                self.show()
                self.setWindowState(self.windowState() & ~Qt.WindowMinimized | Qt.WindowActive)
                self.activateWindow()
            else:
                self.showMinimized()
                if "win32" in sys.platform:
                    self.hide()

    def changeEvent(self, event):
        if event.type() == QEvent.WindowStateChange:
            if self.isMinimized():
                if "win32" in sys.platform:
                    self.hide()
                title = self.window_title
                msg = 'Running in the background.'
                qtVersion = qVersion()
                if parse_version(qtVersion) > parse_version("5.9.0"):
                    self.systemTrayIcon.showMessage(title, msg, self.window_icon)
                else:
                    self.systemTrayIcon.showMessage(title, msg)

        super(AuthWindow, self).changeEvent(event)

    def closeEvent(self, event):
        if not self.authenticated():
            return

        msg = QMessageBox()
        msg.setIcon(QMessageBox.Warning)
        msg.setWindowTitle("Confirm Action")
        msg.setText("Are you sure you wish to exit?")
        msg.setDetailedText("If you close the application, your credentials will not be automatically refreshed "
                            "and will be invalidated once the application has exited.")
        msg.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
        ret = msg.exec_()
        if ret == QMessageBox.No:
            event.ignore()
            return
        self.logout()
        self.systemTrayIcon.hide()


class AuthWindowUI(object):

    def __init__(self, MainWin):
        # Main Window
        MainWin.setObjectName("AuthWindow")
        MainWin.setWindowIcon(MainWin.window_icon)
        MainWin.setWindowTitle(MainWin.tr(MainWin.window_title))
        MainWin.resize(1024, 860)
        self.config = MainWin.config
        self.centralWidget = QWidget(MainWin)
        self.centralWidget.setObjectName("centralWidget")
        MainWin.setCentralWidget(self.centralWidget)
        self.verticalLayout = QVBoxLayout(self.centralWidget)
        self.verticalLayout.setContentsMargins(11, 11, 11, 11)
        self.verticalLayout.setSpacing(6)
        self.verticalLayout.setObjectName("verticalLayout")

        self.tabWidget = QTabWidget(MainWin)
        self.tabWidget.currentChanged.connect(MainWin.onTabChanged)
        self.tabWidget.tabCloseRequested.connect(MainWin.onTabClosed)
        self.tabWidget.setTabsClosable(True)
        # workaround for https://bugreports.qt.io/browse/QTBUG-58267
        if "darwin" in sys.platform:
            self.tabWidget.setDocumentMode(True)

        # Splitter for log
        self.splitter = QSplitter(Qt.Vertical)
        self.splitter.addWidget(self.tabWidget)

        # Log Widget
        self.logTextBrowser = QPlainTextEditLogger(self.centralWidget)
        self.logTextBrowser.widget.setObjectName("logTextBrowser")
        self.logTextBrowser.widget.setStyleSheet(
            """
            QPlainTextEdit {
                    border: 2px solid grey;
                    border-radius: 5px;
                    background-color: lightgray;
            }
            """)
        self.splitter.addWidget(self.logTextBrowser.widget)

        # add splitter
        self.splitter.setSizes([800, 100])
        self.verticalLayout.addWidget(self.splitter)

        # Tool Bar
        self.mainToolBar = QToolBar(MainWin)
        self.mainToolBar.setObjectName("mainToolBar")
        self.mainToolBar.setToolButtonStyle(Qt.ToolButtonTextUnderIcon)
        MainWin.addToolBar(Qt.TopToolBarArea, self.mainToolBar)

        # Servers
        self.serverWidget = QWidget(MainWin)
        self.serverLayout = QHBoxLayout()
        self.serverLabel = QLabel("Server:")
        self.serverLayout.addWidget(self.serverLabel)
        self.serverComboBox = QComboBox()
        self.serverComboBox.setEditable(True)
        self.serverComboBox.setDuplicatesEnabled(False)
        self.serverComboBox.setMinimumContentsLength(50)
        self.serverComboBox.currentIndexChanged.connect(MainWin.onServerListChanged)
        lineEdit = self.serverComboBox.lineEdit()
        lineEdit.returnPressed.connect(MainWin.on_actionAdd_triggered)
        self.serverLayout.addWidget(self.serverComboBox)
        self.serverWidget.setLayout(self.serverLayout)
        self.mainToolBar.addWidget(self.serverWidget)

        # Add
        self.actionAdd = QAction(MainWin)
        self.actionAdd.setObjectName("actionAdd")
        self.actionAdd.setText(MainWin.tr("Add"))
        self.actionAdd.setToolTip(MainWin.tr("Add to server list"))
        self.actionAdd.setShortcut(MainWin.tr("Ctrl+A"))

        # Remove
        self.actionRemove = QAction(MainWin)
        self.actionRemove.setObjectName("actionRemove")
        self.actionRemove.setText(MainWin.tr("Remove"))
        self.actionRemove.setToolTip(MainWin.tr("Remove from server list"))
        self.actionRemove.setShortcut(MainWin.tr("Ctrl+X"))

        # Show Token
        self.actionShowToken = QAction(MainWin)
        self.actionShowToken.setEnabled(False)
        self.actionShowToken.setObjectName("actionShowToken")
        self.actionShowToken.setText(MainWin.tr("Show Token"))
        self.actionShowToken.setToolTip(MainWin.tr("Display the current authentication token"))
        self.actionShowToken.setShortcut(MainWin.tr("Ctrl+S"))

        # Login
        self.actionLogin = QAction(MainWin)
        self.actionLogin.setObjectName("actionLogin")
        self.actionLogin.setText(MainWin.tr("Login"))
        self.actionLogin.setToolTip(MainWin.tr("Login to the currently selected server"))
        self.actionLogin.setShortcut(MainWin.tr("Ctrl+L"))

        # Logout
        self.actionLogout = QAction(MainWin)
        self.actionLogout.setObjectName("actionLogout")
        self.actionLogout.setText(MainWin.tr("Logout"))
        self.actionLogout.setToolTip(MainWin.tr("Logout of the currently selected server"))
        self.actionLogout.setShortcut(MainWin.tr("Ctrl+O"))

        # Add
        self.mainToolBar.addAction(self.actionAdd)
        self.actionAdd.setIcon(qApp.style().standardIcon(QStyle.SP_FileDialogNewFolder))

        # Remove
        self.mainToolBar.addAction(self.actionRemove)
        self.actionRemove.setIcon(qApp.style().standardIcon(QStyle.SP_DialogDiscardButton))

        # Show Token
        self.mainToolBar.addAction(self.actionShowToken)
        self.actionShowToken.setIcon(qApp.style().standardIcon(QStyle.SP_FileDialogInfoView))
        self.mainToolBar.addSeparator()

        # this spacer right justifies everything that comes after it
        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.mainToolBar.addWidget(spacer)

        # Login
        self.mainToolBar.addSeparator()
        self.mainToolBar.addAction(self.actionLogin)
        self.actionLogin.setIcon(qApp.style().standardIcon(QStyle.SP_DialogApplyButton))

        # Logout
        self.mainToolBar.addSeparator()
        self.mainToolBar.addAction(self.actionLogout)
        self.actionLogout.setIcon(qApp.style().standardIcon(QStyle.SP_DialogOkButton))

        # Status Bar
        self.statusBar = QStatusBar(MainWin)
        self.statusBar.setToolTip("")
        self.statusBar.setStatusTip("")
        self.statusBar.setObjectName("statusBar")
        MainWin.setStatusBar(self.statusBar)

        # configure logging
        self.logTextBrowser.widget.log_update_signal.connect(MainWin.updateLog)
        self.logTextBrowser.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))
        logging.getLogger().addHandler(self.logTextBrowser)
        logging.getLogger().setLevel(logging.INFO)

        # finalize UI setup
        QMetaObject.connectSlotsByName(MainWin)
