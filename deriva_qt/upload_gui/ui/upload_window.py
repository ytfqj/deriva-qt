import os
import logging
from PyQt5.QtCore import Qt, QCoreApplication, QMetaObject, QThreadPool, QModelIndex, pyqtSlot, pyqtSignal
from PyQt5.QtWidgets import qApp, QMainWindow, QWidget, QAction, QSizePolicy, QPushButton, QStyle, QSplitter, QLabel, \
     QToolBar, QStatusBar, QVBoxLayout, QHBoxLayout, QTableWidgetItem, QAbstractItemView, QLineEdit, QFileDialog
from PyQt5.QtGui import QIcon
from deriva_qt.common import log_widget, table_widget, async_task
from deriva_qt.auth_agent.ui.auth_window import AuthWindow
from deriva_qt.upload_gui.impl.upload_tasks import *


# noinspection PyArgumentList
class MainWindow(QMainWindow):
    uploader = None
    credential = None
    identity = None
    current_path = None
    progress_update_signal = pyqtSignal(str)
    
    def __init__(self, uploader, config_path=None, credential_path=None, window_title=None):
        super(MainWindow, self).__init__()
        self.uploader = uploader
        self.ui = MainWindowUI(self)
        if window_title:
            self.setWindowTitle(window_title)
        self.ui.browseButton.clicked.connect(self.on_actionBrowse_triggered)
        self.configure(config_path)
        self.authWindow = AuthWindow(config_path, credential_path, self.onLoginSuccess, True)
        self.getSession()
        if not self.identity or not self.current_path:
            self.ui.actionUpload.setEnabled(False)
            # self.on_actionLogin_triggered()

    def configure(self, config_path):
        # configure logging
        self.ui.logTextBrowser.widget.log_update_signal.connect(self.updateLog)
        self.ui.logTextBrowser.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))
        logging.getLogger().addHandler(self.ui.logTextBrowser)
        logging.getLogger().setLevel(logging.INFO)

    def getSession(self):
        qApp.setOverrideCursor(Qt.WaitCursor)
        self.updateStatus("Validating session.")
        queryTask = SessionQueryTask(self.uploader)
        queryTask.status_update_signal.connect(self.onSessionResult)
        queryTask.query()

    def onLoginSuccess(self, **kwargs):
        self.authWindow.hide()
        self.credential = kwargs["credential"]
        server = self.uploader.config["server"]["host"]
        self.uploader.catalog.set_credentials(self.credential, server)
        self.uploader.store.set_credentials(self.credential, server)
        self.getSession()

    def enableControls(self):
        self.ui.actionUpload.setEnabled(True)
        self.ui.actionLogin.setEnabled(True)
        self.ui.actionLogout.setEnabled(True)
        self.ui.actionExit.setEnabled(True)
        self.ui.uploadList.setEnabled(True)
        self.ui.browseButton.setEnabled(True)

    def disableControls(self):
        self.ui.actionUpload.setEnabled(False)
        self.ui.actionLogin.setEnabled(False)
        self.ui.actionLogout.setEnabled(False)
        self.ui.actionExit.setEnabled(False)
        self.ui.uploadList.setEnabled(False)
        self.ui.browseButton.setEnabled(False)

    def closeEvent(self, event=None):
        self.cancelTasks()
        if event:
            event.accept()

    def cancelTasks(self):
        self.disableControls()
        async_task.Request.shutdown()
        self.statusBar().showMessage("Waiting for background tasks to terminate...")

        while True:
            qApp.processEvents()
            if QThreadPool.globalInstance().waitForDone(10):
                break

        self.enableControls()
        self.statusBar().showMessage("All background tasks terminated successfully")

    def uploadCallback(self, **kwargs):
        status = kwargs.get("progress")
        if not status:
            status = kwargs.get("summary")
        if status:
            self.progress_update_signal.emit(status)
        return True

    def displayUploads(self, upload_list):
        keys = ["State",
                "File",
                "Status"]
        hidden = []
        self.ui.uploadList.setRowCount(len(upload_list))
        self.ui.uploadList.setColumnCount(len(keys))

        rows = 0
        for row in upload_list:
            cols = 0
            for key in keys:
                item = QTableWidgetItem()
                value = row.get(key)
                item.setText(str(value) or "")
                self.ui.uploadList.setItem(rows, cols, item)
                if key in hidden:
                    self.ui.uploadList.hideColumn(cols)
                cols += 1
            rows += 1

        self.ui.uploadList.setHorizontalHeaderLabels(keys)  # add header names
        self.ui.uploadList.horizontalHeader().setDefaultAlignment(Qt.AlignLeft)  # set alignment
        self.ui.uploadList.resizeColumnToContents(0)
        self.ui.uploadList.resizeColumnToContents(1)
        self.ui.uploadList.resizeColumnToContents(2)
        if (self.ui.uploadList.rowCount() > 0) and self.identity:
            self.ui.actionUpload.setEnabled(True)
        else:
            self.ui.actionUpload.setEnabled(False)

    @pyqtSlot()
    def taskTriggered(self):
        self.ui.logTextBrowser.widget.clear()
        self.disableControls()

    @pyqtSlot(str)
    def updateProgress(self, status):
        self.statusBar().showMessage(status)

    @pyqtSlot(str, str)
    def updateStatus(self, status, detail=None):
        logging.info(status + ((": %s" % detail) if detail else ""))
        self.statusBar().showMessage(status)

    @pyqtSlot(str, str)
    def resetUI(self, status, detail=None):
        self.updateStatus(status, detail)
        self.enableControls()

    @pyqtSlot(str)
    def updateLog(self, text):
        self.ui.logTextBrowser.widget.appendPlainText(text)

    @pyqtSlot(bool, str, str, object)
    def onSessionResult(self, success, status, detail, result):
        qApp.restoreOverrideCursor()
        if success:
            self.identity = result["client"]["id"]
            if self.current_path:
                self.ui.actionUpload.setEnabled(True)
        else:
            self.updateStatus(status, detail)

    @pyqtSlot()
    def on_actionBrowse_triggered(self):
        dialog = QFileDialog()
        path = dialog.getExistingDirectory(self,
                                           "Select Directory",
                                           self.current_path,
                                           QFileDialog.ShowDirsOnly)
        if self.current_path == path:
            return
        else:
            self.current_path = path

        self.uploader.cleanup()
        self.ui.pathTextBox.setText(os.path.normpath(self.current_path))
        self.disableControls()
        scanTask = ScanDirectoryTask(self.uploader)
        scanTask.status_update_signal.connect(self.onScanResult)
        scanTask.scan(self.current_path)

    @pyqtSlot(bool, str, str, object)
    def onScanResult(self, success, status, detail, result):
        qApp.restoreOverrideCursor()
        if success:
            self.displayUploads(self.uploader.getFileStatusAsArray())
            if self.ui.uploadList.rowCount() > 0:
                self.ui.actionUpload.setEnabled(True)
            self.resetUI("Ready...")
        else:
            self.resetUI(status, detail)

    @pyqtSlot()
    def on_actionUpload_triggered(self):
        self.disableControls()
        qApp.setOverrideCursor(Qt.WaitCursor)
        self.resetUI("Uploading...")
        self.disableControls()
        uploadTask = UploadFilesTask(self.uploader)
        uploadTask.status_update_signal.connect(self.onUploadResult)
        uploadTask.upload(self.current_path)

    @pyqtSlot(bool, str, str, object)
    def onUploadResult(self, success, status, detail, result):
        qApp.restoreOverrideCursor()
        self.displayUploads(self.uploader.getFileStatusAsArray())
        if success:
            self.resetUI("Ready.")
        else:
            self.resetUI(status, detail)

    @pyqtSlot()
    def on_actionCancel_triggered(self):
        pass

    @pyqtSlot(bool, str, str, object)
    def onCancelResult(self, success, status, detail, result):
        qApp.restoreOverrideCursor()
        if success:
            self.resetUI("Ready.")
        else:
            self.resetUI(status, detail)

    @pyqtSlot()
    def on_actionLogin_triggered(self):
        self.authWindow.show()
        self.authWindow.login()

    @pyqtSlot()
    def on_actionLogout_triggered(self):
        self.authWindow.logout()
        self.identity = None
        self.ui.actionUpload.setEnabled(False)

    @pyqtSlot()
    def on_actionHelp_triggered(self):
        pass

    @pyqtSlot()
    def on_actionExit_triggered(self):
        self.closeEvent()
        QCoreApplication.quit()


# noinspection PyArgumentList
class MainWindowUI(object):

    def __init__(self, MainWin):
        super(MainWindow).__init__()

        # Main Window
        MainWin.setObjectName("MainWindow")
        MainWin.setWindowTitle(MainWin.tr("DERIVA File Uploader"))
        # MainWin.setWindowIcon(QIcon(":/images/bag.png"))
        MainWin.resize(640, 600)
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
        self.horizontalLayout.addWidget(self.pathTextBox)
        self.browseButton = QPushButton("Browse", self.centralWidget)
        self.horizontalLayout.addWidget(self.browseButton)
        self.verticalLayout.addLayout(self.horizontalLayout)

        # Splitter for Upload list/Log
        self.splitter = QSplitter(Qt.Vertical)

        # Table View (Upload list)
        self.uploadList = table_widget.TableWidget(self.centralWidget)
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
        self.uploadList.setSelectionMode(QAbstractItemView.SingleSelection)
        self.uploadList.verticalHeader().setDefaultSectionSize(18)  # tighten up the row size
        self.uploadList.horizontalHeader().setStretchLastSection(True)
        # self.uploadList.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.uploadList.setSortingEnabled(True)  # allow sorting
        self.splitter.addWidget(self.uploadList)

        # Log Widget
        self.logTextBrowser = log_widget.QPlainTextEditLogger(self.centralWidget)
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

        # Cancel
        self.actionCancel = QAction(MainWin)
        self.actionCancel.setObjectName("actionCancel")
        self.actionCancel.setText(MainWin.tr("Cancel"))
        self.actionCancel.setToolTip(MainWin.tr("Cancel any upload(s) in-progress"))
        self.actionCancel.setShortcut(MainWin.tr("Ctrl+C"))

        # Login
        self.actionLogin = QAction(MainWin)
        self.actionLogin.setObjectName("actionLogin")
        self.actionLogin.setText(MainWin.tr("Login"))
        self.actionLogin.setToolTip(MainWin.tr("Login to the server"))
        self.actionLogin.setShortcut(MainWin.tr("Ctrl+G"))

        # Logout
        self.actionLogout = QAction(MainWin)
        self.actionLogout.setObjectName("actionLogout")
        self.actionLogout.setText(MainWin.tr("Logout"))
        self.actionLogout.setToolTip(MainWin.tr("Logout of the server"))
        self.actionLogout.setShortcut(MainWin.tr("Ctrl+O"))

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

    # Tool Bar

        self.mainToolBar = QToolBar(MainWin)
        self.mainToolBar.setObjectName("mainToolBar")
        self.mainToolBar.setToolButtonStyle(Qt.ToolButtonTextUnderIcon)
        MainWin.addToolBar(Qt.TopToolBarArea, self.mainToolBar)

        # Upload
        self.mainToolBar.addAction(self.actionUpload)
        self.actionUpload.setIcon(qApp.style().standardIcon(QStyle.SP_FileDialogToParent))

        # Cancel
        self.mainToolBar.addAction(self.actionCancel)
        self.actionCancel.setIcon(qApp.style().standardIcon(QStyle.SP_BrowserStop))

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

    # finalize UI setup
        QMetaObject.connectSlotsByName(MainWin)