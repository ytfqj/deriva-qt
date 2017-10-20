import logging
import os
import urllib.parse
import webbrowser

from PyQt5.QtCore import Qt, QMetaObject, QThreadPool, pyqtSlot, pyqtSignal
from PyQt5.QtWidgets import qApp, QMainWindow, QWidget, QAction, QSizePolicy, QPushButton, QStyle, QSplitter, QLabel, \
    QToolBar, QStatusBar, QVBoxLayout, QHBoxLayout, QTableWidgetItem, QAbstractItemView, QLineEdit, QFileDialog, \
    QMessageBox
from deriva.core import write_config, stob
from deriva.qt import EmbeddedAuthWindow, QPlainTextEditLogger, TableWidget, Request
from deriva.qt.upload_gui.impl.upload_tasks import *
from deriva.qt.upload_gui.ui.options_window import OptionsDialog
from deriva.qt.upload_gui.resources import resources


class UploadWindow(QMainWindow):
    uploader = None
    config_file = None
    credential_file = None
    cookie_persistence = True
    auth_window = None
    identity = None
    current_path = None
    uploading = False
    save_progress_on_cancel = False
    progress_update_signal = pyqtSignal(str)

    def __init__(self,
                 uploader,
                 config_file=None,
                 credential_file=None,
                 hostname=None,
                 window_title=None,
                 cookie_persistence=True):
        super(UploadWindow, self).__init__()
        qApp.aboutToQuit.connect(self.quitEvent)

        self.ui = UploadWindowUI(self)
        self.ui.title = window_title if window_title else "Deriva Upload Utility %s" % uploader.getVersion()
        self.setWindowTitle(self.ui.title)

        self.config_file = config_file
        self.credential_file = credential_file
        self.cookie_persistence = cookie_persistence

        self.show()
        qApp.setOverrideCursor(Qt.WaitCursor)
        self.configure(uploader, hostname)
        qApp.restoreOverrideCursor()

    def configure(self, uploader, hostname):

        # if a hostname has been provided, it overrides whatever default host a given uploader is configured for
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

        # instantiate the uploader...
        # if an uploader instance does not have a default host configured, prompt the user to configure one
        if self.uploader:
            del self.uploader
        self.uploader = uploader(self.config_file, self.credential_file, server)
        if not self.uploader.server:
            if not self.checkValidServer():
                return
            else:
                self.uploader.setServer(server)

        self.setWindowTitle("%s (%s)" % (self.ui.title, self.uploader.server["host"]))

        self.getNewAuthWindow()
        if not self.checkVersion():
            return
        self.getSession()

    def getNewAuthWindow(self):
        if self.auth_window:
            if self.auth_window.authenticated():
                self.on_actionLogout_triggered()
            del self.auth_window

        self.auth_window = \
            EmbeddedAuthWindow(config=self.uploader.server,
                               cookie_persistence=self.cookie_persistence,
                               authentication_success_callback=self.onLoginSuccess)
        self.ui.actionLogin.setEnabled(True)

    def getSession(self):
        qApp.setOverrideCursor(Qt.WaitCursor)
        logging.debug("Validating session: %s" % self.uploader.server["host"])
        queryTask = SessionQueryTask(self.uploader)
        queryTask.status_update_signal.connect(self.onSessionResult)
        queryTask.query()

    def onLoginSuccess(self, **kwargs):
        self.auth_window.hide()
        self.uploader.setCredentials(kwargs["credential"])
        self.getSession()

    def enableControls(self):
        self.ui.actionUpload.setEnabled(self.canUpload())
        self.ui.actionRescan.setEnabled(self.current_path is not None and self.auth_window.authenticated())
        self.ui.actionCancel.setEnabled(False)
        self.ui.actionOptions.setEnabled(True)
        self.ui.actionLogin.setEnabled(not self.auth_window.authenticated())
        self.ui.actionLogout.setEnabled(self.auth_window.authenticated())
        self.ui.actionExit.setEnabled(True)
        self.ui.browseButton.setEnabled(True)

    def disableControls(self):
        self.ui.actionUpload.setEnabled(False)
        self.ui.actionRescan.setEnabled(False)
        self.ui.actionOptions.setEnabled(False)
        self.ui.actionLogin.setEnabled(False)
        self.ui.actionLogout.setEnabled(False)
        self.ui.actionExit.setEnabled(False)
        self.ui.browseButton.setEnabled(False)

    def closeEvent(self, event=None):
        self.disableControls()
        if self.uploading:
            self.cancelTasks(self.cancelConfirmation())
        if event:
            event.accept()

    def checkValidServer(self):
        qApp.restoreOverrideCursor()
        if self.uploader.server and self.uploader.server.get("host"):
            return True
        msg = QMessageBox()
        msg.setIcon(QMessageBox.Warning)
        msg.setWindowTitle("No Server Configured")
        msg.setText("Add server configuration now?")
        msg.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
        ret = msg.exec_()
        if ret == QMessageBox.Yes:
            self.on_actionOptions_triggered()
        else:
            return False

    def onServerChanged(self, server):
        if server is None or server == self.uploader.server:
            return

        qApp.setOverrideCursor(Qt.WaitCursor)
        self.uploader.setServer(server)
        qApp.restoreOverrideCursor()
        if not self.checkValidServer():
            return
        self.setWindowTitle("%s (%s)" % (self.ui.title, self.uploader.server["host"]))
        self.getNewAuthWindow()
        self.getSession()

    def cancelTasks(self, save_progress):
        qApp.setOverrideCursor(Qt.WaitCursor)
        self.save_progress_on_cancel = save_progress
        self.uploader.cancel()
        Request.shutdown()
        self.statusBar().showMessage("Waiting for background tasks to terminate...")

        while True:
            qApp.processEvents()
            if QThreadPool.globalInstance().waitForDone(10):
                break

        self.uploading = False
        self.statusBar().showMessage("All background tasks terminated successfully")
        qApp.restoreOverrideCursor()

    def uploadCallback(self, **kwargs):
        completed = kwargs.get("completed")
        total = kwargs.get("total")
        file_path = kwargs.get("file_path")
        file_name = os.path.basename(file_path) if file_path else ""
        job_info = kwargs.get("job_info", {})
        job_info.update()
        if completed and total:
            file_name = " [%s]" % file_name
            job_info.update({"completed": completed, "total": total, "host": kwargs.get("host")})
            status = "Uploading file%s: %d%% complete" % (file_name, round(((completed / total) % 100) * 100))
            self.uploader.setTransferState(file_path, job_info)
        else:
            summary = kwargs.get("summary", "")
            file_name = "Uploaded file: [%s] " % file_name
            status = file_name  # + summary
        if status:
            self.progress_update_signal.emit(status)

        if self.uploader.cancelled:
            if self.save_progress_on_cancel:
                return -1
            else:
                return False

        return True

    def statusCallback(self, **kwargs):
        status = kwargs.get("status")
        self.progress_update_signal.emit(status)

    def displayUploads(self, upload_list):
        keys = ["State",
                "Status",
                "File"]
        hidden = ["State"]
        self.ui.uploadList.setRowCount(len(upload_list))
        self.ui.uploadList.setColumnCount(len(keys))

        rows = 0
        for row in upload_list:
            cols = 0
            for key in keys:
                item = QTableWidgetItem()
                value = row.get(key)
                text = str(value) or ""
                item.setText(text)
                item.setToolTip("<span>" + text + "</span>")
                self.ui.uploadList.setItem(rows, cols, item)
                if key in hidden:
                    self.ui.uploadList.hideColumn(cols)
                cols += 1
            rows += 1

        self.ui.uploadList.setHorizontalHeaderLabels(keys)  # add header names
        self.ui.uploadList.horizontalHeader().setDefaultAlignment(Qt.AlignLeft)  # set alignment
        self.ui.uploadList.resizeColumnToContents(0)

    def canUpload(self):
        return (self.ui.uploadList.rowCount() > 0) and self.auth_window.authenticated()

    def checkVersion(self):
        if not self.uploader.isVersionCompatible():
            self.updateStatus("Version incompatibility detected", "Current version: [%s], required version(s): %s." % (
                self.uploader.getVersion(), self.uploader.getVersionCompatibility()))
            self.disableControls()
            self.ui.actionExit.setEnabled(True)
            self.updateConfirmation()
            return False
        return True

    def updateConfirmation(self):
        url = self.uploader.config.get("version_update_url")
        if not url:
            return
        qApp.restoreOverrideCursor()
        msg = QMessageBox()
        msg.setIcon(QMessageBox.Warning)
        msg.setWindowTitle("Update Required")
        msg.setText("Launch browser and download new version?")
        msg.setInformativeText("Selecting \"Yes\" will launch an external web browser which will take you to a "
                               "download page where you can get the latest version of this software.")
        msg.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
        ret = msg.exec_()
        if ret == QMessageBox.Yes:
            webbrowser.open_new(url)

    def updateConfig(self):
        qApp.setOverrideCursor(Qt.WaitCursor)
        configUpdateTask = ConfigUpdateTask(self.uploader)
        configUpdateTask.status_update_signal.connect(self.onUpdateConfigResult)
        configUpdateTask.update_config()

    def scanDirectory(self):
        self.uploader.reset()
        scanTask = ScanDirectoryTask(self.uploader)
        scanTask.status_update_signal.connect(self.onScanResult)
        scanTask.scan(self.current_path)

    @pyqtSlot(str)
    def updateProgress(self, status):
        if status:
            self.statusBar().showMessage(status)
        else:
            self.displayUploads(self.uploader.getFileStatusAsArray())

    @pyqtSlot(str, str)
    def updateStatus(self, status, detail=None, success=True):
        msg = status + ((": %s" % detail) if detail else "")
        logging.info(msg) if success else logging.error(msg)
        self.statusBar().showMessage(status)

    @pyqtSlot(str, str)
    def resetUI(self, status, detail=None, success=True):
        self.updateStatus(status, detail, success)
        self.enableControls()

    @pyqtSlot(str)
    def updateLog(self, text):
        self.ui.logTextBrowser.widget.appendPlainText(text)

    @pyqtSlot(bool, str, str, object)
    def onSessionResult(self, success, status, detail, result):
        qApp.restoreOverrideCursor()
        if success:
            self.identity = result["client"]["id"]
            display_name = result["client"]["full_name"]
            self.setWindowTitle("%s (%s - %s)" % (self.ui.title, self.uploader.server["host"], display_name))
            self.ui.actionLogout.setEnabled(True)
            self.ui.actionLogin.setEnabled(False)
            if self.current_path:
                self.ui.actionRescan.setEnabled(True)
                self.ui.actionUpload.setEnabled(True)
            self.updateStatus("Logged in.")
            self.updateConfig()
        else:
            self.updateStatus("Login required.")

    @pyqtSlot(bool, str, str, object)
    def onUpdateConfigResult(self, success, status, detail, result):
        qApp.restoreOverrideCursor()
        if not success:
            self.resetUI(status, detail)
            return
        if not result:
            return
        confirm_updates = stob(self.uploader.server.get("confirm_updates", False))
        if confirm_updates:
            msg = QMessageBox()
            msg.setIcon(QMessageBox.Information)
            msg.setWindowTitle("Updated Configuration Available")
            msg.setText("Apply updated configuration?")
            msg.setInformativeText(
                "Selecting \"Yes\" will apply the latest configuration from the server and overwrite the existing "
                "default configuration file.\n\nSelecting \"No\" will ignore these updates and continue to use the "
                "existing configuration.\n\nYou should always apply the latest configuration changes from the server "
                "unless you understand the risk involved with using a potentially out-of-date configuration.")

            msg.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
            ret = msg.exec_()
            if ret == QMessageBox.No:
                return

        write_config(self.uploader.getDeployedConfigFilePath(), result)
        self.uploader.initialize(cleanup=False)
        if not self.checkVersion():
            return
        self.on_actionRescan_triggered()

    @pyqtSlot()
    def on_actionBrowse_triggered(self):
        dialog = QFileDialog()
        path = dialog.getExistingDirectory(self,
                                           "Select Directory",
                                           self.current_path,
                                           QFileDialog.ShowDirsOnly)
        if not path:
            return
        self.current_path = path
        self.ui.pathTextBox.setText(os.path.normpath(self.current_path))
        self.scanDirectory()

    @pyqtSlot()
    def on_actionRescan_triggered(self):
        if not self.current_path:
            return

        self.scanDirectory()

    @pyqtSlot(bool, str, str, object)
    def onScanResult(self, success, status, detail, result):
        qApp.restoreOverrideCursor()
        if success:
            self.displayUploads(self.uploader.getFileStatusAsArray())
            self.ui.actionUpload.setEnabled(self.canUpload())
            self.resetUI("Ready...")
            if self.uploading:
                self.on_actionUpload_triggered()
        else:
            self.resetUI(status, detail, success)

    @pyqtSlot()
    def on_actionUpload_triggered(self):
        if not self.uploading:
            if self.uploader.cancelled:
                self.uploading = True
                self.on_actionRescan_triggered()
                return

        self.disableControls()
        self.ui.actionCancel.setEnabled(True)
        self.save_progress_on_cancel = False
        qApp.setOverrideCursor(Qt.WaitCursor)
        self.uploading = True
        self.updateStatus("Uploading...")
        self.progress_update_signal.connect(self.updateProgress)
        uploadTask = UploadFilesTask(self.uploader)
        uploadTask.status_update_signal.connect(self.onUploadResult)
        uploadTask.upload(status_callback=self.statusCallback, file_callback=self.uploadCallback)

    @pyqtSlot(bool, str, str, object)
    def onUploadResult(self, success, status, detail, result):
        qApp.restoreOverrideCursor()
        self.uploading = False
        self.displayUploads(self.uploader.getFileStatusAsArray())
        if success:
            self.resetUI("Ready.")
        else:
            self.resetUI(status, detail, success)

    @pyqtSlot()
    def on_actionCancel_triggered(self):
        self.cancelTasks(self.cancelConfirmation())
        qApp.restoreOverrideCursor()
        self.displayUploads(self.uploader.getFileStatusAsArray())
        self.resetUI("Ready.")

    @pyqtSlot()
    def on_actionLogin_triggered(self):
        if not self.auth_window:
            if self.checkValidServer():
                self.getNewAuthWindow()
            else:
                return
        self.auth_window.show()
        self.auth_window.login()

    @pyqtSlot()
    def on_actionLogout_triggered(self):
        self.setWindowTitle("%s (%s)" % (self.ui.title, self.uploader.server["host"]))
        self.auth_window.logout(delete_cookies=True)
        self.identity = None
        self.ui.actionUpload.setEnabled(False)
        self.ui.actionRescan.setEnabled(False)
        self.ui.actionLogout.setEnabled(False)
        self.ui.actionLogin.setEnabled(True)
        self.updateStatus("Logged out.")

    @pyqtSlot()
    def on_actionOptions_triggered(self):
        OptionsDialog.getOptions(self)

    @pyqtSlot()
    def on_actionHelp_triggered(self):
        pass

    @pyqtSlot()
    def on_actionExit_triggered(self):
        self.closeEvent()
        qApp.quit()

    def quitEvent(self):
        if self.auth_window:
            self.auth_window.logout(self.logoutConfirmation())
        qApp.closeAllWindows()

    def logoutConfirmation(self):
        if self.auth_window and not self.auth_window.cookie_persistence:
            return
        msg = QMessageBox()
        msg.setIcon(QMessageBox.Warning)
        msg.setWindowTitle("Confirm Action")
        msg.setText("Do you wish to completely logout of the system?")
        msg.setInformativeText("Selecting \"Yes\" will clear the login state and invalidate the current user identity."
                               "\n\nSelecting \"No\" will keep your current identity cached, which will allow you to "
                               "log back in without authenticating until your session expires.\n\nNOTE: Select \"Yes\" "
                               "if this is a shared system using a single user account.")
        msg.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
        ret = msg.exec_()
        if ret == QMessageBox.Yes:
            return True
        return False

    @staticmethod
    def cancelConfirmation():
        qApp.restoreOverrideCursor()
        msg = QMessageBox()
        msg.setIcon(QMessageBox.Warning)
        msg.setWindowTitle("Confirm Action")
        msg.setText("Save progress for the current upload?")
        msg.setInformativeText("Selecting \"Yes\" will attempt to resume this transfer from the point where it was "
                               "cancelled.\n\nSelecting \"No\" will require the transfer to be started over from the "
                               "beginning of file.")
        msg.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
        ret = msg.exec_()
        if ret == QMessageBox.Yes:
            return True
        return False


# noinspection PyArgumentList
class UploadWindowUI(object):

    title = "DERIVA File Uploader"

    def __init__(self, MainWin):

        # Main Window
        MainWin.setObjectName("UploadWindow")
        MainWin.setWindowTitle(MainWin.tr(self.title))
        MainWin.resize(800, 600)
        self.centralWidget = QWidget(MainWin)
        self.centralWidget.setObjectName("centralWidget")
        MainWin.setCentralWidget(self.centralWidget)
        self.verticalLayout = QVBoxLayout(self.centralWidget)
        self.verticalLayout.setContentsMargins(11, 11, 11, 11)
        self.verticalLayout.setSpacing(6)
        self.verticalLayout.setObjectName("verticalLayout")

        self.horizontalLayout = QHBoxLayout()
        self.pathLabel = QLabel("Directory:")
        self.horizontalLayout.addWidget(self.pathLabel)
        self.pathTextBox = QLineEdit()
        self.pathTextBox.setReadOnly(True)
        self.horizontalLayout.addWidget(self.pathTextBox)
        self.browseButton = QPushButton("Browse", self.centralWidget)
        self.browseButton.clicked.connect(MainWin.on_actionBrowse_triggered)
        self.horizontalLayout.addWidget(self.browseButton)
        self.verticalLayout.addLayout(self.horizontalLayout)

        # Splitter for Upload list/Log
        self.splitter = QSplitter(Qt.Vertical)

        # Table View (Upload list)
        self.uploadList = TableWidget(self.centralWidget)
        self.uploadList.setObjectName("uploadList")
        self.uploadList.setStyleSheet(
            """
            QTableWidget {
                    border: 2px solid grey;
                    border-radius: 5px;
            }
            """)
        self.uploadList.setEditTriggers(QAbstractItemView.NoEditTriggers)  # use NoEditTriggers to disable editing
        self.uploadList.setAlternatingRowColors(True)
        self.uploadList.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.uploadList.setSelectionMode(QAbstractItemView.NoSelection)
        self.uploadList.verticalHeader().setDefaultSectionSize(18)  # tighten up the row size
        self.uploadList.horizontalHeader().setStretchLastSection(True)
        self.uploadList.setSortingEnabled(True)  # allow sorting
        self.splitter.addWidget(self.uploadList)

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
        self.splitter.setSizes([400, 200])
        self.verticalLayout.addWidget(self.splitter)

    # Actions

        # Browse
        self.actionBrowse = QAction(MainWin)
        self.actionBrowse.setObjectName("actionBrowse")
        self.actionBrowse.setText(MainWin.tr("Browse"))
        self.actionBrowse.setToolTip(MainWin.tr("Set the upload directory"))
        self.actionBrowse.setShortcut(MainWin.tr("Ctrl+B"))

        # Upload
        self.actionUpload = QAction(MainWin)
        self.actionUpload.setObjectName("actionUpload")
        self.actionUpload.setText(MainWin.tr("Upload"))
        self.actionUpload.setToolTip(MainWin.tr("Upload files"))
        self.actionUpload.setShortcut(MainWin.tr("Ctrl+L"))
        self.actionUpload.setEnabled(False)

        # Rescan
        self.actionRescan = QAction(MainWin)
        self.actionRescan.setObjectName("actionRescan")
        self.actionRescan.setText(MainWin.tr("Rescan"))
        self.actionRescan.setToolTip(MainWin.tr("Rescan the upload directory"))
        self.actionRescan.setShortcut(MainWin.tr("Ctrl+R"))
        self.actionRescan.setEnabled(False)

        # Cancel
        self.actionCancel = QAction(MainWin)
        self.actionCancel.setObjectName("actionCancel")
        self.actionCancel.setText(MainWin.tr("Cancel"))
        self.actionCancel.setToolTip(MainWin.tr("Cancel any upload(s) in-progress"))
        self.actionCancel.setShortcut(MainWin.tr("Ctrl+C"))

        # Options
        self.actionOptions = QAction(MainWin)
        self.actionOptions.setObjectName("actionOptions")
        self.actionOptions.setText(MainWin.tr("Options"))
        self.actionOptions.setToolTip(MainWin.tr("Configuration Options"))
        self.actionOptions.setShortcut(MainWin.tr("Ctrl+P"))

        # Login
        self.actionLogin = QAction(MainWin)
        self.actionLogin.setObjectName("actionLogin")
        self.actionLogin.setText(MainWin.tr("Login"))
        self.actionLogin.setToolTip(MainWin.tr("Login to the server"))
        self.actionLogin.setShortcut(MainWin.tr("Ctrl+G"))
        self.actionLogin.setEnabled(False)

        # Logout
        self.actionLogout = QAction(MainWin)
        self.actionLogout.setObjectName("actionLogout")
        self.actionLogout.setText(MainWin.tr("Logout"))
        self.actionLogout.setToolTip(MainWin.tr("Logout of the server"))
        self.actionLogout.setShortcut(MainWin.tr("Ctrl+O"))
        self.actionLogout.setEnabled(False)

        # Exit
        self.actionExit = QAction(MainWin)
        self.actionExit.setObjectName("actionExit")
        self.actionExit.setText(MainWin.tr("Exit"))
        self.actionExit.setToolTip(MainWin.tr("Exit the application"))
        self.actionExit.setShortcut(MainWin.tr("Ctrl+Z"))

        # Help
        self.actionHelp = QAction(MainWin)
        self.actionHelp.setObjectName("actionHelp")
        self.actionHelp.setText(MainWin.tr("Help"))
        self.actionHelp.setToolTip(MainWin.tr("Help"))
        self.actionHelp.setShortcut(MainWin.tr("Ctrl+H"))

    # Menu Bar

        """
        self.menuBar = QMenuBar(MainWin)
        self.menuBar.setObjectName("menuBar")
        MainWin.setMenuBar(self.menuBar)
        self.menuBar.setStyleSheet(
            "QMenuBar{font-family: Arial;font-style: normal;font-size: 10pt;font-weight: bold;};")
        """

    # Tool Bar

        self.mainToolBar = QToolBar(MainWin)
        self.mainToolBar.setObjectName("mainToolBar")
        self.mainToolBar.setToolButtonStyle(Qt.ToolButtonTextUnderIcon)
        MainWin.addToolBar(Qt.TopToolBarArea, self.mainToolBar)

        # Upload
        self.mainToolBar.addAction(self.actionUpload)
        self.actionUpload.setIcon(qApp.style().standardIcon(QStyle.SP_FileDialogToParent))

        # Rescan
        self.mainToolBar.addAction(self.actionRescan)
        self.actionRescan.setIcon(qApp.style().standardIcon(QStyle.SP_BrowserReload))

        # Cancel
        self.mainToolBar.addAction(self.actionCancel)
        self.actionCancel.setIcon(qApp.style().standardIcon(QStyle.SP_BrowserStop))
        self.actionCancel.setEnabled(False)

        # Options
        self.mainToolBar.addAction(self.actionOptions)
        self.actionOptions.setIcon(qApp.style().standardIcon(QStyle.SP_FileDialogDetailedView))

        # this spacer right justifies everything that comes after it
        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.mainToolBar.addWidget(spacer)

        # Login
        self.mainToolBar.addAction(self.actionLogin)
        self.actionLogin.setIcon(qApp.style().standardIcon(QStyle.SP_DialogApplyButton))

        # Logout
        self.mainToolBar.addAction(self.actionLogout)
        self.actionLogout.setIcon(qApp.style().standardIcon(QStyle.SP_DialogOkButton))

        # Help
        #self.mainToolBar.addAction(self.actionHelp)
        self.actionHelp.setIcon(qApp.style().standardIcon(QStyle.SP_MessageBoxQuestion))

        # Exit
        self.mainToolBar.addAction(self.actionExit)
        self.actionExit.setIcon(qApp.style().standardIcon(QStyle.SP_DialogCancelButton))

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
