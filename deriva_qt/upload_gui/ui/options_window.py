import os

from PyQt5.QtCore import Qt, pyqtSlot
from PyQt5.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QFileDialog, \
    QGroupBox, QRadioButton, QComboBox, QCheckBox, QMessageBox, qApp
from deriva_qt.common.json_editor import JSONEditor
from deriva_io.generic_uploader import GenericUploader
from deriva_common import stob


def warningMessageBox(parent, text, detail):
    msg = QMessageBox(parent)
    msg.setIcon(QMessageBox.Warning)
    msg.setWindowTitle("Attention Required")
    msg.setText(text)
    msg.setInformativeText(detail)
    msg.exec_()


def getServerDisplayName(server):
    host = server.get("host", "")
    desc = server.get("desc", "")
    display_name = ("%s" % "https://" + host) if not desc else ("%s: %s" % (desc, "https://" + host))
    return display_name


class OptionsDialog(QDialog):
    def __init__(self, parent):
        super(OptionsDialog, self).__init__(parent)
        self.reconfigure = False
        self.setWindowTitle("Options")
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)
        self.setMinimumWidth(600)
        layout = QVBoxLayout(self)
        layout.addStretch(1)

        # Servers
        setServers = getattr(parent.uploader, "setServers", None)
        self.serversConfigurable = True if callable(setServers) else False
        self.serversGroupBox = QGroupBox("Servers:", self)
        self.serverLayout = QHBoxLayout()
        self.serverLabel = QLabel("Server:")
        self.serverLayout.addWidget(self.serverLabel)
        self.serverComboBox = QComboBox()
        self.serverComboBox.setEditable(False)
        self.serverComboBox.setMinimumContentsLength(50)
        self.serverComboBox.currentIndexChanged.connect(self.onServerChanged)
        self.serverLayout.addWidget(self.serverComboBox)
        self.serverLayout.addStretch(1)
        self.addServerButton = QPushButton("Add", parent)
        self.addServerButton.clicked.connect(self.onServerAdd)
        self.addServerButton.setEnabled(self.serversConfigurable)
        self.serverLayout.addWidget(self.addServerButton)
        self.editServerButton = QPushButton("Edit", parent)
        self.editServerButton.clicked.connect(self.onServerEdit)
        self.editServerButton.setEnabled(self.serversConfigurable)
        self.serverLayout.addWidget(self.editServerButton)
        self.serversGroupBox.setLayout(self.serverLayout)
        layout.addWidget(self.serversGroupBox)

        # Configuration
        self.configurable = isinstance(parent.uploader, GenericUploader)
        self.configGroupBox = QGroupBox("Configuration:", self)
        self.configLayout = QHBoxLayout()
        self.configPathLabel = QLabel("File:")
        self.configLayout.addWidget(self.configPathLabel)
        self.configPathTextBox = QLineEdit()
        self.configPathTextBox.setReadOnly(True)
        self.configPathTextBox.setText(os.path.normpath(parent.uploader.getCurrentConfigFilePath()))
        self.configLayout.addWidget(self.configPathTextBox)
        self.configBrowseButton = QPushButton("Change", parent)
        self.configBrowseButton.clicked.connect(self.onConfigChange)
        self.configBrowseButton.setEnabled(self.configurable)
        self.configLayout.addWidget(self.configBrowseButton)
        self.configEditButton = QPushButton("Edit", parent)
        self.configEditButton.clicked.connect(self.onConfigEdit)
        self.configEditButton.setEnabled(self.configurable)
        self.configLayout.addWidget(self.configEditButton)
        self.configGroupBox.setLayout(self.configLayout)
        layout.addWidget(self.configGroupBox)

        # Upload
        self.uploadGroupBox = QGroupBox("Upload:", self)
        self.uploadLayout = QHBoxLayout()
        self.uploadAllButton = QRadioButton("Files and Data")
        self.uploadAllButton.setChecked(True)
        self.uploadLayout.addWidget(self.uploadAllButton)
        self.uploadFilesButton = QRadioButton("Files only")
        self.uploadLayout.addWidget(self.uploadFilesButton)
        self.uploadDataButton = QRadioButton("Data only")
        self.uploadLayout.addWidget(self.uploadDataButton)
        self.uploadGroupBox.setLayout(self.uploadLayout)
        layout.addWidget(self.uploadGroupBox)

        self.populateServers()

    @pyqtSlot()
    def onConfigChange(self):
        uploader = self.parent().uploader
        current_path = os.path.normpath(self.configPathTextBox.text())
        new_path = QFileDialog.getOpenFileName(self,
                                               "Select Configuration File",
                                               current_path,
                                               "Configuration Files (*.json)")
        if new_path[0]:
            new_path = os.path.normpath(new_path[0])
            if new_path != current_path:
                self.configPathTextBox.setText(new_path)
                if new_path != uploader.getDefaultConfigFilePath():
                    uploader.override_config_file = new_path
                else:
                    uploader.override_config_file = None
                self.reconfigure = True
            else:
                self.reconfigure = False

    @pyqtSlot()
    def onConfigEdit(self):
        uploader = self.parent().uploader
        configEditor = JSONEditor(self, self.configPathTextBox.text(), "Configuration Editor")
        configEditor.exec_()
        if configEditor.isModified():
            path = self.configPathTextBox.text()
            uploader.override_config_file = path
            self.reconfigure = True
        del configEditor

    @pyqtSlot()
    def onServerAdd(self):
        server = ServerDialog.configureServer(self.parent(), {})
        if not server:
            return
        hostname = server.get("host")
        index = self.serverComboBox.findText(hostname, Qt.MatchExactly)
        if index > -1:
            warningMessageBox(self.parent(), "Server already exists!",
                              "A server configuration for this hostname already exists. "
                              "Please edit that configuration directly if you wish to make changes to it.")
            return
        else:
            index = self.serverComboBox.count()
            self.serverComboBox.insertItem(index, getServerDisplayName(server), server)

        self.updateDefaultServer(index)
        self.editServerButton.setEnabled(self.serversConfigurable)

    @pyqtSlot()
    def onServerEdit(self):
        index = self.serverComboBox.currentIndex()
        server = self.serverComboBox.itemData(index, Qt.UserRole)
        server = ServerDialog.configureServer(self.parent(), server if server else {})
        self.serverComboBox.setItemData(index, server, Qt.UserRole)
        self.updateDefaultServer(index)

    @pyqtSlot()
    def onServerChanged(self):
        uploader = self.parent().uploader
        if not uploader.override_config_file:
            server = self.serverComboBox.currentData(Qt.UserRole)
            if not server:
                return
            config_file = os.path.normpath(os.path.join(
                uploader.getDeployedConfigPath(), server.get('host', ''), uploader.DefaultConfigFileName))
            self.configPathTextBox.setText(config_file)
            if not (os.path.exists(config_file) and os.path.isfile(config_file)):
                self.configEditButton.setEnabled(False)
            elif self.configurable:
                self.configEditButton.setEnabled(True)

    def updateDefaultServer(self, index):
        new = self.serverComboBox.itemData(index, Qt.UserRole)
        if not new.get("default", False):
            return
        else:
            self.serverComboBox.removeItem(index)
            self.serverComboBox.insertItem(0, getServerDisplayName(new), new)
            self.serverComboBox.setCurrentIndex(0)

        for x in range(self.serverComboBox.count()):
            current = self.serverComboBox.itemData(x, Qt.UserRole)
            if new.get("host") != current.get("host"):
                current["default"] = False

    def populateServers(self):
        uploader = self.parent().uploader
        servers = uploader.getServers()
        if not servers:
            self.editServerButton.setEnabled(False)
            return
        else:
            index = 0
            for server in servers:
                self.serverComboBox.insertItem(index, getServerDisplayName(server), server)
                if server == uploader.server:
                    self.serverComboBox.setCurrentIndex(index)
                elif not uploader.server and server.get("default", False):
                    self.serverComboBox.setCurrentIndex(index)
                index += 1
            self.editServerButton.setEnabled(self.serversConfigurable)

    def getServers(self):
        servers = list()
        for x in range(self.serverComboBox.count()):
            servers.append(self.serverComboBox.itemData(x, Qt.UserRole))
        return servers

    @staticmethod
    def getOptions(parent):
        uploader = parent.uploader
        dialog = OptionsDialog(parent)
        dialog.exec_()
        setServers = getattr(uploader, "setServers", None)
        if callable(setServers):
            setServers(dialog.getServers())
        current_server = dialog.serverComboBox.currentData(Qt.UserRole)
        if current_server != uploader.server:
            parent.onServerChanged(current_server)
            return
        if dialog.reconfigure:
            qApp.setOverrideCursor(Qt.WaitCursor)
            uploader.initialize(cleanup=False)
            qApp.restoreOverrideCursor()
        del dialog


class ServerDialog(QDialog):
    def __init__(self, parent, server):
        super(ServerDialog, self).__init__(parent)
        self.server = server
        self.setWindowTitle("Server Configuration")
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)
        self.setMinimumWidth(400)
        layout = QVBoxLayout(self)

        self.hostnameLayout = QHBoxLayout()
        self.hostnameLabel = QLabel("Host:")
        self.hostnameLayout.addWidget(self.hostnameLabel)
        self.hostnameTextBox = QLineEdit()
        self.hostnameTextBox.setText(server.get("host", ""))
        self.hostnameLayout.addWidget(self.hostnameTextBox)
        layout.addLayout(self.hostnameLayout)

        self.descriptionLayout = QHBoxLayout()
        self.descriptionLabel = QLabel("Description:")
        self.descriptionLayout.addWidget(self.descriptionLabel)
        self.descriptionTextBox = QLineEdit()
        self.descriptionTextBox.setText(server.get("desc", ""))
        self.descriptionLayout.addWidget(self.descriptionTextBox)
        layout.addLayout(self.descriptionLayout)

        self.catalogIDLayout = QHBoxLayout()
        self.catalogIDLabel = QLabel("Catalog ID:")
        self.catalogIDLayout.addWidget(self.catalogIDLabel)
        self.catalogIDTextBox = QLineEdit()
        self.catalogIDTextBox.setText(str(server.get("catalog_id", 1)))
        self.catalogIDLayout.addWidget(self.catalogIDTextBox)
        layout.addLayout(self.catalogIDLayout)

        setServers = getattr(parent.uploader, "setServers", None)
        self.serversConfigurable = True if callable(setServers) else False
        self.checkboxLayout = QHBoxLayout()
        self.defaultServer = QCheckBox("Set as &Default", parent)
        self.defaultServer.setChecked(stob(server.get("default", False)))
        self.defaultServer.setEnabled(self.serversConfigurable)
        self.checkboxLayout.addWidget(self.defaultServer)
        self.confirm_updates = QCheckBox("&Confirm configuration updates", parent)
        self.confirm_updates.setChecked(stob(server.get("confirm_updates", False)))
        self.confirm_updates.setEnabled(self.serversConfigurable)
        self.checkboxLayout.addWidget(self.confirm_updates)
        layout.addLayout(self.checkboxLayout)

    def validate(self):
        hostname = self.hostnameTextBox.text()
        if not hostname:
            warningMessageBox(self.parent(), "Please enter a valid hostname:",
                              "For example: \'www.host.com\' or \'localhost\', etc.")
            return False
        else:
            self.server["host"] = hostname

        self.server["default"] = self.defaultServer.isChecked()
        self.server["confirm_updates"] = self.confirm_updates.isChecked()

        desc = self.descriptionTextBox.text()
        self.server["desc"] = desc if desc else ""

        catalog_id = int(self.catalogIDTextBox.text())
        self.server["catalog_id"] = catalog_id if catalog_id else 1

        return True

    @staticmethod
    def configureServer(parent, server):
        dialog = ServerDialog(parent, server)
        dialog.exec_()
        if dialog.validate():
            return dialog.server.copy()
        else:
            return None
