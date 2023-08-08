"""
SpotAlong
~~~~~~~~~

Listen along to your friends in Spotify!

:copyright: (C) 2020-Present CriticalElement
:license: GNU AGPLv3, see LICENSE.txt for more details.

"""


__title__ = 'SpotAlong'
__author__ = 'CriticalElement'
__license__ = 'GNU AGPLv3'
__copyright__ = 'Copyright (C) 2020-Present CriticalElement'
__version__ = '1.0.0'


import io
import gc
import json
import logging
import os
import sys
import time
import re
import typing

import mainclient

if sys.version_info.major == 3 and sys.version_info.minor >= 10:
    import collections
    from _collections_abc import MutableMapping
    collections.MutableMapping = MutableMapping

from pathlib import Path
from threading import Thread
from shutil import copyfile

import keyring
import requests
import pyperclip
from PyQt5 import sip
from PyQt5 import QtCore, QtGui, QtWidgets
from appdirs import user_data_dir
from PIL import Image, ImageOps

import ui.customwidgets
import utils.utils
from utils.login import *
from mainclient import MainClient
from ui.mainui import UiMainWindow
from ui.customwidgets import *
from utils.uiutils import Runnable, limit_text_smart, DpiFont, adjust_sizing, adj_style, get_ratio, scale_images
from utils.constants import *


QtGui.QFont = DpiFont

data_dir = user_data_dir('SpotAlong', 'CriticalElement') + '\\'
forward_data_dir = data_dir.replace('\\', '/')

level = logging.INFO
if {'-d', '-v', '--debug', '--verbose'} & set(sys.argv):
    level = logging.DEBUG
formatter = logging.Formatter('%(asctime)s - %(levelname)-8s - %(name)-29s - %(message)s')
logging.basicConfig(level=level, format='%(asctime)s - %(levelname)-8s - %(name)-29s - %(message)s')
os.makedirs(data_dir, exist_ok=True)
filehandler = logging.FileHandler(f'{data_dir}spotalong.log', 'w', 'utf-8')
filehandler.setFormatter(formatter)
logging.getLogger().addHandler(filehandler)
logging_io = io.StringIO()
console = logging.StreamHandler(stream=logging_io)
console.setLevel(level)
console.setFormatter(formatter)
logging.getLogger().addHandler(console)
logging.getLogger().addHandler(mainclient.watcher)


def my_exception_hook(exctype, value, traceback):
    print(f'{exctype}, {value}, \n{traceback}')
    sys.__excepthook__(exctype, value, traceback)  # noqa
    sys.exit(1)


sys.excepthook = my_exception_hook


# speed enhancement
requests.packages.urllib3.util.connection.HAS_IPV6 = False  # noqa


@adjust_sizing()
class MainUI(UiMainWindow):
    """
        This is a class that combines the ui with all the frontend components / widgets.

        Parameters:
            accent_color: A tuple that represents the rgb value of the user's selected accent color.
            window_transparency: A float (0 - 1.0) that represents the transparency of the window.
            album_cache_maxsize: An int that represents the maximum size of the album cache before deletion (MB).
            client: The MainClient used for handling the SpotAlong server connection.
            progress_bar: The QProgressBar used in the loading screen.
    """
    def __init__(self, accent_color: tuple, window_transparency: float, album_cache_maxsize: int,
                 client: MainClient, progress_bar, *args: tuple, **kwargs: dict):
        UiMainWindow.__init__(self, *args, **kwargs)
        global app
        self.isInitialized = False
        self.isshown = False
        self.accent_color = accent_color
        self.client = client
        self.albumcachelimit = album_cache_maxsize
        self.devicelist = None
        self.active_dialog: typing.Optional[Dialog] = None
        self.animation_timer: typing.Optional[QtCore.QTimer] = None
        self.current_snack_bar: typing.Optional[SnackBar] = None
        self.setWindowFlags(QtCore.Qt.FramelessWindowHint | QtCore.Qt.Window | QtCore.Qt.WindowMinMaxButtonsHint)
        self.widgets_to_ignore = []
        app = QtCore.QCoreApplication.instance()
        self.setWindowOpacity(window_transparency)
        self.setupUi(self)
        self.retranslateUi(self)
        app.client = client
        client.ui = self
        ui.customwidgets.mainui = self
        utils.utils.ui = self
        self.listentofriends = ListeningToFriends()
        self.verticalLayout_38.addWidget(self.listentofriends)
        self.spotifylistener = None
        self.partiallisteningtofriends = PartialListeningToFriends()
        while not client.initialized:
            time.sleep(0.1)
        self.resize(1440, 850)
        self.setObjectName('SpotAlong')
        self.scaled = ''
        self.disconnected = False
        ratio = get_ratio()
        self.ratio = ratio
        if ratio != 1:
            icons = ['24x24\\cil-menu', '24x24\\cil-window-minimize', '24x24\\cil-window-maximize', '24x24\\cil-x',
                     '16x16\\cil-people', '16x16\\cil-history', '16x16\\cil-size-grip', '20x20\\cil-home',
                     '20x20\\cil-settings', '20x20\\cil-people', '20x20\\cil-user-follow', '20x20\\cil-headphones',
                     '20x20\\cil-user-follow-notif', '24x24\\cil-lock-locked', '24x24\\cil-exit-to-app',
                     '24x24\\cil-check-alt', '24x24\\cil-trash', '24x24\\cil-save', '24x24\\cil-terminal',
                     '16x16\\cil-arrow-bottom', '16x16\\cil-arrow-top', '24x24\\cil-window-restore']
            scale_images(icons, ratio)
            self.scaled = 'scaled'
        self.label_6.setText(f'v{VERSION}')
        self.label_5.setText(f'Copyright © 2020-{time.gmtime().tm_year} CriticalElement // Check me out on GitHub!')
        url = self.client.mainstatus.clientavatar
        if url is not None:
            img_data = requests.get(url, timeout=15).content
            with open(data_dir + f'icon{self.client.mainstatus.client_id}.png', 'wb') as handler:
                handler.write(img_data)
        else:
            image = Image.open(data_dir + 'default_user.png').resize((200, 200))
            image.save(data_dir + f'icon{self.client.mainstatus.client_id}.png')
        mask = Image.open(data_dir + 'mask.png').convert('L')
        mask = mask.resize((200, 200))
        im = Image.open(data_dir + f'icon{self.client.mainstatus.client_id}.png').convert('RGBA')
        output = ImageOps.fit(im, mask.size, centering=(0.5, 0.5))
        output.putalpha(mask)
        output.resize((200, 200))
        output.save(data_dir + f'icon{self.client.mainstatus.client_id}.png')
        self.pushButton.setIcon(QtGui.QIcon(data_dir + f'icons\\24x24\\cil-menu{self.scaled}.png'))
        self.pushButton.setIconSize(QtCore.QSize(48 * ratio, 48 * ratio))
        self.label_7.setPixmap(QtGui.QPixmap(data_dir + 'logo.ico').scaled
                               (24 * ratio, 24 * ratio, transformMode=QtCore.Qt.SmoothTransformation))
        self.label_7.setAlignment(QtCore.Qt.AlignHCenter | QtCore.Qt.AlignVCenter)
        self.pushButton_4.setIcon(QtGui.QIcon(data_dir + f'icons\\24x24\\cil-window-minimize{self.scaled}.png'))
        self.pushButton_4.tooltip = Tooltip('Minimize', self.pushButton_4)
        self.pushButton_4.setIconSize(QtCore.QSize(24 * ratio, 24 * ratio))
        self.pushButton_3.setIcon(QtGui.QIcon(data_dir + f'icons\\24x24\\cil-window-maximize{self.scaled}.png'))
        self.pushButton_3.tooltip = Tooltip('Maximize', self.pushButton_3)
        self.pushButton_3.setIconSize(QtCore.QSize(24 * ratio, 24 * ratio))
        self.pushButton_2.setIcon(QtGui.QIcon(data_dir + f'icons\\24x24\\cil-x{self.scaled}.png'))
        self.pushButton_2.setIconSize(QtCore.QSize(24 * ratio, 24 * ratio))
        self.pushButton_2.tooltip = Tooltip('Close', self.pushButton_2)
        self.pushButton_12.setIcon(QtGui.QIcon(data_dir + f'icons\\16x16\\cil-people{self.scaled}.png'))
        self.pushButton_12.tooltip = Tooltip('Show Friends List', self.pushButton_12)
        self.pushButton_13.setIcon(QtGui.QIcon(data_dir + f'icons\\16x16\\cil-history{self.scaled}.png'))
        self.pushButton_13.tooltip = Tooltip('Show Recent Friend Activity', self.pushButton_13)
        font = QtGui.QFont()
        font.setFamily("Segoe UI")
        font.setPointSize(7)
        self.label_top_info_2.setFont(font)
        self.label_6.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        self.frame.hide()
        self.frame = QtWidgets.QSizeGrip(self.bottomFrame_2)
        self.frame.setMinimumSize(QtCore.QSize(30, 0))
        self.frame.setMaximumSize(QtCore.QSize(30, 16777215))
        self.frame.setStyleSheet("QSizeGrip {\n"
                                 f"	background-image: url({forward_data_dir}icons/16x16/cil-size-grip"
                                 f"{self.scaled}.png);\n "
                                 "  background-size: 48px;\n"
                                 "	background-position: bottom right;\n"
                                 "	background-repeat: no-repeat;\n"
                                 "  width: 48px;\n"
                                 "  height: 48px;"
                                 "}\n")
        self.frame.setObjectName("frame")
        self.horizontalLayout_2.addWidget(self.frame)
        self.label_top_info_1.setText(f'Logged in as: {client.spotifyclient.clientUsername}')

        self.statuswidgets = {}  # start building the default components / widgets
        self.laststatuses = {}
        self.friendstatuswidgets = {}
        self.inboundfriendrequests = {}
        self.outboundfriendrequests = {}
        self.listeningfriendlist = {}
        self.onlinefriendlist = {}
        self.offlinefriendlist = {}
        self.advancedfriendstatuses = {}
        self.horizontalLayout_6.setAlignment(QtCore.Qt.AlignCenter)
        it = 1
        for id_, friend in client.friendstatus.items():
            skipiter = False
            if friend.playing_type not in ('None', 'ad', 'episode'):
                status = friend.playing_status.lower()
            else:
                status = 'online' if friend.playing_status == 'Online' else 'offline'

            def callbackfunc(wi):
                statuswi = wi.convert_to_widget()
                friendstatuswidget = wi.convert_to_secondary_widget()
                self.horizontalLayout_6.addWidget(statuswi)
                self.statuswidgets.update({friend.client_id: statuswi})
                self.verticalLayout_22.insertWidget(len(self.friendstatuswidgets), friendstatuswidget)
                self.friendstatuswidgets.update({friend.client_id: friendstatuswidget})

            widget = Runnable(lambda: PartialStatusWidget(status, friend.clientavatar, id_, friend.clientusername,
                                                          friend, client.friendstatus[id_], self.accent_color))
            widget.callback.connect(callbackfunc)
            widget.start()

            while len(self.friendstatuswidgets) != it:
                QtCore.QCoreApplication.processEvents()

            def callbackfunc(wi):
                nonlocal skipiter
                laststatuswidget = wi.convert_to_widget()
                if laststatuswidget:
                    self.verticalLayout_16.insertWidget(0, laststatuswidget)
                    self.laststatuses.update({id_: laststatuswidget})
                else:
                    skipiter = True

            widget = Runnable(lambda: PartialPastFriendStatus(friend))
            widget.callback.connect(callbackfunc)
            widget.start()
            progress_bar.setValue(60)

            while len(self.laststatuses) != it and not skipiter:
                QtCore.QCoreApplication.processEvents()

            def callbackfunc(wi):
                statuswi = wi.convert_to_widget()
                self.advanceduserstatus.addWidget(statuswi)
                self.advancedfriendstatuses.update({id_: statuswi})
                self.advanceduserstatus.addWidget(statuswi)
                self.advancedfriendstatuses.update({id_: statuswi})

            widget = Runnable(lambda: PartialAdvancedUserStatus(friend, status))
            widget.callback.connect(callbackfunc)
            widget.start()

            while len(self.advancedfriendstatuses) != it:
                QtCore.QCoreApplication.processEvents()

            it = it + 1

        self.scrollArea_3.verticalScrollBar().setFixedWidth(6)
        self.scrollArea_4.verticalScrollBar().setFixedWidth(6)
        self.scrollArea_3.setStyleSheet(self.scrollArea_3.styleSheet())
        self.horizontalFrame_4.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Preferred)
        listening_friends = [status for status in client.friendstatus.values() if status.playing_status == 'Listening']
        it = 1
        for friend in listening_friends:

            def callbackfunc(wi):
                statuswi = wi.convert_to_widget()
                self.verticalLayout_28.addWidget(statuswi)
                self.listeningfriendlist.update({friend.client_id: statuswi})

            widget = Runnable(lambda: PartialListedFriendStatus(friend, friend.playing_status.lower()))
            widget.callback.connect(callbackfunc)
            widget.start()

            while len(self.listeningfriendlist) != it:
                QtCore.QCoreApplication.processEvents()

            it = it + 1

        progress_bar.setValue(70)
        spacer = self.verticalLayout_28.itemAt(1)
        self.verticalLayout_28.removeItem(spacer)
        online_friends = [status for status in client.friendstatus.values() if status.playing_status == 'Online']
        it = 1
        for friend in online_friends:

            def callbackfunc(wi):
                statuswi = wi.convert_to_widget()
                self.verticalLayout_29.addWidget(statuswi)
                self.onlinefriendlist.update({friend.client_id: statuswi})

            widget = Runnable(lambda: PartialListedFriendStatus(friend, friend.playing_status.lower()))
            widget.callback.connect(callbackfunc)
            widget.start()

            while len(self.onlinefriendlist) != it:
                QtCore.QCoreApplication.processEvents()

            it = it + 1
        spacer = self.verticalLayout_29.itemAt(1)
        self.verticalLayout_29.removeItem(spacer)
        offline_friends = [status for status in client.friendstatus.values() if status.playing_status == 'Offline']
        it = 1
        for friend in offline_friends:

            def callbackfunc(wi):
                statuswi = wi.convert_to_widget()
                self.verticalLayout_30.addWidget(statuswi)
                self.offlinefriendlist.update({statuswi.user_id: statuswi})

            widget = Runnable(lambda: PartialListedFriendStatus(friend, friend.playing_status.lower()))
            widget.callback.connect(callbackfunc)
            widget.start()

            while len(self.offlinefriendlist) != it:
                QtCore.QCoreApplication.processEvents()

            it = it + 1
        spacer = self.verticalLayout_30.itemAt(1)
        self.verticalLayout_30.removeItem(spacer)
        self.verticalLayout_27.addItem(spacer)
        listening_friends, online_friends, offline_friends = (len(listening_friends), len(online_friends),
                                                              len(offline_friends))

        def sort_friend_history():
            historywidgets = self.laststatuses.values()
            historywidgets = sorted(historywidgets, key=lambda wi: wi.last_timestamp.timestamp(), reverse=True)
            historyindexes = self.laststatuses.values()
            for index in historyindexes:
                self.verticalLayout_16.removeWidget(index)
            for ix, wid in enumerate(historywidgets):
                self.verticalLayout_16.insertWidget(ix, wid)

        sort_friend_history()
        self.label_27.setText(f'Listening - {listening_friends}')
        self.label_28.setText(f'Online - {online_friends}')
        self.label_29.setText(f'Offline - {offline_friends}')
        listening_friends = f'{listening_friends} friend' if listening_friends == 1 else f'{listening_friends} friends'
        online_friends = f'{online_friends} friend' if online_friends == 1 else f'{online_friends} friends'
        offline_friends = f'{offline_friends} friend' if offline_friends == 1 else f'{offline_friends} friends'
        self.label_3.setText(
            f'<span style="color:rgb(29, 185, 84)">‎  {listening_friends} listening • </span>' 
            f'<span style="color:rgb(33, 92, 255)">{online_friends} online • </span>' 
            f'<span style="color:rgb(125, 125, 125)">{offline_friends} offline  </span>')
        self.label_3.setTextFormat(QtCore.Qt.RichText)
        font = QtGui.QFont()
        font.setFamily("Segoe UI")
        font.setPointSize(20)
        self.label_3.setFont(font)
        self.label_3.setFixedHeight(100)
        self.label_3.setWordWrap(True)
        progress_bar.setValue(80)

        self.horizontalLayout_6.setSpacing(2)
        self.pushButton_5.setStyleSheet('''QPushButton {
        background-image: url(%sicons/20x20/cil-home%s.png);
        background-position: left;
        background-repeat: no-repeat;
        border: none;
        border-left: 20px solid rgb(27, 29, 35);
        background-color: rgb(27, 29, 35);
        text-align: left;
        padding-left: 45px;
    }
    QPushButton:hover {
        background-color: rgb(33, 37, 43);
        border-left: 20px solid rgb(33, 37, 43);
    }
    QPushButton:pressed {
        background-color: rgb(85, 170, 255);
        border-left: 20px solid rgb(85, 170, 255);
    }''' % (forward_data_dir, self.scaled))
        self.pushButton_6.setStyleSheet('''QPushButton {
                background-image: url(%sicons/20x20/cil-settings%s.png);
                background-position: left;
                background-repeat: no-repeat;
                border: none;
                border-left: 20px solid rgb(27, 29, 35);
                background-color: rgb(27, 29, 35);
                text-align: left;
                padding-left: 45px;
            }
            QPushButton:hover {
                background-color: rgb(33, 37, 43);
                border-left: 20px solid rgb(33, 37, 43);
            }
            QPushButton:pressed {
                background-color: rgb(85, 170, 255);
                border-left: 20px solid rgb(85, 170, 255);
            }''' % (forward_data_dir, self.scaled))
        self.pushButton_14.setStyleSheet('''QPushButton {
                        background-image: url(%sicons/20x20/cil-people%s.png);
                        background-position: left;
                        background-repeat: no-repeat;
                        border: none;
                        border-left: 20px solid rgb(27, 29, 35);
                        background-color: rgb(27, 29, 35);
                        text-align: left;
                        padding-left: 45px;
                    }
                    QPushButton:hover {
                        background-color: rgb(33, 37, 43);
                        border-left: 20px solid rgb(33, 37, 43);
                    }
                    QPushButton:pressed {
                        background-color: rgb(85, 170, 255);
                        border-left: 20px solid rgb(85, 170, 255);
                    }''' % (forward_data_dir, self.scaled))
        self.pushButton_11.setStyleSheet('''QPushButton {
                        background-image: url(%sicons/20x20/cil-user-follow%s.png);
                        background-position: left;
                        background-repeat: no-repeat;
                        border: none;
                        border-left: 20px solid rgb(27, 29, 35);
                        background-color: rgb(27, 29, 35);
                        text-align: left;
                        padding-left: 45px;
                    }
                    QPushButton:hover {
                        background-color: rgb(33, 37, 43);
                        border-left: 20px solid rgb(33, 37, 43);
                    }
                    QPushButton:pressed {
                        background-color: rgb(85, 170, 255);
                        border-left: 20px solid rgb(85, 170, 255);
                    }''' % (forward_data_dir, self.scaled))
        self.pushButton_18.setStyleSheet('''QPushButton {
                                background-image: url(%sicons/20x20/cil-headphones%s.png);
                                background-position: left;
                                background-repeat: no-repeat;
                                border: none;
                                border-left: 20px solid rgb(27, 29, 35);
                                background-color: rgb(27, 29, 35);
                                text-align: left;
                                padding-left: 45px;
                            }
                            QPushButton:hover {
                                background-color: rgb(33, 37, 43);
                                border-left: 20px solid rgb(33, 37, 43);
                            }
                            QPushButton:pressed {
                                background-color: rgb(85, 170, 255);
                                border-left: 20px solid rgb(85, 170, 255);
                            }''' % (forward_data_dir, self.scaled))
        self.comboBox.setStyleSheet(self.comboBox.styleSheet().replace('.png', f'{self.scaled}.png'))
        self.pushButton_18.setFont(self.pushButton_5.font())
        self.pushButton_8.setStyleSheet(self.pushButton_8.styleSheet().replace('20', '20px'))
        self.pushButton_5.setLayoutDirection(QtCore.Qt.LeftToRight)
        self.pushButton_5.setText('Home')
        self.pushButton_6.setLayoutDirection(QtCore.Qt.LeftToRight)
        self.pushButton_6.setText('Settings')
        self.pushButton_14.setText('Friends')
        self.pushButton_11.setText('Add Friend')
        self.pushButton_18.setText('Listen Along')
        if client.mainstatus.playing_type not in ('None', 'ad', None):
            status = client.mainstatus.playing_status.lower()
        else:
            status = 'online' if client.mainstatus.playing_status == 'Online' else 'offline'

        def callbackfunc(wi):
            self.mainuserstatus = wi.convert_to_widget()
            self.verticalLayout_6.replaceWidget(self.label_2, self.mainuserstatus)

        self.mainuserstatus = Runnable(
            lambda: PartialBasicUserStatusWidget(status, client.mainstatus.clientavatar, client.mainstatus)
        )
        self.mainuserstatus.callback.connect(callbackfunc)
        self.mainuserstatus.start()

        while isinstance(self.mainuserstatus, Runnable):
            QtCore.QCoreApplication.processEvents()

        self.widgets_to_ignore.append(self.mainuserstatus)

        for request_id, request_data in client.friend_requests.items():
            requestwidget = PartialInboundFriendRequest(request_data, request_id, self, client).convert_to_widget()
            self.verticalLayout_18.insertWidget(1, requestwidget)
            self.inboundfriendrequests.update({request_id: requestwidget})
        for request_id, request_data in client.outbound_friend_requests.items():
            requestwidget = PartialOutboundFriendRequest(request_data, request_id, self, client).convert_to_widget()
            self.verticalLayout_19.insertWidget(1, requestwidget)
            self.outboundfriendrequests.update({request_id: requestwidget})
        self.label_2.hide()
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.mainuserstatus.sizePolicy().hasHeightForWidth())
        self.mainuserstatus.setSizePolicy(sizePolicy)
        sizePolicy3 = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed)
        sizePolicy3.setHorizontalStretch(0)
        sizePolicy3.setVerticalStretch(0)
        sizePolicy3.setHeightForWidth(self.pushButton_5.sizePolicy().hasHeightForWidth())
        self.leftFrame.setMaximumWidth(60)
        self.pushButton_5.setMaximumWidth(16777215)
        self.pushButton_5.setMinimumSize(0, 60)
        self.pushButton_5.setSizePolicy(sizePolicy3)
        self.pushButton_6.setMaximumWidth(16777215)
        self.pushButton_6.setMinimumSize(0, 60)
        self.pushButton_6.setSizePolicy(sizePolicy3)
        self.pushButton_11.setMaximumWidth(16777215)
        self.pushButton_11.setMinimumSize(0, 60)
        self.pushButton_11.setSizePolicy(sizePolicy3)
        self.pushButton_14.setMaximumWidth(16777215)
        self.pushButton_14.setMinimumSize(0, 60)
        self.pushButton_14.setSizePolicy(sizePolicy3)
        self.pushButton_18.setMaximumWidth(16777215)
        self.pushButton_18.setMinimumSize(0, 60)
        self.pushButton_18.setSizePolicy(sizePolicy3)
        self.pushButton_2.clicked.connect(lambda: self.close())
        self.pushButton_3.clicked.connect(self.maximized_check)
        self.pushButton_4.clicked.connect(lambda: self.showMinimized())
        self.dragPos = None
        self.label_4.setMouseTracking(True)
        self.label_7.setMouseTracking(True)
        self.pushButton_15.setMouseTracking(True)
        self.frame.setMouseTracking(True)
        app.installEventFilter(self)
        self.animation = None
        self.isMenuOpened = False
        self.rightFrame.setSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Preferred)
        self.pushButton.clicked.connect(self.menu_animation)
        self.label_30_originalStyleSheet = self.label_30.styleSheet()
        self.label_30.setStyleSheet(self.label_30.styleSheet().replace('replace',
                                                                       f'{forward_data_dir}icon{client.id}.png'))
        self.label_31.setText(limit_text_smart(client.spotifyclient.clientUsername, self.label_31))
        self.label_34.setText(client.spotifyclient.friendCode)
        self.label_34.setStyleSheet('color: white; text-decoration: underline;')
        self.label_34.setCursor(QtGui.QCursor(QtCore.Qt.PointingHandCursor))

        def copy():
            try:
                pyperclip.copy(client.spotifyclient.friendCode)
                self.show_snack_bar(SnackBar('Copied to clipboard.'))
            except Exception as exc:
                logging.error('An unexpected error occured while trying to copy the friend code: ', exc_info=exc)
                self.show_snack_bar(SnackBar('An error occured while trying to copy the friend code.', True, True))

        self.label_34.mousePressEvent = lambda *_: copy()

        self.pushButton_15.setIcon(QtGui.QIcon(f'{forward_data_dir}icon{client.id}.png'))
        self.pushButton_15.setIconSize(QtCore.QSize(40 * ratio + 1, 40 * ratio + 1))
        self.pushButton_16.setStyleSheet(self.pushButton_16.styleSheet().replace('replace', forward_data_dir).replace(
            '.png', f'{self.scaled}.png'))
        self.pushButton_17.setStyleSheet(self.pushButton_17.styleSheet().replace('replace', forward_data_dir).replace(
            '.png', f'{self.scaled}.png'
        ))
        self.comboBox.setStyleSheet(self.comboBox.styleSheet().replace('replace', forward_data_dir))
        self.overlay = QtWidgets.QWidget(parent=self)
        self.overlay.setStyleSheet('background-color: rgba(0, 0, 0, 60);')
        self.overlay.setAttribute(QtCore.Qt.WA_TransparentForMouseEvents, True)
        self.overlay.hide()
        self.disconnect_overlay = DisconnectBanner(parent=self)

        def log_out():
            keyring.set_password('SpotAlong', 'auth_token', '')
            logging.info(f'Logging out as user {client.spotifyclient.clientUsername}')
            stop_all()

            app.setQuitOnLastWindowClosed(True)
            QtCore.QCoreApplication.exit(4)

        def stop_all():
            # stop all the QTimers and attempt to delete everything
            self.worker.exit(0)
            self.worker.running = False
            self.worker2.exit(0)
            self.worker2.runnning = False
            self.worker3.exit(0)
            self.worker3.running = False
            self.worker4.exit(0)
            self.worker4.running = False
            if hasattr(self, 'playbackcontroller') and hasattr(self.playbackcontroller, 'timer3'):
                self.playbackcontroller.timer2.stop()
                self.playbackcontroller.timer3.stop()
            for advstatuswidget in self.advancedfriendstatuses.values():
                if hasattr(advstatuswidget, 'timer'):
                    advstatuswidget.timer.stop()
            for historywidget in self.laststatuses.values():
                historywidget.timer.stop()
            self.client.disconnected = True
            self.client.client.disconnect()
            if self.client.spotifyplayer:
                self.client.spotifyplayer.disconnect()
            self.deleteLater()
            gc.collect()

        self.stop_all = stop_all

        self.pushButton_17.clicked.connect(lambda: self.__setattr__(
            'active_dialog', Dialog('Log Out', 'Are you sure you want to log out? This will return you back to the'
                                               ' login screen.', 'Log Out', log_out)))
        self.middleFrame_3.raise_()
        self.middleFrame_3.setMinimumWidth(0)
        self.usersettingsopened = False
        self.failure_combo_box_changed = time.time()

        def change_song_broadcast():
            if time.time() - self.failure_combo_box_changed < 0.2:
                return
            i = self.comboBox.currentIndex()

            def success():
                self.show_snack_bar(SnackBar('The listening status setting was changed successfully.'))

            def failure():
                self.failure_combo_box_changed = time.time()
                if sip.isdeleted(self):
                    return
                self.comboBox.setCurrentIndex(0 if i == 1 else 1)
                self.show_snack_bar(SnackBar('An error occured while changing the listening status setting.',
                                             True, True))

            success_runner = Runnable()
            success_runner.callback.connect(success)
            failure_runner = Runnable()
            failure_runner.callback.connect(failure)

            Thread(target=client.invoke_request, args=(BASE_URL + '/me/status_broadcast', {'broadcast': not bool(i)},
                                                       'POST', success_runner.run, failure_runner.run)).start()

        self.comboBox.currentIndexChanged.connect(change_song_broadcast)

        def resize_check(a0):
            if self.middleFrame_3.width() == 0:
                return QtWidgets.QSizeGrip.mousePressEvent(self.frame, a0)

        self.frame.mousePressEvent = resize_check

        def open_user_settings():
            self.user_settings_animation = QtCore.QPropertyAnimation(self.middleFrame_3, b'minimumWidth')
            self.user_settings_animation.setDuration(250)
            self.user_settings_animation.setStartValue(self.middleFrame_3.width())
            if self.usersettingsopened:
                self.animation_timer = QtCore.QTimer()
                self.animation_timer.setInterval(250)
                self.frame.setDisabled(True)
                self.animation_timer.timeout.connect(lambda: (self.rightFrame. # noqa
                                                              setSizePolicy(QtWidgets.QSizePolicy.Preferred,
                                                                            QtWidgets.QSizePolicy.Preferred),
                                                              self.animation_timer.stop(),
                                                              self.frame.setDisabled(False)))
                self.user_settings_animation.setEndValue(0)

            else:
                self.animation_timer = None
                self.rightFrame.setSizePolicy(QtWidgets.QSizePolicy.Ignored, QtWidgets.QSizePolicy.Preferred)
                self.user_settings_animation.setEndValue(200 * ratio)
            self.user_settings_animation.setEasingCurve(QtCore.QEasingCurve.InOutQuart)
            self.usersettingsopened = not self.usersettingsopened
            self.animation_timer.start() if self.animation_timer else None
            self.user_settings_animation.start()

        def open_advanced_user_settings(page):
            self.advanced_user_settings_animation = QtCore.QPropertyAnimation(self.middleFrame_3, b'minimumWidth')
            self.advanced_user_settings_animation.setDuration(250)
            self.advanced_user_settings_animation.setStartValue(self.middleFrame_3.width())
            self.advanced_user_settings_animation.setEndValue(700 * ratio)
            self.advanced_user_settings_animation.setEasingCurve(QtCore.QEasingCurve.InOutQuart)
            self.verticalStackedWidgetUserSettings.setCurrentWidget(page)
            self.advanced_user_settings_animation.start()

        def user_settings_menu_under_mouse():
            pos = self.middleFrame_3.mapFromGlobal(QtGui.QCursor.pos())
            return self.middleFrame_3.rect().contains(pos)

        self.user_settings_menu_under_mouse = user_settings_menu_under_mouse
        self.open_user_settings = open_user_settings

        def opensettings():
            if self.middleFrame_3.width() == 0:
                open_user_settings()

        self.pushButton_15.clicked.connect(opensettings)
        self.pushButton_16.clicked.connect(lambda: open_advanced_user_settings(self.verticalStackedWidget_14Page1))

        self.worker = MainUpdateThread(client)  # initialize all the update threads

        def mainstatusdata(data):

            def changeicons():
                self.pushButton_15.setIcon(QtGui.QIcon(f'{forward_data_dir}icon{client.id}.png'))
                self.pushButton_15.setIconSize(QtCore.QSize(40 * ratio + 1, 40 * ratio + 1))
                self.label_30.setStyleSheet(self.label_30_originalStyleSheet
                                            .replace('replace', f'{forward_data_dir}icon{client.id}.png'))
                self.label_31.setText(limit_text_smart(client.spotifyclient.clientUsername, self.label_31))
                self.label_top_info_1.setText(f'Logged in as: {client.spotifyclient.clientUsername}')

            QtCore.QTimer.singleShot(0, changeicons)
            if isinstance(data, PartialBasicUserStatusWidget):
                mainstatus = data.convert_to_widget()
                self.verticalLayout_6.replaceWidget(self.mainuserstatus, mainstatus)
                self.mainuserstatus.hide()
                self.mainuserstatus.deleteLater()
                del self.mainuserstatus
                self.mainuserstatus = mainstatus
            elif isinstance(data, PartialListeningToFriends):
                listener = data.convert_to_widget()
                self.verticalLayout_38.replaceWidget(self.listentofriends, listener)
                listener.show()
                listener.setStyleSheet(listener.styleSheet())
                if hasattr(self.listentofriends, 'timer'):
                    self.listentofriends.timer.stop()
                self.listentofriends.hide()
                self.listentofriends.deleteLater()
                del self.listentofriends
                self.listentofriends = listener
            else:
                playbackcontroller = data.convert_to_widget()
                if self.playbackcontroller.is_player:
                    try:
                        self.playbackcontroller.timer3.stop()
                        self.playbackcontroller.timer2.stop()
                        self.playbackcontroller.timer.stop()
                    except AttributeError:
                        pass
                    if self.devicelist:
                        try:
                            self.devicelist.deleteLater()
                        except RuntimeError:
                            pass
                    try:
                        client.spotifyplayer.remove_event_reciever(self.playbackcontroller.slider_pos)
                    except TypeError:
                        pass
                self.horizontalLayout_14.replaceWidget(self.playbackcontroller, playbackcontroller)
                self.playbackcontroller.hide()

                self.playbackcontroller.deleteLater()
                del self.playbackcontroller
                self.horizontalFrame5.setFixedHeight(120 * self.ratio)
                if self.active_dialog:
                    if self.active_dialog.error:
                        self.active_dialog.pushButton_2.click()
                self.playbackcontroller = playbackcontroller  # noqa
            gc.collect()

        self.worker.emitter.connect(lambda data: mainstatusdata(data))
        self.worker.start()

        self.worker2 = FriendUpdateThread(client, self.statuswidgets, self)

        def friendstatusdata(data, data2, data3, data4):
            friendstatus = data.convert_to_widget()
            index = data.index
            if index in self.statuswidgets:
                self.horizontalLayout_6.replaceWidget(self.statuswidgets[index], friendstatus)
                self.statuswidgets[index].hide()
                self.statuswidgets[index].deleteLater()
                del self.statuswidgets[index]
            else:
                self.horizontalLayout_6.addWidget(friendstatus)
            self.statuswidgets.update({index: friendstatus})
            friendstatus = data2.convert_to_secondary_widget()
            index = data2.index
            if index in self.friendstatuswidgets:
                self.verticalLayout_22.replaceWidget(self.friendstatuswidgets[index], friendstatus)
                self.friendstatuswidgets[index].hide()
                self.friendstatuswidgets[index].deleteLater()
                del self.friendstatuswidgets[index]
            else:
                self.verticalLayout_22.insertWidget(len(self.friendstatuswidgets), friendstatus)
            self.friendstatuswidgets.update({index: friendstatus})
            friendstatus = data3.convert_to_widget()
            if data3.user_id in self.listeningfriendlist.keys():
                self.verticalLayout_28.removeWidget(friendstatus)
                self.listeningfriendlist[data3.user_id].hide()
                self.listeningfriendlist[data3.user_id].deleteLater()
                del self.listeningfriendlist[data3.user_id]
            elif data3.user_id in self.onlinefriendlist.keys():
                self.verticalLayout_29.removeWidget(friendstatus)
                self.onlinefriendlist[data3.user_id].hide()
                self.onlinefriendlist[data3.user_id].deleteLater()
                del self.onlinefriendlist[data3.user_id]
            elif data3.user_id in self.offlinefriendlist.keys():
                self.verticalLayout_30.removeWidget(friendstatus)
                self.offlinefriendlist[data3.user_id].hide()
                self.offlinefriendlist[data3.user_id].deleteLater()
                del self.offlinefriendlist[data3.user_id]
            if friendstatus.status == 'listening':
                self.verticalLayout_28.addWidget(friendstatus)
                self.listeningfriendlist.update({friendstatus.user_id: friendstatus})
            if friendstatus.status == 'online':
                self.verticalLayout_29.addWidget(friendstatus)
                self.onlinefriendlist.update({friendstatus.user_id: friendstatus})
            if friendstatus.status == 'offline':
                self.verticalLayout_30.addWidget(friendstatus)
                self.offlinefriendlist.update({friendstatus.user_id: friendstatus})
            friendstatus = data4.convert_to_widget()
            if friendstatus.user_id in self.advancedfriendstatuses:
                self.advanceduserstatus.addWidget(friendstatus)
                self.advanceduserstatus.removeWidget(self.advancedfriendstatuses[friendstatus.user_id])
                try:
                    self.advancedfriendstatuses[friendstatus.user_id].timer.stop()
                except AttributeError:
                    pass
                self.advancedfriendstatuses[friendstatus.user_id].deleteLater()
                self.advancedfriendstatuses.update({friendstatus.user_id: friendstatus})
            else:
                self.advanceduserstatus.addWidget(friendstatus)
                self.advancedfriendstatuses.update({friendstatus.user_id: friendstatus})
            if friendstatus.user_id in self.laststatuses:
                label = self.laststatuses[friendstatus.user_id].label
                label.setStyleSheet(label.styleSheet())
                self.laststatuses[friendstatus.user_id].label_7.setText(friendstatus.spotifysong.clientusername)
                self.laststatuses[friendstatus.user_id].show()
            gc.collect()

        def friendemitter(data):
            if isinstance(data, tuple):
                friendstatusdata(*data)
            elif isinstance(data, DeleteWidget):
                for delwidget in data.args:
                    self.horizontalLayout_6.removeWidget(self.statuswidgets[delwidget])
                    self.statuswidgets[delwidget].hide()
                    self.statuswidgets[delwidget].deleteLater()
                    del self.statuswidgets[delwidget]

                    self.verticalLayout_22.removeWidget(self.friendstatuswidgets[delwidget])
                    self.friendstatuswidgets[delwidget].hide()
                    self.friendstatuswidgets[delwidget].deleteLater()
                    del self.friendstatuswidgets[delwidget]

                    if delwidget in self.listeningfriendlist:
                        self.verticalLayout_28.removeWidget(self.listeningfriendlist[delwidget])
                        self.listeningfriendlist[delwidget].hide()
                        self.listeningfriendlist[delwidget].deleteLater()
                        del self.listeningfriendlist[delwidget]
                    elif delwidget in self.onlinefriendlist:
                        self.verticalLayout_29.removeWidget(self.onlinefriendlist[delwidget])
                        self.onlinefriendlist[delwidget].hide()
                        self.onlinefriendlist[delwidget].deleteLater()
                        del self.onlinefriendlist[delwidget]
                    elif delwidget in self.offlinefriendlist:
                        self.verticalLayout_30.removeWidget(self.offlinefriendlist[delwidget])
                        self.offlinefriendlist[delwidget].hide()
                        self.offlinefriendlist[delwidget].deleteLater()
                        del self.offlinefriendlist[delwidget]

                    self.advanceduserstatus.removeWidget(self.advancedfriendstatuses[delwidget])
                    try:
                        self.advancedfriendstatuses[delwidget].timer.stop()
                    except AttributeError:
                        pass
                    self.advancedfriendstatuses[delwidget].deleteLater()
                    del self.advancedfriendstatuses[delwidget]
            gc.collect()

        self.worker2.emitter.connect(friendemitter)
        self.worker2.start()

        def inboundrequestemmitter(data):
            if isinstance(data, PartialInboundFriendRequest):
                request = data.convert_to_widget()
                self.verticalLayout_18.insertWidget(1, request)
                self.inboundfriendrequests.update({data.request_id: request})
                if self.verticalStackedWidget.currentWidget() != self.page_2:
                    col = 'transparent'
                else:
                    col = 'rgb(44, 49, 60)'
                self.pushButton_11.setStyleSheet(adj_style(ratio, '''QPushButton {
                                                        background-image: url(%s.png);
                                                        background-position: left;
                                                        background-repeat: no-repeat;
                                                        border: none;
                                                        border-left: 20px solid rgb(27, 29, 35);
                                                        border-right: 5px solid %s;
                                                        background-color: rgb(27, 29, 35);
                                                        text-align: left;
                                                        padding-left: 45px;
                                                    }
                                                    QPushButton:hover {
                                                        background-color: rgb(33, 37, 43);
                                                        border-left: 20px solid rgb(33, 37, 43);
                                                    }
                                                    QPushButton:pressed {
                                                        background-color: rgb%s;
                                                        border-left: 20px solid rgb%s;
                                                    }''') % (forward_data_dir +
                                                             f'icons/20x20/cil-user-follow-notif{self.scaled}',
                                                             col,
                                                             repr(self.accent_color), repr(self.accent_color)))

            else:
                request = data
                self.verticalLayout_18.removeWidget(self.inboundfriendrequests[request])
                self.inboundfriendrequests[request].hide()
                self.inboundfriendrequests[request].deleteLater()
                del self.inboundfriendrequests[request]

        def outboundrequestemmitter(data):
            if isinstance(data, PartialOutboundFriendRequest):
                request = data.convert_to_widget()
                self.verticalLayout_19.insertWidget(1, request)
                self.outboundfriendrequests.update({data.request_id: request})
            else:
                request = data
                self.verticalLayout_19.removeWidget(self.outboundfriendrequests[request])
                self.outboundfriendrequests[request].hide()
                self.outboundfriendrequests[request].deleteLater()
                del self.outboundfriendrequests[request]

        def requestsplitter(data):
            if isinstance(data, DeleteWidget):
                for request in data.args:
                    if request in self.inboundfriendrequests:
                        inboundrequestemmitter(request)
                    else:
                        outboundrequestemmitter(request)
            else:
                if isinstance(data, PartialInboundFriendRequest):
                    inboundrequestemmitter(data)
                else:
                    outboundrequestemmitter(data)
            gc.collect()

        self.worker3 = RequestUpdateThread(client, self)
        self.worker3.emitter.connect(requestsplitter)
        self.worker3.start()

        def friend_history_updater(historywidget):
            if isinstance(historywidget, PartialPastFriendStatus):
                if historywidget.id in self.laststatuses and historywidget:
                    historywidget = historywidget.convert_to_widget()
                    self.verticalLayout_16.replaceWidget(self.laststatuses[historywidget.id], historywidget)
                    self.laststatuses[historywidget.id].hide()
                    try:
                        self.laststatuses[historywidget.id].timer.stop()
                    except NameError:
                        pass
                    self.laststatuses[historywidget.id].deleteLater()
                    self.laststatuses.update({historywidget.id: historywidget})
                else:
                    historywidget = historywidget.convert_to_widget()
                    if historywidget:
                        self.verticalLayout_16.insertWidget(0, historywidget)
                        self.laststatuses.update({historywidget.id: historywidget})
            elif isinstance(historywidget, DeleteWidget):
                for delete in historywidget.args:
                    if delete in self.laststatuses:
                        self.laststatuses[delete].hide()
                        self.laststatuses[delete].deleteLater()
                        try:
                            self.laststatuses[delete].timer.stop()
                        except NameError:
                            pass
                        del self.laststatuses[delete]
            sort_friend_history()
            gc.collect()

        self.worker4 = FriendHistoryUpdateThread(client, self)
        self.worker4.emitter.connect(friend_history_updater)
        self.worker4.start()

        progress_bar.setValue(90)

        # add the sidebar buttons
        self.pushButton_5.clicked.connect(lambda: self.set_main_menu(self.homePage, self.pushButton_5, 'cil-home',
                                                                     'Home'))
        self.pushButton_5.menuAttrs = [self.homePage, self.pushButton_5, 'cil-home', self.pushButton_5.styleSheet()]
        self.pushButton_6.clicked.connect(lambda: self.set_main_menu(self.page, self.pushButton_6, 'cil-settings',
                                                                     'Settings'))
        self.pushButton_6.menuAttrs = [self.page, self.pushButton_6, 'cil-settings', self.pushButton_6.styleSheet()]
        self.pushButton_14.clicked.connect(lambda: self.set_main_menu(self.page_3, self.pushButton_14, 'cil-people',
                                                                      'Friends'))
        self.pushButton_14.menuAttrs = [self.page_3, self.pushButton_14, 'cil-people', self.pushButton_14.styleSheet()]
        self.pushButton_18.clicked.connect(lambda: self.set_main_menu(self.page_4, self.pushButton_18,
                                                                      'cil-headphones', 'Listen Along'))
        self.pushButton_18.menuAttrs = [self.page_4, self.pushButton_18, 'cil-headphones',
                                        self.pushButton_18.styleSheet()]
        self.pushButton_11.clicked.connect(lambda: self.set_main_menu(self.page_2, self.pushButton_11,
                                                                      'cil-user-follow', 'Add Friend'))
        self.pushButton_11.menuAttrs = [self.page, self.pushButton_11, 'cil-user-follow',
                                        self.pushButton_11.styleSheet()]
        self.buttons = [self.pushButton_5, self.pushButton_6, self.pushButton_11, self.pushButton_14,
                        self.pushButton_18]
        self.pushButton_5.setStyleSheet('''QPushButton {
        background-image: url(%sicons/20x20/cil-home%s.png);
        background-position: left;
        background-repeat: no-repeat;
        border: none;
        border-left: 20px solid rgb(27, 29, 35);
        border-right: 5px solid rgb(44, 49, 60);
        background-color: rgb(27, 29, 35);
        text-align: left;
        padding-left: 45px;
    }
    QPushButton:hover {
        background-color: rgb(33, 37, 43);
        border-left: 20px solid rgb(33, 37, 43);
    }
    QPushButton:pressed {
        background-color: rgb(85, 170, 255);
        border-left: 20px solid rgb(85, 170, 255);
    }''' % (forward_data_dir, self.scaled))
        self.verticalStackedWidget.setCurrentWidget(self.homePage)
        # settings related stuff
        self.pushButton_10.setStyleSheet(self.pushButton_10.styleSheet().
                                         replace('replace', forward_data_dir).replace('.png', f'{self.scaled}.png'))
        self.pushButton_10.setText(' View Logs')
        self.pushButton_8.setStyleSheet(self.pushButton_8.styleSheet().replace('replace', forward_data_dir).replace(
            '.png', f'{self.scaled}.png'
        ))

        def clear_album_cache():
            dont_del = ['unknown_album.png', 'albumNone.png', 'partialalbumNone.png']
            [file.unlink() for file in Path(data_dir).glob("*album*") if file.is_file() and file.name not in dont_del]
            self.label_26.setText('Cleared!')
            Thread(target=lambda: (time.sleep(1), self.label_26.setText(''))).start()

        self.pushButton_8.clicked.connect(clear_album_cache)
        self.pushButton_10.clicked.connect(lambda: self.__setattr__('LogViewer', LogViewer(logging_io)))
        self.widgets_to_ignore.append(self.horizontalFrame5)
        if client.spotifyplayer and client.spotifyplayer.isinitialized:
            self.horizontalFrame5.setFixedHeight(120 * self.ratio)

            def callbackfunc(wi):
                self.playbackcontroller = wi.convert_to_widget()
                self.horizontalLayout_14.addWidget(self.playbackcontroller)
                self.widgets_to_ignore.append(self.playbackcontroller)

            self.playbackcontroller = Runnable(
                lambda: PartialPlaybackController(client.mainstatus, client.spotifyplayer, client)
            )
            self.playbackcontroller.callback.connect(callbackfunc)
            self.playbackcontroller.start()
        else:
            self.horizontalFrame5.setFixedHeight(0)

        self.last_update = time.time()

        def set_transparency(transparency: float):
            self.window_transparency = transparency / 100
            self.setWindowOpacity(self.window_transparency)
            if (curr_time := time.time()) - self.last_update > 0.3:
                Thread(target=self.change_file).start()
                self.last_update = curr_time

        self.window_transparency = window_transparency
        self.horizontalSlider.setStyleSheet(self.horizontalSlider.styleSheet().replace('white', 'transparent'))
        self.horizontalSlider_2.setStyleSheet(self.horizontalSlider.styleSheet().replace('white', 'transparent'))
        self.horizontalSlider.setValue(int(window_transparency * 100))
        self.horizontalSlider.valueChanged.connect(lambda: set_transparency(self.horizontalSlider.value()))
        self.horizontalSlider.mouseReleaseEvent = lambda a0: set_transparency(self.horizontalSlider.value())
        self.accent_color = (85, 170, 255)
        self.checkboxes = [self.checkBox, self.checkBox_2, self.checkBox_3, self.checkBox_4, self.checkBox_5,
                           self.checkBox_7, self.checkBox_10, self.checkBox_8, self.checkBox_9]
        [checkbox.setStyleSheet(checkbox.styleSheet().replace('replace', forward_data_dir).replace(
            '.png', f'{self.scaled}.png'))
         for checkbox in self.checkboxes]
        self.accent_colors_checkboxes = {
            self.checkBox: (255, 0, 0),
            self.checkBox_2: (255, 165, 0),
            self.checkBox_3: (255, 255, 0),
            self.checkBox_4: (0, 255, 0),
            self.checkBox_5: (29, 185, 84),
            self.checkBox_7: (85, 170, 255),
            self.checkBox_10: (33, 92, 255),
            self.checkBox_8: (128, 0, 128),
            self.checkBox_9: (255, 182, 193)
        }
        self.label_9.setFixedHeight(37)
        self.horizontalFrame1.setMaximumHeight(84)
        self.horizontalFrame1.setMinimumHeight(84)
        self.widgets_to_ignore += (self.verticalLayout_10, self.horizontalLayout_20, self.horizontalLayout_12)
        self.horizontalFrame2.setMaximumHeight(62)
        self.horizontalFrame2.setMinimumHeight(62)
        self.verticalFrame_7.setMinimumHeight(150)
        self.accent_widgets = [attr for attr in [getattr(self, a) for a in dir(self) if a not in ['mainuserstatus',
                                                                                                  'playbackcontroller',
                                                                                                  'frameMain'] and not
                                                 a.startswith('checkBox')]
                               if issubclass(type(attr), QtWidgets.QWidget)
                               and ('(85, 170, 255)' in attr.styleSheet()
                                    or repr(self.accent_color) in attr.styleSheet())
                               and '/* NO ACCENT COLOR */' not in attr.styleSheet()]  # why
        self.inverse_accent_colors = {value: key for key, value in self.accent_colors_checkboxes.items()}
        [widget.setStyleSheet(widget.styleSheet() + '/* NO ACCENT COLOR */') for widget in self.checkboxes]
        self.change_accent_color(accent_color)
        self.inverse_accent_colors[accent_color].setChecked(True)
        self.checkBox.clicked.connect(lambda: self.change_accent_color((255, 0, 0)))
        self.checkBox_2.clicked.connect(lambda: self.change_accent_color((255, 165, 0)))
        self.checkBox_3.clicked.connect(lambda: self.change_accent_color((255, 255, 0)))
        self.checkBox_4.clicked.connect(lambda: self.change_accent_color((0, 255, 0)))
        self.checkBox_5.clicked.connect(lambda: self.change_accent_color((29, 185, 84)))
        self.checkBox_7.clicked.connect(lambda: self.change_accent_color((85, 170, 255)))
        self.checkBox_10.clicked.connect(lambda: self.change_accent_color((33, 92, 255)))
        self.checkBox_8.clicked.connect(lambda: self.change_accent_color((128, 0, 128)))
        self.checkBox_9.clicked.connect(lambda: self.change_accent_color((255, 182, 193)))

        self.lineEdit.setValidator(QtGui.QRegExpValidator(QtCore.QRegExp(r'\d{4}-\d{4}-\d{4}')))
        font = self.lineEdit.font()
        font.setLetterSpacing(QtGui.QFont.AbsoluteSpacing, 5)
        self.lineEdit.setFont(font)
        self.label_20.setStyleSheet(f'color: rgb{repr(self.accent_color)};')

        def friend_code_validator():
            self.label_20.setText('')
            text = self.lineEdit.text()
            if len(text) != 14:
                self.label_20.setText('The friend code must be 14 characters in length, including dashes.')
            elif text == client.spotifyclient.friendCode:
                self.label_20.setText('You cannot friend yourself.')
            elif text in [friend_id.friend_code for friend_id in client.friendstatus.values()]:
                self.label_20.setText('You already friended that user.')
            elif text in [request['target']['friend_code'] for request in client.outbound_friend_requests.values()]:
                self.label_20.setText('You already sent a friend request to that user.')
            elif text in [request['sender']['friend_code'] for request in client.friend_requests.values()]:
                self.label_20.setText('That user has already sent a friend request to you.')
            else:
                self.label_20.setText('Loading...')
                self.pushButton_7.setDisabled(True)

                def success():
                    self.lineEdit.setText('')
                    self.delayed_text(self.label_20, 'Success!', '')
                    self.pushButton_7.setDisabled(False)

                def failure():
                    self.delayed_text(self.label_20, 'Invalid friend code.', '')
                    self.pushButton_7.setDisabled(False)

                success_runner = Runnable(parent=self)
                success_runner.callback.connect(success)
                failure_runner = Runnable(parent=self)
                failure_runner.callback.connect(failure)

                Thread(target=client.invoke_request,
                       args=(BASE_URL + '/friends/friend_request', {'target_id': text}, 'POST', success_runner.run,
                             failure_runner.run)).start()

        self.pushButton_7.clicked.connect(friend_code_validator)

        self.label_22.setFixedHeight(35)
        self.scrollAreaWidgetContents.setStyleSheet('background-color: rgb(33, 37, 43);')
        self.label_23.setFixedHeight(35)
        self.scrollAreaWidgetContents_2.setStyleSheet('background-color: rgb(33, 37, 43);')
        self.verticalFrame_4.setMinimumWidth(250)

        self.friendlistopened = True  # sidebar related
        self.friendhistoryopened = False
        self.verticalFrame_4.setMinimumWidth(0)
        self.verticalFrame_4.setMaximumWidth(0)
        self.label_14.setMinimumWidth(230)
        self.label_14.setMaximumWidth(230)

        def friend_animation():
            self.friendsanimation = QtCore.QPropertyAnimation(self.verticalFrame_2, b'minimumWidth')
            self.friendsanimation.setDuration(250)
            self.friendsanimation.setStartValue(self.verticalFrame_2.width())
            if self.friendlistopened:
                self.friendsanimation.setEndValue(0)
            else:
                self.friendsanimation.setEndValue(230 * self.ratio)
            self.friendsanimation.setEasingCurve(QtCore.QEasingCurve.InOutQuart)

            self.friendsanimation2 = QtCore.QPropertyAnimation(self.verticalFrame_2, b'maximumWidth')
            self.friendsanimation2.setDuration(250)
            self.friendsanimation2.setStartValue(self.verticalFrame_2.width())
            if self.friendlistopened:
                self.friendsanimation2.setEndValue(0)
                self.friendlistopened = False
            else:
                self.friendsanimation2.setEndValue(230 * self.ratio)
                self.friendlistopened = True
            self.friendsanimation2.setEasingCurve(QtCore.QEasingCurve.InOutQuart)
            self.friendsparallelanimation = QtCore.QParallelAnimationGroup()
            self.friendsparallelanimation.addAnimation(self.friendsanimation)
            self.friendsparallelanimation.addAnimation(self.friendsanimation2)
            self.friendsparallelanimation.start()

        self.pushButton_12.clicked.connect(friend_animation)

        def friend_history_animation():
            self.verticalFrame_9.setFixedWidth(250 * self.ratio)
            self.friendhistoryanimation = QtCore.QPropertyAnimation(self.verticalFrame_4, b'minimumWidth')
            self.friendhistoryanimation.setDuration(250)
            self.friendhistoryanimation.setStartValue(self.verticalFrame_4.width())
            if self.friendhistoryopened:
                self.friendhistoryanimation.setEndValue(0)
            else:
                self.friendhistoryanimation.setEndValue(250 * self.ratio)
            self.friendhistoryanimation.setEasingCurve(QtCore.QEasingCurve.InOutQuart)
            self.friendhistoryanimation2 = QtCore.QPropertyAnimation(self.verticalFrame_4, b'maximumWidth')
            self.friendhistoryanimation2.setDuration(250)
            self.friendhistoryanimation2.setStartValue(self.verticalFrame_4.width())
            if self.friendhistoryopened:
                self.friendhistoryanimation2.setEndValue(0)
                self.friendhistoryopened = False
            else:
                self.friendhistoryanimation2.setEndValue(250 * self.ratio)
                self.friendhistoryopened = True
            self.friendhistoryanimation2.setEasingCurve(QtCore.QEasingCurve.InOutQuart)
            self.friendhistoryparallelanimation = QtCore.QParallelAnimationGroup()
            self.friendhistoryparallelanimation.addAnimation(self.friendhistoryanimation)
            self.friendhistoryparallelanimation.addAnimation(self.friendhistoryanimation2)
            self.friendhistoryparallelanimation.start()

        self.pushButton_13.clicked.connect(friend_history_animation)

        def change_album_cache():
            value = self.horizontalSlider_2.value()
            if value > 999:
                value_string = f'{round(value / 1000, 3)} GB'
            else:
                value_string = f'{value} MB'
            self.lineEdit_2.setText(value_string)
            self.horizontalSlider_2.setFocus()
            self.lastalbumcachetext = value_string
            self.albumcachelimit = value

        def change_album_cache_text():
            text = self.lineEdit_2.text()
            value_re_mb = r'^(\d+) *(MB)?$'
            if match := re.match(value_re_mb, text, re.IGNORECASE):
                num = int(match.group(1))
                if 10 <= num <= 5000:
                    self.horizontalSlider_2.setValue(num)
                    change_album_cache()
                    return
            value_re_gb = r'^((\d+([.]\d+)?) *GB)$'
            if match := re.match(value_re_gb, text, re.IGNORECASE):
                num = round(float(match.group(2)), 3) * 1000
                if 1000 <= num <= 5000:
                    self.horizontalSlider_2.setValue(num)
                    change_album_cache()
                    return
            self.lineEdit_2.setText(self.lastalbumcachetext)
            self.horizontalSlider_2.setFocus()

        self.horizontalSlider_2.valueChanged.connect(change_album_cache)
        self.lineEdit_2.editingFinished.connect(change_album_cache_text)
        self.lastalbumcachetext = self.lineEdit_2
        self.pushButton_9.setStyleSheet(self.pushButton_9.styleSheet().replace('replace', forward_data_dir).replace(
            '.png', f'{self.scaled}.png'
        ))

        def try_file_change():
            try:
                self.change_file()
                self.show_snack_bar(SnackBar('The settings were updated successfully.'))
            except Exception as exc:
                logging.error('An error occured while changing the settings: ', exc_info=exc)
                self.show_snack_bar(SnackBar('An error occured while changing the settings.', True, True))

        self.pushButton_9.clicked.connect(try_file_change)
        self.horizontalSlider_2.setValue(self.albumcachelimit)
        self.tabWidget.setCurrentWidget(self.Personalization)
        self.overlay.setGeometry(self.rect())
        self.resize(1700, 850)
        self.verticalFrame_4.setMinimumWidth(250)
        self.verticalFrame_4.setMaximumWidth(250)
        self.friendhistoryopened = True
        geometry = self.frameGeometry()
        geometry.moveCenter(QtWidgets.QDesktopWidget().availableGeometry().center())
        self.move(geometry.topLeft())
        self.isInitialized = True
        progress_bar.setValue(100)
        if not self.client.spotifyplayer:
            self.active_dialog = Dialog('A login error occured', 'There was an error with your login, and so the '
                                                                 'playback controller and listen along features have '
                                                                 'been disabled. Logging out and logging back in '
                                                                 'should remedy the issue.', 'Close', lambda: None,
                                        error=True)
        self.threadsafe_snackbar_runner = Runnable()
        self.threadsafe_snackbar_runner.args = ()
        self.threadsafe_snackbar_runner.kwargs = {}
        self.threadsafe_snackbar_runner.callback.\
            connect(lambda: self.show_snack_bar(SnackBar(*self.threadsafe_snackbar_runner.args,
                                                         **self.threadsafe_snackbar_runner.kwargs)))
        if self.client.mainstatus.playing_status == 'Listening':
            QtCore.QTimer.singleShot(5000, lambda: Thread(target=self.client.send_queue_for_caching).start())
        logging.info(f'Start Time: {time.perf_counter() - getattr(QtCore, "start_time")}')

    def change_accent_color(self, color: tuple):
        widgets = self.accent_widgets.copy()
        [widgets.append(widget.pushButton) for widget in list(self.statuswidgets.values()) +
         list(self.friendstatuswidgets.values())]
        for widget in self.inboundfriendrequests.values():
            widgets.append(widget.pushButton)
            widgets.append(widget.pushButton_2)
        colors = [repr((85, 170, 255)), repr(self.accent_color)]
        [widget.setStyleSheet(widget.styleSheet().replace(colors[0], repr(color)).replace(colors[1], repr(color)))
         for widget in widgets if '/* NO ACCENT COLOR */' not in widget.styleSheet()]
        self.accent_color = color
        [widget.setChecked(False) if color != color_value else widget.setChecked(True) for widget, color_value
         in self.accent_colors_checkboxes.items()]
        Thread(target=self.change_file).start()

    def change_file(self):
        with open(data_dir + 'config.json', 'w') as file:
            data = {'accent_color': list(self.accent_color), 'window_transparency': self.window_transparency,
                    'album_cache_maxsize': self.albumcachelimit}
            json.dump(data, file)
        file.close()

    def show_snack_bar_threadsafe(self, *args, **kwargs):
        self.threadsafe_snackbar_runner.args = args
        self.threadsafe_snackbar_runner.kwargs = kwargs
        self.threadsafe_snackbar_runner.run()

    def show_snack_bar(self, snack_bar: SnackBar):
        def show_():
            if self.isHidden():
                return
            self.current_snack_bar = snack_bar
            snack_bar.show()
            snack_bar.move_to_pos()
            snack_bar.animation.start()
            QtCore.QTimer.singleShot(4000, lambda: self.close_snack_bar(snack_bar))
            app.alert(self)

        if self.current_snack_bar is not None:
            self.close_snack_bar(self.current_snack_bar)
            QtCore.QTimer.singleShot(500, show_)
            return

        show_()

    def close_snack_bar(self, snack_bar: SnackBar):
        if self.current_snack_bar == snack_bar:
            self.current_snack_bar = None
        snack_bar.start_closing()

    def set_main_menu(self, page, button, icon, name_):
        self.verticalStackedWidget.setCurrentWidget(page)
        button.setStyleSheet(adj_style(self.ratio, '''QPushButton {
        background-image: url(%sicons/20x20/%s%s.png);
        background-position: left;
        background-repeat: no-repeat;
        border: none;
        border-left: 20px solid rgb(27, 29, 35);
        border-right: 5px solid rgb(44, 49, 60);
        background-color: rgb(27, 29, 35);
        text-align: left;
        padding-left: 45px;
    }
    QPushButton:hover {
                background-color: rgb(33, 37, 43);
                border-left: 20px solid rgb(33, 37, 43);
            }
            QPushButton:pressed {
                background-color: rgb(85, 170, 255);
                border-left: 20px solid rgb(85, 170, 255);
            }''').replace('(85, 170, 255)', repr(self.accent_color)) % (forward_data_dir, icon, self.scaled))
        self.label_top_info_2.setText(name_)
        self.setWindowTitle(name_)
        [pushbutton.setStyleSheet(adj_style(self.ratio, pushbutton.menuAttrs[-1]).replace('(85, 170, 255)',
                                                                                          repr(self.accent_color)))
         for pushbutton in self.buttons if pushbutton != button]

    def menu_animation(self):
        self.animation = QtCore.QPropertyAnimation(self.leftFrame, b"minimumWidth")
        self.animation.setDuration(300)
        if self.isMenuOpened:
            self.animation.setStartValue(int(self.leftFrame.minimumWidth()))
            self.animation.setEndValue(60 * self.ratio)
            self.isMenuOpened = False
        else:
            self.animation.setStartValue(int(self.leftFrame.minimumWidth()))
            self.animation.setEndValue(150 * self.ratio)
            self.isMenuOpened = True
        self.animation.setEasingCurve(QtCore.QEasingCurve.InOutQuart)
        self.animation.start()

    def maximized_check(self):
        if self.isMaximized():
            self.showNormal()
            self.frame.show()
            self.pushButton_3.setIcon(QtGui.QIcon(data_dir + f'icons\\24x24\\cil-window-maximize{self.scaled}.png'))
            self.pushButton_3.tooltip = Tooltip('Maximize', self.pushButton_3)
        else:
            self.showMaximized()
            self.frame.hide()
            self.pushButton_3.setIcon(QtGui.QIcon(data_dir + f'icons\\24x24\\cil-window-restore{self.scaled}.png'))
            self.pushButton_3.tooltip = Tooltip('Restore', self.pushButton_3)
        if self.active_dialog:
            global_coords = self.mapToGlobal(self.rect().center())
            self.active_dialog.move(global_coords.x() - self.active_dialog.width() // 2,
                                    global_coords.y() - self.active_dialog.height() // 2)
        if hasattr(self, 'disconnect_overlay'):
            self.disconnect_overlay.maximized_check()

    @staticmethod
    def delayed_text(text, first, second, interval=5):
        QtCore.QTimer.singleShot(0, lambda: text.setText(first))
        QtCore.QTimer.singleShot(interval * 1000, lambda: text.setText(second))

    def eventFilter(self, watched, event):
        if not self.isInitialized:
            return UiMainWindow.eventFilter(self, watched, event)
        if watched in (self.label_4, self.label_7) and event.type() == QtCore.QEvent.MouseButtonDblClick:
            self.maximized_check()
        elif watched in (self.label_4, self.label_7, self.disconnect_overlay.spacerItem)\
                and event.type() == QtCore.QEvent.MouseButtonPress:
            if event.button() == QtCore.Qt.LeftButton:
                self.dragPos = event.pos()
        elif watched in (self.label_4, self.label_7, self.disconnect_overlay.spacerItem) \
                and event.type() == QtCore.QEvent.MouseMove:
            if self.dragPos and not self.isMaximized():
                self.move(self.pos() + (event.pos() - self.dragPos))
                self.disconnect_overlay.move(self.disconnect_overlay.pos() + (event.pos() - self.dragPos))
                if self.active_dialog:
                    self.active_dialog.move(self.active_dialog.pos() + (event.pos() - self.dragPos))
                if self.current_snack_bar:
                    self.current_snack_bar.move(self.current_snack_bar.pos() + (event.pos() - self.dragPos))
        elif watched in (self.label_4, self.label_7, self.disconnect_overlay.spacerItem)\
                and event.type() == QtCore.QEvent.MouseButtonRelease:
            self.dragPos = None
        if self.devicelist:
            if not self.devicelist.mouseoverwindow and event.type() == QtCore.QEvent.MouseButtonPress:
                try:
                    self.devicelist.hide()
                except RuntimeError:
                    pass
        if event.type() == QtCore.QEvent.MouseButtonPress\
                and not self.user_settings_menu_under_mouse() and self.usersettingsopened and not self.active_dialog:
            self.open_user_settings()
        if self.active_dialog and event.type() == QtCore.QEvent.MouseButtonPress:
            if not self.active_dialog.underMouse():
                if not (self.horizontalFrame.underMouse() or self.frame.underMouse()):
                    self.active_dialog.close_dialog()
        event.accept()
        return super(UiMainWindow, self).eventFilter(watched, event)

    def showEvent(self, a0: QtGui.QShowEvent) -> None:
        UiMainWindow.showEvent(self, a0)  # what
        if not self.isshown:  # the
            self.isshown = True  # hell
            self.scrollArea_3.setStyleSheet(self.scrollArea_3.styleSheet())  # is
            self.scrollArea_4.setStyleSheet(self.scrollArea_4.styleSheet())  # this
            self.middleFrame_3.raise_()
            self.label_31.setText(limit_text_smart(self.client.spotifyclient.clientUsername, self.label_31))
            self.pushButton_8.setStyleSheet(self.pushButton_8.styleSheet())

    def resizeEvent(self, a0: QtGui.QResizeEvent) -> None:
        if self.isInitialized and hasattr(self, 'disconnect_overlay'):
            self.disconnect_overlay.move_dialog_pos()
            size = a0.size()
            size.setHeight(size.height())
            self.disconnect_overlay.setFixedSize(size)
        UiMainWindow.resizeEvent(self, a0)
        if self.isInitialized and self.active_dialog and hasattr(self, 'overlay'):
            self.active_dialog.move_dialog_pos()
        if self.isInitialized and self.current_snack_bar:
            self.current_snack_bar.move_to_pos()
        if self.isInitialized:
            self.overlay.setGeometry(self.rect())


global app


if __name__ == '__main__':
    QtCore.start_time = time.perf_counter()

    from ui.loginwidgets import LoggingInUi
    app = QtWidgets.QApplication(sys.argv)
    app.setApplicationDisplayName('SpotAlong')
    app.setObjectName('SpotAlong')
    app.setWindowIcon(QtGui.QIcon(data_dir + 'logo.ico'))
    if sys.platform == 'win32':
        import ctypes
        appid = 'CriticalElement.SpotAlong.SpotAlong.1.0'
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(appid)

    if not os.path.isdir(f'{data_dir}/icons'):
        os.makedirs(data_dir, exist_ok=True)
        copyfile('logo.ico', data_dir + 'logo.ico')
        app.setWindowIcon(QtGui.QIcon(data_dir + 'logo.ico'))
        dialog = LoggingInUi(placeholder=True)
        dialog.label_2.setText('Extracting default files...\n(This may take a while)')
        dialog.label_2.show()
        app.exec()

    app.setQuitOnLastWindowClosed(False)

    # terrible way to manage the starting sequence
    def login_to_api():
        global starting
        login_data = login()
        if not login_data:
            logging.info('Login failed, directing to login screen')
            starting.update({'second': True})
            return
        starting.update({'first': login_data})
        return login_data

    def main_user(login_data, progress_ui, error_callback=None):
        global starting
        client = MainClient(*login_data, progress_ui.progressBar)
        while not client.initialized:
            if client.disconnected:
                dc = client.disconnected

                def callback(code=4):
                    progress_ui.close()
                    QtWidgets.QApplication.setQuitOnLastWindowClosed(True)
                    QtWidgets.QApplication.exit(code)
                    client.quit(code)
                    return

                if isinstance(dc, str) and error_callback:
                    error_callback.emitter.emit((dc, lambda: callback(code=-4)))
                    return
                else:
                    logging.warning('Authorization failed, directing to login screen')
                    keyring.set_password('SpotAlong', 'auth_token', '')
                    callback()
                    return
            time.sleep(0.1)
        starting.pop('second', None)
        starting.update({'third': client})
        starting.update({'fourth': client})

    starting = {}

    tray = QtWidgets.QSystemTrayIcon()
    tray.setIcon(QtGui.QIcon(data_dir + 'logo.ico'))
    tray.setVisible(True)
    tray.setToolTip('SpotAlong')
    menu = QtWidgets.QMenu()
    name = QtWidgets.QAction('SpotAlong')
    name.setIcon(QtGui.QIcon(data_dir + 'logo.ico'))
    name.setDisabled(True)
    menu.addAction(name)
    menu.addSeparator()
    quit_action = QtWidgets.QAction('Quit')

    def quit_func():
        app = QtCore.QCoreApplication.instance()
        if hasattr(app, 'client'):
            app.client.quit(0)
        del app

    quit_action.triggered.connect(quit_func)
    menu.addAction(quit_action)
    show_action = QtWidgets.QAction('Show')

    def maximize_from_tray():
        if starting.get('fourth'):
            window = starting['fourth'].ui
            if window.disconnected:
                window.disconnect_overlay.show(fast=True)
            window.show()
            window.activateWindow()
            window.showNormal()

    show_action.triggered.connect(maximize_from_tray)
    menu.addAction(show_action)
    minimize_action = QtWidgets.QAction('Minimize To Tray   ')  # padding

    def minimize_to_tray():
        if starting.get('fourth'):
            _ui = starting['fourth'].ui
            _ui.close()
            if _ui.disconnected:
                _ui.disconnect_overlay.hide(fast=True)

    minimize_action.triggered.connect(minimize_to_tray)
    menu.addAction(minimize_action)
    menu.setStyleSheet('''QMenu::item:selected {
            background-color: rgb(73, 77, 83);
        }
        QMenu {
            background-color: rgb(41, 42, 45);
            border: 1px solid rgb(54, 57, 60);
            padding-top: 6px;
            padding-bottom: 6px;
        }
        QMenu::separator {
            height: 16px;
            background-color: qlineargradient(spread:pad, x1:0.5, y1:0.572864, x2:0.5, y2:0.449, stop:0 
            rgba(0, 0, 0, 0), stop:0.512438 rgba(54, 57, 60, 255), stop:1 rgba(0, 0, 0, 0));
            margin-left: 0px;
            margin-right: 0px;
        }
        QMenu::item:pressed {
            background-color: rgb(103, 107, 113);
        }
        QMenu::item {
            color: white;
            padding: 2px 30px 2px 8px;
            border: 1px solid transparent; /* reserve space for selection border */
        }''')
    tray.setContextMenu(menu)
    tray.activated.connect(lambda reason: maximize_from_tray() if reason == 3 else None)
    logging_in_window = LoggingInUi(starting, main_user)
    logging_in_window.show()
    Thread(target=login_to_api).start()
    while (exit_code := app.exec()) >= 1:
        try:
            if hasattr(app, 'client'):
                app.client.disconnected = True
                if app.client.spotifyplayer:
                    app.client.spotifyplayer.disconnect()
                app.client.client.disconnect()
        except Exception as exc:
            logging.error('Error occured while closing client: ', exc_info=exc)
        app.closeAllWindows()
        starting: typing.Dict[typing.AnyStr, typing.Any] = {}
        if exit_code == 3:  # missing or invalid files
            os.makedirs(data_dir, exist_ok=True)
            starting.update({'previous_exit_code': 3})
            try:
                copyfile('logo.ico', data_dir + 'logo.ico')
                app.setWindowIcon(QtGui.QIcon(data_dir + 'logo.ico'))
            except Exception as ex:
                logging.error('Icon not found: ', exc_info=ex)
                # honestly if something goes this horribly wrong it's going to get handled later on and I don't need
                # to give this special treatment
            dialog = LoggingInUi(placeholder=True)
            dialog.label_2.setText('Extracting default files...\n(This may take a while)')
            dialog.label_2.show()
            app.setQuitOnLastWindowClosed(True)
            app.exec()
        app.setQuitOnLastWindowClosed(False)
        logging_in_window = LoggingInUi(starting, main_user)
        logging_in_window.show()
        Thread(target=login_to_api).start()
    else:
        del app
        # noinspection PyProtectedMember
        os._exit(exit_code)
