import os
import json
import logging
import requests
import time
import platform
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry
from PyQt5.QtCore import Qt, QTimer, QUrl
from PyQt5.QtWidgets import qApp
from PyQt5.QtNetwork import QNetworkCookie
from PyQt5.QtWebEngineWidgets import QWebEngineView, QWebEnginePage, QWebEngineProfile
from deriva.core import read_config, read_credential, write_credential, format_exception, DEFAULT_SESSION_CONFIG, \
    DEFAULT_CREDENTIAL
from deriva.qt import __version__ as VERSION

DEFAULT_CONFIG = {
  "servers": []
}

DEFAULT_CONFIG_FILE = os.path.join(os.path.expanduser(os.path.normpath("~/.deriva")), "auth-agent-config.json")

DEFAULT_HTML = '<!DOCTYPE html><html lang="en"><head><meta charset="UTF-8"><title>DERIVA Auth Agent</title></head>' \
               '<body style="text-align: center; vertical-align: middle;">' \
               '<div id = "spinner" style="margin:0 auto;"><img src = "loader.gif" class ="spinner"/>' \
               '<div style = "margin-top: 15px;">Please wait... </div></div>' \
               '</body></html>'

ERROR_HTML = '<!DOCTYPE html><html lang="en"><head><meta charset="UTF-8"><title>Error</title></head>' \
             '<body style="text-align: center; vertical-align: middle;">%s</body></html>'

SUCCESS_HTML = '<!DOCTYPE html><html lang="en"><head><meta charset="UTF-8"><title>Authentication Success</title></head>' \
               '<body style="text-align: center; vertical-align: middle;">Authentication successful.</body></html>'


class AuthWidget(QWebEngineView):
    config = None
    config_file = DEFAULT_CONFIG_FILE
    credential = DEFAULT_CREDENTIAL
    credential_file = None
    auth_url = None
    authn_session = None
    authn_session_page = None
    authn_cookie_name = None
    authn_expires = time.time()
    cookie_persistence = False
    _success_callback = None
    _session = requests.session()
    token = None

    def __init__(self, parent, config=None, credential_file=None, cookie_persistence=False):
        super(AuthWidget, self).__init__(parent)
        self.cookie_persistence = cookie_persistence
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._onTimerFired)
        self.configure(config, credential_file)
        info = "%s v%s [Python %s, %s]" % (
            self.__class__.__name__, VERSION, platform.python_version(), platform.platform(aliased=True))
        logging.info("Initializing authorization provider: %s" % info)
        # logging.getLogger().setLevel(logging.TRACE)

    def configure(self, config, credential_file):
        self.config = config if config else read_config(self.config_file, create_default=True, default=DEFAULT_CONFIG)
        self.credential_file = credential_file
        host = self.config.get("host")
        if not host:
            self.setHtml(ERROR_HTML % "Could not locate hostname parameter in configuration.")
            return
        self.auth_url = QUrl()
        self.auth_url.setScheme(config.get("protocol", "https"))
        self.auth_url.setHost(host)
        if config.get("port") is not None:
            self.auth_url.setPort(config["port"])
        self.authn_cookie_name = self.config.get("cookie_name", "webauthn")

        retries = Retry(connect=DEFAULT_SESSION_CONFIG['retry_connect'],
                        read=DEFAULT_SESSION_CONFIG['retry_read'],
                        backoff_factor=DEFAULT_SESSION_CONFIG['retry_backoff_factor'],
                        status_forcelist=DEFAULT_SESSION_CONFIG['retry_status_forcelist'])

        self._session.mount(self.auth_url.toString() + '/',
                            HTTPAdapter(max_retries=retries))

    def authenticated(self):
        if self.authn_session is None:
            return False

        now = time.time()
        if now >= self.authn_expires:
            return False

        return True

    def login(self):
        if not (self.auth_url and (self.auth_url.host() and self.auth_url.scheme())):
            logging.error("Missing or invalid hostname parameter in configuration.")
            return
        logging.info("Authenticating with host: %s" % self.auth_url.toString())
        qApp.setOverrideCursor(Qt.WaitCursor)
        self._cleanup()
        self.setHtml(DEFAULT_HTML)
        self.authn_session_page = \
            QWebEnginePage(QWebEngineProfile(self), self) if not self.cookie_persistence else QWebEnginePage(self)
        self.authn_session_page.loadProgress.connect(self._onLoadProgress)
        self.authn_session_page.loadFinished.connect(self._onLoadFinished)
        self.authn_session_page.profile().cookieStore().cookieAdded.connect(self._onCookieAdded)
        self.authn_session_page.profile().cookieStore().cookieRemoved.connect(self._onCookieRemoved)
        self.authn_session_page.setUrl(QUrl(self.auth_url.toString() + "/authn/preauth"))

    def logout(self, delete_cookies=False):
        if not (self.auth_url and (self.auth_url.host() and self.auth_url.scheme())):
            return
        if not self.authenticated():
            return
        try:
            logging.info("Logging out of host: %s" % self.auth_url.toString())
            if delete_cookies and self.cookie_persistence:
                self.authn_session_page.profile().cookieStore().deleteAllCookies()
            self._session.delete(self.auth_url.toString() + "/authn/session")
        except Exception as e:
            logging.warning("Logout error: %s" % format_exception(e))
        self._cleanup()

    def setSuccessCallback(self, callback=None):
        self._success_callback = callback

    def setStatus(self, message):
        if self.window().statusBar is not None:
            self.window().statusBar().showMessage(message)

    def _execSuccessCallback(self):
        if self._success_callback:
            self._success_callback(host=self.auth_url.host(), credential=self.credential)

    def _onTimerFired(self):
        if not self.authenticated():
            self.authn_session = None
            return
        resp = self._session.put(self.auth_url.toString() + "/authn/session")
        seconds_remaining = self.authn_session['seconds_remaining']
        self.authn_expires = time.time() + seconds_remaining + 1
        if resp.ok:
            logging.trace("webauthn session:\n%s\n", resp.json())
            logging.info("Session refreshed for: %s" % self.auth_url.host())
        else:
            logging.warning(
                "Unable to refresh session for: %s. Server responded: %s" %
                (self.auth_url.host(),
                 str.format("%s %s: %s" % (resp.status_code, resp.reason, resp.content.decode()))))

    def _onSessionContent(self, content):
        try:
            self.setHtml(SUCCESS_HTML)
            self.authn_session = json.loads(content)
            seconds_remaining = self.authn_session['seconds_remaining']
            if not self._timer.isActive():
                interval = seconds_remaining // 2
                logging.info("Authentication successful for [%s]: credential refresh in %d seconds." %
                             (self.auth_url.toString(), interval))
                self._timer.start(interval * 1000)
            self.authn_expires = time.time() + seconds_remaining + 1
            logging.trace("webauthn session:\n%s\n", json.dumps(self.authn_session, indent=2))
            qApp.restoreOverrideCursor()
            QTimer.singleShot(100, self._execSuccessCallback)
        except (ValueError, Exception) as e:
            logging.error(format_exception(e))
            self.setHtml(ERROR_HTML % content)

    def _onPreAuthContent(self, content):
        try:
            if not content:
                logging.debug("no preauth content")
                return
            preauth = json.loads(content)
            logging.trace("webauthn preauth:\n%s\n", json.dumps(preauth, indent=2))
            qApp.setOverrideCursor(Qt.WaitCursor)
            self.authn_session_page.setUrl(QUrl(preauth["redirect_url"]))
        except (ValueError, Exception) as e:
            logging.error(format_exception(e))
            self.setHtml(ERROR_HTML % content)

    def _onLoadFinished(self, result):
        qApp.restoreOverrideCursor()
        if not result:
            logging.debug("Page load error: %s" % self.authn_session_page.url().toDisplayString())
            self.setPage(self.authn_session_page)
            return
        if self.authn_session_page.url().path() == "/authn/preauth":
            self.authn_session_page.toPlainText(self._onPreAuthContent)
        elif self.authn_session_page.url().path() == "/authn/session":
            self.authn_session_page.toPlainText(self._onSessionContent)
        else:
            self.setPage(self.authn_session_page)

    def _onLoadProgress(self, progress):
        self.setStatus("Loading page: %s [%d%%]" % (self.url().host(), progress))

    def _onCookieAdded(self, cookie):
        cookie_str = str(cookie.toRawForm(QNetworkCookie.NameAndValueOnly), encoding='utf-8')
        cookie_name = str(cookie.name(), encoding='utf-8')
        cookie_val = str(cookie.value(), encoding='utf-8')
        if (cookie_name == self.authn_cookie_name) and (cookie.domain() == self.config.get("host")):
            logging.trace("%s cookie added:\n\n%s\n\n" % (self.authn_cookie_name, cookie_str))
            self.credential["cookie"] = "%s=%s" % (self.authn_cookie_name, cookie_val)
            host = self.auth_url.host()
            cred_entry = dict()
            cred_entry[host] = self.credential
            if self.credential_file:
                creds = read_credential(self.credential_file, create_default=True)
                creds.update(cred_entry)
                write_credential(self.credential_file, creds)
            self.token = cookie_val
            self._session.cookies.set(self.authn_cookie_name, cookie_val, domain=host, path='/')
            self.authn_session_page.setUrl(QUrl(self.auth_url.toString() + "/authn/session"))

    def _onCookieRemoved(self, cookie):
        cookie_str = str(cookie.toRawForm(QNetworkCookie.NameAndValueOnly), encoding='utf-8')
        cookie_name = str(cookie.name(), encoding='utf-8')
        if cookie_name == self.authn_cookie_name and cookie.domain() == self.url().host():
            logging.trace("%s cookie removed:\n\n%s\n\n" % (self.authn_cookie_name, cookie_str))

    def _cleanup(self):
        self._timer.stop()
        self.token = None
        self.authn_session = None
        self.authn_expires = time.time()
        if self.authn_session_page:
            self.authn_session_page.loadProgress.disconnect(self._onLoadProgress)
            self.authn_session_page.loadFinished.disconnect(self._onLoadFinished)
            self.authn_session_page.profile().cookieStore().cookieAdded.disconnect(self._onCookieAdded)
            self.authn_session_page.profile().cookieStore().cookieRemoved.disconnect(self._onCookieRemoved)
            del self.authn_session_page
