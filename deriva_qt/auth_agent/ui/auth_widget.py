import os
import json
import logging
import requests
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry
from PyQt5.QtCore import Qt, QTimer, QUrl
from PyQt5.QtWidgets import qApp
from PyQt5.QtNetwork import QNetworkCookie
from PyQt5.QtWebEngineWidgets import QWebEngineView, QWebEnginePage
from deriva_common import read_config, read_credential, write_credential, format_exception, \
     DEFAULT_SESSION_CONFIG, DEFAULT_CONFIG_FILE, DEFAULT_CREDENTIAL, DEFAULT_CREDENTIAL_FILE

DEFAULT_CONFIG = {
  "server": {
    "protocol": "https",
    "host": ""
  },
  "cookie_name": "webauthn"
}

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
    config_file = os.path.join(os.path.expanduser(os.path.normpath("~/.deriva")), "auth-agent-config.json")
    credential = DEFAULT_CREDENTIAL
    credential_file = None
    auth_url = None
    authn_session = {}
    authn_cookie_name = None
    authenticated = False
    _success_callback = None
    _session = requests.session()
    _timer = QTimer()

    def __init__(self, config_file=DEFAULT_CONFIG_FILE, credential_file=DEFAULT_CREDENTIAL_FILE):
        super(AuthWidget, self).__init__()
        self.loadProgress.connect(self.onLoadProgress)
        self.loadFinished.connect(self.onLoadFinished)
        self.page().profile().cookieStore().cookieAdded.connect(self.onCookieAdded)
        self.page().profile().cookieStore().cookieRemoved.connect(self.onCookieRemoved)

        self.auth_session_page = QWebEnginePage(self)
        self.auth_session_page.loadFinished.connect(self.onAuthLoadFinished)

        self._timer.timeout.connect(self.onTimerFired)
        qApp.aboutToQuit.connect(self.quitEvent)

        self.configure(config_file, credential_file)

    def configure(self, config_file, credential_file):
        if config_file:
            self.config_file = config_file
        self.config = read_config(self.config_file, create_default=True, default=DEFAULT_CONFIG)
        self.credential_file = credential_file
        if self.credential_file:
            self.credential = read_credential(self.credential_file, create_default=True)
        server = self.config.get("server")
        if not server:
            self.setHtml(ERROR_HTML % "Could not locate server parameters in configuration file.")
            return
        self.auth_url = QUrl()
        self.auth_url.setScheme(server.get("protocol", "https"))
        self.auth_url.setHost(server.get("host", "localhost"))
        if server.get("port") is not None:
            self.auth_url.setPort(server["port"])
        self.authn_cookie_name = self.config.get("cookie_name", DEFAULT_CONFIG["cookie_name"])

        retries = Retry(connect=DEFAULT_SESSION_CONFIG['retry_connect'],
                        read=DEFAULT_SESSION_CONFIG['retry_read'],
                        backoff_factor=DEFAULT_SESSION_CONFIG['retry_backoff_factor'],
                        status_forcelist=DEFAULT_SESSION_CONFIG['retry_status_forcelist'])

        self._session.mount(self.auth_url.toString() + '/',
                            HTTPAdapter(max_retries=retries))

    def login(self):
        self.setHtml(DEFAULT_HTML)
        logging.info("Authenticating with host: %s" % self.auth_url.toString())
        qApp.setOverrideCursor(Qt.WaitCursor)
        self.auth_session_page.setUrl(QUrl(self.auth_url.toString() + "/authn/preauth"))

    def logout(self):
        logging.info("Logging out of host: %s" % self.auth_url.toString())
        self._timer.stop()
        self._session.delete(self.auth_url.toString() + "/authn/session")
        self.page().profile().cookieStore().deleteAllCookies()
        self.page().profile().clearHttpCache()
        self.auth_session_page.profile().cookieStore().deleteAllCookies()
        self.auth_session_page.profile().clearHttpCache()
        globus_logout = QWebEnginePage(self)
        globus_logout.setUrl(QUrl("https://www.globusid.org/logout"))
        self.authenticated = False

    def setSuccessCallback(self, callback=None):
        self._success_callback = callback

    def setStatus(self, message):
        if self.window().statusBar is not None:
            self.window().statusBar().showMessage(message)

    def onTimerFired(self):
        resp = self._session.put(self.auth_url.toString() + "/authn/session")
        logging.debug("webauthn session:\n%s\n", resp.json())

    def onAuthLoadFinished(self, result):
        qApp.restoreOverrideCursor()
        if not result:
            self.setPage(self.auth_session_page)
            return
        if self.auth_session_page.url().path() == "/authn/preauth":
            self.auth_session_page.toPlainText(self.onPreAuthContent)

    def onSessionContent(self, content):
        try:
            self.authn_session = json.loads(content)
            seconds_remaining = self.authn_session['seconds_remaining']
            if not self._timer.isActive():
                refresh = (seconds_remaining / 2) * 1000
                logging.info("Authentication successful: setting credential refresh interval to %d seconds." %
                             (seconds_remaining / 2))
                self._timer.start(refresh)
            logging.debug("webauthn session:\n%s\n", json.dumps(self.authn_session, indent=2))
            self.setHtml(SUCCESS_HTML)
            if self._success_callback:
                self._success_callback(credential=self.credential)
        except (ValueError, Exception) as e:
            logging.error(format_exception(e))
            self.setHtml(ERROR_HTML % content)

    def onPreAuthContent(self, content):
        try:
            preauth = json.loads(content)
            logging.debug("webauthn preauth:\n%s\n", json.dumps(preauth, indent=2))
            qApp.setOverrideCursor(Qt.WaitCursor)
            self.setUrl(QUrl(preauth["redirect_url"]))
        except (ValueError, Exception) as e:
            logging.error(format_exception(e))
            self.setHtml(ERROR_HTML % content)

    def onLoadFinished(self, result):
        qApp.restoreOverrideCursor()
        if self.url().path() == "/authn/session":
            self.page().toPlainText(self.onSessionContent)

    def onLoadProgress(self, progress):
        self.setStatus("Loading page: %s [%d%%]" % (self.url().host(), progress))

    def onCookieAdded(self, cookie):
        cookie_str = str(cookie.toRawForm(QNetworkCookie.NameAndValueOnly), encoding='utf-8')
        cookie_name = str(cookie.name(), encoding='utf-8')
        cookie_val = str(cookie.value(), encoding='utf-8')
        if cookie_name == self.authn_cookie_name:
            self.authenticated = True
            logging.debug("%s cookie added:\n\n%s\n\n" % (self.authn_cookie_name, cookie_str))
            self.credential["cookie"] = "%s=%s" % (self.authn_cookie_name, cookie_val)
            if self.credential_file:
                write_credential(self.credential_file, self.credential)
            self._session.cookies.set(self.authn_cookie_name, cookie_val, domain=self.auth_url.host(), path='/')
            qApp.setOverrideCursor(Qt.WaitCursor)
            self.auth_session_page.setUrl(QUrl(self.auth_url.toString() + "/authn/session"))

    def onCookieRemoved(self, cookie):
        cookie_str = str(cookie.toRawForm(QNetworkCookie.NameAndValueOnly), encoding='utf-8')
        cookie_name = str(cookie.name(), encoding='utf-8')
        if cookie_name == self.authn_cookie_name:
            logging.debug("%s cookie removed:\n\n%s\n\n" % (self.authn_cookie_name, cookie_str))

    def quitEvent(self):
        self.logout()






