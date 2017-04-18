from PyQt5.QtCore import pyqtSignal
from deriva_common import format_exception, DEFAULT_HEADERS
from deriva_io.deriva_upload import DerivaUpload
from deriva_qt.common.async_task import async_execute, AsyncTask


class UploadTask(AsyncTask):
    def __init__(self, uploader, parent=None):
        super(UploadTask, self).__init__(parent)
        assert (uploader is not None and isinstance(uploader, DerivaUpload))
        self.uploader = uploader


class SessionQueryTask(UploadTask):
    status_update_signal = pyqtSignal(bool, str, str, object)

    def __init__(self, parent=None):
        super(SessionQueryTask, self).__init__(parent)

    def success_callback(self, rid, result):
        if rid != self.rid:
            return
        self.status_update_signal.emit(True, "Session query success", "", result.json())

    def error_callback(self, rid, error):
        if rid != self.rid:
            return
        self.status_update_signal.emit(False, "Session query failure", format_exception(error), None)

    def query(self):
        self.init_request()
        self.request = async_execute(self.uploader.catalog.get_authn_session,
                                     [],
                                     self.rid,
                                     self.success_callback,
                                     self.error_callback)


class ScanDirectoryTask(UploadTask):
    status_update_signal = pyqtSignal(bool, str, str, object)

    def __init__(self, parent=None):
        super(ScanDirectoryTask, self).__init__(parent)

    def success_callback(self, rid, result):
        if rid != self.rid:
            return
        self.status_update_signal.emit(True, "Directory scan success", "", None)

    def error_callback(self, rid, error):
        if rid != self.rid:
            return
        self.status_update_signal.emit(False, "Directory scan failed", format_exception(error), None)

    def scan(self, path):
        self.init_request()
        self.request = async_execute(self.uploader.scanDirectory,
                                     [path],
                                     self.rid,
                                     self.success_callback,
                                     self.error_callback)


class UploadFilesTask(UploadTask):
    status_update_signal = pyqtSignal(bool, str, str, object)
    progress_update_signal = pyqtSignal(int, int)

    def __init__(self, parent=None):
        super(UploadFilesTask, self).__init__(parent)

    def success_callback(self, rid, result):
        if rid != self.rid:
            return
        self.status_update_signal.emit(True, "File upload success", "", None)

    def error_callback(self, rid, error):
        if rid != self.rid:
            return
        self.status_update_signal.emit(False, "File upload failed", format_exception(error), None)

    def upload(self, status_callback=None, file_callback=None):
        self.init_request()
        self.request = async_execute(self.uploader.uploadFiles,
                                     [status_callback, file_callback],
                                     self.rid,
                                     self.success_callback,
                                     self.error_callback)
