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

import json
import time
import os
import logging
from threading import Thread
from zipfile import ZipFile

from PyQt5 import QtWidgets, QtCore, QtGui
from appdirs import user_data_dir

from app import MainUI
from utils.login import *
from ui.browser import Browser
from utils.constants import REGULAR_BASE, VERSION
from utils.uiutils import DpiFont, adjust_sizing, get_ratio, scale_one


QtGui.QFont = DpiFont

data_dir = user_data_dir('SpotAlong', 'CriticalElement') + '\\'
forward_data_dir = data_dir.replace('\\', '/')


logger = logging.getLogger(__name__)


@adjust_sizing()
class LoggingInUi(QtWidgets.QMainWindow):
    """
        This is a QMainWindow that represents the very first logging in window that the user will see.
        This window can also be configured for first time use, where the default files will be extracted.
    """
    def __init__(self, starting=None, user_func=None, placeholder=False, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.starting = starting
        self.user_func = user_func
        self.loadingscreen = None
        self.loginscreen = None
        self.setWindowFlags(QtCore.Qt.FramelessWindowHint)
        self.setObjectName("MainWindow")
        self.resize(433, 500)
        self.showNormal()
        self.centralwidget = QtWidgets.QWidget(self)
        self.centralwidget.setStyleSheet("background-color: rgb(44, 49, 60);")
        self.centralwidget.setObjectName("centralwidget")
        self.verticalFrame = QtWidgets.QFrame(self.centralwidget)
        self.verticalFrame.setGeometry(QtCore.QRect(0, 0, 431, 501))
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.verticalFrame.sizePolicy().hasHeightForWidth())
        self.verticalFrame.setSizePolicy(sizePolicy)
        self.verticalFrame.setMinimumSize(QtCore.QSize(0, 0))
        self.verticalFrame.setObjectName("verticalFrame")
        self.verticalLayout_2 = QtWidgets.QVBoxLayout(self.verticalFrame)
        self.verticalLayout_2.setSpacing(30)
        self.verticalLayout_2.setObjectName("verticalLayout_2")
        self.label = QtWidgets.QLabel(self.verticalFrame)
        font = QtGui.QFont()
        font.setFamily("Segoe UI Light")
        font.setPointSize(26)
        self.label.setFont(font)
        self.label.setStyleSheet("color: white;")
        self.label.setAlignment(QtCore.Qt.AlignBottom | QtCore.Qt.AlignHCenter)
        self.label.setObjectName("label")
        self.label.setText('Spot<strong>Along</strong>')
        self.verticalLayout_2.addWidget(self.label)
        self.label_2 = QtWidgets.QLabel(self.verticalFrame)
        font = QtGui.QFont()
        font.setFamily("Segoe UI Semilight")
        font.setPointSize(14)
        font.setBold(False)
        font.setItalic(True)
        font.setWeight(50)
        self.label_2.setFont(font)
        self.label_2.setStyleSheet("color: white;")
        self.label_2.setAlignment(QtCore.Qt.AlignCenter)
        self.label_2.setObjectName("label_2")
        self.label_2.setText('Logging in...')
        self.verticalLayout_2.addWidget(self.label_2)
        self.setCentralWidget(self.centralwidget)
        if not placeholder:
            self.timer = QtCore.QTimer()
            self.timer.setInterval(100)

            def auth_checker():
                if time.time() - self.start_time > 15:
                    # timeout
                    self.error_callback('Timeout')
                if starting.get('first'):
                    self.start_loading_screen()
                elif starting.get('second'):
                    self.start_login_screen()

            self.start_time = time.time()
            self.timer.timeout.connect(auth_checker)
            QtCore.QTimer().singleShot(1000, self.timer.start)
        else:
            self.worker = DefaultFilesExtractor()
            self.worker.emitter.connect(lambda _: self.close())  # noqa
            self.worker.start()
        self.runner = None

    def start_loading_screen(self):
        self.timer.stop()
        self.hide()
        self.close()
        self.loadingscreen = LoadingScreenUi(self.starting)
        user_func = self.user_func
        starting = self.starting
        loadingscreen = self.loadingscreen

        class Runner(QtCore.QThread):
            emitter = QtCore.pyqtSignal(tuple)

            def __init__(self, *args, **kwargs):
                super(Runner, self).__init__(*args, **kwargs)

            def run(self):
                user_func(starting['first'], loadingscreen, self)
                return

        self.runner = Runner()

        def call(arg):
            self.error_callback(arg[0], arg[1])

        self.runner.emitter.connect(call)
        self.runner.start()

    def error_callback(self, msg, cb=None):
        """
            Handle the various possible errors that could occur during authorization.
        """
        if msg == 'Spotify server error':
            error = QtWidgets.QMessageBox()
            error.setWindowTitle('An error occured!')
            error.setText('An error occured with the Spotify servers during authorization. '
                          'Try again after a few minutes, and the problem should be resolved (if Spotify '
                          'fixes it).')
            error.setIcon(QtWidgets.QMessageBox.Critical)
            error.exec_()
        elif msg == 'Duplicate session detected':
            error = QtWidgets.QMessageBox()
            error.setWindowTitle('An error occured!')
            error.setText('You are already connected to SpotAlong on another device/client. SpotAlong does not yet '
                          'support multiple instances of the same user being connected. '
                          'Close the other instance and try again.')
            error.setIcon(QtWidgets.QMessageBox.Critical)
            error.exec_()
        elif msg == 'Outdated version':
            error = QtWidgets.QMessageBox()
            error.setWindowTitle('An error occured!')
            error.setText('You are on an outdated version of SpotAlong. Consider updating to the newest version at '
                          f'{REGULAR_BASE}.')
            error.setIcon(QtWidgets.QMessageBox.Critical)
            error.exec_()
        elif msg == 'Timeout':
            error = QtWidgets.QMessageBox()
            error.setWindowTitle('An error occured!')
            error.setText('Unable to connect to the SpotAlong servers. Please check your internet / firewall settings, '
                          'and try again later.')
            error.setIcon(QtWidgets.QMessageBox.Critical)
            error.exec_()
        try:
            assert cb
            cb()
        except:  # noqa
            self.loadingscreen.close() if self.loadingscreen else None  # this is a dumb workaround
            self.starting.update({'second': 1})
            QtWidgets.QApplication.setQuitOnLastWindowClosed(True)
            QtWidgets.QApplication.exit(-4)
            return

    def start_login_screen(self):
        self.timer.stop()
        self.loginscreen = LoginUi(self.starting, self.user_func)
        self.loginscreen.show()
        self.close()

    def showEvent(self, a0: QtGui.QShowEvent) -> None:
        QtWidgets.QWidget.showEvent(self, a0)
        self.raise_()
        self.activateWindow()
        self.showNormal()


@adjust_sizing()
class LoadingScreenUi(QtWidgets.QMainWindow):
    """
        This is a QMainWindow that represents the main progress bar that a user will see after the initial logging in
        screen.
    """
    def __init__(self, starting, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.starting = starting
        self.main_window = None
        self.setWindowFlags(QtCore.Qt.FramelessWindowHint)
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        self.setObjectName("MainWindow")
        self.resize(819, 479)
        self.setStyleSheet("border-radius: 10px;")
        self.centralwidget = QtWidgets.QWidget(self)
        self.centralwidget.setStyleSheet("""#centralwidget {
        border-image: url(%ssplash/forest.png) 0 0 0 0 stretch stretch;
        background-position: center;
        }""" % forward_data_dir)
        self.centralwidget.setObjectName("centralwidget")
        self.label = QtWidgets.QLabel(self.centralwidget)
        self.label.setGeometry(QtCore.QRect(60, 40, 321, 81))
        font = QtGui.QFont()
        font.setFamily("Segoe UI Semilight")
        font.setPointSize(28)
        self.label.setFont(font)
        self.label.setStyleSheet("border-image: none;\n"
                                 "background: transparent;")
        self.label.setObjectName("label")
        self.label_2 = QtWidgets.QLabel(self.centralwidget)
        self.label_2.setGeometry(QtCore.QRect(580, 440, 211, 21))
        font = QtGui.QFont()
        font.setFamily("Segoe UI Semilight")
        font.setPointSize(10)
        self.label_2.setFont(font)
        self.label_2.setStyleSheet("border-image: none;\n"
                                   "background: transparent;\n"
                                   "color: white;")
        self.label_2.setObjectName("label_2")
        self.progressBar = QtWidgets.QProgressBar(self.centralwidget)
        self.progressBar.setGeometry(QtCore.QRect(60, 290, 691, 31))
        font = QtGui.QFont()
        font.setFamily("Segoe UI")
        font.setPointSize(12)
        self.progressBar.setFont(font)
        scaled = ''
        ratio = get_ratio()
        if ratio != 1:
            scale_one(f'{forward_data_dir}splash\\forest-slice', ratio)
            scaled = 'scaled'
        self.progressBar.setStyleSheet("QProgressBar {\n"
                                       "    background-color: rgba(120, 120, 120, 150);\n"
                                       "    color: white;\n"
                                       "    border-radius: 10px;\n"
                                       "    text-align: center;\n"
                                       "    border-image: none;\n"
                                       "}\n"
                                       "\n"
                                       "QProgressBar::chunk {\n"
                                       "    border-radius: 10px;\n"
                                       "    border: 1px solid white;\n"
                                       f"    background-image: url({forward_data_dir}splash/forest-slice{scaled}.png);"
                                       "\n    background-position: center left;\n"
                                       "background-color: transparent;"
                                        
                                       "}")
        self.progressBar.setValue(0)
        self.progressBar.setObjectName("progressBar")
        self.label_3 = QtWidgets.QLabel(self.centralwidget)
        self.label_3.setGeometry(QtCore.QRect(310, 220, 181, 51))
        font = QtGui.QFont()
        font.setFamily("Segoe UI Semilight")
        font.setPointSize(12)
        font.setItalic(True)
        self.label_3.setFont(font)
        self.label_3.setStyleSheet("border-image: none;\n"
                                   "color: white;")
        self.label_3.setAlignment(QtCore.Qt.AlignBottom | QtCore.Qt.AlignHCenter)
        self.label_3.setObjectName("label_3")
        self.label_4 = QtWidgets.QLabel(self.centralwidget)
        self.label_4.setGeometry(QtCore.QRect(30, 440, 400, 21))
        font = QtGui.QFont()
        font.setFamily("Segoe UI Semilight")
        font.setPointSize(10)
        self.label_4.setFont(font)
        self.label_4.setStyleSheet("border-image: none;\n"
                                   "color: white;")
        self.label_4.setObjectName("label_4")
        self.setCentralWidget(self.centralwidget)
        self.label.setText('SpotAlong')
        self.label_2.setText('Vlad Bagacian on Unsplash')
        self.label_3.setText('Loading...')
        self.label_4.setText(f'Copyright © 2020-{time.gmtime().tm_year} CriticalElement')
        self.show()
        self.timer = QtCore.QTimer()
        self.timer.setInterval(100)

        def runner():
            if starting.get('third'):
                self.timer.stop()
                self.start_main_window()
            else:
                QtCore.QCoreApplication.processEvents()

        self.timer.timeout.connect(runner)
        self.timer.start()

    def start_main_window(self):
        """
            Try to create and show MainUI, and handle possible errors.
        """
        try:
            if not os.path.isdir(data_dir):
                os.makedirs(data_dir)

            with open(data_dir + 'config.json', 'r') as f:
                load = json.load(f)
                ui_accent_color = tuple(load['accent_color'])
                ui_window_transparency = load['window_transparency']
                ui_cache_maxsize = load['album_cache_maxsize']
            f.close()
        except Exception as exc:
            if self.starting.get('previous_exit_code') == 3:
                self.exit_with_fatal_error(
                    'A fatal error occured and reinstall is most likely required: ', exc,
                    'SpotAlong could not access critical files needed even after attempting to re-make the '
                    'files, possibly due to file corruption / deletion. Consider reinstalling SpotAlong to resolve '
                    'this issue.', -3)
                return
            logger.critical('An error occured while trying to access critical files, attempting to re-make the files: ',
                            exc_info=exc)
            client = self.starting['third']
            client.disconnected = True
            if client.spotifyplayer:
                client.spotifyplayer.disconnect()
            client.client.disconnect()
            self.starting.clear()
            QtWidgets.QApplication.setQuitOnLastWindowClosed(True)
            QtWidgets.QApplication.exit(3)
            return
        try:
            self.main_window = MainUI(ui_accent_color, ui_window_transparency, ui_cache_maxsize,
                                      self.starting['third'], self.progressBar)
            self.main_window.failure_combo_box_changed = time.time()
            self.main_window.comboBox.setCurrentIndex(self.starting['third'].song_broadcast)
            self.hide()
            self.main_window.show()
            self.main_window.setWindowTitle('Home')
        except Exception as exc:
            self.exit_with_fatal_error('A fatal error has occured, exiting: ', exc,
                                       f'An unexpected error has occured, and the application has to be exited. '
                                       f'Consider viewing the logs at {data_dir}spotalong.log.', -4)
            return

        self.close()

    def showEvent(self, a0: QtGui.QShowEvent) -> None:
        QtWidgets.QWidget.showEvent(self, a0)
        self.raise_()
        self.activateWindow()
        self.showNormal()

    def exit_with_fatal_error(self, log, exc, error_popup, code):
        """
            Helper function that will exit the app by showing a fatal error message.
        """
        try:
            client = self.starting['third']
            client.disconnected = True
            if client.spotifyplayer:
                client.spotifyplayer.disconnect()
            client.client.disconnect()
        except Exception:  # noqa
            pass  # I don't care at this point
        logger.fatal(log, exc_info=exc)
        error = QtWidgets.QMessageBox()
        error.setWindowTitle('A fatal error occured.')
        error.setText(error_popup)
        error.setIcon(QtWidgets.QMessageBox.Critical)
        error.exec_()
        self.starting.clear()
        QtWidgets.QApplication.setQuitOnLastWindowClosed(True)
        QtWidgets.QApplication.exit(code)


@adjust_sizing()
class LoginUi(QtWidgets.QMainWindow):
    """
        This QMainWindow is the window used by users to log into their Spotify accounts through the app.
    """
    def __init__(self, starting, user_func, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.starting = starting
        self.user_func = user_func
        self.setWindowFlag(QtCore.Qt.FramelessWindowHint)
        self.setObjectName("MainWindow")
        self.resize(465, 625)
        self.centralwidget = QtWidgets.QWidget(self)
        self.centralwidget.setStyleSheet("QWidget {\n"
                                         "background-color: rgb(44, 49, 60);\n"
                                         "}")
        self.centralwidget.setObjectName("centralwidget")
        self.verticalLayout_2 = QtWidgets.QVBoxLayout(self.centralwidget)
        self.verticalLayout_2.setContentsMargins(0, 0, 0, 0)
        self.verticalLayout_2.setSpacing(0)
        self.verticalLayout_2.setObjectName("verticalLayout_2")
        self.verticalFrame = QtWidgets.QFrame(self.centralwidget)
        self.verticalFrame.setObjectName("verticalFrame")
        self.verticalLayout = QtWidgets.QVBoxLayout(self.verticalFrame)
        self.verticalLayout.setSpacing(14)
        self.verticalLayout.setObjectName("verticalLayout")
        self.label = QtWidgets.QLabel(self.verticalFrame)
        self.label.setMinimumSize(QtCore.QSize(0, 100))
        self.label.setMaximumSize(QtCore.QSize(16777215, 100))
        font = QtGui.QFont()
        font.setFamily("Segoe UI Light")
        font.setPointSize(20)
        self.label.setFont(font)
        self.label.setStyleSheet("color: white;")
        self.label.setAlignment(QtCore.Qt.AlignCenter)
        self.label.setObjectName("label")
        self.verticalLayout.addWidget(self.label)
        self.horizontalFrame = QtWidgets.QFrame(self.verticalFrame)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.horizontalFrame.sizePolicy().hasHeightForWidth())
        self.horizontalFrame.setSizePolicy(sizePolicy)
        self.horizontalFrame.setMinimumSize(QtCore.QSize(0, 80))
        self.horizontalFrame.setObjectName("horizontalFrame")
        self.horizontalLayout_2 = QtWidgets.QHBoxLayout(self.horizontalFrame)
        self.horizontalLayout_2.setObjectName("horizontalLayout_2")
        self.pushButton = QtWidgets.QPushButton(self.horizontalFrame)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.pushButton.sizePolicy().hasHeightForWidth())
        self.pushButton.setSizePolicy(sizePolicy)
        self.pushButton.setMinimumSize(QtCore.QSize(220, 68))
        self.pushButton.setMaximumSize(QtCore.QSize(220, 68))
        font = QtGui.QFont()
        font.setFamily("Segoe UI")
        font.setPointSize(10)
        self.pushButton.setFont(font)
        self.pushButton.setContextMenuPolicy(QtCore.Qt.NoContextMenu)
        self.pushButton.setLayoutDirection(QtCore.Qt.LeftToRight)
        scaled = ''
        ratio = get_ratio()
        if ratio != 1:
            ratio = ratio * 0.8  # padding
            scale_one(f'{forward_data_dir}Spotify_Icon_RGB_Black', ratio)
            scaled = 'scaled'
        self.pushButton.setStyleSheet("QPushButton {\n"
                                      "    border: 3px solid darkgreen;\n"
                                      "    border-radius: 15px;\n"
                                      "    background-color: rgb(29, 185, 84);\n"
                                      f"    background-image: url({forward_data_dir}Spotify_Icon_RGB_Black{scaled}.png)"
                                      f";\n"
                                      "    background-repeat: no-repeat;\n"
                                      "    background-position: right center;\n"
                                      "}"
                                      "QPushButton::hover {"
                                      "    background-color: rgb(49, 205, 104);"
                                      "}"
                                      "QPushButton::pressed {"
                                      "    background-color: rgb(69, 225, 124);"
                                      "}")
        self.pushButton.setObjectName("pushButton")
        self.horizontalLayout_2.addWidget(self.pushButton)
        self.verticalLayout.addWidget(self.horizontalFrame)
        self.label_3 = QtWidgets.QLabel(self.verticalFrame)
        self.label_3.setMinimumSize(QtCore.QSize(0, 60))
        font = QtGui.QFont()
        font.setFamily("Segoe UI Semilight")
        font.setPointSize(12)
        self.label_3.setFont(font)
        self.label_3.setStyleSheet("color: white;")
        self.label_3.setAlignment(QtCore.Qt.AlignCenter)
        self.label_3.setObjectName("label_3")
        self.verticalLayout.addWidget(self.label_3)
        self.horizontalFrame1 = QtWidgets.QFrame(self.verticalFrame)
        self.horizontalFrame1.setMinimumSize(QtCore.QSize(0, 0))
        self.horizontalFrame1.setMaximumSize(QtCore.QSize(16777215, 16777215))
        self.horizontalFrame1.setObjectName("horizontalFrame1")
        self.horizontalLayout_3 = QtWidgets.QHBoxLayout(self.horizontalFrame1)
        self.horizontalLayout_3.setSpacing(0)
        self.horizontalLayout_3.setObjectName("horizontalLayout_3")
        self.lineEdit = QtWidgets.QLineEdit(self.horizontalFrame1)
        self.lineEdit.setMinimumSize(QtCore.QSize(300, 150))
        self.lineEdit.setMaximumSize(QtCore.QSize(300, 150))
        font = QtGui.QFont()
        font.setFamily("Segoe UI")
        font.setPointSize(22)
        font.setBold(False)
        font.setWeight(50)
        font.setLetterSpacing(QtGui.QFont.AbsoluteSpacing, 10)
        self.lineEdit.setFont(font)
        self.lineEdit.setCursor(QtGui.QCursor(QtCore.Qt.IBeamCursor))
        self.lineEdit.setStyleSheet("QLineEdit { \n"
                                    "    border-radius: 20px;\n"
                                    "    border: 4px solid rgb(20, 35, 255);\n"
                                    "    background: rgb(33, 92, 255);\n"
                                    "    color: white;\n"
                                    "}")
        self.lineEdit.setMaxLength(6)
        self.lineEdit.setAlignment(QtCore.Qt.AlignCenter)
        self.lineEdit.setPlaceholderText('______')
        self.lineEdit.setObjectName("lineEdit")
        self.lineEdit.setValidator(QtGui.QIntValidator(0, 999999))
        self.horizontalLayout_3.addWidget(self.lineEdit)
        self.verticalLayout.addWidget(self.horizontalFrame1)
        self.horizontalFrame2 = QtWidgets.QFrame(self.verticalFrame)
        self.horizontalFrame2.setMinimumSize(QtCore.QSize(0, 50))
        self.horizontalFrame2.setMaximumSize(QtCore.QSize(16777215, 50))
        self.horizontalFrame2.setObjectName("horizontalFrame2")
        self.horizontalLayout_4 = QtWidgets.QHBoxLayout(self.horizontalFrame2)
        self.horizontalLayout_4.setObjectName("horizontalLayout_4")
        self.pushButton_2 = QtWidgets.QPushButton(self.horizontalFrame2)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Expanding)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.pushButton_2.sizePolicy().hasHeightForWidth())
        self.pushButton_2.setSizePolicy(sizePolicy)
        self.pushButton_2.setMinimumSize(QtCore.QSize(100, 37))
        self.pushButton_2.setMaximumSize(QtCore.QSize(100, 16777215))
        font = QtGui.QFont()
        font.setFamily("Segoe UI")
        font.setPointSize(9)
        self.pushButton_2.setFont(font)
        self.pushButton_2.setStyleSheet("QPushButton {\n"
                                        "    border: 3px solid darkgreen;\n"
                                        "    border-radius: 10px;\n"
                                        "    background: rgb(29, 185, 84);\n"
                                        "}"
                                        "QPushButton::hover {"
                                        "    background-color: rgb(49, 205, 104);"
                                        "}"
                                        "QPushButton::pressed {"
                                        "    background-color: rgb(69, 225, 124);"
                                        "}")
        self.pushButton_2.setObjectName("pushButton_2")
        self.horizontalLayout_4.addWidget(self.pushButton_2)
        self.verticalLayout.addWidget(self.horizontalFrame2)
        self.label_2 = QtWidgets.QLabel(self.verticalFrame)
        font = QtGui.QFont()
        font.setFamily("Segoe UI Semilight")
        font.setPointSize(10)
        self.label_2.setFont(font)
        self.label_2.setStyleSheet("color: red;")
        self.label_2.setText("")
        self.label_2.setAlignment(QtCore.Qt.AlignCenter)
        self.label_2.setObjectName("label_2")
        self.verticalLayout.addWidget(self.label_2)
        self.verticalLayout_2.addWidget(self.verticalFrame)
        self.horizontalFrame3 = QtWidgets.QFrame(self.centralwidget)
        self.horizontalFrame3.setMaximumSize(QtCore.QSize(16777215, 50))
        self.horizontalFrame3.setObjectName("horizontalFrame3")
        self.horizontalLayout = QtWidgets.QHBoxLayout(self.horizontalFrame3)
        self.horizontalLayout.setContentsMargins(5, 5, 5, 5)
        self.horizontalLayout.setSpacing(0)
        self.horizontalLayout.setObjectName("horizontalLayout")
        self.label_4 = QtWidgets.QLabel(self.horizontalFrame3)
        font = QtGui.QFont()
        font.setFamily("Segoe UI")
        font.setPointSize(8)
        self.label_4.setFont(font)
        self.label_4.setStyleSheet("color: white;")
        self.label_4.setObjectName("label_4")
        self.pushButton_3 = QtWidgets.QPushButton(self)
        self.pushButton_3.setFixedSize(50, 50)
        self.pushButton_3.setStyleSheet('''
            QPushButton {
                background-color: rgb(44, 49, 60);
                background-image: url(%sicons/24x24/cil-x.png);
                background-repeat: no-repeat;
                background-position: center;
                border: none;
            }
            QPushButton::hover {
                background-color: rgb(64, 69, 80);
            }
            QPushButton::pressed {
                background-color: rgb(33, 92, 255);
            }''' % forward_data_dir)
        self.pushButton_3.move(415, 0)

        def exit_():
            starting.pop('second', None)
            if self.browser:
                del self.browser.webview
            QtWidgets.QApplication.setQuitOnLastWindowClosed(True)
            self.close()
            QtWidgets.QApplication.exit(0)

        self.pushButton_3.clicked.connect(exit_)
        self.horizontalLayout.addWidget(self.label_4)
        self.verticalLayout_2.addWidget(self.horizontalFrame3)
        self.setCentralWidget(self.centralwidget)
        self.label.setText('SpotAlong')
        self.pushButton.setText('Login with Spotify           ')
        self.label_3.setText('After logging in, you will be given a code. \nEnter that code here:')
        self.pushButton_2.setText('Verify Code')
        self.label_4.setText(f'v{VERSION}')
        self.browser = None

        def callback(auth_url, _):
            nonlocal emitter
            if auth_url == 'Failed':
                self.label_2.setText('Could not connect to the server.')
                emitter = []
                self.pushButton.setDisabled(False)
                self.label_2.setText('')
                return
            elif auth_url == 'Login':
                self.timer.stop()
                self.close()
                QtWidgets.QApplication.setQuitOnLastWindowClosed(True)
                QtWidgets.QApplication.exit(1)
                return
            self.browser = Browser(auth_url)
            self.browser.show()
            self.pushButton.setDisabled(False)
            self.label_2.setText('')
            emitter = []

        emitter = []
        self.pushButton.clicked.connect(lambda: (Thread(target=create_user, args=(emitter,)).start(),  # noqa
                                                 self.label_2.setText('Loading...'),
                                                 self.pushButton.setDisabled(True)))
        self.timer = QtCore.QTimer()
        self.timer.setInterval(250)
        self.timer.timeout.connect(lambda: callback(*emitter[0]) if emitter and emitter[0] is not False else None)
        self.timer.start()

        def verify_code():
            self.label_2.setText('')
            if len(self.lineEdit.text()) < 6:
                self.label_2.setText('The code must be 6 characters long.')
            else:
                self.label_2.setText('Loading...')
                code = redeem_code(self.lineEdit.text())
                if code != 'Failed' and code:
                    self.timer.stop()
                    self.close()
                    self.starting.clear()
                    QtWidgets.QApplication.setQuitOnLastWindowClosed(True)
                    QtWidgets.QApplication.exit(1)
                    return
                elif code == 'Failed':
                    self.label_2.setText('Could not connect to the server.')
                else:
                    self.label_2.setText('The code was invalid.')

        self.pushButton_2.clicked.connect(verify_code)


class DefaultFilesExtractor(QtCore.QThread):
    """
        This is a helper QThread that will attempt to extract all the default files required for SpotAlong to work.
    """

    emitter = QtCore.pyqtSignal(bool)

    def __init__(self, *args, **kwargs):
        super(DefaultFilesExtractor, self).__init__(*args, **kwargs)

    def run(self):
        try:
            with ZipFile('default_files.zip', 'r') as zipfile:
                for name in zipfile.namelist():
                    zipfile.extract(name, data_dir[:-1])
            time.sleep(2)
            self.emitter.emit(True)
        except Exception as exc:
            logger.critical('The default files were unable to be extracted: ', exc_info=exc)
            self.emitter.emit(False)
