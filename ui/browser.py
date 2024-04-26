"""
Copyright (C) 2020-Present CriticalElement

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU Affero General Public License as published
    by the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU Affero General Public License for more details.

    You should have received a copy of the GNU Affero General Public License
    along with this program at LICENSE.txt at the root of the source tree.
    If not, see <https://www.gnu.org/licenses/>.
"""

import typing
import keyring
import os

from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtNetwork import QNetworkCookie, QNetworkCookieJar
from PyQt5.QtWebEngineCore import *
from PyQt5.QtWebEngineWidgets import *
from PyQt5.QtWidgets import *
from appdirs import user_data_dir

from utils.uiutils import adjust_sizing, get_ratio, scale_images

sep = os.path.sep

data_dir = user_data_dir('SpotAlong', 'CriticalElement') + sep


class WebEngineUrlRequestInterceptor(QWebEngineUrlRequestInterceptor):
    """
        This will attempt to make sure that the "Remember me" option is checked, so that SpotAlong can save the cookie
        that is recieved for authentication for use in the SpotifyPlayer.
    """

    def __init__(self, webview, parent=None):
        super().__init__(parent)
        self.webview = webview

    def interceptRequest(self, info: QWebEngineUrlRequestInfo):
        url = info.requestUrl()
        if url.toString() == 'https://accounts.spotify.com/login/password':
            self.webview.page().runJavaScript('document.getElementById("login-remember").class = "ng-valid ng-dirty'
                                              ' ng-valid-parse ng-touched ng-not-empty";')


@adjust_sizing()
class Browser(QWidget):
    """
        This is the "wrapper" window for the browser used for Spotify login.
    """
    def __init__(self, url, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setWindowFlags(Qt.FramelessWindowHint)
        self.webview = QWebEngineView()  # noqa
        self.setObjectName("Form")
        self.resize(700, 800)
        scaled = ''
        ratio = get_ratio()
        if ratio != 1:
            icons = [f'24x24{sep}cil-window-restore', f'24x24{sep}cil-window-maximize',
                     f'16x16{sep}cil-size-grip', f'24x24{sep}cil-x', f'24x24{sep}cil-window-maximize', f'24x24{sep}cil-window-minimize']
            scale_images(icons, ratio)
            scaled = 'scaled'
        self.setStyleSheet("#Form {\n"
                           "    background-color: rgba(27, 29, 35, 200);\n"
                           "}\n"
                           "\n"
                           "QPushButton {\n"
                           "    background-color: transparent;\n"
                           "    border: none;\n"
                           "}\n"
                           "QPushButton:hover {\n"
                           "    background-color: rgb(64, 69, 80, 100);\n"
                           "}\n"
                           "QPushButton:pressed {\n"
                           "    background-color: rgb(33, 92, 255);\n"
                           "}")
        self.verticalLayout_2 = QVBoxLayout(self)
        self.verticalLayout_2.setContentsMargins(0, 0, 0, 0)
        self.verticalLayout_2.setSpacing(0)
        self.verticalLayout_2.setObjectName("verticalLayout_2")
        self.horizontalFrame = QFrame(self)
        self.horizontalFrame.setMinimumSize(QSize(0, 40))
        self.horizontalFrame.setMaximumSize(QSize(16777215, 40))
        self.horizontalFrame.setObjectName("horizontalFrame")
        self.horizontalLayout = QHBoxLayout(self.horizontalFrame)
        self.horizontalLayout.setContentsMargins(0, 0, 0, 0)
        self.horizontalLayout.setSpacing(0)
        self.horizontalLayout.setObjectName("horizontalLayout")
        self.label_2 = QLabel(self.horizontalFrame)
        self.label_2.setMinimumSize(QSize(40, 40))
        self.label_2.setMaximumSize(QSize(40, 40))
        self.label_2.setText("")
        self.label_2.setPixmap(QPixmap(data_dir + 'logo.ico').scaled(24 * ratio, 24 * ratio,
                                                                     transformMode=Qt.SmoothTransformation))  # noqa
        self.label_2.setAlignment(Qt.AlignHCenter | Qt.AlignVCenter)
        self.label_2.setObjectName("label_2")
        self.horizontalLayout.addWidget(self.label_2)
        self.label = QLabel(self.horizontalFrame)
        font = QFont()
        font.setFamily("Segoe UI")
        font.setPointSize(10)
        self.label.setFont(font)
        self.label.setStyleSheet("#label {\n"
                                 "    color: white;\n"
                                 "}")
        self.label.setObjectName("label")
        self.label.setText('SpotAlong - Login')
        self.setWindowTitle('SpotAlong - Login')
        self.horizontalLayout.addWidget(self.label)
        self.pushButton = QPushButton(self.horizontalFrame)
        self.pushButton.setMinimumSize(QSize(40, 40))
        self.pushButton.setMaximumSize(QSize(40, 40))
        self.pushButton.setText("")
        self.pushButton.setObjectName("pushButton")
        self.pushButton.setIcon(QIcon(data_dir + f'icons{sep}24x24{sep}cil-window-minimize{scaled}.png'))
        self.pushButton.clicked.connect(lambda: self.showMinimized())  # noqa
        self.horizontalLayout.addWidget(self.pushButton)
        self.pushButton_2 = QPushButton(self.horizontalFrame)
        self.pushButton_2.setMinimumSize(QSize(40, 40))
        self.pushButton_2.setMaximumSize(QSize(40, 40))
        self.pushButton_2.setText("")
        self.pushButton_2.setObjectName("pushButton_2")
        self.pushButton_2.setIcon(QIcon(data_dir + f'icons{sep}24x24{sep}cil-window-maximize{scaled}.png'))
        self.horizontalLayout.addWidget(self.pushButton_2)
        self.pushButton_3 = QPushButton(self.horizontalFrame)
        self.pushButton_3.setMinimumSize(QSize(40, 40))
        self.pushButton_3.setMaximumSize(QSize(40, 40))
        self.pushButton_3.setText("")
        self.pushButton_3.setObjectName("pushButton_3")
        self.pushButton_3.setIcon(QIcon(data_dir + f'icons{sep}24x24{sep}cil-x{scaled}.png'))
        self.pushButton_3.clicked.connect(lambda: (self.webview.page().deleteLater(), self.webview.deleteLater(),  # noqa
                                                   self.webview.page().profile().deleteLater(), self.close(),
                                                   self.deleteLater()))
        self.horizontalLayout.addWidget(self.pushButton_3)
        self.verticalLayout_2.addWidget(self.horizontalFrame)
        self.horizontalFrame_2 = QFrame(self)
        sizePolicy = QSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.horizontalFrame_2.sizePolicy().hasHeightForWidth())
        self.horizontalFrame_2.setSizePolicy(sizePolicy)
        self.horizontalFrame_2.setObjectName("horizontalFrame_2")
        self.horizontalLayout_2 = QHBoxLayout(self.horizontalFrame_2)
        self.horizontalLayout_2.setContentsMargins(0, 0, 0, 0)
        self.horizontalLayout_2.setSpacing(0)
        self.horizontalLayout_2.setObjectName("horizontalLayout_2")
        self.verticalFrame = QFrame(self.horizontalFrame_2)
        self.verticalFrame.setObjectName("verticalFrame")
        self.verticalLayout = QVBoxLayout(self.verticalFrame)
        self.verticalLayout.setContentsMargins(0, 0, 0, 0)
        self.verticalLayout.setSpacing(0)
        self.verticalLayout.setObjectName("verticalLayout")
        self.verticalLayout.addWidget(self.webview)
        self.horizontalFrame1 = QFrame(self.verticalFrame)
        self.horizontalFrame1.setMinimumSize(QSize(0, 30))
        self.horizontalFrame1.setMaximumSize(QSize(16777215, 30))
        self.horizontalFrame1.setObjectName("horizontalFrame1")
        self.horizontalLayout_3 = QHBoxLayout(self.horizontalFrame1)
        self.horizontalLayout_3.setObjectName("horizontalLayout_3")
        spacerItem = QSpacerItem(40, 20, QSizePolicy.Expanding, QSizePolicy.Minimum)
        self.horizontalLayout_3.addItem(spacerItem)
        self.verticalLayout.addWidget(self.horizontalFrame1)
        self.horizontalLayout_2.addWidget(self.verticalFrame)
        self.verticalLayout_2.addWidget(self.horizontalFrame_2)
        self.sizegrip = QSizeGrip(self.horizontalFrame1)
        self.sizegrip.setFixedSize(30, 30)
        self.sizegrip.setStyleSheet(f'''background-image: url({user_data_dir}icons/16x16/cil-size-grip{scaled}.png);
                                        background-position: right bottom;
                                        background-repeat: no-repeat;''')
        self.horizontalLayout_3.addWidget(self.sizegrip)
        self.horizontalLayout_3.setSpacing(0)
        self.horizontalLayout_3.setContentsMargins(0, 0, 0, 0)

        self.oldpos = QPoint(0, 0)

        def mousePressEvent(event):
            self.oldpos = event.globalPos()

        def mouseMoveEvent(event):
            if isinstance(self.oldpos, QPoint):
                delta = QPoint(event.globalPos() - self.oldpos)
                self.move(self.x() + delta.x(), self.y() + delta.y())
                self.oldpos = event.globalPos()

        self.label.mousePressEvent = mousePressEvent
        self.label.mouseMoveEvent = mouseMoveEvent

        def maximizeCheck(_=None):
            if self.isMaximized():
                self.showNormal()
                self.pushButton_2.setIcon(QIcon(data_dir + f'icons{sep}24x24{sep}cil-window-maximize{scaled}.png'))
            else:
                self.showMaximized()
                self.pushButton_2.setIcon(QIcon(data_dir + f'icons{sep}24x24{sep}cil-window-restore{scaled}.png'))

        self.pushButton_2.clicked.connect(maximizeCheck)  # noqa
        self.label.mouseDoubleClickEvent = maximizeCheck

        self.interceptor = WebEngineUrlRequestInterceptor(self.webview)
        self.spotifyplayer = None
        profile = QWebEngineProfile(self.webview)
        cookie_store = profile.cookieStore()
        cookie_store.cookieAdded.connect(self.onCookieAdded)
        profile.settings().setAttribute(QWebEngineSettings.WebAttribute.JavascriptCanPaste, True)
        profile.settings().setAttribute(QWebEngineSettings.WebAttribute.JavascriptCanAccessClipboard, True)
        self.cookies: typing.List[QNetworkCookie] = []
        webpage = QWebEnginePage(profile, self.webview)
        self.webview.setPage(webpage)
        self.cookiejar = QNetworkCookieJar()
        self.cookiejar.setAllCookies(self.cookies)
        self.webview.page().profile().setUrlRequestInterceptor(self.interceptor)
        self.webview.page().profile().setHttpUserAgent('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
                                                       '(KHTML, like Gecko) QtWebEngine/5.15.6 '
                                                       'Chrome/83.0.4103.122 Safari/537.36')
        self.webview.load(QUrl(url))

    def onCookieAdded(self, cookie):
        for c in self.cookies:
            if c.hasSameIdentifier(cookie):
                return
        qcookie = QNetworkCookie(cookie)
        if 'spotify.com' not in qcookie.domain():
            return
        self.cookies.append(qcookie)
        self.tostring()

    def tostring(self):
        if bytearray(self.cookies[-1].name()).decode() == 'sp_key':
            cookie = ' '.join([bytearray(cookie.toRawForm()).decode().split(';')[0] + ';' for cookie in self.cookies])
            keyring.set_password('SpotAlong', 'cookie', cookie)  # I could do a better job obfuscating this, but since
            # the code is open source it won't stop anyone who really wants to steal the cookie


if __name__ == '__main__':
    app = QApplication([])
    browser = Browser('http://localhost:8000')
    browser.show()
    app.exec_()
