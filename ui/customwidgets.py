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

from __future__ import annotations

import logging
import random
import re
import socket
import typing
import time
import datetime
import json
import os
from io import StringIO
from threading import Thread

import PIL
import requests
import numpy as np
from PIL import Image, ImageOps
from PIL.PyAccess import PyAccess
from PyQt5 import QtCore, QtWidgets, QtGui, sip
from appdirs import *
from colorthief import ColorThief

from spotifyclient.spotifyplayer import SpotifyPlayer
from spotifyclient.spotifysong import SpotifySong
from spotifyclient.spotifylistener import SpotifyListener
from utils.uiutils import *
from utils.constants import *
from utils.utils import *


QtGui.QFont = DpiFont

if typing.TYPE_CHECKING:
    from app import MainUI

sep = os.path.sep

data_dir = user_data_dir('SpotAlong', 'CriticalElement') + sep
forward_data_dir = data_dir.replace('\\', '/')
logger = logging.getLogger(__name__)


__all__ = ('PartialStatusWidget', 'StatusWidget', 'FriendsListStatusWidget', 'PartialBasicUserStatusWidget',
           'BasicUserStatusWidget', 'PartialPlaybackController', 'PlaybackController', 'PartialInboundFriendRequest',
           'InboundFriendRequest', 'PartialLogViewer', 'MainUpdateThread', 'FriendUpdateThread', 'RequestUpdateThread',
           'DeleteWidget', 'PartialOutboundFriendRequest', 'OutboundFriendRequest', 'PartialPastFriendStatus',
           'PastFriendStatus', 'FriendHistoryUpdateThread', 'LogViewer', 'PartialAdvancedUserStatus',
           'AdvancedUserStatus', 'PartialListedFriendStatus', 'ListedFriendStatus', 'PartialDeviceList', 'DeviceList',
           'Device', 'Dialog', 'Tooltip', 'PartialListeningToFriends', 'ListeningToFriends', 'DisconnectBanner',
           'SnackBar', 'SocketListener')

mainui: typing.Optional[MainUI] = None


class PartialStatusWidget:
    def __init__(self, status: str, icon_url: str, client_id: str, client_name: str, spotifysong: SpotifySong,
                 index: int, accent_color: tuple):
        """
            A class that loads the initial status widget, to be later converted into a QWidget.

            Parameters:
                status (str): The user's status. This can be 'listening', 'online', or 'offline'.
                icon_url (str): The user's profile icon url.
                client_id (str): The user's user id.
                client_name (str): The user's username.
                spotifysong: (SpotifySong): This is a class that contains extra data of what the user is listening to,
                    plus extra data of the user.
                index (int): This is the index of the widget in the friends list.
        """
        self.status = status
        self.icon_url = icon_url
        self.client_id = client_id
        self.client_name = client_name
        self.spotifysong = spotifysong
        self.index = index
        self.accent_color = accent_color
        url = icon_url
        if url:
            img_data = requests.get(url, timeout=15).content
            with open(data_dir + f'statusicon{client_id}.png', 'wb') as handler:
                handler.write(img_data)
        else:
            image = Image.open(data_dir + 'default_user.png').resize((120, 120))
            image.save(data_dir + f'statusicon{client_id}.png')
        mask = Image.open(data_dir + 'mask.png').convert('L')
        mask = mask.resize((120, 120))
        im = Image.open(data_dir + f'statusicon{client_id}.png').convert('RGBA')
        if status == 'offline' and icon_url:
            im = ImageOps.grayscale(im)

        output = ImageOps.fit(im, mask.size, centering=(0.5, 0.5))
        output.putalpha(mask)

        back = Image.open(data_dir + f'{status}.png').convert('RGBA')
        back.paste(output, (15, 15), mask)

        back = back.resize((50, 50))

        padding = Image.new('RGBA', (80, 70), (0, 0, 0, 0))
        padding.paste(back, (6, 10))

        padding.save(data_dir + f'statusicon{client_id}.png')

    def convert_to_widget(self):
        return StatusWidget(self.status, self.icon_url, self.client_id, self.client_name, self.spotifysong,
                            self.accent_color)

    def convert_to_secondary_widget(self):
        return FriendsListStatusWidget(self.status, self.icon_url, self.client_id, self.client_name, self.spotifysong,
                                       self.accent_color)


@adjust_sizing()
class StatusWidget(QtWidgets.QWidget):
    def __init__(self, status: str, icon_url: str, client_id: str, client_name: str, spotifysong: SpotifySong,
                 accent_color: tuple, *args, **kwargs):
        """
            This is the QWidget implementation of the PartialStatusWidget.

            Parameters:
                status (str): The user's status. This can be 'listening', 'online', or 'offline'.
                icon_url (str): The user's profile icon url.
                client_id (str): The user's client id.
                client_name (str): The user's username.
                spotifysong: (SpotifySong): This is a class that contains extra data of what the user is listening to,
                    plus extra data of the user.
                index (int): This is the index of the widget in the friends list.
        """
        QtWidgets.QWidget.__init__(self, *args, **kwargs)
        self.status = status
        self.icon_url = icon_url
        self.client_id = client_id
        self.client_name = client_name
        self.accent_color = accent_color
        self.spotifysong = spotifysong
        self.setObjectName("WidgetForm")
        self.setStyleSheet("""
        QMenu::item:selected {
            background-color: rgb(73, 77, 83);
        }
        QMenu {
            background-color: rgb(33, 37, 43);
            border: none;
        }
        QMenu::item:pressed {
            background-color: rgb(103, 107, 113);
        }""")
        self.horizontalLayout = QtWidgets.QHBoxLayout()
        self.horizontalLayout.setObjectName("verticalLayout")
        self.pushButton = QtWidgets.QPushButton(self)
        font = QtGui.QFont()
        font.setFamily("Segoe UI")
        font.setPointSize(8)
        self.pushButton.setObjectName("pushButton")
        self.pushButton.setFont(font)
        if spotifysong.song_authors:
            song_authors = ', '.join(spotifysong.song_authors)
        else:
            song_authors = 'Unknown'
        ratio = get_ratio()
        scaled = ''
        if ratio != 1:
            scale_one(f'{forward_data_dir}statusicon{client_id}', ratio)
            scaled = 'scaled'
        self.pushButton.setText(limit_text_smart(self.client_name, self.pushButton, 115 * ratio))
        listeningcolor = {'listening': 'rgb(32, 206, 93)', 'online': 'rgb(0, 120, 192)', 'offline': 'rgb(27, 29, 35)'}
        self.pushButton.setStyleSheet('''QPushButton {
                background-image: url(%s);
                border-style: outset;
                background-position: left;
                background-repeat: no-repeat;
                border-width: 4px;
                border-radius: 20px;
                border-color: %s;
                background-color: rgba(27, 29, 35, 0);
                text-align: left;
                padding-left: 65px;
                border-left: 4px solid %s;
                }
                QPushButton:hover {
                        background-color: rgba(33, 37, 43, 0);
                }
                QPushButton:pressed {
                        background-color: rgb%s;
                }
                QToolTip { 
                    color: #ffffff; 
                    background-color: rgb(0, 0, 0); 
                    border: 10px; 
                    border-radius: 10;
                }''' % (f'{forward_data_dir}statusicon{client_id}{scaled}.png', listeningcolor[status],
                        listeningcolor[status], repr(self.accent_color)))
        self.horizontalLayout.addWidget(self.pushButton)
        text_width = self.pushButton.fontMetrics().boundingRect(self.pushButton.text()).width() + 10 * ratio
        self.maxAmount = int(75 * ratio + text_width)
        scaleAmount = 70
        self.resize(scaleAmount, 70)
        self.setMinimumSize(80, 80)
        self.setMaximumSize(80, 80)
        self.pushButton.resize(70, 70)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Minimum)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.pushButton.sizePolicy().hasHeightForWidth())
        self.pushButton.setSizePolicy(sizePolicy)
        self.pushButton.setMaximumWidth(self.maxAmount)
        self.pushButton.setMouseTracking(True)
        self.animation = None
        self.animation2 = None
        self.animationgroup = None
        self.isopened = False

        def mouseMoveEvent(a0):
            if not self.isopened:
                self.animation = QtCore.QPropertyAnimation(self.pushButton, b'minimumWidth')
                self.animation.setDuration(150)
                self.animation.setStartValue(self.pushButton.width())
                self.animation.setEndValue(self.maxAmount)
                self.animation.setEasingCurve(QtCore.QEasingCurve.InOutQuart)
                self.animation2 = QtCore.QPropertyAnimation(self, b'maximumWidth')
                self.animation2.setDuration(150)
                self.animation2.setStartValue(self.width())
                self.animation2.setEndValue(self.maxAmount + 10 * ratio)
                self.animation2.setEasingCurve(QtCore.QEasingCurve.InOutQuart)
                self.animationgroup = QtCore.QParallelAnimationGroup()
                self.animationgroup.addAnimation(self.animation)
                self.animationgroup.addAnimation(self.animation2)
                self.animationgroup.start()

            self.isopened = True
            a0.accept()

        def leaveEvent(a0):
            if self.isopened:
                self.animation = QtCore.QPropertyAnimation(self.pushButton, b'minimumWidth')
                self.animation.setDuration(150)
                self.animation.setStartValue(self.pushButton.width())
                self.animation.setEndValue(70 * ratio)
                self.animation.setEasingCurve(QtCore.QEasingCurve.InOutQuart)
                self.animation2 = QtCore.QPropertyAnimation(self, b'maximumWidth')
                self.animation2.setDuration(150)
                self.animation2.setStartValue(self.width())
                self.animation2.setEndValue(80 * ratio)
                self.animation2.setEasingCurve(QtCore.QEasingCurve.InOutQuart)
                self.animation3 = QtCore.QPropertyAnimation(self.pushButton, b'maximumWidth')
                self.animation3.setDuration(150)
                self.animation3.setStartValue(self.pushButton.width())
                self.animation3.setEndValue(70 * ratio)
                self.animation3.setEasingCurve(QtCore.QEasingCurve.InOutQuart)
                self.animationgroup = QtCore.QParallelAnimationGroup()
                self.animationgroup.addAnimation(self.animation)
                self.animationgroup.addAnimation(self.animation2)
                self.animationgroup.addAnimation(self.animation3)
                self.animationgroup.start()

            self.isopened = False
            a0.accept()

        self.pushButton.enterEvent = mouseMoveEvent
        self.pushButton.leaveEvent = leaveEvent

        if status == 'listening':
            self.pushButton.tooltip = Tooltip(f' Listening to Spotify\n{spotifysong.songname}'
                                              f' - By {song_authors}', self.pushButton, mouseMoveEvent, 450, leaveEvent)
        elif status == 'online':
            self.pushButton.tooltip = Tooltip(f'Online', self.pushButton, mouseMoveEvent, 450,
                                              leaveEvent)
        else:
            self.pushButton.tooltip = Tooltip(f'Offline', self.pushButton, mouseMoveEvent, 450,
                                              leaveEvent)

        self.setSizePolicy(QtWidgets.QSizePolicy.MinimumExpanding, QtWidgets.QSizePolicy.Preferred)
        self.removefriend = QtWidgets.QAction('Remove Friend', parent=self)
        self.setContextMenuPolicy(QtCore.Qt.ActionsContextMenu)
        self.addAction(self.removefriend)

        def remove_friend():

            def success():
                self.hide()
                mainui.friendstatuswidgets[self.client_id].hide()

            def failure():
                if sip.isdeleted(mainui):
                    return
                mainui.show_snack_bar(SnackBar(f'An unexpected error occured while trying to remove '
                                               f'{spotifysong.clientusername} as a friend, please try again.',
                                               True, True))

            success_runner = Runnable()
            success_runner.callback.connect(success)
            failure_runner = Runnable()
            failure_runner.callback.connect(failure)

            Thread(target=mainui.client.invoke_request, args=(BASE_URL + '/friends/remove_friend',
                                                              {'target_id': spotifysong.friend_code}, 'DELETE',
                                                              success_runner.run, failure_runner.run)).start()  # why

        def create_dialog():
            mainui.active_dialog = Dialog('Remove Friend', f'Are you sure you want to remove '
                                                           f'<strong>{spotifysong.clientusername}</strong>'
                                                           f' as your friend?',
                                          'Remove Friend', remove_friend)

        self.removefriend.triggered.connect(create_dialog)

        def clicked():
            mainui.pushButton_14.click()
            mainui.advanceduserstatus.setCurrentWidget(mainui.advancedfriendstatuses[self.client_id])

        self.pushButton.clicked.connect(clicked)


@adjust_sizing()
class FriendsListStatusWidget(QtWidgets.QWidget):
    def __init__(self, status: str, icon_url: str, client_id: str, client_name: str, spotifysong: SpotifySong,
                 accent_color: tuple, *args, **kwargs):
        """
            This is a secondary QWidget implementation of the PartialStatusWidget.

            Parameters:
                status (str): The user's status. This can be 'listening', 'online', or 'offline'.
                icon_url (str): The user's profile icon url.
                client_id (str): The user's client id.
                client_name (str): The user's username.
                spotifysong: (SpotifySong): This is a class that contains extra data of what the user is listening to,
                    plus extra data of the user.
                index (int): This is the index of the widget in the friends list.
        """
        QtWidgets.QWidget.__init__(self, *args, **kwargs)
        self.status = status
        self.icon_url = icon_url
        self.client_id = client_id
        self.client_name = client_name
        self.spotifysong = spotifysong
        self.accent_color = accent_color
        self.setFixedSize(200, 70)
        self.setObjectName("WidgetForm")
        self.setStyleSheet("""
                QMenu::item:selected {
                    background-color: rgb(73, 77, 83);
                }
                QMenu {
                    background-color: rgb(33, 37, 43);
                    border: none;
                }
                QMenu::item:pressed {
                    background-color: rgb(103, 107, 113);
                }""")
        self.horizontalLayout = QtWidgets.QHBoxLayout()
        self.horizontalLayout.setObjectName("verticalLayout")
        self.pushButton = QtWidgets.QPushButton(self)
        font = QtGui.QFont()
        font.setFamily("Segoe UI")
        font.setPointSize(8)
        self.pushButton.setObjectName("pushButton")
        self.pushButton.setFont(font)
        self.pushButton.setFixedSize(200, 70)
        ratio = get_ratio()
        scaled = ''
        if ratio != 1:
            scale_one(f'{forward_data_dir}statusicon{client_id}', ratio)
            scaled = 'scaled'
        self.pushButton.setText(limit_text_smart(self.client_name, self.pushButton, 115 * ratio))
        if spotifysong.song_authors:
            song_authors = ', '.join(spotifysong.song_authors)
        else:
            song_authors = 'Unknown'
        if status == 'listening':
            self.pushButton.tooltip = Tooltip(f'Listening to Spotify\n{spotifysong.songname}'
                                              f' - By {song_authors}', self.pushButton)
        elif status == 'online':
            self.pushButton.tooltip = Tooltip(f'Online', self.pushButton)
        else:
            self.pushButton.tooltip = Tooltip(f'Offline', self.pushButton)
        listeningcolor = {'listening': 'rgb(32, 206, 93)', 'online': 'rgb(0, 120, 192)', 'offline': 'rgb(27, 29, 35)'}
        self.pushButton.setStyleSheet('''QPushButton {
                background-image: url(%s);
                border-style: outset;
                background-position: left;
                background-repeat: no-repeat;
                border-width: 4px;
                border-radius: 20px;
                border-color: %s;
                background-color: rgba(27, 29, 35, 0);
                text-align: left;
                padding-left: 65px;
                border-left: 4px solid %s;
                border-top 4px solid %s;
                }
                QPushButton:hover {
                        background-color: rgba(33, 37, 43, 0);
                }
                QPushButton:pressed {
                        background-color: rgb%s;
                }''' % (f'{forward_data_dir}statusicon{client_id}{scaled}.png', listeningcolor[status],
                        listeningcolor[status], listeningcolor[status], repr(accent_color)))
        self.horizontalLayout.addWidget(self.pushButton)

        self.removefriend = QtWidgets.QAction('Remove Friend', parent=self)
        self.setContextMenuPolicy(QtCore.Qt.ActionsContextMenu)
        self.addAction(self.removefriend)

        def remove_friend():

            def success():
                self.hide()
                mainui.statuswidgets[self.client_id].hide()

            def failure():
                if sip.isdeleted(mainui):
                    return
                mainui.show_snack_bar(SnackBar(f'An unexpected error occured while trying to remove '
                                               f'{spotifysong.clientusername} as a friend, please try again.',
                                               True, True))

            success_runner = Runnable()
            success_runner.callback.connect(success)
            failure_runner = Runnable()
            failure_runner.callback.connect(failure)

            Thread(target=mainui.client.invoke_request, args=(BASE_URL + '/friends/remove_friend',
                                                              {'target_id': spotifysong.friend_code}, 'DELETE',
                                                              success_runner.run, failure_runner.run)).start()  # why

        def create_dialog():
            mainui.active_dialog = Dialog('Remove Friend', f'Are you sure you want to remove '
                                                           f'<strong>{spotifysong.clientusername}</strong>'
                                                           f' as your friend?',
                                          'Remove Friend', remove_friend)

        self.removefriend.triggered.connect(create_dialog)

        def clicked():
            mainui.pushButton_14.click()
            mainui.advanceduserstatus.setCurrentWidget(mainui.advancedfriendstatuses[self.client_id])

        self.pushButton.clicked.connect(clicked)


class PartialBasicUserStatusWidget:
    def __init__(self, status: str, icon_url: str, mainstatus: SpotifySong):
        """
            This is a class that loads the initial user status widget, to be later converted into a QWidget.

            Parameters:
                status (str): The user's status. This can be 'listening', 'online', or 'offline'.
                icon_url (str): The user's profile icon url.
                mainstatus: (SpotifySong): This is a class that contains extra data of what the user is listening to,
                    plus extra data of the user.
        """
        self.status = status
        self.icon_url = icon_url
        self.mainstatus = mainstatus
        if not os.path.exists(data_dir + f'icon{mainstatus.client_id}.png'):
            url = icon_url
            rand = random.randint(0, 10000)
            if url is not None:
                img_data = requests.get(url, timeout=15).content
                with open(data_dir + f'partialicon{rand}{mainstatus.client_id}.png', 'wb') as handler:
                    handler.write(img_data)
            else:
                image = Image.open(data_dir + 'default_user.png').resize((200, 200))
                image.save(data_dir + f'partialicon{rand}{mainstatus.client_id}.png')
            mask = Image.open(data_dir + 'mask.png').convert('L')
            mask = mask.resize((200, 200))
            im = Image.open(data_dir + f'partialicon{rand}{mainstatus.client_id}.png').convert('RGBA')
            output = ImageOps.fit(im, mask.size, centering=(0.5, 0.5))
            output.putalpha(mask)
            output.resize((200, 200))
            output.save(data_dir + f'icon{mainstatus.client_id}.png')
            try:
                os.remove(data_dir + f'partialicon{rand}{mainstatus.client_id}.png')
            except (FileNotFoundError, OSError, PermissionError):
                pass
        shadow_color = None
        if mainstatus.songname:
            download_album(mainstatus.albumimagelink)
            self.dominant_color, self.dark_color, self.text_color = extract_color(mainstatus.albumimagelink)
            feather_image(mainstatus.albumimagelink)
            with open(data_dir + 'profile_cache.json') as imagefile:
                profile_images = json.load(imagefile)
            if mainstatus.client_id in profile_images:
                avg = np.average(profile_images[mainstatus.client_id][0])
                if avg > 200:
                    shadow_color = [255, 255, 255, 200]
                else:
                    shadow_color = [0, 0, 0, 200]
        else:
            with open(data_dir + 'profile_cache.json') as imagefile:
                profile_images = json.load(imagefile)
            if mainstatus.client_id in profile_images:
                self.dominant_color = tuple(profile_images[mainstatus.client_id][0])
                self.dark_color = tuple(profile_images[mainstatus.client_id][1])
                self.text_color = tuple(profile_images[mainstatus.client_id][2])
                if np.average(self.dominant_color) > 200:
                    shadow_color = [255, 255, 255, 200]
                else:
                    shadow_color = [0, 0, 0, 200]
            else:
                image = ColorThief(data_dir + f'icon{mainstatus.client_id}.png')
                dominant_color = image.get_color(quality=1)
                dark_color = [color - 30 if not (color - 30) < 0 else 0 for color in dominant_color]
                if np.average(dominant_color) > 200:
                    text_color = [0, 0, 0]
                    shadow_color = [255, 255, 255, 200]
                else:
                    text_color = [255, 255, 255]
                    shadow_color = [0, 0, 0, 200]
                with open(data_dir + 'profile_cache.json', 'w') as imagefile:
                    profile_images.update({mainstatus.client_id:
                                           [list(dominant_color), list(dark_color), text_color]})
                    json.dump(profile_images, imagefile, indent=4)
                self.dominant_color = dominant_color
                self.dark_color = dark_color
                self.text_color = text_color
        self.shadow_color = shadow_color

    def convert_to_widget(self):
        if self.text_color:
            return BasicUserStatusWidget(self.status, self.icon_url, self.mainstatus, self.dominant_color,
                                         self.dark_color, text_color=self.text_color,
                                         image_url=self.mainstatus.albumimagelink, shad_color=self.shadow_color)
        else:
            return BasicUserStatusWidget(self.status, self.icon_url, self.mainstatus, self.dominant_color,
                                         self.dark_color, shad_color=self.shadow_color)


@adjust_sizing()
class BasicUserStatusWidget(QtWidgets.QWidget):
    # noinspection PyTypeChecker
    def __init__(self, status: str, icon_url: str, mainstatus: SpotifySong, dominant_color: list, dark_color: list,
                 text_color: list = None, image_url: str = None, shad_color: list = None, *args, **kwargs):
        """
            This is the QWidget implementation of PartialBasicUserStatusWidget.

            Parameters:
                status (str): The user's status. This can be 'listening', 'online', or 'offline'.
                icon_url (str): The user's profile icon url.
                mainstatus: (SpotifySong): This is a class that contains extra data of what the user is listening to,
                    plus extra data of the user.
                dominant_color (list): This is a list that contains the dominant color of the user's profile picture.
                dark_color (list): This is the dominant color, but slightly darker.
                text_color (list) (optional): This is the text color.
                image_url (str) (optional): This is the album image url.
        """
        super().__init__(*args, **kwargs)
        self.status = status
        self.icon_url = icon_url
        self.mainstatus = mainstatus
        self.text_color = text_color
        self.image_url = image_url
        self.resize(200, 250)
        self.setMinimumHeight(250)
        self.setMaximumHeight(250)
        self.setObjectName("Form")
        self.verticalLayout = QtWidgets.QVBoxLayout(self)
        self.verticalLayout.setContentsMargins(0, 0, 0, 0)
        self.verticalLayout.setSpacing(0)
        self.verticalLayout.setObjectName("verticalLayout")
        self.frame = QtWidgets.QFrame(self)
        self.frame.setStyleSheet(
            f"background-color: qlineargradient(spread:pad, x1:1, y1:0.5, x2:0, y2:0.5, "
            f"stop:0 rgba({dominant_color[0]}, {dominant_color[1]}, "
            f"{dominant_color[2]}, 255), stop:1 rgba({dark_color[0]}, {dark_color[1]}, {dark_color[2]}, 255));\n "
            f"border-radius: 40px;\n"
            "")
        self.frame.setFrameShape(QtWidgets.QFrame.StyledPanel)
        self.frame.setFrameShadow(QtWidgets.QFrame.Raised)
        self.frame.setObjectName("frame")
        self.verticalLayout_2 = QtWidgets.QVBoxLayout(self.frame)
        self.verticalLayout_2.setObjectName("verticalLayout_2")
        self.verticalLayout_2.setContentsMargins(11, 11, 11, 11)
        self.verticalLayout_2.setSpacing(7)
        self.horizontalFrame = QtWidgets.QFrame(self.frame)
        self.horizontalFrame.setStyleSheet("background-color: rgba(0, 0, 0, 0);")
        self.horizontalFrame.setObjectName("horizontalFrame")
        self.horizontalLayout = QtWidgets.QHBoxLayout(self.horizontalFrame)
        self.horizontalLayout.setContentsMargins(11, 11, 11, 11)
        self.horizontalLayout.setSpacing(15)
        self.horizontalLayout.setObjectName("horizontalLayout")
        self.verticalFrame_2 = QtWidgets.QFrame(self.horizontalFrame)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Expanding)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.verticalFrame_2.sizePolicy().hasHeightForWidth())
        self.verticalFrame_2.setSizePolicy(sizePolicy)
        self.verticalFrame_2.setMinimumSize(QtCore.QSize(200, 0))
        self.verticalFrame_2.setMaximumSize(QtCore.QSize(200, 16777215))
        self.verticalFrame_2.setStyleSheet("background-color: rgba(0, 0, 0, 0);")
        self.verticalFrame_2.setObjectName("verticalFrame_2")
        self.verticalLayout_4 = QtWidgets.QVBoxLayout(self.verticalFrame_2)
        self.verticalLayout_4.setSpacing(0)
        self.verticalLayout_4.setObjectName("verticalLayout_4")
        self.label = QtWidgets.QLabel(self.verticalFrame_2)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Minimum)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.label.sizePolicy().hasHeightForWidth())
        self.label.setSizePolicy(sizePolicy)
        self.label.setMinimumSize(QtCore.QSize(182, 182))
        self.label.setMaximumSize(QtCore.QSize(182, 182))
        self.label.setStyleSheet(
            f"border-image: url({forward_data_dir}icon{mainstatus.client_id}.png)"
            f" 0 0 0 0 strech strech;\n"
            "background-repeat: no-repeat;\n"
            "background-color: transparent;\n"
            f"border-radius: 91px;")
        self.label.setText("")
        self.label.setAlignment(QtCore.Qt.AlignHCenter)
        self.label.setObjectName("label")
        self.shadow = QtWidgets.QGraphicsDropShadowEffect(self)
        self.shadow.setBlurRadius(17)
        self.shadow.setXOffset(0)
        self.shadow.setYOffset(0)
        self.shadow.setColor(QtGui.QColor(*shad_color))
        self.label.setGraphicsEffect(self.shadow)
        self.verticalLayout_4.addWidget(self.label)
        self.spacerItem = QtWidgets.QSpacerItem(20, 40, QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Expanding)
        self.verticalLayout_4.addItem(self.spacerItem)
        self.horizontalLayout.addWidget(self.verticalFrame_2)
        self.verticalFrame = QtWidgets.QFrame(self.horizontalFrame)
        self.verticalFrame.setStyleSheet("background-color: rgba(0, 0, 0, 0);")
        self.verticalFrame.setObjectName("verticalFrame")
        self.verticalLayout_3 = QtWidgets.QVBoxLayout(self.verticalFrame)
        self.verticalLayout_3.setObjectName("verticalLayout_3")
        self.verticalLayout_3.setContentsMargins(11, 11, 11, 11)
        self.verticalLayout_3.setSpacing(7)
        self.label_2 = QtWidgets.QLabel(self.verticalFrame)
        self.label_2.setMinimumSize(QtCore.QSize(0, 140))
        self.label_2.setMaximumSize(QtCore.QSize(16777215, 140))
        font = QtGui.QFont()
        font.setFamily("Segoe UI")
        font.setPointSize(28)
        font.setBold(False)
        font.setWeight(50)
        self.label_2.setFont(font)
        if self.text_color:
            self.label_2.setStyleSheet("background-color: rgba(0, 0, 0, 0);\n"
                                       f"color: rgb({self.text_color[0]}, {self.text_color[1]}, {self.text_color[2]});")
        else:
            self.label_2.setStyleSheet("background-color: rgba(0, 0, 0, 0);\n"
                                       "color: white;")
        self.label_2.setAlignment(QtCore.Qt.AlignLeading | QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter)
        self.label_2.setObjectName("label_2")
        self.label_2.setSizePolicy(QtWidgets.QSizePolicy.Ignored, QtWidgets.QSizePolicy.Preferred)
        self.verticalLayout_3.addWidget(self.label_2)
        self.label_3 = QtWidgets.QLabel(self.verticalFrame)
        font = QtGui.QFont()
        font.setFamily("Segoe UI")
        font.setPointSize(12)
        self.label_3.setFont(font)
        if self.text_color:
            self.label_3.setStyleSheet("background-color: rgba(0, 0, 0, 0);\n"
                                       f"color: rgb({self.text_color[0]}, {self.text_color[1]}, {self.text_color[2]});")
        else:
            self.label_3.setStyleSheet("background-color: rgba(0, 0, 0, 0);\n"
                                       "color: white;")
        self.label_3.setAlignment(QtCore.Qt.AlignLeading | QtCore.Qt.AlignLeft | QtCore.Qt.AlignTop)
        self.label_3.setObjectName("label_3")
        self.label_3.setSizePolicy(QtWidgets.QSizePolicy.Ignored, QtWidgets.QSizePolicy.Preferred)
        if mainstatus.song_authors:
            song_authors = ', '.join(mainstatus.song_authors)
        else:
            song_authors = 'Unknown'
        if status == 'listening':
            self.full_text = f'Listening to Spotify - {mainstatus.songname} - By {song_authors}'
        elif status == 'online':
            self.full_text = 'Online'
        else:
            self.full_text = 'Offline'
        self.verticalLayout_3.addWidget(self.label_3)
        self.horizontalLayout.addWidget(self.verticalFrame)
        self.verticalLayout_2.addWidget(self.horizontalFrame)
        self.verticalLayout.addWidget(self.frame)
        if not self.image_url:
            self.image_url = 'None/image/None'
        if mainstatus.playing_type in ('track', 'local file'):
            self.label_4 = QtWidgets.QLabel(self.horizontalFrame)
            self.label_4.setStyleSheet('''QLabel {
                border-image: url(%s) 0 0 0 0 strech strech;
                border-radius: 0px;
            }''' % f"{forward_data_dir}album{self.image_url.split('/image/')[1]}.png")
            self.label_4.setFixedSize(200, 200)
            self.horizontalLayout.addWidget(self.label_4)

    def resizeEvent(self, a0: QtGui.QResizeEvent) -> None:
        QtWidgets.QWidget.resizeEvent(self, a0)
        self.label_2.setText(limit_text_smart(self.mainstatus.clientusername, self.label_2))
        self.label_3.setText(limit_text_smart(self.full_text, self.label_3))

    def showEvent(self, a0: QtGui.QShowEvent) -> None:
        QtWidgets.QWidget.showEvent(self, a0)
        self.label_2.setText(limit_text_smart(self.mainstatus.clientusername, self.label_2))
        self.label_3.setText(limit_text_smart(self.full_text, self.label_3))


class PartialPlaybackController:
    def __init__(self, mainstatus: SpotifySong, spotifyplayer: SpotifyPlayer, client):
        """
            This is a class that loads the initial playback controller, to be later converted into a QWidget.
            Parameters:
                mainstatus (SpotifySong): This represents the user's playing status.
                spotifyplayer (SpotifyPlayer): This represents the interactive spotify player.
        """
        self.mainstatus = mainstatus
        self.spotifyplayer = spotifyplayer
        self.client = client
        self.dominant_color = None
        self.dark_color = None
        self.text_color = None
        self.is_saved = False
        self.shuffle_state = False
        self.is_playing = False
        self.loop_state = ''
        self.volume = 65535
        self.song_length = 0
        if mainstatus.playing_type in ('track', 'local file'):
            if mainstatus.songid:
                saved_songs = spotifyplayer.create_api_request(f'/me/tracks/contains?ids={mainstatus.songid}').json()
                if isinstance(saved_songs, dict) and saved_songs.get('status', 401) != 200:
                    # noinspection PyProtectedMember
                    spotifyplayer._authorize()
                    saved_songs = spotifyplayer.create_api_request(f'/me/tracks/contains?ids={mainstatus.songid}')
                    saved_songs = saved_songs.json()
                if not saved_songs:
                    self.is_saved = False
                else:
                    self.is_saved = saved_songs[0]
            else:
                self.is_saved = False
            self.shuffle_state = spotifyplayer.shuffling
            self.is_playing = spotifyplayer.playing
            self.volume = spotifyplayer.current_volume
            self.song_length = mainstatus.duration
            url = mainstatus.albumimagelink
            download_album(url)
            dominant_color, dark_color, text_color = extract_color(url)
            self.dominant_color = dominant_color
            self.dark_color = dark_color
            self.text_color = text_color
            feather_image(url)
            icons = [f'24x24{sep}cil-media-play.png', f'24x24{sep}cil-media-pause.png', f'20x20{sep}cil-media-step-forward.png',
                     f'20x20{sep}cil-media-step-backward.png', f'16x16{sep}cil-shuffle.png', f'16x16{sep}cil-shuffle-on.png',
                     f'16x16{sep}cil-loop.png', f'16x16{sep}cil-loop-on.png', f'16x16{sep}cil-loop-1.png', f'20x20{sep}cil-heart.png',
                     f'20x20{sep}cil-heart-filled.png', f'16x16{sep}cil-screen-smartphone.png', f'16x16{sep}cil-volume-high.png',
                     f'16x16{sep}cil-volume-low.png', f'16x16{sep}cil-volume-off.png']
            icons = [data_dir + f'icons{sep}' + icon for icon in icons]
            for icon in icons:
                img = Image.open(icon)
                img = img.convert('RGBA')
                pixdata: typing.Optional[PyAccess] = img.load()
                for y in range(img.size[1]):
                    for x in range(img.size[0]):
                        if pixdata[x, y][3] > 0:
                            new_color = list(text_color)
                            new_color.append(pixdata[x, y][3])
                            pixdata[x, y] = tuple(new_color)
                img.save(icon)

    def convert_to_widget(self):
        return PlaybackController(self.mainstatus, self.spotifyplayer, self.client, self.dominant_color,
                                  self.dark_color, self.text_color, self.is_saved)


@safe_color
@adjust_sizing()
class PlaybackController(QtWidgets.QWidget):
    def __init__(self, spotifysong: SpotifySong, spotifyplayer: SpotifyPlayer, client,
                 dominant_color: tuple = None, dark_color: tuple = None, text_color: tuple = None,
                 is_saved: bool = False, *args, **kwargs):
        """
            This is a class that represents the playback controller.
            Parameters:
                spotifysong (SpotifySong): This is a representation of the user's playback.
                spotifyplayer (SpotifyPlayer): This is a class that handles the changing of the user's playback state.
        """
        super().__init__(*args, **kwargs)
        self.spotifysong = spotifysong
        self.spotifyplayer = spotifyplayer
        self.client = client
        self.dominant_color = dominant_color
        self.dark_color = dark_color
        self.text_color = text_color
        self.is_saved = is_saved
        self.shuffle_state = spotifyplayer.shuffling
        self.is_playing = spotifyplayer.playing
        self.loop_state = spotifyplayer.looping
        self.volume = spotifyplayer.current_volume
        self.verticalLayout = QtWidgets.QVBoxLayout(self)
        self.verticalLayout.setContentsMargins(0, 0, 0, 0)
        self.verticalLayout.setSpacing(0)
        self.verticalLayout.setObjectName("verticalLayout")
        self.scaled = ''
        ratio = get_ratio()
        self.ratio = ratio
        if ratio != 1:
            self.ratio = ratio
            icons = [f'24x24{sep}cil-media-play', f'24x24{sep}cil-media-pause', f'20x20{sep}cil-media-step-forward',
                     f'20x20{sep}cil-media-step-backward', f'16x16{sep}cil-shuffle', f'16x16{sep}cil-shuffle-on',
                     f'16x16{sep}cil-loop', f'16x16{sep}cil-loop-on', f'16x16{sep}cil-loop-1', f'20x20{sep}cil-heart',
                     f'20x20{sep}cil-heart-filled', f'16x16{sep}cil-screen-smartphone', f'16x16{sep}cil-volume-high',
                     f'16x16{sep}cil-volume-low', f'16x16{sep}cil-volume-off']
            scale_images(icons, ratio)
            self.scaled = 'scaled'
        if not dominant_color:
            self.text = QtWidgets.QLabel()
            font = QtGui.QFont()
            font.setFamily("Segoe UI")
            font.setPointSize(14)
            self.text.setFont(font)
            self.text.setText('     Nothing Currently Playing')
            self.verticalLayout.addWidget(self.text)
            self.is_player = False
            return
        if not spotifysong.songid:
            albumimagelink = 'None'
        else:
            albumimagelink = spotifysong.albumimagelink.split('/image/')[1]
        self.is_player = True
        self.horizontalFrame = QtWidgets.QFrame(self)
        self.horizontalFrame.setMinimumSize(QtCore.QSize(0, 120))
        self.horizontalFrame.setMaximumSize(QtCore.QSize(16777215, 120))
        self.horizontalFrame.setStyleSheet(
            f"background-color: qlineargradient(spread:pad, x1:0, y1:0, x2:1, y2:0, stop:0 rgba({dominant_color[0]}, "
            f"{dominant_color[1]}, {dominant_color[2]}, 255), "
            f"stop:1 rgba({dark_color[0]}, {dark_color[1]}, {dark_color[2]}, 255));")
        self.horizontalFrame.setObjectName("horizontalFrame")
        self.horizontalLayout_3 = QtWidgets.QHBoxLayout(self.horizontalFrame)
        self.horizontalLayout_3.setContentsMargins(10, 0, 10, 0)
        self.horizontalLayout_3.setSpacing(0)
        self.horizontalLayout_3.setObjectName("horizontalLayout_3")
        self.horizontalFrame1 = QtWidgets.QFrame(self.horizontalFrame)
        self.horizontalFrame1.setMinimumSize(QtCore.QSize(0, 100))
        self.horizontalFrame1.setMaximumSize(QtCore.QSize(16777215, 100))
        self.horizontalFrame1.setObjectName("horizontalFrame1")
        self.horizontalLayout = QtWidgets.QHBoxLayout(self.horizontalFrame1)
        self.horizontalLayout.setContentsMargins(0, 0, 0, 0)
        self.horizontalLayout.setSpacing(20)
        self.horizontalLayout.setObjectName("horizontalLayout")
        self.label = QtWidgets.QLabel(self.horizontalFrame1)
        self.label.setMinimumSize(QtCore.QSize(100, 0))
        self.label.setMaximumSize(QtCore.QSize(100, 16777215))
        self.label.setStyleSheet(
            f"border-image: url({forward_data_dir}album{albumimagelink}."
            f"png) 0 0 0 0 strech strech;\nbackground-color: rgba(0, 0, 0, 0);")
        self.label.setText("")
        self.label.setObjectName("label")
        self.horizontalLayout.addWidget(self.label)
        self.horizontalFrame_2 = QtWidgets.QFrame(self.horizontalFrame1)
        self.horizontalFrame_2.setStyleSheet("background-color: rgba(0, 0, 0, 0);")
        self.horizontalFrame_2.setObjectName("horizontalFrame_2")
        self.horizontalLayout_4 = QtWidgets.QHBoxLayout(self.horizontalFrame_2)
        self.horizontalLayout_4.setContentsMargins(0, 0, 0, 0)
        self.horizontalLayout_4.setObjectName("horizontalLayout_4")
        self.verticalFrame = QtWidgets.QFrame(self.horizontalFrame_2)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Maximum, QtWidgets.QSizePolicy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.verticalFrame.sizePolicy().hasHeightForWidth())
        self.verticalFrame.setSizePolicy(sizePolicy)
        self.verticalFrame.setObjectName("verticalFrame")
        self.verticalLayout_2 = QtWidgets.QVBoxLayout(self.verticalFrame)
        self.verticalLayout_2.setContentsMargins(0, 0, 0, 0)
        self.verticalLayout_2.setObjectName("verticalLayout_2")
        self.label_2 = QtWidgets.QLabel(self.verticalFrame)
        self.label_2.setMinimumSize(QtCore.QSize(0, 35))
        self.label_2.setMaximumSize(QtCore.QSize(16777215, 35))
        font = QtGui.QFont()
        font.setFamily("Segoe UI")
        font.setPointSize(14)
        self.label_2.setFont(font)
        self.label_2.setStyleSheet(f"color: rgb{text_color};")
        self.label_2.setAlignment(QtCore.Qt.AlignBottom | QtCore.Qt.AlignLeading | QtCore.Qt.AlignLeft)
        self.label_2.setObjectName("label_2")
        self.label_2.setText(limit_text(spotifysong.songname, 25))
        if self.label_2.text()[-3:] == '...':
            self.label_2.tooltip = Tooltip(spotifysong.songname, self.label_2)
        self.verticalLayout_2.addWidget(self.label_2)
        self.label_3 = QtWidgets.QLabel(self.verticalFrame)
        font = QtGui.QFont()
        font.setFamily("Segoe UI")
        font.setPointSize(9)
        self.label_3.setFont(font)
        self.label_3.setStyleSheet(f"color: rgb{text_color};")
        self.label_3.setObjectName("label_3")
        if spotifysong.song_authors:
            song_authors = limit_text(', '.join(spotifysong.song_authors), 30)
            if song_authors[-3:] == '...':
                self.label_3.tooltip = Tooltip(', '.join(spotifysong.song_authors), self.label_3)
        else:
            song_authors = 'Unknown'
        self.label_3.setText(f'By <strong>{song_authors}</strong>')
        self.verticalLayout_2.addWidget(self.label_3)
        self.label_4 = QtWidgets.QLabel(self.verticalFrame)
        font = QtGui.QFont()
        font.setFamily("Segoe UI")
        font.setPointSize(9)
        self.label_4.setFont(font)
        self.label_4.setStyleSheet(f"color: rgb{text_color};")
        self.label_4.setObjectName("label_4")
        if spotifysong.albumname:
            albumname = limit_text(spotifysong.albumname, 30)
            if albumname[-3:] == '...':
                self.label_4.tooltip = Tooltip(spotifysong.albumname, self.label_4)
        else:
            albumname = 'Unknown'
        self.label_4.setText(f'On <strong>{albumname}</strong>')
        self.verticalLayout_2.addWidget(self.label_4)
        self.horizontalLayout_4.addWidget(self.verticalFrame)
        self.horizontalLayout.addWidget(self.horizontalFrame_2)
        self.verticalFrame1 = QtWidgets.QFrame(self.horizontalFrame1)
        self.verticalFrame1.setMinimumSize(QtCore.QSize(25, 25))
        self.verticalFrame1.setMaximumSize(QtCore.QSize(25, 16777215))
        self.verticalFrame1.setStyleSheet("background-color: rgba(0, 0, 0, 0);")
        self.verticalFrame1.setObjectName("verticalFrame1")
        self.verticalLayout_4 = QtWidgets.QVBoxLayout(self.verticalFrame1)
        self.verticalLayout_4.setContentsMargins(0, 0, 0, 0)
        self.verticalLayout_4.setSpacing(0)
        self.verticalLayout_4.setObjectName("verticalLayout_4")
        self.spacerItem = QtWidgets.QSpacerItem(20, 11, QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Maximum)
        self.verticalLayout_4.addItem(self.spacerItem)
        self.pushButton_6 = QtWidgets.QPushButton(self.verticalFrame1)
        self.pushButton_6.setMinimumSize(QtCore.QSize(25, 25))
        self.pushButton_6.setMaximumSize(QtCore.QSize(25, 25))
        self.pushButton_6.setFixedSize(25, 25)
        self.pushButton_6.setText("")
        self.pushButton_6.setObjectName("pushButton_6")
        self.verticalLayout_4.addWidget(self.pushButton_6)
        self.spacerItem1 = QtWidgets.QSpacerItem(20, 40, QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Expanding)
        self.verticalLayout_4.addItem(self.spacerItem1)
        self.horizontalLayout.addWidget(self.verticalFrame1)
        self.verticalFrame2 = QtWidgets.QFrame(self.horizontalFrame1)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.verticalFrame2.sizePolicy().hasHeightForWidth())
        self.verticalFrame2.setSizePolicy(sizePolicy)
        self.verticalFrame2.setStyleSheet("background-color: rgba(0, 0, 0, 0);")
        self.verticalFrame2.setObjectName("verticalFrame2")
        self.verticalLayout_3 = QtWidgets.QVBoxLayout(self.verticalFrame2)
        self.verticalLayout_3.setContentsMargins(0, 0, 0, 0)
        self.verticalLayout_3.setObjectName("verticalLayout_3")
        self.horizontalFrame2 = QtWidgets.QFrame(self.verticalFrame2)
        self.horizontalFrame2.setObjectName("horizontalFrame2")
        self.horizontalLayout_7 = QtWidgets.QHBoxLayout(self.horizontalFrame2)
        self.horizontalLayout_7.setObjectName("horizontalLayout_7")
        self.horizontalFrame_21 = QtWidgets.QFrame(self.horizontalFrame2)
        self.horizontalFrame_21.setMinimumSize(QtCore.QSize(338, 28))
        self.horizontalFrame_21.setMaximumSize(QtCore.QSize(338, 28))
        self.horizontalFrame_21.setObjectName("horizontalFrame_21")
        self.horizontalLayout_6 = QtWidgets.QHBoxLayout(self.horizontalFrame_21)
        self.horizontalLayout_6.setContentsMargins(0, 0, 0, 0)
        self.horizontalLayout_6.setSpacing(0)
        self.horizontalLayout_6.setObjectName("horizontalLayout_6")
        self.pushButton_5 = QtWidgets.QPushButton(self.horizontalFrame_21)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Expanding)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.pushButton_5.sizePolicy().hasHeightForWidth())
        self.pushButton_5.setSizePolicy(sizePolicy)
        self.pushButton_5.setText("")
        self.pushButton_5.setObjectName("pushButton_5")
        self.pushButton_5.setFixedHeight(28)
        self.horizontalLayout_6.addWidget(self.pushButton_5)
        self.pushButton_4 = QtWidgets.QPushButton(self.horizontalFrame_21)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Expanding)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.pushButton_4.sizePolicy().hasHeightForWidth())
        self.pushButton_4.setSizePolicy(sizePolicy)
        self.pushButton_4.setStyleSheet(
            f"background-image: url({forward_data_dir}icons/20x20/cil-media-step-backward{self.scaled}.png);\n"
            "background-repeat: none;\n"
            "background-position: center;")

        self.pushButton_4.clicked.connect(lambda: Thread(target=lambda:
                                          self.spotifyplayer.command(self.spotifyplayer.previous)).start())
        self.pushButton_4.setText("")
        self.pushButton_4.setObjectName("pushButton_4")
        self.horizontalLayout_6.addWidget(self.pushButton_4)
        self.pushButton_3 = QtWidgets.QPushButton(self.horizontalFrame_21)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Expanding)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.pushButton_3.sizePolicy().hasHeightForWidth())
        self.pushButton_3.setSizePolicy(sizePolicy)
        self.pushButton_3.setText("")
        self.pushButton_3.setObjectName("pushButton_3")
        self.horizontalLayout_6.addWidget(self.pushButton_3)
        self.pushButton_2 = QtWidgets.QPushButton(self.horizontalFrame_21)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Expanding)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.pushButton_2.sizePolicy().hasHeightForWidth())
        self.pushButton_2.setSizePolicy(sizePolicy)
        self.pushButton_2.setStyleSheet(
            f"background-image: url({forward_data_dir}icons/20x20/cil-media-step-forward{self.scaled}.png);\n"
            "background-repeat: none;\n"
            "background-position: center;")

        self.pushButton_2.clicked.connect(lambda: Thread(target=lambda:
                                          self.spotifyplayer.command(self.spotifyplayer.skip)).start())
        self.pushButton_2.setText("")
        self.pushButton_2.setObjectName("pushButton_2")
        self.horizontalLayout_6.addWidget(self.pushButton_2)
        self.pushButton = QtWidgets.QPushButton(self.horizontalFrame_21)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.pushButton.sizePolicy().hasHeightForWidth())
        self.pushButton.setSizePolicy(sizePolicy)
        self.pushButton.setMinimumSize(QtCore.QSize(0, 0))
        self.pushButton.setMaximumSize(QtCore.QSize(16777215, 16777215))
        self.pushButton.setText("")
        self.pushButton.setObjectName("pushButton")
        self.pushButton.setFixedHeight(28)
        self.horizontalLayout_6.addWidget(self.pushButton)
        self.horizontalLayout_7.addWidget(self.horizontalFrame_21)
        self.verticalLayout_3.addWidget(self.horizontalFrame2)
        self.horizontalFrame3 = QtWidgets.QFrame(self.verticalFrame2)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.horizontalFrame3.sizePolicy().hasHeightForWidth())
        self.horizontalFrame3.setSizePolicy(sizePolicy)
        self.horizontalFrame3.setMinimumSize(QtCore.QSize(55, 48))
        self.horizontalFrame3.setMaximumSize(QtCore.QSize(16777215, 48))
        self.horizontalFrame3.setObjectName("horizontalFrame3")
        self.horizontalLayout_5 = QtWidgets.QHBoxLayout(self.horizontalFrame3)
        self.horizontalLayout_5.setObjectName("horizontalLayout_5")
        self.label_5 = QtWidgets.QLabel(self.horizontalFrame3)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Maximum, QtWidgets.QSizePolicy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.label_5.sizePolicy().hasHeightForWidth())
        self.label_5.setSizePolicy(sizePolicy)
        font = QtGui.QFont()
        font.setFamily("Segoe UI")
        font.setPointSize(8)
        self.label_5.setFont(font)
        self.label_5.setStyleSheet(f"color: rgb{text_color};")
        self.label_5.setObjectName("label_5")

        def label_time():
            if self.slider_raw_position <= 0.4 * 100:
                current_time = f'0:00'
            elif self.slider_raw_position >= 100.2 * 100:
                current_time = self.label_6.text()
            else:
                minutes = self.slider_raw_position / 10000 * (spotifysong.duration / 1000) // 60
                seconds = self.slider_raw_position / 10000 * (spotifysong.duration // 1000) - \
                    minutes * 60
                if seconds <= 1:
                    seconds = 0
                current_time = f'{int(minutes)}:{(int(seconds)):02}'
            try:
                self.label_5.setText(current_time)
            except RuntimeError:
                pass

        self.timer3 = QtCore.QTimer()
        self.timer3.setInterval(100)
        self.timer3.timeout.connect(label_time)
        self.timer3.start()
        self.horizontalLayout_5.addWidget(self.label_5)
        self.horizontalSlider = QtWidgets.QSlider(self.horizontalFrame3)
        self.horizontalSlider.setMinimumSize(QtCore.QSize(0, 30))
        self.horizontalSlider.setMaximum(10000)
        self.horizontalSlider.setMinimum(0)
        self.slider_clicked = False
        self.slider_release_time = 0
        self.slider_raw_position = 0

        def fill_slider(touch=False):
            if self.slider_raw_position <= 50:
                if not touch:
                    self.horizontalSlider.setSliderPosition(0)
                    self.horizontalSlider.setStyleSheet(adj_style(ratio, """QSlider::groove:horizontal {
                                                        border-radius: 7px;
                                                        height: 15px;
                                                        background-color: rgba(52, 59, 72, 50);
                                                        }
                                                        QSlider::groove:horizontal:hover {
                                                        background-color: rgba(55, 62, 76, 50);
                                                        }
                                                        QSlider::handle:horizontal {
                                                        background-color: rgbreplace;
                                                        border: none;
                                                        height: 15px;
                                                        width: 15px;
                                                        border-radius: 7px;
                                                        margin-top: 0px;
                                                        margin-bottom: 0px;
                                                        }""").replace('replace', repr(text_color)))
                else:
                    self.horizontalSlider.setStyleSheet(adj_style(ratio, """QSlider::groove:horizontal {
                                                    border-radius: 7px;
                                                    height: 15px;
                                                    background-color: rgba(52, 59, 72, 50);
                                                    }
                                                    QSlider::groove:horizontal:hover {
                                                        background-color: rgba(55, 62, 76, 50);
                                                    }
                                                    QSlider::handle:horizontal {
                                                        background-color: rgbreplace;
                                                        border: none;
                                                        height: 26px;
                                                        width: 26px;
                                                        margin-top: -6px;
                                                        margin-bottom: -6px;
                                                        border-radius: 13px;
                                                    }
                                                    QSlider::sub-page:horizontal {
                                                        background-color: rgbreplace;
                                                        border-radius: 7px;
                                                    }""").replace('replace', repr(text_color)))
            else:
                if not touch:
                    self.horizontalSlider.setStyleSheet(adj_style(ratio, """QSlider::groove:horizontal {
                                border-radius: 7px;
                                height: 15px;
                                background-color: rgba(52, 59, 72, 50);
                                }
                                QSlider::groove:horizontal:hover {
                                background-color: rgba(55, 62, 76, 50);
                                }
                                QSlider::handle:horizontal {
                                background-color: rgbreplace;
                                border: none;
                                height: 15px;
                                width: 18px;
                                border-radius: 7px;
                                margin-top: 0px;
                                margin-bottom: 0px;
                                }
                                QSlider::sub-page:horizontal {
                                background-color: rgbreplace;
                                border-radius: 7px;
                                }""").replace('replace', repr(text_color)))
                else:
                    self.horizontalSlider.setStyleSheet(adj_style(ratio, """QSlider::groove:horizontal {
                                border-radius: 7px;
                                height: 15px;
                                background-color: rgba(52, 59, 72, 50);
                                }
                                QSlider::groove:horizontal:hover {
                                    background-color: rgba(55, 62, 76, 50);
                                }
                                QSlider::handle:horizontal {
                                    background-color: rgbreplace;
                                    border: none;
                                    height: 26px;
                                    width: 26px;
                                    margin-top: -6px;
                                    margin-bottom: -6px;
                                    border-radius: 13px;
                                }
                                QSlider::sub-page:horizontal {
                                    background-color: rgbreplace;
                                    border-radius: 7px;
                                }""").replace('replace', repr(text_color)))

        def release(a0):
            self.slider_clicked = False
            self.slider_release_time = time.time()
            if a0.pos().x() == 0:
                Thread(target=lambda: self.spotifyplayer.command(self.spotifyplayer.seek_to(0))).start()
                self.slider_raw_position = 0
                self.horizontalSlider.setSliderPosition(0)
                fill_slider(True)
            else:
                Thread(target=lambda: self.spotifyplayer.
                       command(self.spotifyplayer.seek_to(1 / (self.horizontalSlider.width() / a0.pos().x()) *
                                                          spotifysong.duration))).start()
                self.slider_raw_position = 10000 // (self.horizontalSlider.width() / a0.pos().x())
                self.horizontalSlider.setSliderPosition(self.slider_raw_position)

        def drag(a0):
            self.slider_clicked = True
            self.slider_release_time = 0
            if a0.pos().x() == 0:
                self.slider_raw_position = 0
                self.horizontalSlider.setSliderPosition(0)
            else:
                self.slider_raw_position = 10000 // (self.horizontalSlider.width() / a0.pos().x())
                self.horizontalSlider.setSliderPosition(self.slider_raw_position)

        self.horizontalSlider.mouseReleaseEvent = release
        self.horizontalSlider.mousePressEvent = drag
        self.horizontalSlider.mouseMoveEvent = drag

        def pos():
            if not self.slider_clicked and time.time() - self.slider_release_time > 1:
                self.slider_raw_position = spotifyplayer.get_position() / (spotifysong.duration / 1000) * 10000
                self.slider_raw_position = min(2147483646, self.slider_raw_position)
                self.slider_raw_position = max(-2147483647, self.slider_raw_position)
                self.horizontalSlider.setSliderPosition(int(self.slider_raw_position))
                if not self.horizontalSlider.underMouse():
                    fill_slider()
                else:
                    fill_slider(True)

        self.timer2 = QtCore.QTimer()
        self.timer2.setInterval(100)
        self.timer2.timeout.connect(pos)
        self.timer2.start()

        pos()
        fill_slider()
        self.horizontalSlider.enterEvent = lambda a0: self.horizontalSlider. \
            setStyleSheet(adj_style(ratio, """QSlider::groove:horizontal {
                                border-radius: 7px;
                                height: 15px;
                                background-color: rgba(52, 59, 72, 50);
                                }
                                QSlider::groove:horizontal:hover {
                                    background-color: rgba(55, 62, 76, 50);
                                }
                                QSlider::handle:horizontal {
                                    background-color: rgbreplace;
                                    border: none;
                                    height: 26px;
                                    width: 26px;
                                    margin-top: -6px;
                                    margin-bottom: -6px;
                                    border-radius: 13px;
                                }
                                QSlider::sub-page:horizontal {
                                    background-color: rgbreplace;
                                    border-radius: 7px;
                                }""").replace('replace', repr(text_color)))
        self.horizontalSlider.leaveEvent = lambda a0: fill_slider()
        self.horizontalSlider.setAttribute(QtCore.Qt.WA_AcceptTouchEvents, True)
        self.horizontalSlider.setOrientation(QtCore.Qt.Horizontal)
        self.horizontalSlider.setObjectName("horizontalSlider")
        self.horizontalLayout_5.addWidget(self.horizontalSlider)
        self.label_6 = QtWidgets.QLabel(self.horizontalFrame3)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Maximum, QtWidgets.QSizePolicy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.label_6.sizePolicy().hasHeightForWidth())
        self.label_6.setSizePolicy(sizePolicy)
        font = QtGui.QFont()
        font.setFamily("Segoe UI")
        font.setPointSize(8)
        self.label_6.setFont(font)
        self.label_6.setStyleSheet(f"color: rgb{text_color};")
        self.label_6.setObjectName("label_6")
        self.label_6.setText(f'{spotifysong.duration // 1000 // 60}:'
                             f'{(spotifysong.duration // 1000 - spotifysong.duration // 1000 // 60 * 60):02}')
        self.horizontalLayout_5.addWidget(self.label_6)
        self.verticalLayout_3.addWidget(self.horizontalFrame3)
        self.horizontalLayout.addWidget(self.verticalFrame2)
        self.horizontalFrame4 = QtWidgets.QFrame(self.horizontalFrame1)
        self.horizontalFrame4.setMinimumSize(QtCore.QSize(250, 0))
        self.horizontalFrame4.setMaximumSize(QtCore.QSize(250, 16777215))
        self.horizontalFrame4.setStyleSheet("background-color: rgba(0, 0, 0, 0);")
        self.horizontalFrame4.setObjectName("horizontalFrame4")
        self.horizontalLayout_2 = QtWidgets.QHBoxLayout(self.horizontalFrame4)
        self.horizontalLayout_2.setObjectName("horizontalLayout_2")
        self.pushButton_7 = QtWidgets.QPushButton(self.horizontalFrame4)
        self.pushButton_7.setMinimumSize(QtCore.QSize(25, 25))
        self.pushButton_7.setMaximumSize(QtCore.QSize(25, 25))
        self.pushButton_7.setStyleSheet(
            f"background-image: url({forward_data_dir}icons/16x16/cil-screen-smartphone{self.scaled}.png);\n"
            "background-repeat: none;\n"
            "background-position: center;")
        self.pushButton_7.setText("")
        self.pushButton_7.setObjectName("pushButton_7")
        self.horizontalLayout_2.addWidget(self.pushButton_7)
        self.devicelist = None

        def move_device_list():
            buttoncoords = self.pushButton_7.mapTo(mainui.window(),
                                                   QtCore.QPoint(mainui.pos().x() -
                                                                 mainui.devicelist.width() // 2 + 12 * ratio,
                                                                 mainui.pos().y() - mainui.devicelist.size().height()))
            buttoncoords = mainui.mapFrom(mainui.window(), buttoncoords)  # ^^^^ this is terrible
            mainui.devicelist.move(buttoncoords)

        def create_device_list():
            mainui.devicelist = PartialDeviceList(self.spotifyplayer, None, parent=mainui).convert_to_widget()
            mainui.devicelist.show()
            move_device_list()
            mainui.devicelist.move_to_position = lambda: move_device()

            def move_device():
                try:
                    move_device_list()
                except RuntimeError:
                    pass

        self.pushButton_7.clicked.connect(create_device_list)
        self.pushButton_8 = QtWidgets.QPushButton(self.horizontalFrame4)
        self.pushButton_8.setMinimumSize(QtCore.QSize(25, 25))
        self.pushButton_8.setMaximumSize(QtCore.QSize(25, 25))
        self.pushButton_8.setText("")
        self.pushButton_8.setObjectName("pushButton_8")
        self.horizontalLayout_2.addWidget(self.pushButton_8)
        self.horizontalSlider_2 = QtWidgets.QSlider(self.horizontalFrame4)
        self.horizontalSlider_2.setMinimumSize(QtCore.QSize(150, 22))
        volume = 'cil-volume-off' if self.spotifyplayer.current_volume < 7208 else 'cil-volume-low' if \
            self.spotifyplayer.current_volume < 32767 else 'cil-volume-high'
        self.pushButton_8.setStyleSheet(
            f"background-image: url({forward_data_dir}icons/16x16/{volume}{self.scaled}.png);\n"
            "background-repeat: none;\n"
            "background-position: center;")
        self.set_volume_slider()
        self.last_volume_change = time.time()
        self.horizontalSlider_2_clicked = False

        def change_volume(force=False):
            if (time.time() - self.last_volume_change > 0.1 and self.horizontalSlider_2_clicked) or force is False:
                self.regenerate_icons()
                Thread(target=lambda: self.spotifyplayer.command(self.spotifyplayer.
                                                                 volume(self.horizontalSlider_2.value()))).start()
                self.last_volume_change = time.time()

        self.horizontalSlider_2.valueChanged.connect(change_volume)

        def volume_keyboard_change(a0: QtGui.QKeyEvent):
            if a0.key() in (QtCore.Qt.Key_Left, QtCore.Qt.Key_Right, QtCore.Qt.Key_Up, QtCore.Qt.Key_Down):
                QtWidgets.QSlider.keyPressEvent(self.horizontalSlider_2, a0)
                self.regenerate_icons()
                Thread(target=lambda: self.spotifyplayer.command(self.spotifyplayer.
                                                                 volume(self.horizontalSlider_2.value()))).start()
                self.last_volume_change = time.time()
                self.fill_slider_2()
            else:
                QtWidgets.QSlider.keyPressEvent(self.horizontalSlider_2, a0)

        self.horizontalSlider_2.keyPressEvent = volume_keyboard_change

        def sliderMouseReleaseEvent(a0):
            change_volume()
            self.horizontalSlider_2_clicked = False
            QtWidgets.QSlider.mouseReleaseEvent(self.horizontalSlider_2, a0)

        self.horizontalSlider_2.mouseReleaseEvent = sliderMouseReleaseEvent

        def slider_pos():
            if not self.horizontalSlider_2_clicked:
                self.set_volume_slider()
                self.fill_slider_2()

        def volume_click(a0: QtGui.QMouseEvent):
            self.horizontalSlider_2_clicked = True
            self.horizontalSlider_2.setSliderPosition(int(a0.x() / self.horizontalSlider_2.width() * 100))
            return QtWidgets.QSlider.mousePressEvent(self.horizontalSlider_2, a0)

        self.horizontalSlider_2.mousePressEvent = volume_click

        self.slider_pos = slider_pos

        self.fill_slider_2()

        self.horizontalSlider_2.enterEvent = lambda a0: self.horizontalSlider_2 \
            .setStyleSheet(adj_style(ratio, """QSlider::groove:horizontal {
                        border-radius: 5px;
                        height: 10px;
                        margin: 0px;
                        background-color: rgba(52, 59, 72, 50);
                        }
                        QSlider::groove:horizontal:hover {
                        background-color: rgba(55, 62, 76, 50);
                        }
                        QSlider::handle:horizontal {
                        background-color: rgbreplace;
                        border: none;
                        height: 20px;
                        width: 20px;
                        margin-top: -5px;
                        margin-bottom: -5px;
                        border-radius: 10px;
                        }
                        QSlider::handle:horizontal:hover {
                        background-color: rgbreplace;
                        }
                        QSlider::handle:horizontal:pressed {
                        background-color: rgbreplace;
                        }
                        QSlider::sub-page:horizontal {
                        background: rgbreplace;
                        border-radius: 5px;
                        }""").replace('replace', repr(text_color)))
        self.horizontalSlider_2.leaveEvent = lambda a0: self.fill_slider_2()
        self.horizontalSlider_2.setOrientation(QtCore.Qt.Horizontal)
        self.horizontalSlider_2.setObjectName("horizontalSlider_2")
        self.horizontalLayout_2.addWidget(self.horizontalSlider_2)
        self.horizontalLayout.addWidget(self.horizontalFrame4)
        self.horizontalLayout_3.addWidget(self.horizontalFrame1)
        self.verticalLayout.addWidget(self.horizontalFrame)
        self._payload = None
        self.regenerate_icons()
        self.styles_to_ignore = [self.horizontalSlider, self.horizontalSlider_2]
        self.spotifyplayer.add_event_reciever(self.event_regenerate)
        self.snack_bar_callback = Runnable()
        snackbar = SnackBar('An unexpected error occured; please try again.', True, True)
        self.snack_bar_callback.callback.connect(lambda: mainui.show_snack_bar(snackbar))

    def handle_regeneration_error(self, func):
        def wrap():
            try:
                func()
            except IndexError as exc:
                logger.error('No active Spotify session found: ', exc_info=exc)
                mainui.show_snack_bar_threadsafe('No active Spotify session detected; '
                                                 'try playing a song on your device.', True, True)
            except Exception as exc:
                logger.error('An error occured while trying to change the playback state: ', exc_info=exc)
                self.snack_bar_callback.run()
        return wrap

    def regenerate_icons(self):
        if self.spotifyplayer.disconnected:
            if not mainui.client.disconnected:

                def cb():
                    if not self.spotifyplayer.disconnected:
                        return
                    mainui.active_dialog = Dialog('Disconnected', 'A network problem occured, and the playback '
                                                                  'controller was disconnected. It will attempt to '
                                                                  'reconnect every 15 seconds, and then the playback '
                                                                  'controller will re-appear.',
                                                  'Close', lambda: None, error=True)
                    mainui.horizontalFrame5.setFixedHeight(0)

                QtCore.QTimer.singleShot(4000, cb)

        else:
            mainui.horizontalFrame5.setFixedHeight(120 * self.ratio)
            if mainui.active_dialog:
                if mainui.active_dialog.error and "playback controller" in mainui.active_dialog.label_2.text():
                    mainui.active_dialog.pushButton_2.click()
        try:
            if self.spotifysong.songid:
                self.pushButton_6.clicked.disconnect()
            self.pushButton_5.clicked.disconnect()
            self.pushButton_3.clicked.disconnect()
            self.pushButton.clicked.disconnect()
        except TypeError:
            pass

        def saved_check():
            saved_songs = self.spotifyplayer.create_api_request(f'/me/tracks/contains?ids={self.spotifysong.songid}')
            self.is_saved = saved_songs.json()[0]

        @self.handle_regeneration_error
        def heart_function():
            self.slider_release_time = time.time()
            if self.is_saved:
                self.spotifyplayer.create_api_request(f'/me/tracks?ids={self.spotifysong.songid}',
                                                      request_type='DELETE')

                self.pushButton_6.setStyleSheet(
                    f"background-image: url({forward_data_dir}icons/20x20/cil-heart{self.scaled}.png);\n"
                    "background-repeat: none;\n"
                    "background-position: center;\n"
                    "border: none;\n"
                    "background-color: rgba(0, 0, 0, 0);")
            else:
                self.spotifyplayer.create_api_request(f'/me/tracks?ids={self.spotifysong.songid}',
                                                      request_type='PUT')
                self.pushButton_6.setStyleSheet(
                    f"background-image: url({forward_data_dir}icons/20x20/cil-heart-filled{self.scaled}.png);\n"
                    "background-repeat: none;\n"
                    "background-position: center;\n"
                    "border: none;\n"
                    "background-color: rgba(0, 0, 0, 0);")
            self.is_saved = not self.is_saved

        if self.spotifysong.songid:
            self.pushButton_6.clicked.connect(lambda: Thread(target=heart_function).start())
        else:
            self.pushButton_6.hide()

        def set_heart():
            heart = 'cil-heart-filled' if self.is_saved else 'cil-heart'
            self.pushButton_6.setStyleSheet(
                f"background-image: url({forward_data_dir}icons/20x20/{heart}{self.scaled}.png);\n"
                "background-repeat: none;\n"
                "background-position: center;\n"
                "border: none;\n"
                "background-color: rgba(0, 0, 0, 0);")
        set_heart()
        if self._payload and time.time() - self.slider_release_time > 0.5:
            runner = Runnable(saved_check, parent=mainui)
            runner.callback.connect(set_heart)
            runner.start()

        shuffle = 'cil-shuffle-on' if self.spotifyplayer.shuffling else 'cil-shuffle'

        @self.handle_regeneration_error
        def shuffle_function():
            self.slider_release_time = time.time()
            if self.spotifyplayer.shuffling:
                self.spotifyplayer.command(self.spotifyplayer.stop_shuffle)
            else:
                self.spotifyplayer.command(self.spotifyplayer.shuffle)

        self.pushButton_5.clicked.connect(lambda: Thread(target=shuffle_function).start())
        self.pushButton_5.setStyleSheet(
            f"background-image: url({forward_data_dir}icons/16x16/{shuffle}{self.scaled}.png);\n"
            "background-repeat: none;\n"
            "background-position: center;")
        play = 'cil-media-pause' if self.spotifyplayer.playing else 'cil-media-play'

        @self.handle_regeneration_error
        def play_function():
            self.slider_release_time = time.time()
            if self.spotifyplayer.playing:
                self.spotifyplayer.command(self.spotifyplayer.pause)
            else:
                self.spotifyplayer.command(self.spotifyplayer.resume)

        self.pushButton_3.clicked.connect(lambda: Thread(target=play_function).start())
        self.pushButton_3.setStyleSheet(
            f"background-image: url({forward_data_dir}icons/24x24/{play}{self.scaled}.png);\n"
            "background-repeat: none;\n"
            "background-position: center;")
        loop = 'cil-loop-on' if self.spotifyplayer.looping == 'context' else 'cil-loop-1' if self.spotifyplayer.looping\
               == 'track' else 'cil-loop'

        @self.handle_regeneration_error
        def loop_function():
            self.slider_release_time = time.time()
            if self.spotifyplayer.looping == 'context':
                self.spotifyplayer.command(self.spotifyplayer.repeating_track)
            elif self.spotifyplayer.looping == 'track':
                self.spotifyplayer.command(self.spotifyplayer.no_repeat)
            else:
                self.spotifyplayer.command(self.spotifyplayer.repeating_context)

        self.pushButton.clicked.connect(lambda: Thread(target=loop_function).start())
        self.pushButton.setStyleSheet(
            f"background-image: url({forward_data_dir}icons/16x16/{loop}{self.scaled}.png);\n"
            "background-repeat: none;\n"
            "background-position: center;")
        if not self.horizontalSlider_2_clicked and time.time() - self.last_volume_change > 0.5:
            self.set_volume_slider()
        volume = 'cil-volume-off' if self.horizontalSlider_2.value() == 0 else 'cil-volume-low' if \
            self.horizontalSlider_2.value() < 50 else 'cil-volume-high'
        self.pushButton_8.setStyleSheet(
            f"background-image: url({forward_data_dir}icons/16x16/{volume}{self.scaled}.png);\n"
            "background-repeat: none;\n"
            "background-position: center;")

    def set_volume_slider(self):
        if self.spotifyplayer.current_volume == 0:
            self.horizontalSlider_2.setSliderPosition(0)
        else:
            self.horizontalSlider_2.setSliderPosition(self.spotifyplayer.current_volume // 655.35 + 1)
        self.fill_slider_2()

    def fill_slider_2(self):
        ratio = get_ratio()
        if self.horizontalSlider_2.value() <= 2:
            self.horizontalSlider_2.setStyleSheet(adj_style(ratio, """QSlider::groove:horizontal {
                    border-radius: 5px;
                    height: 10px;
                    margin: 0px;
                    background-color: rgba(52, 59, 72, 50);
                    }
                    QSlider::groove:horizontal:hover {
                    background-color: rgba(55, 62, 76, 50);
                    }
                    QSlider::handle:horizontal {
                    background-color: rgbreplace;
                    border: none;
                    height: 10px;
                    width: 10px;
                    margin-top: 0;
                    margin-bottom: 0;
                    border-radius: 5px;
                    }
                    QSlider::handle:horizontal:hover {
                    background-color: rgbreplace;
                    }
                    QSlider::handle:horizontal:pressed {
                    background-color: rgbreplace;
                    }""").replace('replace', repr(self.text_color)))
        else:
            self.horizontalSlider_2.setStyleSheet(adj_style(ratio, """QSlider::groove:horizontal {
                    border-radius: 5px;
                    height: 10px;
                    margin: 0px;
                    background-color: rgba(52, 59, 72, 50);
                    }
                    QSlider::groove:horizontal:hover {
                    background-color: rgba(55, 62, 76, 50);
                    }
                    QSlider::handle:horizontal {
                    background-color: rgbreplace;
                    border: none;
                    height: 10px;
                    width: 12px;
                    margin-top: 0px;
                    margin-bottom: 0px;
                    border-radius: 5px;
                    }
                    QSlider::handle:horizontal:hover {
                    background-color: rgbreplace;
                    }
                    QSlider::handle:horizontal:pressed {
                    background-color: rgbreplace;
                    }
                    QSlider::sub-page:horizontal {
                    background: rgbreplace;
                    border-radius: 5px;
                    }""").replace('replace', repr(self.text_color)))

    def event_regenerate(self, payload=None):
        self._payload = payload  # some weird hack to make singleShot work ???
        QtCore.QTimer().singleShot(0, self.regenerate_icons)

    def __del__(self):
        try:
            self.spotifyplayer.remove_event_reciever(self.event_regenerate)
        except TypeError:
            pass


class PartialInboundFriendRequest:
    def __init__(self, request, request_id, ui, client):
        self.request_id = request_id
        self.request = request
        self.client = client
        self.ui = ui
        self.sender = request['sender']
        self.sender_id = self.sender['id']
        if not os.path.exists(data_dir + f'icon{self.sender_id}.png'):
            if self.sender['images']:
                url = self.sender['images'][-1]['url']
                img_data = requests.get(url, timeout=15).content
                with open(data_dir + f'icon{self.sender_id}.png', 'wb') as handler:
                    handler.write(img_data)
            else:
                image = Image.open(data_dir + 'default_user.png').resize((200, 200))
                image.save(data_dir + f'icon{self.sender_id}.png')
            mask = Image.open(data_dir + 'mask.png').convert('L')
            mask = mask.resize((200, 200))
            im = Image.open(data_dir + f'icon{self.sender_id}.png').convert('RGBA')
            output = ImageOps.fit(im, mask.size, centering=(0.5, 0.5))
            output.putalpha(mask)
            output.resize((200, 200))
            output.save(data_dir + f'icon{self.sender_id}.png')

    def convert_to_widget(self):
        return InboundFriendRequest(self.request, self.request_id, self.client, self.ui)


class InboundFriendRequest(QtWidgets.QWidget):
    def __init__(self, request, request_id, client, ui, *args, **kwargs):
        self.request = request
        self.request_id = request_id
        self.ui = ui
        self.client = client
        self.sender = request['sender']
        self.sender_id = self.sender['id']
        super().__init__(*args, **kwargs)
        self.setObjectName("Form")
        scaled = ''
        ratio = get_ratio()
        if ratio != 1:
            icons = [f'20x20{sep}cil-x', f'20x20{sep}cil-check-alt']
            scale_images(icons, ratio)
            scaled = 'scaled'
        self.setStyleSheet("background-color: rgb(39, 44, 54);"
                           f"border-radius: {10 * ratio}px; ")
        self.verticalLayout_2 = QtWidgets.QVBoxLayout(self)
        self.verticalLayout_2.setContentsMargins(0, 0, 0, 0)
        self.verticalLayout_2.setObjectName("verticalLayout_2")
        self.horizontalFrame = QtWidgets.QFrame(self)
        self.horizontalFrame.setMinimumSize(QtCore.QSize(0, 22 * ratio))
        self.horizontalFrame.setMaximumSize(QtCore.QSize(16777215, 16777215))
        self.horizontalFrame.setObjectName("horizontalFrame")
        self.horizontalLayout_4 = QtWidgets.QHBoxLayout(self.horizontalFrame)
        self.horizontalLayout_4.setContentsMargins(0, 0, 0, 0)
        self.horizontalLayout_4.setObjectName("horizontalLayout_4")
        self.spacer = QtWidgets.QFrame(self.horizontalFrame)
        self.spacer.setFixedWidth(0)
        self.horizontalLayout_4.addWidget(self.spacer)
        self.label = QtWidgets.QLabel(self.horizontalFrame)
        self.label.setFixedSize(40 * ratio, 40 * ratio)
        self.label.setStyleSheet(f"border-image: url({forward_data_dir}icon{self.sender_id}.png);")
        self.label.setText("")
        self.label.setObjectName("label")
        self.horizontalLayout_4.addWidget(self.label)
        self.verticalFrame = QtWidgets.QFrame(self.horizontalFrame)
        self.verticalFrame.setObjectName("verticalFrame")
        self.verticalLayout = QtWidgets.QVBoxLayout(self.verticalFrame)
        self.verticalLayout.setContentsMargins(0, 0, 0, 0)
        self.verticalLayout.setSpacing(0)
        self.verticalLayout.setObjectName("verticalLayout")
        self.label_2 = QtWidgets.QLabel(self.verticalFrame)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.label_2.sizePolicy().hasHeightForWidth())
        self.label_2.setSizePolicy(sizePolicy)
        self.label_2.setFixedHeight(28 * ratio)
        font = QtGui.QFont()
        font.setFamily("Segoe UI Semilight")
        font.setPointSize(10)
        self.label_2.setFont(font)
        self.label_2.setStyleSheet("color: white;")
        self.label_2.setText(self.request['sender']['display_name'])
        self.label_2.setObjectName("label_2")
        self.verticalLayout.addWidget(self.label_2)
        self.label_3 = QtWidgets.QLabel(self.verticalFrame)
        font = QtGui.QFont()
        font.setFamily("Segoe UI")
        font.setPointSize(8)
        self.label_3.setFont(font)
        self.label_3.setStyleSheet("color: rgb(200, 200, 200);")
        self.label_3.setAlignment(QtCore.Qt.AlignLeading | QtCore.Qt.AlignLeft | QtCore.Qt.AlignTop)
        self.label_3.setObjectName("label_3")
        self.label_3.setText(f'Friend Code: {self.request["sender"]["friend_code"]}')
        self.verticalLayout.addWidget(self.label_3)
        self.horizontalLayout_4.addWidget(self.verticalFrame)
        self.horizontalFrame_2 = QtWidgets.QFrame(self.horizontalFrame)
        self.horizontalFrame_2.setMaximumSize(QtCore.QSize(120 * ratio, 16777215))
        self.horizontalFrame_2.setStyleSheet("QPushButton {\n"
                                             f"    border-radius: {17 * ratio}px;\n"
                                             "    background-color: rgb(33, 37, 43);\n"
                                             "}\n"
                                             "\n"
                                             "QPushButton::hover {\n"
                                             "    background-color: rgb(53, 57, 63);\n"
                                             "}\n"
                                             "\n"
                                             "QPushButton::pressed {\n"
                                             f"    background-color: rgb{repr(self.ui.accent_color)}\n"
                                             "}")
        self.horizontalFrame_2.setObjectName("horizontalFrame_2")
        self.horizontalLayout_2 = QtWidgets.QHBoxLayout(self.horizontalFrame_2)
        self.horizontalLayout_2.setContentsMargins(14 * ratio, 0, 14 * ratio, 0)
        self.horizontalLayout_2.setSpacing(23 * ratio)
        self.horizontalLayout_2.setObjectName("horizontalLayout_2")
        self.pushButton = QtWidgets.QPushButton(self.horizontalFrame_2)
        self.pushButton.setMinimumSize(QtCore.QSize(35 * ratio, 35 * ratio))
        self.pushButton.setMaximumSize(QtCore.QSize(35 * ratio, 35 * ratio))
        self.pushButton.setStyleSheet(
            f"background-image: url({forward_data_dir}icons/20x20/cil-x{scaled}.png);\n"
            "background-position: center;\n"
            "background-repeat: no-repeat;")
        self.pushButton.setText("")
        self.pushButton.setObjectName("pushButton")
        self.horizontalLayout_2.addWidget(self.pushButton)
        self.pushButton_2 = QtWidgets.QPushButton(self.horizontalFrame_2)
        self.pushButton_2.setMinimumSize(QtCore.QSize(35 * ratio, 35 * ratio))
        self.pushButton_2.setMaximumSize(QtCore.QSize(35 * ratio, 35 * ratio))
        self.pushButton_2.setStyleSheet(
            f"background-image: url({forward_data_dir}icons/20x20/cil-check-alt{scaled}.png);\n"
            "background-position: center;\n"
            "background-repeat: no-repeat;")
        self.pushButton_2.setText("")
        self.pushButton_2.setObjectName("pushButton_2")
        self.horizontalLayout_2.addWidget(self.pushButton_2)
        self.horizontalLayout_4.addWidget(self.horizontalFrame_2)
        self.verticalLayout_2.addWidget(self.horizontalFrame)
        self.pushButton.clicked.connect(self.decline)
        self.pushButton_2.clicked.connect(self.accept)
        self.setFixedHeight(50 * ratio)
        self.setSizePolicy(QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Preferred))

    def accept(self):

        def success():
            try:
                self.hide()
            except RuntimeError:
                pass

        def failure():
            if sip.isdeleted(mainui):
                return
            mainui.show_snack_bar(SnackBar('An unexpected error occured while the friend request was being accepted, '
                                           'please try again.', False, True))

        success_runner = Runnable()
        success_runner.callback.connect(success)
        failure_runner = Runnable()
        failure_runner.callback.connect(failure)

        Thread(target=lambda: self.client.invoke_request(BASE_URL + '/friends/accept', {'request_id': self.request_id},
                                                         'POST', success_runner.run, failure_runner.run)).start()

    def decline(self):

        def success():
            try:
                self.hide()
            except RuntimeError:
                pass

        def failure():
            if sip.isdeleted(mainui):
                return
            mainui.show_snack_bar(SnackBar('An unexpected error occured while the friend request was being declined, '
                                           'please try again.', False, True))

        success_runner = Runnable()
        success_runner.callback.connect(success)
        failure_runner = Runnable()
        failure_runner.callback.connect(failure)

        Thread(target=lambda: self.client.invoke_request(BASE_URL + '/friends/decline', {'request_id': self.request_id},
                                                         'POST', success_runner.run, failure_runner.run)).start()


class PartialOutboundFriendRequest:
    def __init__(self, request, request_id, ui, client):
        self.request_id = request_id
        self.request = request
        self.client = client
        self.ui = ui
        self.reciever = request['target']
        self.reciever_id = self.reciever['id']
        if self.reciever['images']:
            url = self.reciever['images'][0]['url']
            img_data = requests.get(url, timeout=15).content
            with open(data_dir + f'icon{self.reciever_id}.png', 'wb') as handler:
                handler.write(img_data)
        else:
            image = Image.open(data_dir + 'default_user.png').resize((200, 200))
            image.save(data_dir + f'icon{self.reciever_id}.png')
        mask = Image.open(data_dir + 'mask.png').convert('L')
        mask = mask.resize((200, 200))
        im = Image.open(data_dir + f'icon{self.reciever_id}.png').convert('RGBA')
        output = ImageOps.fit(im, mask.size, centering=(0.5, 0.5))
        output.putalpha(mask)
        output.resize((200, 200))
        output.save(data_dir + f'icon{self.reciever_id}.png')

    def convert_to_widget(self):
        return OutboundFriendRequest(self.request, self.request_id, self.client, self.ui)


class OutboundFriendRequest(QtWidgets.QWidget):
    def __init__(self, request, request_id, client, ui, *args, **kwargs):
        self.request = request
        self.request_id = request_id
        self.ui = ui
        self.client = client
        self.reciever = request['target']
        self.reciever_id = self.reciever['id']
        super().__init__(*args, **kwargs)
        self.setObjectName("Form")
        scaled = ''
        ratio = get_ratio()
        if ratio != 1:
            icons = [f'20x20{sep}cil-x']
            scale_images(icons, ratio)
            scaled = 'scaled'
        self.setStyleSheet("background-color: rgb(39, 44, 54);"
                           f"border-radius: {10 * ratio}px; ")
        self.verticalLayout_2 = QtWidgets.QVBoxLayout(self)
        self.verticalLayout_2.setContentsMargins(0, 0, 0, 0)
        self.verticalLayout_2.setObjectName("verticalLayout_2")
        self.horizontalFrame = QtWidgets.QFrame(self)
        self.horizontalFrame.setMinimumSize(QtCore.QSize(0, 22 * ratio))
        self.horizontalFrame.setMaximumSize(QtCore.QSize(16777215, 16777215))
        self.horizontalFrame.setObjectName("horizontalFrame")
        self.horizontalLayout_4 = QtWidgets.QHBoxLayout(self.horizontalFrame)
        self.horizontalLayout_4.setContentsMargins(0, 0, 0, 0)
        self.horizontalLayout_4.setObjectName("horizontalLayout_4")
        self.spacer = QtWidgets.QFrame(self.horizontalFrame)
        self.spacer.setFixedWidth(0)
        self.horizontalLayout_4.addWidget(self.spacer)
        self.label = QtWidgets.QLabel(self.horizontalFrame)
        self.label.setFixedSize(40 * ratio, 40 * ratio)
        self.label.setStyleSheet(f"border-image: url({forward_data_dir}icon{self.reciever_id}.png);")
        self.label.setText("")
        self.label.setObjectName("label")
        self.horizontalLayout_4.addWidget(self.label)
        self.verticalFrame = QtWidgets.QFrame(self.horizontalFrame)
        self.verticalFrame.setObjectName("verticalFrame")
        self.verticalLayout = QtWidgets.QVBoxLayout(self.verticalFrame)
        self.verticalLayout.setContentsMargins(0, 0, 0, 0)
        self.verticalLayout.setSpacing(0)
        self.verticalLayout.setObjectName("verticalLayout")
        self.label_2 = QtWidgets.QLabel(self.verticalFrame)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.label_2.sizePolicy().hasHeightForWidth())
        self.label_2.setSizePolicy(sizePolicy)
        self.label_2.setFixedHeight(28 * ratio)
        font = QtGui.QFont()
        font.setFamily("Segoe UI Semilight")
        font.setPointSize(10)
        self.label_2.setFont(font)
        self.label_2.setStyleSheet("color: white;")
        self.label_2.setText(self.request['target']['display_name'])
        self.label_2.setObjectName("label_2")
        self.verticalLayout.addWidget(self.label_2)
        self.label_3 = QtWidgets.QLabel(self.verticalFrame)
        font = QtGui.QFont()
        font.setFamily("Segoe UI")
        font.setPointSize(8)
        self.label_3.setFont(font)
        self.label_3.setStyleSheet("color: rgb(200, 200, 200);")
        self.label_3.setAlignment(QtCore.Qt.AlignLeading | QtCore.Qt.AlignLeft | QtCore.Qt.AlignTop)
        self.label_3.setObjectName("label_3")
        self.label_3.setText(f'Friend Code: {self.request["target"]["friend_code"]}')
        self.verticalLayout.addWidget(self.label_3)
        self.horizontalLayout_4.addWidget(self.verticalFrame)
        self.horizontalFrame_2 = QtWidgets.QFrame(self.horizontalFrame)
        self.horizontalFrame_2.setMaximumSize(QtCore.QSize(120 * ratio, 16777215))
        self.horizontalFrame_2.setStyleSheet("QPushButton {\n"
                                             f"    border-radius: {17 * ratio}px;\n"
                                             "    background-color: rgb(33, 37, 43);\n"
                                             "}\n"
                                             "\n"
                                             "QPushButton::hover {\n"
                                             "    background-color: rgb(53, 57, 63);\n"
                                             "}\n"
                                             "\n"
                                             "QPushButton::pressed {\n"
                                             f"    background-color: rgb{repr(self.ui.accent_color)}\n"
                                             "}")
        self.horizontalFrame_2.setObjectName("horizontalFrame_2")
        self.horizontalLayout_2 = QtWidgets.QHBoxLayout(self.horizontalFrame_2)
        self.horizontalLayout_2.setContentsMargins(14 * ratio, 0, 14 * ratio, 0)
        self.horizontalLayout_2.setSpacing(23 * ratio)
        self.horizontalLayout_2.setObjectName("horizontalLayout_2")
        self.pushButton = QtWidgets.QPushButton(self.horizontalFrame_2)
        self.pushButton.setMinimumSize(QtCore.QSize(35 * ratio, 35 * ratio))
        self.pushButton.setMaximumSize(QtCore.QSize(35 * ratio, 35 * ratio))
        self.pushButton.setStyleSheet(
            f"background-image: url({forward_data_dir}icons/20x20/cil-x{scaled}.png);\n"
            "background-position: center;\n"
            "background-repeat: no-repeat;")
        self.pushButton.setText("")
        self.pushButton.setObjectName("pushButton")
        self.horizontalLayout_2.addWidget(self.pushButton)
        self.horizontalLayout_4.addWidget(self.horizontalFrame_2)
        self.verticalLayout_2.addWidget(self.horizontalFrame)
        self.pushButton.clicked.connect(self.decline)
        self.setFixedHeight(50 * ratio)

    def decline(self):

        def success():
            try:
                self.hide()
            except RuntimeError:
                pass

        def failure():
            if sip.isdeleted(mainui):
                return
            mainui.show_snack_bar(SnackBar('An unexpected error occured while the friend request was being canceled, '
                                           'please try again.', False, True))

        success_runner = Runnable()
        success_runner.callback.connect(success)
        failure_runner = Runnable()
        failure_runner.callback.connect(failure)

        Thread(target=lambda: self.client.invoke_request(BASE_URL + '/friends/decline', {'request_id': self.request_id},
                                                         'POST', success_runner.run, failure_runner.run)).start()


class PartialPastFriendStatus:
    def __init__(self, friendstatus: SpotifySong):
        self.friendstatus = friendstatus
        self.id = friendstatus.client_id
        if not self.friendstatus.songid and not self.friendstatus.last_song:
            return
        if not os.path.exists(data_dir + f'icon{self.friendstatus.client_id}.png'):
            rand = random.randint(0, 10000)
            if self.friendstatus.clientavatar:
                url = self.friendstatus.clientavatar
                img_data = requests.get(url, timeout=15).content
                with open(data_dir + f'tempicon{rand}{self.friendstatus.client_id}.png', 'wb') as handler:
                    handler.write(img_data)
            else:
                image = Image.open(data_dir + 'default_user.png').resize((200, 200))
                image.save(data_dir + f'tempicon{rand}{self.friendstatus.client_id}.png')
            mask = Image.open(data_dir + 'mask.png').convert('L')
            mask = mask.resize((200, 200))
            im = Image.open(data_dir + f'tempicon{rand}{self.friendstatus.client_id}.png').convert('RGBA')
            output = ImageOps.fit(im, mask.size, centering=(0.5, 0.5))
            output.putalpha(mask)
            output.resize((200, 200))
            output.save(data_dir + f'icon{self.friendstatus.client_id}.png')
            try:
                os.remove(data_dir + f'tempicon{rand}{self.friendstatus.client_id}.png')
            except (FileNotFoundError, OSError, PermissionError):
                pass
        if self.friendstatus.contexttype == 'playlist':
            if self.friendstatus.songname:
                try:
                    id_ = self.friendstatus.contextdata.split('/')[-1]
                    resp = mainui.client.spotifyplayer.create_api_request(f'/playlists/{id_}').json()
                    if 'error' in resp:
                        self.playlist_name = None
                        return
                    self.playlist_name = resp['name'] if resp['public'] else None
                    """what kind of feature is this? if you have the link to a spotify playlist and it's private you can
                    still view it????? that makes no sense, so we have to check that the playlist is public and show it,
                    otherwise we will hide it
                    update: nvm they fixed it i guess
                    update 2: only shows playlists that are featured on the users' profile
                    """
                except Exception as e:
                    logger.error('An unexpected error has occured: ', exc_info=e)
                    self.playlist_name = None
            else:
                self.playlist_name = None
        elif self.friendstatus.last_song.contexttype == 'playlist':
            if self.friendstatus.last_song.songname:
                try:
                    id_ = self.friendstatus.last_song.contextdata.split('/')[-1]
                    resp = mainui.client.spotifyplayer.create_api_request(f'/playlists/{id_}').json()
                    if 'error' in resp:
                        self.playlist_name = None
                        return
                    self.playlist_name = resp['name'] if resp['public'] else None
                except Exception as e:
                    logger.error('An unexpected error has occured: ', exc_info=e)
                    self.playlist_name = None
            else:
                self.playlist_name = None
        else:
            self.playlist_name = None

    def convert_to_widget(self):
        if not self.friendstatus.songid and not self.friendstatus.last_song:
            return
        if self.friendstatus.songname:
            return PastFriendStatus(self.friendstatus, self.playlist_name)
        else:
            return PastFriendStatus(self.friendstatus.last_song, self.playlist_name,
                                    self.friendstatus.last_song_timestamp)


@adjust_sizing()
class PastFriendStatus(QtWidgets.QWidget):
    def __init__(self, friendstatus: SpotifySong, playlist_name, last_timestamp: datetime.datetime = None,
                 *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setMinimumWidth(240)
        self.setSizePolicy(QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Preferred))
        self.friendstatus = friendstatus
        self.playlist_name = playlist_name
        self.last_timestamp = last_timestamp
        self.id = friendstatus.client_id
        self.setStyleSheet('''QLabel {
                color: white;
            }''')
        self.verticalLayout = QtWidgets.QVBoxLayout(self)
        self.verticalLayout.setContentsMargins(0, 0, 0, 0)
        self.verticalLayout.setSpacing(0)
        self.verticalLayout.setObjectName("verticalLayout")
        self.horizontalFrame = QtWidgets.QFrame(self)
        self.horizontalFrame.setObjectName("horizontalFrame")
        self.horizontalLayout = QtWidgets.QHBoxLayout(self.horizontalFrame)
        self.horizontalLayout.setContentsMargins(0, 0, 0, 0)
        self.horizontalLayout.setSpacing(7)
        self.horizontalLayout.setObjectName("horizontalLayout")
        self.verticalFrame = QtWidgets.QFrame(self.horizontalFrame)
        self.verticalFrame.setMaximumSize(QtCore.QSize(50, 16777215))
        self.verticalFrame.setObjectName("verticalFrame")
        self.verticalLayout_2 = QtWidgets.QVBoxLayout(self.verticalFrame)
        self.verticalLayout_2.setObjectName("verticalLayout_2")
        self.verticalLayout_2.setContentsMargins(0, 0, 0, 0)
        self.label = QtWidgets.QLabel(self.verticalFrame)
        self.label.setMaximumSize(QtCore.QSize(16777215, 50))
        font = QtGui.QFont()
        font.setFamily("Segoe UI")
        font.setPointSize(8)
        self.label.setFont(font)
        self.label.setText("")
        self.label.setObjectName("label")
        self.label.setStyleSheet('''QLabel { 
            border-image: url(%sicon%s.png);
            border: 2px solid white;
        }''' % (forward_data_dir, friendstatus.client_id))
        self.label.setFixedSize(50, 50)
        self.verticalLayout_2.addWidget(self.label)
        self.horizontalLayout.addWidget(self.verticalFrame)
        self.verticalFrame1 = QtWidgets.QFrame(self.horizontalFrame)
        self.verticalFrame1.setObjectName("verticalFrame1")
        self.verticalLayout_3 = QtWidgets.QVBoxLayout(self.verticalFrame1)
        self.verticalLayout_3.setContentsMargins(0, 0, 0, 0)
        self.verticalLayout_3.setObjectName("verticalLayout_3")
        self.horizontalFrame1 = QtWidgets.QFrame(self.verticalFrame1)
        self.horizontalFrame1.setMinimumSize(QtCore.QSize(0, 20))
        self.horizontalFrame1.setMaximumSize(QtCore.QSize(16777215, 20))
        self.horizontalFrame1.setObjectName("horizontalFrame1")
        self.horizontalLayout_2 = QtWidgets.QHBoxLayout(self.horizontalFrame1)
        self.horizontalLayout_2.setObjectName("horizontalLayout_2")
        self.horizontalLayout_2.setContentsMargins(0, 0, 0, 0)
        self.horizontalLayout_2.setSpacing(0)
        self.label_7 = QtWidgets.QLabel(self.horizontalFrame1)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.label_7.sizePolicy().hasHeightForWidth())
        self.label_7.setSizePolicy(sizePolicy)
        font = QtGui.QFont()
        font.setFamily("Segoe UI")
        font.setPointSize(8)
        self.label_7.setFont(font)
        self.label_7.setObjectName("label_7")
        self.horizontalLayout_2.addWidget(self.label_7)
        self.label_2 = QtWidgets.QLabel(self.horizontalFrame1)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.label_2.sizePolicy().hasHeightForWidth())
        self.label_2.setSizePolicy(sizePolicy)
        self.label_2.setMaximumSize(QtCore.QSize(40, 16777215))
        font = QtGui.QFont()
        font.setFamily("Segoe UI")
        font.setPointSize(8)
        self.label_2.setFont(font)
        self.label_2.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignTrailing | QtCore.Qt.AlignVCenter)
        self.label_2.setObjectName("label_2")
        self.horizontalLayout_2.addWidget(self.label_2)
        self.verticalLayout_3.addWidget(self.horizontalFrame1)
        self.label_3 = QtWidgets.QLabel(self.verticalFrame1)
        font = QtGui.QFont()
        font.setFamily("Segoe UI")
        font.setPointSize(8)
        self.label_3.setFont(font)
        self.label_3.setObjectName("label_3")
        self.verticalLayout_3.addWidget(self.label_3)
        self.label_4 = QtWidgets.QLabel(self.verticalFrame1)
        font = QtGui.QFont()
        font.setFamily("Segoe UI")
        font.setPointSize(8)
        self.label_4.setFont(font)
        self.label_4.setObjectName("label_4")
        self.verticalLayout_3.addWidget(self.label_4)
        self.label_5 = QtWidgets.QLabel(self.verticalFrame1)
        font = QtGui.QFont()
        font.setFamily("Segoe UI")
        font.setPointSize(8)
        self.label_5.setFont(font)
        self.label_5.setObjectName("label_5")
        self.verticalLayout_3.addWidget(self.label_5)
        self.label_6 = QtWidgets.QLabel(self.verticalFrame1)
        self.label_6.setObjectName("label_6")
        self.label_6.setFont(font)
        self.verticalLayout_3.addWidget(self.label_6)
        self.horizontalLayout.addWidget(self.verticalFrame1)
        self.verticalLayout.addWidget(self.horizontalFrame)

        def update_timestamp():
            if last_timestamp:
                diff = time.time() - last_timestamp.timestamp()
                if diff < 60:
                    text = f'{round(diff)}s '
                elif diff < 3600:
                    text = f'{round(diff / 60)}m '
                elif diff < 86400:
                    text = f'{round(diff / 3600)}h '
                elif diff < 604800:
                    text = f'{round(diff / 86400)}d '
                else:
                    text = f'{round(diff / 604800)}w '
                self.label_2.setText(text)
            elif self.friendstatus.songname:
                self.last_timestamp = datetime.datetime.now()
                self.label_2.setText('Now ')
        self.timer = QtCore.QTimer()
        self.timer.setInterval(1000)
        self.timer.timeout.connect(update_timestamp)
        self.timer.start()
        update_timestamp()

    def showEvent(self, a0: QtGui.QShowEvent) -> None:
        self.label_3.setText(limit_text_smart(self.friendstatus.songname, self.label_3))
        if self.friendstatus.song_authors:
            song_authors = ', '.join(self.friendstatus.song_authors)
        else:
            song_authors = 'Unknown'
        if self.friendstatus.albumname:
            albumname = self.friendstatus.albumname
        else:
            albumname = 'Unknown'
        self.label_4.setText(limit_text_rich(f'By: <strong>{song_authors}</strong>', self.label_4))
        self.label_5.setText(limit_text_rich(f'On: <strong>{albumname}</strong>', self.label_5))
        if self.playlist_name:
            self.label_6.setText(limit_text_rich(f'Playlist: <strong>{self.playlist_name}</strong>', self.label_6))
        else:
            self.label_6.setText('')
            self.label_6.hide()
            self.verticalLayout_3.removeWidget(self.label_6)
        self.label_7.setText(limit_text_smart(self.friendstatus.clientusername, self.label_7))
        text_widgets = [self.label_3, self.label_4, self.label_5, self.label_6, self.label_7]
        real_text = [self.friendstatus.songname, f'By: {song_authors}',
                     f'On: {albumname}', f'Playlist: {self.playlist_name}',
                     self.friendstatus.clientusername]
        for idx, text_wid in enumerate(text_widgets):
            if '...' in text_wid.text() or '…' in text_wid.text():
                setattr(text_wid, 'tooltip', Tooltip(real_text[idx], text_wid))
        QtWidgets.QWidget.showEvent(self, a0)


class PartialLogViewer:
    def __init__(self, log: StringIO):
        """
            This is a class that handles the logs of the program, to be later converted into a QWidget.
        """
        regex = r"(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d{3}) - (\w+) *- ([\w\.]+) *- (.+)"
        logs = []
        try:
            for log_str in log.getvalue().split('\n'):
                if match := re.fullmatch(regex, log_str):
                    groups = list(match.group(1, 2, 3, 4))
                    logs.append(groups)
                else:
                    logs[-1][3] = f'{logs[-1][3]}\n{log_str}'
            self.log = logs
        except IndexError:
            self.log = []


@adjust_sizing()
class LogViewer(QtWidgets.QWidget):
    def __init__(self, log, *args, **kwargs):
        self.log = log
        self.logs = []
        self.last_logs = []
        super().__init__(*args, **kwargs)
        self.setObjectName("Dialog")
        self.resize(930, 419)

        self.setStyleSheet(mainui.frameMain.styleSheet())
        self.setStyleSheet(self.styleSheet().replace('(85, 170, 255)', repr(mainui.accent_color)))
        self.verticalLayout_2 = QtWidgets.QVBoxLayout(self)
        self.verticalLayout_2.setContentsMargins(0, 0, 0, 0)
        self.verticalLayout_2.setObjectName("verticalLayout_2")
        self.verticalFrame = QtWidgets.QFrame(self)
        self.verticalFrame.setStyleSheet("background-color: rgb(27, 29, 35);\n"
                                         "border-radius: 25px;")
        self.verticalFrame.setObjectName("verticalFrame")
        self.verticalLayout = QtWidgets.QVBoxLayout(self.verticalFrame)
        self.verticalLayout.setObjectName("verticalLayout")
        self.horizontalFrame = QtWidgets.QFrame(self.verticalFrame)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Ignored, QtWidgets.QSizePolicy.Ignored)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.horizontalFrame.sizePolicy().hasHeightForWidth())
        self.horizontalFrame.setSizePolicy(sizePolicy)
        self.horizontalFrame.setMinimumSize(QtCore.QSize(0, 35))
        self.horizontalFrame.setMaximumSize(QtCore.QSize(16777215, 35))
        self.horizontalFrame.setStyleSheet("QFrame {\n"
                                           "    background: transparent;\n"
                                           "}")
        self.horizontalFrame.setObjectName("horizontalFrame")
        self.horizontalLayout_2 = QtWidgets.QHBoxLayout(self.horizontalFrame)
        self.horizontalLayout_2.setSpacing(0)
        self.horizontalLayout_2.setContentsMargins(0, 0, 0, 0)
        self.horizontalLayout_2.setObjectName("horizontalLayout_2")
        self.spacerItem = QtWidgets.QSpacerItem(40, 20, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum)
        self.horizontalLayout_2.addItem(self.spacerItem)
        self.pushButton = QtWidgets.QPushButton(self.horizontalFrame)
        self.pushButton.setMinimumSize(QtCore.QSize(35, 35))
        self.pushButton.setMaximumSize(QtCore.QSize(35, 35))
        scaled = ''
        ratio = get_ratio()
        if ratio != 1:
            scale_one(f'{forward_data_dir}icons{sep}24x24{sep}cil-x', ratio)
            scaled = 'scaled'
        self.pushButton.setStyleSheet("QPushButton {\n"
                                      "                background-color: rgb(44, 49, 60);\n"
                                      "                background-image: url(%sicons/24x24/cil-x%s.png);\n"
                                      "                background-repeat: no-repeat;\n"
                                      "                background-position: center;\n"
                                      "                border: none;\n"
                                      "                border-radius: 7px;\n"
                                      "            }\n"
                                      "            QPushButton::hover {\n"
                                      "                background-color: rgb(64, 69, 80);\n"
                                      "            }\n"
                                      "            QPushButton::pressed {\n"
                                      "                background-color: rgb%s;\n"
                                      "            }" % (forward_data_dir, scaled, mainui.accent_color))
        self.pushButton.setText("")
        self.pushButton.setObjectName("pushButton")
        self.horizontalLayout_2.addWidget(self.pushButton)
        self.verticalLayout.addWidget(self.horizontalFrame)
        self.label = QtWidgets.QLabel(self.verticalFrame)
        self.label.setMinimumSize(QtCore.QSize(0, 60))
        self.label.setMaximumSize(QtCore.QSize(16777215, 60))
        font = QtGui.QFont()
        font.setFamily("Segoe UI")
        font.setPointSize(14)
        self.label.setFont(font)
        self.label.setStyleSheet("color: white; background: transparent;")
        self.label.setAlignment(QtCore.Qt.AlignCenter)
        self.label.setObjectName("label")
        self.verticalLayout.addWidget(self.label)
        self.frame = QtWidgets.QFrame(self.verticalFrame)
        self.frame.setStyleSheet("background-color: rgb(39, 44, 54);")
        self.frame.setFrameShape(QtWidgets.QFrame.StyledPanel)
        self.frame.setFrameShadow(QtWidgets.QFrame.Raised)
        self.frame.setObjectName("frame")
        self.horizontalLayout = QtWidgets.QHBoxLayout(self.frame)
        self.horizontalLayout.setContentsMargins(0, 0, 0, 0)
        self.horizontalLayout.setObjectName("horizontalLayout")
        self.tableWidget = QtWidgets.QTableWidget(self.frame)
        font.setPointSize(8)
        self.tableWidget.setFont(font)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.tableWidget.sizePolicy().hasHeightForWidth())
        self.tableWidget.setSizePolicy(sizePolicy)
        self.tableWidget.setStyleSheet("QTableWidget {    \n"
                                       "    background-color: rgb(39, 44, 54);\n"
                                       "    padding: 10px;\n"
                                       "    border-radius: 5px;\n"
                                       "    gridline-color: rgb(44, 49, 60);\n"
                                       "    border-bottom: 1px solid rgb(44, 49, 60);\n"
                                       "    border-radius: 20px;\n"
                                       "}\n"
                                       "QTableWidget::item{\n"
                                       "    border-color: rgb(44, 49, 60);\n"
                                       "    padding-left: 5px;\n"
                                       "    padding-right: 5px;\n"
                                       "    gridline-color: rgb(44, 49, 60);\n"
                                       "    color: white;\n"
                                       "}\n"
                                       "QScrollBar:horizontal {\n"
                                       "    border: none;\n"
                                       "    background: rgb(52, 59, 72);\n"
                                       "    height: 14px;\n"
                                       "    margin: 0px 21px 0 21px;\n"
                                       "    border-radius: 0px;\n"
                                       "}\n"
                                       " QScrollBar:vertical {\n"
                                       "    border: none;\n"
                                       "    background: rgb(52, 59, 72);\n"
                                       "    width: 14px;\n"
                                       "    margin: 21px 0 21px 0;\n"
                                       "    border-radius: 3px;\n"
                                       " }\n"
                                       "QHeaderView::section{\n"
                                       "    background-color: rgb(39, 44, 54);\n"
                                       "    max-width: 30px;\n"
                                       "    border: 1px solid rgb(44, 49, 60);\n"
                                       "    border-style: none;\n"
                                       "    border-bottom: 1px solid rgb(44, 49, 60);\n"
                                       "    border-right: 1px solid rgb(44, 49, 60);\n"
                                       "}\n"
                                       "QTableWidget::horizontalHeader {    \n"
                                       "    background-color: rgb(81, 255, 0);\n"
                                       "    color: white;\n"
                                       "}\n"
                                       "QHeaderView::section:horizontal\n"
                                       "{\n"
                                       "    border: 1px solid rgb(32, 34, 42);\n"
                                       "    background-color: rgb(27, 29, 35);\n"
                                       "    padding: 3px;\n"
                                       "    border-top-left-radius: 7px;\n"
                                       "    border-top-right-radius: 7px;\n"
                                       "}\n"
                                       "QHeaderView::section:vertical\n"
                                       "{\n"
                                       "    border: 1px solid rgb(44, 49, 60);\n"
                                       "}\n"
                                       "")
        self.tableWidget.setFrameShape(QtWidgets.QFrame.NoFrame)
        self.tableWidget.setFrameShadow(QtWidgets.QFrame.Sunken)
        self.tableWidget.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOn)
        self.tableWidget.setSizeAdjustPolicy(QtWidgets.QAbstractScrollArea.AdjustToContents)
        self.tableWidget.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        self.tableWidget.setAlternatingRowColors(False)
        self.tableWidget.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        self.tableWidget.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.tableWidget.setShowGrid(True)
        self.tableWidget.setGridStyle(QtCore.Qt.SolidLine)
        self.tableWidget.setObjectName("tableWidget")
        self.tableWidget.setColumnCount(4)
        self.tableWidget.setRowCount(1)
        font.setPointSize(12)
        font.setBold(False)
        self.tableWidget.setHorizontalHeaderLabels(['Timestamp', 'Level', 'Source', 'Info'])
        self.tableWidget.horizontalHeader().setFont(font)
        self.tableWidget.horizontalHeader().setSectionsClickable(False)
        self.tableWidget.horizontalHeader().setStyleSheet('color: white;')
        self.tableWidget.horizontalHeader().setVisible(True)
        self.tableWidget.horizontalHeader().setCascadingSectionResizes(True)
        self.tableWidget.horizontalHeader().setDefaultSectionSize(200 * ratio)
        self.tableWidget.horizontalHeader().setStretchLastSection(True)
        self.tableWidget.verticalHeader().setVisible(False)
        self.tableWidget.verticalHeader().setCascadingSectionResizes(False)
        self.tableWidget.verticalHeader().setHighlightSections(False)
        self.tableWidget.verticalHeader().setStretchLastSection(True)
        self.horizontalLayout.addWidget(self.tableWidget)
        self.verticalLayout.addWidget(self.frame)
        self.verticalLayout_2.addWidget(self.verticalFrame)
        self.label.setText('Application Logs')
        self.widgets_to_ignore = [self.tableWidget]
        # noinspection PyTypeChecker
        self.pushButton.clicked.connect(lambda: (self.__setattr__('closed', True), self.close()))
        self.setWindowFlags(QtCore.Qt.FramelessWindowHint)
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        self.oldpos = QtCore.QPoint(0, 0)

        def mousePressEvent(event):
            self.oldpos = event.globalPos()

        def mouseMoveEvent(event):
            if isinstance(self.oldpos, QtCore.QPoint):
                delta = QtCore.QPoint(event.globalPos() - self.oldpos)
                self.move(self.x() + delta.x(), self.y() + delta.y())
                self.oldpos = event.globalPos()

        self.label.mousePressEvent = mousePressEvent
        self.label.mouseMoveEvent = mouseMoveEvent
        self.horizontalFrame.mousePressEvent = mousePressEvent
        self.horizontalFrame.mouseMoveEvent = mouseMoveEvent
        self.horizontalFrame.raise_()
        self.setWindowTitle('Application Logs - SpotAlong')
        self.update_table()
        self.timer = QtCore.QTimer()
        self.timer.setInterval(1000)
        self.timer.timeout.connect(self.update_table)
        self.timer.start()
        self.closed = False
        self.pushButton.keyPressEvent = lambda a0: None
        self.setFocus()
        self.show_after_adjust = True

    def update_table(self):
        self.logs = PartialLogViewer(self.log).log
        for index, log in enumerate(self.logs):
            if log not in self.last_logs:
                if self.tableWidget.rowCount() < index + 1:
                    self.tableWidget.insertRow(index)
                self.tableWidget.setItem(index, 0, QtWidgets.QTableWidgetItem(log[0]))
                self.tableWidget.setItem(index, 1, QtWidgets.QTableWidgetItem(log[1]))
                self.tableWidget.setItem(index, 2, QtWidgets.QTableWidgetItem(log[2]))
                self.tableWidget.setItem(index, 3, QtWidgets.QTableWidgetItem(log[3]))
        self.last_logs = self.logs

    def reject(self):
        if self.closed:
            QtWidgets.QWidget.reject(self)


class PartialDeviceList:
    """
        This is a class that loads the device list of the users Spotify-connectable devices, to be later converted into
        a QWidget.
    """
    def __init__(self, spotifyplayer: SpotifyPlayer, last_device_cache: dict = None, *args, **kwargs):
        if not last_device_cache:
            last_device_cache = spotifyplayer.devices
        self.last_device_cache = last_device_cache
        self.spotifyplayer = spotifyplayer
        self.args = args
        self.kwargs = kwargs

    def convert_to_widget(self):
        return DeviceList(self.spotifyplayer, self.last_device_cache, *self.args, **self.kwargs)


@adjust_sizing()
class DeviceList(QtWidgets.QWidget):
    """
        This is a widget that allows the user to see the Spotify-connectable devices and connect to them.
    """
    def __init__(self, spotifyplayer: SpotifyPlayer, last_device_cache: dict = None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not last_device_cache:
            last_device_cache = self.spotifyplayer.devices
        self.last_device_cache = last_device_cache
        self.spotifyplayer = spotifyplayer
        self.verticalLayout_2 = QtWidgets.QVBoxLayout(self)
        self.verticalLayout_2.setContentsMargins(0, 0, 0, 0)
        self.verticalLayout_2.setSpacing(0)
        self.verticalLayout_2.setObjectName("verticalLayout_2")
        self.verticalFrame = QtWidgets.QFrame(self)
        self.verticalFrame.setObjectName("verticalFrame")
        self.verticalLayout = QtWidgets.QVBoxLayout(self.verticalFrame)
        self.verticalLayout.setContentsMargins(10, 10, 10, 0)
        self.verticalLayout.setSpacing(0)
        self.verticalLayout.setObjectName("verticalLayout")
        self.verticalFrame_2 = QtWidgets.QFrame(self.verticalFrame)
        self.verticalFrame_2.setStyleSheet("QFrame {\n"
                                           "    background-color: rgb(39, 44, 54);\n"
                                           "    border-radius: 20px;\n"
                                           "}")
        self.verticalFrame_2.setObjectName("verticalFrame_2")
        self.verticalLayout_3 = QtWidgets.QVBoxLayout(self.verticalFrame_2)
        self.verticalLayout_3.setContentsMargins(0, 11, 0, 0)
        self.verticalLayout_3.setSpacing(0)
        self.verticalLayout_3.setObjectName("verticalLayout_3")
        self.horizontalFrame_2 = QtWidgets.QFrame(self.verticalFrame_2)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Ignored)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.horizontalFrame_2.sizePolicy().hasHeightForWidth())
        self.horizontalFrame_2.setSizePolicy(sizePolicy)
        self.horizontalFrame_2.setMinimumSize(QtCore.QSize(0, 50))
        self.horizontalFrame_2.setMaximumSize(QtCore.QSize(16777215, 50))
        self.horizontalFrame_2.setStyleSheet("background: transparent;")
        self.horizontalFrame_2.setObjectName("horizontalFrame_2")
        self.horizontalLayout_2 = QtWidgets.QHBoxLayout(self.horizontalFrame_2)
        self.horizontalLayout_2.setContentsMargins(0, 0, 0, 0)
        self.horizontalLayout_2.setSpacing(0)
        self.horizontalLayout_2.setObjectName("horizontalLayout_2")
        self.spacerItem = QtWidgets.QSpacerItem(40, 20, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum)
        self.horizontalLayout_2.addItem(self.spacerItem)
        self.pushButton = QtWidgets.QPushButton(self.horizontalFrame_2)
        self.pushButton.setEnabled(True)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Ignored)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.pushButton.sizePolicy().hasHeightForWidth())
        self.pushButton.setSizePolicy(sizePolicy)
        self.pushButton.setMinimumSize(QtCore.QSize(50, 50))
        self.pushButton.setMaximumSize(QtCore.QSize(50, 50))
        self.pushButton.setLayoutDirection(QtCore.Qt.LeftToRight)
        scaled = ''
        ratio = get_ratio()
        if ratio != 1:
            scale_one(f'{forward_data_dir}icons{sep}24x24{sep}cil-x', ratio)
            scaled = 'scaled'
        self.pushButton.setStyleSheet("QPushButton {\n"
                                      "    background-color: rgb(39, 44, 54);\n"
                                      "    border: none;\n"
                                      "    border-radius: 20px;\n"
                                      f"    background-image: "
                                      f"url({forward_data_dir + f'icons/24x24/cil-x{scaled}.png'});\n"
                                      "    background-repeat: no-repeat;\n"
                                      "    background-position: center;"
                                      "}\n"
                                      "\n"
                                      "QPushButton:hover {\n"
                                      "    background-color: rgb(43, 48, 60);\n"
                                      "}\n"
                                      "\n"
                                      "QPushButton:pressed {\n"
                                      f"    background-color: rgb{repr(mainui.accent_color)};\n"
                                      "}")
        self.pushButton.setText("")
        self.pushButton.setObjectName("pushButton")
        self.horizontalLayout_2.addWidget(self.pushButton)
        self.pushButton.raise_()
        self.verticalLayout_3.addWidget(self.horizontalFrame_2)
        self.label = QtWidgets.QLabel(self.verticalFrame_2)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Expanding)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.label.sizePolicy().hasHeightForWidth())
        self.label.setSizePolicy(sizePolicy)
        font = QtGui.QFont()
        font.setFamily("Segoe UI")
        font.setPointSize(14)
        self.label.setFont(font)
        self.label.setStyleSheet("color: white;\n"
                                 "background: transparent;")
        self.label.setAlignment(QtCore.Qt.AlignHCenter | QtCore.Qt.AlignTop)
        self.label.setObjectName("label")
        self.label.setFixedHeight(50)
        self.verticalLayout_3.addWidget(self.label)
        self.label_2 = QtWidgets.QLabel(self.verticalFrame_2)
        self.label_2.setFixedHeight(30)
        font = QtGui.QFont()
        font.setFamily("Segoe UI")
        font.setPointSize(8)
        self.label_2.setFont(font)
        self.label_2.setStyleSheet("color: white;")
        self.label_2.setAlignment(QtCore.Qt.AlignHCenter | QtCore.Qt.AlignTop)
        self.label_2.setObjectName("label_2")
        self.label_2.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Preferred)
        self.verticalLayout_3.addWidget(self.label_2)
        self.spacerItem1 = QtWidgets.QSpacerItem(20, 40, QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Expanding)
        self.verticalLayout_3.addItem(self.spacerItem1)
        self.label_2.raise_()
        self.label.raise_()
        self.horizontalFrame_2.raise_()
        self.verticalLayout.addWidget(self.verticalFrame_2)
        self.horizontalFrame = QtWidgets.QFrame(self)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.horizontalFrame.sizePolicy().hasHeightForWidth())
        self.horizontalFrame.setSizePolicy(sizePolicy)
        self.horizontalFrame.setMaximumSize(QtCore.QSize(16777215, 20))
        self.horizontalFrame.setObjectName("horizontalFrame")
        self.horizontalLayout = QtWidgets.QHBoxLayout(self.horizontalFrame)
        self.horizontalLayout.setContentsMargins(0, 0, 0, 0)
        self.horizontalLayout.setSpacing(0)
        self.horizontalLayout.setObjectName("horizontalLayout")
        self.frame = QtWidgets.QFrame(self.horizontalFrame)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.frame.sizePolicy().hasHeightForWidth())
        self.frame.setSizePolicy(sizePolicy)
        self.frame.setMinimumSize(QtCore.QSize(20, 20))
        self.frame.setMaximumSize(20, 20)
        self.frame.setStyleSheet("QFrame {\n"
                                 "    background: transparent;\n"
                                 "    border-top: 15px solid rgb(39, 44, 54);\n"
                                 "    border-bottom: 10px solid rgba(255, 255, 255, 0);\n"
                                 "    border-right: 10px solid rgba(255, 255, 255, 0);\n"
                                 "    border-left: 10px solid rgba(255, 255, 255, 0);\n"
                                 "}")
        self.frame.setFrameShape(QtWidgets.QFrame.StyledPanel)
        self.frame.setFrameShadow(QtWidgets.QFrame.Raised)
        self.frame.setObjectName("frame")
        self.horizontalLayout.addWidget(self.frame)
        self.verticalLayout.addWidget(self.horizontalFrame)
        self.verticalLayout_2.addWidget(self.verticalFrame)
        self.shadow = QtWidgets.QGraphicsDropShadowEffect(self)
        self.shadow.setBlurRadius(7)
        self.shadow.setXOffset(0)
        self.shadow.setYOffset(0)
        self.shadow.setColor(QtGui.QColor(0, 0, 0, 170))
        self.setGraphicsEffect(self.shadow)
        spacerItem1 = self.spacerItem1
        self.verticalLayout_3.removeItem(spacerItem1)
        self.setSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Minimum)
        self.verticalFrame_2.setSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Minimum)
        self.setWindowFlags(QtCore.Qt.Tool | QtCore.Qt.FramelessWindowHint)
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground, True)
        self.devices = {}
        self.last_device_cache = {}  # why
        self.last_active_device = ''
        self.timer = QtCore.QTimer()
        self.populate_device_list(self.last_device_cache)
        self.label.setText('Device List')
        self.label_2.setText('Select a device below to connect to it.')
        self.setStyleSheet('background: transparent;')
        self.verticalFrame.setStyleSheet('background: transparent;')
        self.pushButton.hide()
        self.horizontalFrame_2.hide()
        self.mouseoverwindow = False
        self.verticalLayout.setSizeConstraint(QtWidgets.QLayout.SetMinimumSize)
        self.new_event = False
        self.timer.setInterval(250)
        self.timer.timeout.connect(lambda: self.populate_device_list() if self.new_event else None)
        self.timer.start()
        self.spotifyplayer.add_event_reciever(lambda: self.__setattr__('new_event', True))

    def populate_device_list(self, devices: dict = None):
        try:
            self.new_event = False
            if not devices:
                devices = self.spotifyplayer.devices
            if devices == self.last_device_cache and self.spotifyplayer.active_device_id == self.last_active_device:
                return
            for id_, device in self.devices.items():
                self.verticalLayout_3.removeWidget(device)
                device.hide()
                device.deleteLater()
                del device  # you can never be too safe with memory leaks
            self.devices = {}
            for id_, device in devices.items():
                devicewidget = Device(device, self.spotifyplayer)
                self.devices.update({id_: devicewidget})
                self.verticalLayout_3.addWidget(devicewidget)
            if self.timer.isActive():  # what
                for _ in range(0, 10):  # how
                    QtCore.QCoreApplication.instance().processEvents()  # why the hell does this work
                if self.devices:
                    self.setFixedWidth(list(self.devices.values())[0].width())
            self.move_to_position()
            self.last_device_cache = devices.copy()
            self.last_active_device = self.spotifyplayer.active_device_id
        except RuntimeError:
            pass  # help

    def enterEvent(self, a0: QtCore.QEvent) -> None:
        self.mouseoverwindow = True

    def leaveEvent(self, a0: QtCore.QEvent) -> None:
        self.mouseoverwindow = False

    def move_to_position(self):
        pass  # placeholder


@adjust_sizing()
class Device(QtWidgets.QWidget):
    """
        This is a QWidget that represents a Spotify device.
    """
    def __init__(self, device_dict: dict, spotifyplayer: SpotifyPlayer, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.device_dict = device_dict
        self.spotifyplayer = spotifyplayer
        self.verticalLayout = QtWidgets.QVBoxLayout(self)
        self.verticalLayout.setContentsMargins(0, 0, 0, 0)
        self.verticalLayout.setSpacing(0)
        self.verticalLayout.setObjectName("verticalLayout")
        self.horizontalFrame = QtWidgets.QFrame(self)
        self.horizontalFrame.setObjectName("horizontalFrame")
        self.horizontalLayout = QtWidgets.QHBoxLayout(self.horizontalFrame)
        self.horizontalLayout.setObjectName("horizontalLayout")
        self.label = QtWidgets.QLabel(self.horizontalFrame)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Maximum, QtWidgets.QSizePolicy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.label.sizePolicy().hasHeightForWidth())
        font = QtGui.QFont()
        font.setFamily('Segoe UI')
        font.setPointSize(8)
        self.label.setSizePolicy(sizePolicy)
        self.label.setFont(font)
        self.label.setMaximumSize(QtCore.QSize(90, 90))
        self.label.setText("")
        self.label.setObjectName("label")
        self.horizontalLayout.addWidget(self.label)
        self.verticalFrame = QtWidgets.QFrame(self.horizontalFrame)
        self.verticalFrame.setObjectName("verticalFrame")
        self.verticalLayout_2 = QtWidgets.QVBoxLayout(self.verticalFrame)
        self.verticalLayout_2.setContentsMargins(11, 0, 11, 11)
        self.widgets_to_ignore = [self.verticalLayout_2, self.horizontalLayout]
        self.verticalLayout_2.setObjectName("verticalLayout_2")
        self.label_2 = QtWidgets.QLabel(self.verticalFrame)
        self.label_2.setFont(font)
        self.label_2.setStyleSheet("color: white;")
        self.label_2.setObjectName("label_2")
        self.verticalLayout_2.addWidget(self.label_2)
        self.label_3 = QtWidgets.QLabel(self.verticalFrame)
        self.label_3.setMaximumSize(QtCore.QSize(16777215, 30))
        self.label_2.setFixedHeight(30)
        self.label_3.setFixedHeight(30)
        self.label_3.setStyleSheet("color: white;")
        self.label_3.setObjectName("label_3")
        self.label_3.setFont(font)
        self.verticalLayout_2.addWidget(self.label_3)
        self.horizontalLayout.addWidget(self.verticalFrame)
        self.verticalLayout.addWidget(self.horizontalFrame)
        self.label_2.setText(self.device_dict['name'])
        if spotifyplayer.active_device_id == self.device_dict['device_id']:
            active_string = 'Currently Playing'
            self.label_2.setStyleSheet(f'color: rgb{repr(mainui.accent_color)}; background-color: transparent;')
            self.label_3.setStyleSheet(f'color: rgb{repr(mainui.accent_color)}; background-color: transparent;')

        else:
            active_string = 'Not Playing'
        if not self.device_dict['capabilities'].get('is_controllable'):
            self.label_2.setStyleSheet('color: rgb(70, 70, 70); background-color: transparent;')
            self.label_3.setStyleSheet('color: rgb(70, 70, 70); background-color: transparent;')
            self.controllable = False
        else:
            self.controllable = True
        footer_string = f'{self.device_dict["device_type"].title()} • {active_string}'
        self.label_3.setText(footer_string)
        scaled = ''
        ratio = get_ratio()
        if ratio != 1:
            icons = ['cil-monitor', 'cil-mobile', 'cil-mobile-landscape', 'cil-screen-desktop', 'cil-gamepad',
                     'cil-speaker']
            icons = [f'24x24{sep}{icon}' for icon in icons]
            scale_images(icons, ratio)
            scaled = 'scaled'
        device_images = {'COMPUTER': 'cil-monitor.png', 'SMARTPHONE': 'cil-mobile.png',
                         'TABLET': 'cil-mobile-landscape.png', 'TV': 'cil-screen-desktop.png',
                         'GAME_CONSOLE': 'cil-gamepad.png', 'SPEAKER': 'cil-speaker.png'}
        device_image = device_images.get(self.device_dict['device_type'], 'cil-speaker.png')
        device_image = device_image.replace('.png', f'{scaled}.png')
        self.label.setStyleSheet(f'background-image: url({forward_data_dir + f"icons/24x24/{device_image}"});\n'
                                 'background-repeat: no-repeat;\n'
                                 'background-position: center;\n'
                                 'background-color: transparent;')
        self.label.setFixedWidth(34)
        self.setFixedHeight(90)
        self.horizontalFrame.setStyleSheet("QWidget {\n"
                                           "    background-color: rgb(39, 44, 54);\n"
                                           "}\n"
                                           "QWidget:hover {\n"
                                           "    background-color: rgb(45, 50, 60);\n"
                                           "}")
        self.verticalFrame.setStyleSheet('background: transparent;')
        self.setStyleSheet('border-radius: 20px;')
        self.mousePressEvent = lambda a0: self.connect()

    def showEvent(self, a0: QtGui.QShowEvent) -> None:
        QtWidgets.QWidget.showEvent(self, a0)

    def connect(self):
        if not self.spotifyplayer.active_device_id == self.device_dict['device_id'] and self.controllable:
            self.spotifyplayer.transfer(self.device_dict['device_id'])


class PartialAdvancedUserStatus:
    """
        This is a class that represents the advanced user status of a user, to later be turned into a QWidget.
    """
    def __init__(self, spotifysong, status):
        self.spotifysong = spotifysong
        self.status = status
        self.dominant_color = None
        self.user_id = spotifysong.client_id
        if not os.path.exists(data_dir + f'icon{spotifysong.client_id}.png'):
            rand = random.randint(0, 10000)
            if spotifysong.clientavatar:
                url = spotifysong.clientavatar
                img_data = requests.get(url, timeout=15).content
                with open(data_dir + f'tempicon{rand}{spotifysong.client_id}.png', 'wb') as handler:
                    handler.write(img_data)
            else:
                image = Image.open(data_dir + 'default_user.png').resize((200, 200))
                image.save(data_dir + f'tempicon{rand}{spotifysong.client_id}.png')
            mask = Image.open(data_dir + 'mask.png').convert('L')
            mask = mask.resize((200, 200))
            im = Image.open(data_dir + f'tempicon{rand}{spotifysong.client_id}.png').convert('RGBA')
            output = ImageOps.fit(im, mask.size, centering=(0.5, 0.5))
            output.putalpha(mask)
            output.resize((200, 200))
            try:
                os.remove(data_dir + f'tempicon{rand}{spotifysong.client_id}.png')
            except (FileNotFoundError, OSError, PermissionError):
                pass
            output.save(data_dir + f'icon{spotifysong.client_id}.png')
        shadow_color = None
        if spotifysong.playing_type in ('track', 'local file'):
            download_album(spotifysong.albumimagelink)
            self.dominant_color, self.dark_color, self.text_color = extract_color(spotifysong.albumimagelink)
            feather_image(spotifysong.albumimagelink)
            with open(data_dir + 'profile_cache.json') as imagefile:
                profile_images = json.load(imagefile)
            if spotifysong.client_id in profile_images:
                avg = np.average(profile_images[spotifysong.client_id][0])
                if avg > 200:
                    shadow_color = [255, 255, 255, 200]
                else:
                    shadow_color = [0, 0, 0, 200]
        else:
            with open(data_dir + 'profile_cache.json') as imagefile:
                profile_images = json.load(imagefile)
            if spotifysong.client_id in profile_images:
                self.dominant_color = tuple(profile_images[spotifysong.client_id][0])
                self.dark_color = tuple(profile_images[spotifysong.client_id][1])
                self.text_color = tuple(profile_images[spotifysong.client_id][2])
                if np.average(self.dominant_color) > 200:
                    shadow_color = [255, 255, 255, 200]
                else:
                    shadow_color = [0, 0, 0, 200]
            else:
                image = ColorThief(data_dir + f'icon{spotifysong.client_id}.png')
                dominant_color = image.get_color(quality=1)
                dark_color = [color - 30 if not (color - 30) < 0 else 0 for color in dominant_color]
                if np.average(dominant_color) > 200:
                    text_color = [0, 0, 0]
                    shadow_color = [255, 255, 255, 200]
                else:
                    text_color = [255, 255, 255]
                    shadow_color = [0, 0, 0, 200]
                with open(data_dir + 'profile_cache.json', 'w') as imagefile:
                    profile_images.update({spotifysong.client_id:
                                           [list(dominant_color), list(dark_color), text_color]})
                    json.dump(profile_images, imagefile, indent=4)
                self.dominant_color = dominant_color
                self.dark_color = dark_color
                self.text_color = text_color
        self.shadow_color = shadow_color
        if self.spotifysong.contexttype == 'playlist':
            if self.spotifysong.songname:
                try:
                    id_ = self.spotifysong.contextdata.split('/')[-1]
                    resp = mainui.client.spotifyplayer.create_api_request(f'/playlists/{id_}').json()
                    if 'error' in resp:
                        self.playlist_name = None
                    else:
                        self.playlist_name = resp['name'] if resp['public'] else None
                except Exception as e:
                    logger.error('An unexpected error has occured: ', exc_info=e)
                    self.playlist_name = None
            else:
                self.playlist_name = None
        else:
            self.playlist_name = None

    def convert_to_widget(self):
        return AdvancedUserStatus(self.spotifysong, self.user_id, self.status, self.playlist_name,
                                  self.dominant_color, self.dark_color, self.text_color, self.shadow_color)


@adjust_sizing()
class AdvancedUserStatus(QtWidgets.QWidget):
    """
        This is the QWidget representation of PartialAdvancedUserStatus.
    """
    def __init__(self, spotifysong: SpotifySong, user_id: str, status: str, playlist_name: typing.Optional[str],
                 dominant_color, dark_color, text_color=None, shadow_color=None,
                 *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setAttribute(QtCore.Qt.WA_StyledBackground)
        self.spotifysong = spotifysong
        self.user_id = user_id
        self.status = status
        self.playlist_name = playlist_name
        self.dominant_color = tuple(dominant_color)
        self.dark_color = tuple(dark_color)
        if text_color:
            self.text_color = tuple(text_color)
        else:
            self.text_color = (255, 255, 255)
        self.setObjectName("Form")
        self.resize(788, 560)
        self.setStyleSheet("#Form {\n"
                           "background-color: qlineargradient(spread:pad, x1:0, y1:0, x2:1, y2:0,"
                           f" stop:0 rgb{repr(self.dominant_color)}, stop:1 rgb{repr(self.dark_color)});\n"
                           "}")
        self.horizontalLayout = QtWidgets.QHBoxLayout(self)
        self.horizontalLayout.setContentsMargins(15, 15, 15, 15)
        self.horizontalLayout.setSpacing(0)
        self.horizontalLayout.setObjectName("horizontalLayout")
        self.verticalFrame = QtWidgets.QFrame(self)
        self.verticalFrame.setObjectName("verticalFrame")
        color = "rgba(0, 0, 0, 50)" if np.mean(text_color) > np.mean(dominant_color) else "rgba(255, 255, 255, 50)"
        if np.mean([abs(dominant_color[i] - text_color[i]) for i in range(3)]) > 60:
            color = 'rgba(0, 0, 0, 50)'
        if np.mean(dominant_color) > 180:
            color = 'rgba(255, 255, 255, 50)'
        self.verticalFrame.setStyleSheet("#verticalFrame {\n"
                                         f"background: {color};\n"
                                         f"border-radius: 30px;\n"
                                         "}")

        self.verticalLayout = QtWidgets.QVBoxLayout(self.verticalFrame)
        self.verticalLayout.setContentsMargins(10, 10, 10, 10)
        self.verticalLayout.setObjectName("verticalLayout")
        self.horizontalFrame = QtWidgets.QFrame(self.verticalFrame)
        self.horizontalFrame.setMaximumSize(QtCore.QSize(16777215, 400))
        self.horizontalFrame.setObjectName("horizontalFrame")
        self.horizontalLayout_2 = QtWidgets.QHBoxLayout(self.horizontalFrame)
        self.horizontalLayout_2.setObjectName("horizontalLayout_2")
        self.verticalFrame_3 = QtWidgets.QFrame(self.horizontalFrame)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.verticalFrame_3.sizePolicy().hasHeightForWidth())
        self.verticalFrame_3.setSizePolicy(sizePolicy)
        self.verticalFrame_3.setObjectName("verticalFrame_3")
        self.verticalLayout_2 = QtWidgets.QVBoxLayout(self.verticalFrame_3)
        self.verticalLayout_2.setContentsMargins(10, 10, -1, -1)
        self.verticalLayout_2.setSpacing(15)
        self.verticalLayout_2.setObjectName("verticalLayout_2")
        self.label_3 = QtWidgets.QLabel(self.verticalFrame_3)
        self.label_3.setMinimumSize(QtCore.QSize(200, 200))
        self.label_3.setMaximumSize(QtCore.QSize(200, 200))
        self.label_3.setStyleSheet(
            f"border-image: url({forward_data_dir + 'icon' + self.user_id}.png);")
        self.label_3.setText("")
        self.label_3.setObjectName("label_3")
        shadow = QtWidgets.QGraphicsDropShadowEffect()
        shadow.setXOffset(0)
        shadow.setYOffset(0)
        shadow.setBlurRadius(15)
        shadow.setColor(QtGui.QColor(*shadow_color))
        self.label_3.setGraphicsEffect(shadow)
        self.verticalLayout_2.addWidget(self.label_3)
        self.label = QtWidgets.QLabel(self.verticalFrame_3)
        font = QtGui.QFont()
        font.setFamily("Segoe UI")
        font.setPointSize(24)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Ignored, QtWidgets.QSizePolicy.Preferred)
        self.label.setFont(font)
        self.label.setSizePolicy(sizePolicy)
        self.label.setStyleSheet(f"color: rgb{repr(text_color)};")
        self.label.setObjectName("label")
        self.verticalLayout_2.addWidget(self.label)
        self.label_2 = QtWidgets.QLabel(self.verticalFrame_3)
        font = QtGui.QFont()
        font.setFamily("Segoe UI")
        font.setPointSize(11)
        self.label_2.setFont(font)
        self.label_2.setStyleSheet(f"color: rgb{repr(text_color)};")
        self.label_2.setObjectName("label_2")
        self.verticalLayout_2.addWidget(self.label_2)
        self.label_6 = QtWidgets.QLabel(self.verticalFrame_3)
        font = QtGui.QFont()
        font.setFamily("Segoe UI")
        font.setPointSize(9)
        self.label_6.setFont(font)
        self.label_6.setStyleSheet(f"color: rgb{repr(text_color)};")
        self.label_6.setObjectName("label_6")
        self.verticalLayout_2.addWidget(self.label_6)
        self.horizontalLayout_2.addWidget(self.verticalFrame_3)
        self.verticalFrame_2 = QtWidgets.QFrame(self.horizontalFrame)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Expanding)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.verticalFrame_2.sizePolicy().hasHeightForWidth())
        self.verticalFrame_2.setSizePolicy(sizePolicy)
        self.verticalFrame_2.setObjectName("verticalFrame_2")
        self.verticalLayout_3 = QtWidgets.QVBoxLayout(self.verticalFrame_2)
        self.verticalLayout_3.setContentsMargins(-1, 0, -1, -1)
        self.verticalLayout_3.setObjectName("verticalLayout_3")
        self.horizontalFrame1 = QtWidgets.QFrame(self.verticalFrame_2)
        font = QtGui.QFont()
        font.setPointSize(7)
        self.horizontalFrame1.setFont(font)
        self.horizontalFrame1.setObjectName("horizontalFrame1")
        self.horizontalLayout_3 = QtWidgets.QHBoxLayout(self.horizontalFrame1)
        self.horizontalLayout_3.setContentsMargins(10, 10, 10, 10)
        self.horizontalLayout_3.setObjectName("horizontalLayout_3")
        self.label_4 = QtWidgets.QLabel(self.horizontalFrame1)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Expanding)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.label_4.sizePolicy().hasHeightForWidth())
        self.label_4.setSizePolicy(sizePolicy)
        self.label_4.setMinimumSize(QtCore.QSize(200, 200))
        self.label_4.setMaximumSize(QtCore.QSize(200, 200))
        if spotifysong.albumimagelink:
            albumlink = spotifysong.albumimagelink.split('/image/')[1]
        else:
            albumlink = 'None'
        self.label_4.setStyleSheet(
            f"border-image: url({forward_data_dir}album{albumlink}.png) 0 0 0 0;")
        self.label_4.setText("")
        self.label_4.setObjectName("label_4")
        self.horizontalLayout_3.addWidget(self.label_4)
        self.verticalLayout_3.addWidget(self.horizontalFrame1)
        self.label_5 = QtWidgets.QLabel(self.verticalFrame_2)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Expanding)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.label_5.sizePolicy().hasHeightForWidth())
        self.label_5.setSizePolicy(sizePolicy)
        font = QtGui.QFont()
        font.setFamily("Segoe UI")
        font.setPointSize(10)
        self.label_5.setFont(font)
        self.label_5.setStyleSheet(f"color: rgb{repr(text_color)};")
        self.label_5.setTextFormat(QtCore.Qt.AutoText)
        self.label_5.setAlignment(QtCore.Qt.AlignCenter)
        self.label_5.setObjectName("label_5")
        self.verticalLayout_3.addWidget(self.label_5)
        self.horizontalLayout_2.addWidget(self.verticalFrame_2)
        self.verticalLayout.addWidget(self.horizontalFrame)
        self.horizontalFrame2 = QtWidgets.QFrame(self.verticalFrame)
        self.horizontalFrame2.setStyleSheet("QPushButton {\n"
                                            f"    border: 2px solid rgb{repr(text_color)};\n"
                                            f"    color: rgb{repr(text_color)};\n"
                                            f"    border-radius: 10px;\n"
                                            "}")
        self.horizontalFrame2.setObjectName("horizontalFrame2")
        self.horizontalLayout_5 = QtWidgets.QHBoxLayout(self.horizontalFrame2)
        self.horizontalLayout_5.setContentsMargins(15, -1, 15, -1)
        self.horizontalLayout_5.setSpacing(15)
        self.horizontalLayout_5.setObjectName("horizontalLayout_5")
        self.pushButton = QtWidgets.QPushButton(self.horizontalFrame2)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.pushButton.sizePolicy().hasHeightForWidth())
        self.pushButton.setSizePolicy(sizePolicy)
        self.pushButton.setMinimumSize(QtCore.QSize(0, 40))
        self.pushButton.setMaximumSize(QtCore.QSize(16777215, 40))
        font = QtGui.QFont()
        font.setFamily("Segoe UI")
        font.setPointSize(12)
        self.pushButton.setFont(font)
        self.pushButton.setObjectName("pushButton")
        self.horizontalLayout_5.addWidget(self.pushButton)
        self.pushButton_2 = QtWidgets.QPushButton(self.horizontalFrame2)
        self.pushButton_2.setMinimumSize(QtCore.QSize(0, 40))
        self.pushButton_2.setMaximumSize(QtCore.QSize(16777215, 40))
        font = QtGui.QFont()
        font.setFamily("Segoe UI")
        font.setPointSize(12)
        self.pushButton_2.setFont(font)
        self.pushButton_2.setStyleSheet("")
        self.pushButton_2.setObjectName("pushButton_2")
        self.horizontalLayout_5.addWidget(self.pushButton_2)
        self.verticalLayout.addWidget(self.horizontalFrame2)
        self.horizontalFrame_2 = QtWidgets.QFrame(self.verticalFrame)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Expanding)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.horizontalFrame_2.sizePolicy().hasHeightForWidth())
        self.horizontalFrame_2.setSizePolicy(sizePolicy)
        self.horizontalFrame_2.setMinimumSize(QtCore.QSize(0, 100))
        self.horizontalFrame_2.setMaximumSize(QtCore.QSize(16777215, 100))
        self.horizontalFrame_2.setObjectName("horizontalFrame_2")
        self.horizontalLayout_4 = QtWidgets.QHBoxLayout(self.horizontalFrame_2)
        self.horizontalLayout_4.setObjectName("horizontalLayout_4")
        self.label_7 = QtWidgets.QLabel(self.horizontalFrame_2)
        self.label_7.setMinimumSize(QtCore.QSize(40, 0))
        self.label_7.setMaximumSize(QtCore.QSize(16777215, 16777215))
        font = QtGui.QFont()
        font.setFamily("Segoe UI")
        font.setPointSize(10)
        self.label_7.setFont(font)
        self.label_7.setStyleSheet(f"color: rgb{repr(text_color)};")
        self.label_7.setAlignment(QtCore.Qt.AlignLeading | QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter)
        self.label_7.setObjectName("label_7")
        self.horizontalLayout_4.addWidget(self.label_7)
        self.horizontalSlider = QtWidgets.QSlider(self.horizontalFrame_2)
        self.horizontalSlider.setMaximumSize(QtCore.QSize(16777215, 10))
        self.horizontalSlider.setStyleSheet("QSlider::groove:horizontal { \n"
                                            "    background-color: rgba(52, 59, 72, 50);\n"
                                            "    border: none;\n"
                                            f"    height: 10px; \n"
                                            f"    border-radius: 5px;\n"
                                            "}\n"
                                            "\n"
                                            "QSlider::sub-page:horizontal {\n"
                                            f"    background-color: rgb{repr(text_color)};\n"
                                            f"    border-top-left-radius: 5px;\n"
                                            f"    border-bottom-left-radius: 5px;\n"
                                            "}\n"
                                            "\n"
                                            "QSlider::handle:horizontal { \n"
                                            f"    background-color: rgb{repr(text_color)}; \n"
                                            f"    border: 0px solid rgb{repr(text_color)}; \n"
                                            f"    width: 10px; \n"
                                            f"    height: 10px; \n"
                                            f"    border-radius: 5px;\n"
                                            "}")
        self.horizontalSlider.setMaximum(10000)
        self.horizontalSlider.setTracking(True)
        self.horizontalSlider.setDisabled(True)
        self.horizontalSlider.setOrientation(QtCore.Qt.Horizontal)
        self.horizontalSlider.setObjectName("horizontalSlider")
        self.horizontalLayout_4.addWidget(self.horizontalSlider)
        self.label_8 = QtWidgets.QLabel(self.horizontalFrame_2)
        self.label_8.setMinimumSize(QtCore.QSize(40, 0))
        self.label_8.setMaximumSize(QtCore.QSize(16777215, 16777215))
        font = QtGui.QFont()
        font.setFamily("Segoe UI")
        font.setPointSize(10)
        self.label_8.setFont(font)
        self.label_8.setStyleSheet(f"color: rgb{repr(text_color)};")
        self.label_8.setObjectName("label_8")
        self.horizontalLayout_4.addWidget(self.label_8)
        self.verticalLayout.addWidget(self.horizontalFrame_2)
        self.horizontalLayout.addWidget(self.verticalFrame)

        self.label.setText(spotifysong.clientusername)
        self.timer = QtCore.QTimer()
        self.spotifylistener = None
        if status == 'listening':
            self.label_2.setText('Listening To Spotify')
            if spotifysong.song_authors:
                song_authors = ', '.join(spotifysong.song_authors)
            else:
                song_authors = 'Unknown'
            if spotifysong.albumname:
                albumname = spotifysong.albumname
            else:
                albumname = 'Unknown'
            self.label_5.setText(f'<html><head/><body><p>{limit_text(spotifysong.songname, 30)}'
                                 f'</p><p>By: <span style=" font-weight:600;">{limit_text(song_authors, 30)}</span></p>'
                                 f'<p>On: <span style=" font-weight:600;">{limit_text(albumname, 30)}'
                                 f'</span></p></body></html>')
            self.pushButton.setText('Play On Spotify')
            if spotifysong.songid:
                self.pushButton.setCursor(QtGui.QCursor(QtCore.Qt.PointingHandCursor))
                self.pushButton_2.setCursor(QtGui.QCursor(QtCore.Qt.PointingHandCursor))

                def play_song():
                    if mainui.client.spotifyplayer and mainui.client.spotifyplayer.active_device_id:
                        try:
                            mainui.client.spotifyplayer.command(mainui.client.spotifyplayer.play(spotifysong.songid))
                            return
                        except Exception as e:
                            logger.warning('Playing song in Spotify failed, opening Spotify', exc_info=e)
                            mainui.show_snack_bar(SnackBar('There was an error trying to play the song in Spotify, '
                                                           'attempting to open Spotify', True))
                    else:
                        try:
                            os.startfile(f'spotify:track:{spotifysong.songid}')
                            mainui.show_snack_bar(SnackBar('No Spotify session detected, opening Spotify...'))
                        except (FileNotFoundError, Exception) as exc:
                            mainui.show_snack_bar(SnackBar('Could not find Spotify. Either install Spotify or start '
                                                           'playing music in Spotify.', False, True))
                            if not isinstance(exc, FileNotFoundError):
                                logger.error('Unexpected error occured while trying to open Spotify: ', exc_info=exc)

                self.pushButton.clicked.connect(play_song)

                def listen(colors):
                    if mainui.listentofriends.spotifylistener:
                        try:
                            mainui.listentofriends.spotifylistener.end(no_log=True)
                        except Exception as _exc:
                            logger.error('Unexpected error occured while ending previous listening session: ',
                                         exc_info=_exc)
                    mainui.partiallisteningtofriends = PartialListeningToFriends(True, spotifysong.client_id,
                                                                                 mainui.spotifylistener, spotifysong,
                                                                                 colors[0], colors[1], colors[2])
                    new = mainui.partiallisteningtofriends.convert_to_widget()
                    mainui.listentofriends.hide()
                    if hasattr(mainui.listentofriends, 'timer'):
                        mainui.listentofriends.timer.stop()
                    mainui.listentofriends.deleteLater()
                    mainui.verticalLayout_38.replaceWidget(mainui.listentofriends, new)
                    mainui.listentofriends = new
                    mainui.listentofriends.show()
                    mainui.pushButton_18.click()

                def extract_color_to_listen():
                    if not mainui.client.spotifyplayer.devices:
                        mainui.show_snack_bar(SnackBar('Unable to find an active Spotify session; try playing a song.',
                                                       False, True))
                        return
                    if self.spotifysong.client_id in mainui.client.listening_friends:
                        mainui.show_snack_bar(SnackBar('You cannot listen to someone who is already listening to you.'))
                        return
                    if mainui.listentofriends and (sp_listener := mainui.listentofriends.spotifylistener):
                        if sp_listener.running and sp_listener.friend_id == spotifysong.client_id:
                            mainui.pushButton_18.click()
                            return

                    try:
                        mainui.client.client.emit('start_listening', self.spotifysong.client_id, '/api/authorization')
                    except Exception as _exc:
                        logger.error('An unexpected error occured while trying to listen along: ', exc_info=_exc)
                        mainui.show_snack_bar(SnackBar('An unexpected error occured while trying to listen along.',
                                                       True, True))

                    def run():
                        dominant, dark, text = extract_color(spotifysong.albumimagelink)
                        return dominant, text, dark

                    runnable = Runnable(run, parent=mainui)
                    runnable.callback.connect(listen)
                    runnable.start()

                if mainui.client.spotifyplayer:
                    self.pushButton_2.clicked.connect(extract_color_to_listen)
                else:
                    self.pushButton_2.setCursor(QtGui.QCursor(QtCore.Qt.ForbiddenCursor))
                    self.pushButton_2.tooltip = Tooltip('Unable to listen along, because there was a problem with your '
                                                        'login', self.pushButton_2)

            else:
                self.horizontalFrame2.hide()
            self.pushButton_2.setText('Listen Along On SpotAlong')
            minutes = int(spotifysong.duration / 1000 // 60)
            seconds = spotifysong.duration / 1000 - minutes * 60
            self.label_8.setText(f'{minutes}:{int(seconds):02}')

            def update_duration():
                progress = mainui.client.friendstatus.get(self.user_id)
                if progress:
                    progress = progress.progress
                    if not progress:
                        return
                    progress_minutes = int(progress // 60)
                    progress_seconds = progress - progress_minutes * 60
                    self.label_7.setText(f'{progress_minutes}:{int(progress_seconds):02}')
                    self.horizontalSlider.setSliderPosition(10000 // (spotifysong.duration / 1000 / progress))

            update_duration()
            self.timer.timeout.connect(update_duration)
            self.timer.setInterval(1000)
            self.timer.start()
        else:
            self.label_2.setText(status.title())
            self.horizontalLayout_2.removeWidget(self.verticalFrame_2)
            self.verticalFrame_2.hide()
            self.verticalFrame_2.deleteLater()
            self.verticalFrame_2 = QtWidgets.QSpacerItem(40, 20)
            self.horizontalLayout_2.addItem(self.verticalFrame_2)
            self.verticalLayout_2.removeWidget(self.label_6)
            self.label_6.hide()
            self.label_6.deleteLater()
            self.verticalLayout.removeWidget(self.horizontalFrame2)
            self.horizontalFrame2.hide()
            self.horizontalFrame2.deleteLater()
            self.verticalLayout.removeWidget(self.horizontalFrame_2)
            self.horizontalFrame_2.hide()
            self.horizontalFrame_2.deleteLater()
        if playlist_name:
            self.label_6.setSizePolicy(QtWidgets.QSizePolicy.Ignored, QtWidgets.QSizePolicy.Preferred)
        else:
            self.verticalLayout_2.removeWidget(self.label_6)

    def showEvent(self, _: QtGui.QShowEvent) -> None:
        QtWidgets.QWidget.showEvent(self, _)
        self.setStyleSheet(self.styleSheet())
        self.label.setText(limit_text_smart(self.spotifysong.clientusername, self.label))
        if self.playlist_name:
            try:
                self.label_6.setText(limit_text_rich(f'Listening to a playlist: <strong>{self.playlist_name}</strong>',
                                                     self.label_6))
            except RuntimeError:
                pass

    def resizeEvent(self, a0):
        QtWidgets.QWidget.resizeEvent(self, a0)
        self.label.setText(limit_text_smart(self.spotifysong.clientusername, self.label))
        if self.playlist_name:
            self.label_6.setText(limit_text_rich(f'Listening to a playlist: <strong>{self.playlist_name}</strong>',
                                                 self.label_6))


class PartialListedFriendStatus:
    """
        This is a class that represents the listed friend status of a user in the friends tab, to be later converted
        into a QWidget.
    """
    def __init__(self, spotifysong, status):
        self.spotifysong = spotifysong
        self.status = status
        self.user_id = spotifysong.client_id
        if os.path.exists(data_dir + f'icon{spotifysong.client_id}.png'):
            rand = random.randint(0, 10000)
            if spotifysong.clientavatar:
                url = spotifysong.clientavatar
                img_data = requests.get(url, timeout=15).content
                with open(data_dir + f'tempicon{rand}{spotifysong.client_id}.png', 'wb') as handler:
                    handler.write(img_data)
            else:
                image = Image.open(data_dir + 'default_user.png').resize((200, 200))
                image.save(data_dir + f'tempicon{rand}{spotifysong.client_id}.png')
            mask = Image.open(data_dir + 'mask.png').convert('L')
            mask = mask.resize((200, 200))
            im = Image.open(data_dir + f'tempicon{rand}{spotifysong.client_id}.png').convert('RGBA')
            output = ImageOps.fit(im, mask.size, centering=(0.5, 0.5))
            output.putalpha(mask)
            output.resize((200, 200))
            try:
                os.remove(data_dir + f'tempicon{rand}{spotifysong.client_id}.png')
            except (FileNotFoundError, OSError, PermissionError):
                pass
            output.save(data_dir + f'icon{spotifysong.client_id}.png')

    def convert_to_widget(self):
        return ListedFriendStatus(self.spotifysong, self.status)


@adjust_sizing()
class ListedFriendStatus(QtWidgets.QWidget):
    """
        This is the QWidget implementation of PartialListedFriendStatus.
    """
    def __init__(self, spotifysong, status, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.spotifysong = spotifysong
        self.status = status
        self.user_id = spotifysong.client_id
        self.setObjectName("Form")
        self.setStyleSheet('#Form {background-color: transparent;}')
        self.resize(178, 50)
        self.setMaximumWidth(229)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.sizePolicy().hasHeightForWidth())
        self.setSizePolicy(sizePolicy)
        self.verticalLayout = QtWidgets.QVBoxLayout(self)
        self.verticalLayout.setContentsMargins(0, 0, 0, 0)
        self.verticalLayout.setSpacing(0)
        self.verticalLayout.setObjectName("verticalLayout")
        self.horizontalFrame = QtWidgets.QFrame(self)
        ratio = get_ratio()

        def leave(_):
            self.horizontalFrame.setStyleSheet(adj_style(ratio, "QFrame {\n"
                                                                "    background-color: rgb(38, 43, 53);\n"
                                                                "    border-radius: 10px;\n"
                                                                "}"))

        def hover(_):
            self.horizontalFrame.setStyleSheet(adj_style(ratio, "QFrame {\n"
                                                                "    background-color: rgb(58, 63, 73);\n"
                                                                "    border-radius: 10px;\n"
                                                                "}"))

        def clicked(_):
            mainui.advanceduserstatus.setCurrentWidget(mainui.advancedfriendstatuses[self.user_id])

        self.horizontalFrame.enterEvent = hover
        self.horizontalFrame.leaveEvent = leave
        self.horizontalFrame.mousePressEvent = clicked
        self.horizontalFrame.setObjectName("horizontalFrame")
        self.horizontalLayout = QtWidgets.QHBoxLayout(self.horizontalFrame)
        self.horizontalLayout.setContentsMargins(7, -1, -1, -1)
        self.horizontalLayout.setObjectName("horizontalLayout")
        self.label = QtWidgets.QLabel(self.horizontalFrame)
        self.label.setMinimumSize(QtCore.QSize(45, 45))
        self.label.setMaximumSize(QtCore.QSize(45, 45))
        self.label.setStyleSheet("border-radius: 22px;\n"
                                 f"border-image: url({forward_data_dir}icon{self.user_id}.png);\n"
                                 "background-color: transparent;")
        self.label.setText("")
        self.label.setObjectName("label")
        self.horizontalLayout.addWidget(self.label)
        self.label_2 = QtWidgets.QLabel(self.horizontalFrame)
        font = QtGui.QFont()
        font.setFamily("Segoe UI")
        font.setPointSize(8)
        self.label_2.setFont(font)
        self.label_2.setStyleSheet("color: white; background-color; transparent;")
        self.label_2.setObjectName("label_2")
        self.horizontalLayout.addWidget(self.label_2)
        self.verticalLayout.addWidget(self.horizontalFrame)

    def showEvent(self, a0):
        self.label_2.setText(limit_text_smart(self.spotifysong.clientusername, self.label_2))
        return QtWidgets.QWidget.showEvent(self, a0)


@adjust_sizing()
class Dialog(QtWidgets.QWidget):
    """
        This is a QWidget that represents a dialog.
    """
    def __init__(self, title: str, description: str, accept: str, callback: typing.Callable, cancel: str = 'Cancel',
                 error=False, *args, **kwargs):
        super().__init__(parent=mainui, *args, **kwargs)
        self.error = error
        self.setObjectName("Form")
        self.resize(497, 168)
        self.setWindowFlags(QtCore.Qt.Tool | QtCore.Qt.FramelessWindowHint)
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground, True)
        self.horizontalLayout = QtWidgets.QHBoxLayout(self)
        self.horizontalLayout.setContentsMargins(0, 0, 0, 0)
        self.horizontalLayout.setSpacing(0)
        self.horizontalLayout.setObjectName("horizontalLayout")
        self.verticalFrame = QtWidgets.QFrame(self)
        self.verticalFrame.setStyleSheet("#verticalFrame {\n"
                                         "    background-color: rgb(27, 29, 35);\n"
                                         "    border-radius: 15px;\n"
                                         "}")
        self.verticalFrame.setObjectName("verticalFrame")
        self.verticalLayout = QtWidgets.QVBoxLayout(self.verticalFrame)
        self.verticalLayout.setContentsMargins(0, 0, 0, 0)
        self.verticalLayout.setObjectName("verticalLayout")
        self.verticalFrame1 = QtWidgets.QFrame(self.verticalFrame)
        self.verticalFrame1.setMinimumSize(QtCore.QSize(0, 0))
        self.verticalFrame1.setObjectName("verticalFrame1")
        self.verticalLayout_2 = QtWidgets.QVBoxLayout(self.verticalFrame1)
        self.verticalLayout_2.setContentsMargins(20, 10, 20, 15)
        self.verticalLayout_2.setSpacing(15)
        self.verticalLayout_2.setObjectName("verticalLayout_2")
        self.label = QtWidgets.QLabel(self.verticalFrame1)
        font = QtGui.QFont()
        font.setFamily("Segoe UI Semibold")
        font.setPointSize(20)
        self.label.setFont(font)
        self.label.setStyleSheet("color: white;")
        self.label.setObjectName("label")
        self.verticalLayout_2.addWidget(self.label)
        self.label_2 = QtWidgets.QLabel(self.verticalFrame1)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Expanding)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.label_2.sizePolicy().hasHeightForWidth())
        self.label_2.setSizePolicy(sizePolicy)
        font = QtGui.QFont()
        font.setFamily("Segoe UI")
        font.setPointSize(12)
        self.label_2.setFont(font)
        self.label_2.setStyleSheet("color: white;")
        self.label_2.setAlignment(QtCore.Qt.AlignLeading | QtCore.Qt.AlignLeft | QtCore.Qt.AlignTop)
        self.label_2.setObjectName("label_2")
        self.verticalLayout_2.addWidget(self.label_2)
        self.verticalLayout.addWidget(self.verticalFrame1)
        self.horizontalFrame = QtWidgets.QFrame(self.verticalFrame)
        self.horizontalFrame.setMinimumSize(QtCore.QSize(0, 60))
        self.horizontalFrame.setStyleSheet("QFrame {\n"
                                           "    background-color: rgb(33, 37, 43);\n"
                                           "    border-bottom-left-radius: 15px;\n"
                                           "    border-bottom-right-radius: 15px;\n"
                                           "}")
        self.horizontalFrame.setObjectName("horizontalFrame")
        self.horizontalLayout_2 = QtWidgets.QHBoxLayout(self.horizontalFrame)
        self.horizontalLayout_2.setContentsMargins(0, 0, 20, 0)
        self.horizontalLayout_2.setObjectName("horizontalLayout_2")
        self.spacerItem = QtWidgets.QSpacerItem(40, 20, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum)
        self.horizontalLayout_2.addItem(self.spacerItem)
        self.pushButton = QtWidgets.QPushButton(self.horizontalFrame)
        self.pushButton.setMinimumSize(QtCore.QSize(90, 40))
        self.pushButton.setMaximumSize(QtCore.QSize(90, 16777215))
        font = QtGui.QFont()
        font.setFamily("Segoe UI")
        font.setPointSize(9)
        self.pushButton.setFont(font)
        self.pushButton.setCursor(QtGui.QCursor(QtCore.Qt.PointingHandCursor))
        self.pushButton.setStyleSheet("QPushButton {\n"
                                      "    color: white;\n"
                                      "    background-color: transparent;\n"
                                      "}\n"
                                      "\n"
                                      "QPushButton:hover {\n"
                                      "    text-decoration: underline;\n"
                                      "}")
        self.pushButton.setObjectName("pushButton")
        self.horizontalLayout_2.addWidget(self.pushButton)
        self.pushButton_2 = QtWidgets.QPushButton(self.horizontalFrame)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.pushButton_2.sizePolicy().hasHeightForWidth())
        self.pushButton_2.setSizePolicy(sizePolicy)
        self.pushButton_2.setMinimumSize(QtCore.QSize(90, 40))
        self.pushButton_2.setMaximumSize(QtCore.QSize(16777215, 16777215))
        self.pushButton_2.setFixedHeight(40)
        font = QtGui.QFont()
        font.setFamily("Segoe UI")
        font.setPointSize(9)
        self.pushButton_2.setFont(font)
        self.pushButton_2.setCursor(QtGui.QCursor(QtCore.Qt.PointingHandCursor))
        background_color = mainui.accent_color
        hover_color = tuple([color - 15 if not (color - 15) < 0 else 0 for color in background_color])
        click_color = tuple([color - 30 if not (color - 30) < 0 else 0 for color in background_color])
        self.pushButton_2.setStyleSheet("QPushButton {\n"
                                        "    color: white;\n"
                                        f"    background-color: rgb{repr(background_color)};\n"
                                        "    border-radius: 8px;\n"
                                        "    padding-left: 8px;\n"
                                        "    padding-right: 8px;\n"
                                        "}\n"
                                        "\n"
                                        "QPushButton:hover {\n"
                                        f"    background-color: rgb{repr(hover_color)};\n"
                                        "}\n"
                                        "QPushButton:pressed {\n"
                                        f"  background-color: rgb{repr(click_color)};\n"
                                        "}")
        self.pushButton_2.setObjectName("pushButton_2")
        self.horizontalLayout_2.addWidget(self.pushButton_2)
        self.verticalLayout.addWidget(self.horizontalFrame)
        self.horizontalLayout.addWidget(self.verticalFrame)
        self.label.setText(title)
        self.label_2.setText(description)
        self.label_2.setWordWrap(True)
        self.pushButton.setText(cancel)
        self.pushButton_2.setText(accept)
        self.setFixedWidth(500)
        self.pushButton.clicked.connect(self.close_dialog)
        self.pushButton_2.clicked.connect(lambda: (Thread(target=callback).start(), self.close_dialog()))  # noqa
        if error:
            self.pushButton.hide()
        mainui.overlay.show()
        self.show_after_adjust = True

    def close_dialog(self):
        mainui.overlay.hide()
        self.hide()
        self.close()
        mainui.active_dialog = None

    def showEvent(self, a0: QtGui.QShowEvent) -> None:
        QtWidgets.QWidget.showEvent(self, a0)
        self.move_dialog_pos()

    def move_dialog_pos(self):
        global_coords = mainui.mapToGlobal(mainui.rect().center())
        self.move(global_coords.x() - self.width() // 2, global_coords.y() - self.height() // 2)


@adjust_sizing()
class Tooltip(QtWidgets.QWidget):
    """
        This is a QWidget that represents a tooltip.
    """
    def __init__(self, text, widget: QtWidgets.QWidget, enter_e: typing.Callable = None, delay: int = 350,
                 leave_e: typing.Callable = None, *args, **kwargs):
        super().__init__(parent=mainui, *args, **kwargs)
        self.setObjectName("Form")
        self.resize(164, 60)
        self.widget = widget
        self.setWindowFlags(QtCore.Qt.Tool | QtCore.Qt.FramelessWindowHint)
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        self.setSizePolicy(sizePolicy)
        self.setMaximumSize(QtCore.QSize(300, 16777215))
        self.horizontalLayout = QtWidgets.QHBoxLayout(self)
        self.horizontalLayout.setContentsMargins(0, 0, 0, 0)
        self.horizontalLayout.setSpacing(0)
        self.horizontalLayout.setObjectName("horizontalLayout")
        self.verticalFrame = QtWidgets.QFrame(self)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        self.verticalFrame.setSizePolicy(sizePolicy)
        self.verticalFrame.setObjectName("verticalFrame")
        self.verticalLayout = QtWidgets.QVBoxLayout(self.verticalFrame)
        self.verticalLayout.setContentsMargins(0, 0, 0, 0)
        self.verticalLayout.setSpacing(0)
        self.verticalLayout.setObjectName("verticalLayout")
        self.verticalFrame_2 = QtWidgets.QFrame(self.verticalFrame)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.MinimumExpanding,
                                           QtWidgets.QSizePolicy.MinimumExpanding)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setWidthForHeight(True)
        self.verticalFrame_2.setSizePolicy(sizePolicy)
        self.verticalFrame_2.setMaximumSize(QtCore.QSize(16777215, 16777215))
        self.verticalFrame_2.setStyleSheet("QFrame {\n"
                                           "    background-color: rgb(27, 29, 35);\n"
                                           "    border-radius: 10px;\n"
                                           "}")
        self.verticalFrame_2.setLineWidth(0)
        self.verticalFrame_2.setObjectName("verticalFrame_2")
        self.verticalLayout_2 = QtWidgets.QHBoxLayout(self.verticalFrame_2)
        self.verticalLayout_2.setObjectName("verticalLayout_2")
        self.verticalLayout_2.setContentsMargins(8, 0, 8, 4)
        self.verticalLayout_2.setAlignment(self.verticalFrame_2, QtCore.Qt.AlignHCenter)
        self.label = QtWidgets.QLabel(self.verticalFrame_2)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Minimum)
        self.label.setSizePolicy(sizePolicy)
        self.label.setMaximumWidth(300)
        font = QtGui.QFont()
        font.setFamily("Segoe UI")
        font.setPointSize(11)
        self.label.setFont(font)
        self.label.setStyleSheet("color: white;")
        self.label.setAlignment(QtCore.Qt.AlignCenter)
        self.label.setObjectName("label")
        self.verticalLayout_2.addWidget(self.label)
        self.verticalLayout.addWidget(self.verticalFrame_2)
        self.horizontalFrame = QtWidgets.QFrame(self.verticalFrame)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.horizontalFrame.sizePolicy().hasHeightForWidth())
        self.horizontalFrame.setSizePolicy(sizePolicy)
        self.horizontalFrame.setMaximumSize(QtCore.QSize(16777215, 20))
        self.horizontalFrame.setObjectName("horizontalFrame")
        self.horizontalLayout_2 = QtWidgets.QHBoxLayout(self.horizontalFrame)
        self.horizontalLayout_2.setContentsMargins(0, 0, 0, 0)
        self.horizontalLayout_2.setSpacing(0)
        self.horizontalLayout_2.setObjectName("horizontalLayout_2")
        self.frame = QtWidgets.QFrame(self.horizontalFrame)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.frame.sizePolicy().hasHeightForWidth())
        self.frame.setSizePolicy(sizePolicy)
        self.frame.setFixedSize(12, 12)
        self.frame.setFrameShape(QtWidgets.QFrame.StyledPanel)
        self.frame.setFrameShadow(QtWidgets.QFrame.Raised)
        self.frame.setObjectName("frame")
        self.horizontalLayout_2.addWidget(self.frame)
        self.orientation = None
        self.horizontalLayout.addWidget(self.verticalFrame)
        self.text = limit_text(text, 70)
        self.label.setText(self.text)
        self.shadow = QtWidgets.QGraphicsDropShadowEffect()
        self.shadow.setColor(QtGui.QColor(0, 0, 0, 100))
        self.shadow.setXOffset(0)
        self.shadow.setYOffset(0)
        self.shadow.setBlurRadius(10)
        self.setGraphicsEffect(self.shadow)
        self.animation = None

        def enter(a0):
            try:
                if not widget.underMouse() or mainui.active_dialog:
                    return
                if self.orientation is None:
                    global_coords = widget.mapTo(mainui.window(), QtCore.QPoint(mainui.pos().x(), mainui.pos().y()))
                    global_coords = mainui.mapFrom(mainui.window(), global_coords)
                    if orientation := mainui.height() // 2 > global_coords.y():
                        self.verticalLayout.insertWidget(0, self.horizontalFrame)
                        self.frame.setStyleSheet("QFrame {\n"
                                                 "    background: transparent;\n"
                                                 "    border-bottom: 10px solid rgb(27, 29, 35);\n"
                                                 "    border-top: 6px solid rgba(255, 255, 255, 0);\n"
                                                 "    border-right: 6px solid rgba(255, 255, 255, 0);\n"
                                                 "    border-left: 6px solid rgba(255, 255, 255, 0);\n"
                                                 "}")
                    else:
                        self.verticalLayout.addWidget(self.horizontalFrame)
                        self.frame.setStyleSheet("QFrame {\n"
                                                 "    background: transparent;\n"
                                                 "    border-top: 10px solid rgb(27, 29, 35);\n"
                                                 "    border-bottom: 6px solid rgba(255, 255, 255, 0);\n"
                                                 "    border-right: 6px solid rgba(255, 255, 255, 0);\n"
                                                 "    border-left: 6px solid rgba(255, 255, 255, 0);\n"
                                                 "}")
                    self.orientation = orientation
                self.show()
                self.hide()
                self.move_to_pos()
                self.setWindowOpacity(0)
                self.animation = QtCore.QPropertyAnimation(self, b'windowOpacity')
                self.animation.setStartValue(0)
                self.animation.setEndValue(1)
                self.animation.setDuration(250)
                self.animation.setEasingCurve(QtCore.QEasingCurve.InOutQuart)
                self.show()
                self.animation.start()
                if delay:
                    return
                if not widget.isVisible():
                    self.hide()
                    return
                return super(type(widget), widget).enterEvent(a0) if not enter_e else enter_e(a0)  # noqa
            except RuntimeError:
                pass

        if delay:

            def new_enter_e(a0):
                try:
                    if enter_e:
                        enter_e(a0)
                    QtCore.QTimer.singleShot(delay, lambda: enter(a0))
                except RuntimeError:
                    pass

            widget.enterEvent = new_enter_e
        else:
            widget.enterEvent = enter

        def leave(a0):
            try:
                self.setWindowOpacity(1)
                self.animation = QtCore.QPropertyAnimation(self, b'windowOpacity')
                self.animation.setStartValue(1)
                self.animation.setEndValue(0)
                self.animation.setDuration(250)
                self.animation.setEasingCurve(QtCore.QEasingCurve.InOutQuart)
                self.animation.start()
                if delay:
                    return QtCore.QTimer.singleShot(delay, self.hide)
                if not widget.isVisible():
                    self.hide()
                    return

                def check_leave():
                    try:
                        if not leave_e:
                            self.hide()
                            super(type(widget), widget).leaveEvent(a0)  # noqa
                        else:
                            leave_e(a0)
                    except RuntimeError:
                        pass

                QtCore.QTimer.singleShot(250, check_leave)
            except RuntimeError:
                self.hide()
                self.deleteLater()

        if delay:

            def new_leave_e(a0):
                try:
                    if leave_e:
                        leave_e(a0)
                    leave(a0)
                except RuntimeError:
                    pass

            widget.leaveEvent = new_leave_e
        else:
            widget.leaveEvent = leave

        def clicked(a0):
            if type(widget) == QtWidgets.QPushButton or issubclass(type(widget), QtWidgets.QPushButton):
                super(type(widget), widget).mousePressEvent(a0)  # noqa
                widget.leaveEvent(a0)
            else:
                super(type(widget), widget).mousePressEvent(a0)  # noqa

        widget.mousePressEvent = clicked
        self.widgets_to_ignore = [self.widget]

    def showEvent(self, a0: QtGui.QShowEvent) -> None:
        QtWidgets.QWidget.showEvent(self, a0)
        ratio = get_ratio()
        if (size := self.label.fontMetrics().boundingRect(self.text).width()) > 284 * ratio or '\n' in self.text:
            self.label.setWordWrap(True)
            rect = QtCore.QRect(0, 0, 284 * ratio, 500)
            size = self.label.fontMetrics().boundingRect(rect, QtCore.Qt.TextWordWrap, self.text)
            self.setFixedSize(size.width() + 24 * ratio, size.height() + 16 * ratio)
        else:
            self.label.setWordWrap(False)
            self.setFixedHeight(56 * ratio)
            self.setFixedWidth(size + 16 * ratio)
        self.move_to_pos()

    def move_to_pos(self):
        if self.orientation:
            offset = 0 + self.widget.height()
        else:
            offset = 0 - self.height()
        coords = self.widget.mapTo(mainui.window(), QtCore.QPoint(mainui.pos().x() + self.widget.width() // 2 -
                                                                  self.width() // 2,
                                                                  mainui.pos().y() + offset))
        self.move(mainui.mapFrom(mainui.window(), coords))


class PartialListeningToFriends:
    """
        This is a class that represents the users' listening to friends status, to be later turned into a QWidget.
    """
    def __init__(self, new: bool = False, friend_id: str = None, spotifylistener: SpotifyListener = None,
                 spotifysong: SpotifySong = None, dominant_color: tuple = (), text_color: tuple = (),
                 dark_color: tuple = ()):
        self.friend_id = friend_id
        self.spotifylistener = spotifylistener
        self.spotifysong = spotifysong
        self.dominant_color = tuple(dominant_color)
        self.text_color = tuple(text_color)
        self.dark_color = tuple(dark_color)
        if mainui.spotifylistener and new:
            mainui.spotifylistener.running = False
        if friend_id and new:
            mainui.spotifylistener = SpotifyListener(mainui.client.spotifyplayer, mainui.client, friend_id)
            self.spotifylistener = mainui.spotifylistener
        if self.dominant_color:
            icons = [f'20x20{sep}cil-media-play.png', f'20x20{sep}cil-loop-circular.png', f'20x20{sep}cil-media-stop.png',
                     f'20x20{sep}cil-media-pause.png']
            icons = [data_dir + f'icons{sep}' + icon for icon in icons]
            for icon in icons:
                img = Image.open(icon)
                img = img.convert('RGBA')
                pixdata: typing.Optional[PyAccess] = img.load()
                for y in range(img.size[1]):
                    for x in range(img.size[0]):
                        if pixdata[x, y][3] > 0:
                            new_color = list(dominant_color)
                            new_color.append(pixdata[x, y][3])
                            pixdata[x, y] = tuple(new_color)
                img.save(icon)

    def convert_to_widget(self):
        return ListeningToFriends(self.spotifylistener, self.spotifysong, self.dominant_color, self.text_color,
                                  self.dark_color)


@adjust_sizing()
class ListeningToFriends(QtWidgets.QWidget):
    """
        This is a class that represents the users' listening to friends status.
    """
    def __init__(self, spotifylistener: SpotifyListener = None, spotifysong: SpotifySong = None,
                 dominant_color: tuple = (44, 49, 60), text_color: tuple = (255, 255, 255),
                 dark_color: tuple = (14, 19, 20),  *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.spotifylistener = spotifylistener
        self.spotifysong = spotifysong
        self.dominant_color = dominant_color
        self.text_color = text_color
        self.dark_color = dark_color
        self.setObjectName("ListeningToFriends")
        if (spotifylistener and not spotifylistener.running) or not spotifylistener:
            self.verticalLayout = QtWidgets.QVBoxLayout(self)
            self.label = QtWidgets.QLabel()
            self.label.setText('You are currently not listening to anyone!\nClick on the '
                               '"Listen Along on SpotAlong" button on any of your friends'
                               ' to start listening to them!')
            self.label.setStyleSheet('color: white;')
            self.label.setWordWrap(True)
            self.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
            font = QtGui.QFont()
            font.setFamily('Segoe UI')
            font.setPointSize(14)
            self.label.setFont(font)
            self.label.setAlignment(QtCore.Qt.AlignHCenter | QtCore.Qt.AlignVCenter)
            self.setLayout(self.verticalLayout)
            self.verticalLayout.addWidget(self.label)
            return
        self.resize(760, 469)
        self.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        self.setAttribute(QtCore.Qt.WA_StyledBackground)
        self.setObjectName("ListeningToFriends")
        self.setStyleSheet("#ListeningToFriends {\n"
                           "    background-color: qlineargradient(spread:pad, x1:0, y1:0, x2:1, y2:0, "
                           f"stop:0 rgb{dominant_color}, stop:1 rgb{dark_color});\n"
                           "}")
        self.horizontalLayout = QtWidgets.QHBoxLayout(self)
        self.horizontalLayout.setContentsMargins(30, 30, 30, 30)
        self.horizontalLayout.setSpacing(0)
        self.horizontalLayout.setObjectName("horizontalLayout")
        self.verticalFrame = QtWidgets.QFrame(self)
        self.verticalFrame.setFixedSize(QtCore.QSize(760, 400))
        color = "rgba(0, 0, 0, 50)" if np.mean(text_color) > np.mean(dominant_color) else "rgba(255, 255, 255, 50)"
        if np.mean([abs(dominant_color[i] - text_color[i]) for i in range(3)]) > 60:
            color = 'rgba(0, 0, 0, 50)'
        if np.mean(dominant_color) > 180:
            color = 'rgba(255, 255, 255, 50)'
        self.verticalFrame.setStyleSheet("#verticalFrame {\n"
                                         f"    background-color: {color};\n"
                                         "    border-radius: 30px;\n"
                                         "}")
        ratio = get_ratio()
        scaled = ''
        if ratio != 1:
            icons = [f'20x20{sep}cil-loop-circular', f'20x20{sep}cil-media-play', f'20x20{sep}cil-media-stop',
                     f'20x20{sep}cil-media-pause']
            scale_images(icons, ratio)
            scaled = 'scaled'
        self.verticalFrame.setObjectName("verticalFrame")
        self.verticalLayout = QtWidgets.QVBoxLayout(self.verticalFrame)
        self.verticalLayout.setContentsMargins(0, 0, 0, 0)
        self.verticalLayout.setSpacing(0)
        self.verticalLayout.setObjectName("verticalLayout")
        self.widget = QtWidgets.QWidget(self.verticalFrame)
        self.widget.setMaximumSize(QtCore.QSize(16777215, 0))
        self.widget.setObjectName("widget")
        self.verticalLayout.addWidget(self.widget)
        self.horizontalFrame = QtWidgets.QFrame(self.verticalFrame)
        self.horizontalFrame.setObjectName("horizontalFrame")
        self.horizontalLayout_2 = QtWidgets.QHBoxLayout(self.horizontalFrame)
        self.horizontalLayout_2.setContentsMargins(0, 0, 0, 0)
        self.horizontalLayout_2.setSpacing(0)
        self.horizontalLayout_2.setObjectName("horizontalLayout_2")
        self.verticalFrame_2 = QtWidgets.QFrame(self.horizontalFrame)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.verticalFrame_2.sizePolicy().hasHeightForWidth())
        self.verticalFrame_2.setSizePolicy(sizePolicy)
        self.verticalFrame_2.setStyleSheet(f"color: rgb{text_color};")
        self.verticalFrame_2.setObjectName("verticalFrame_2")
        self.verticalLayout_2 = QtWidgets.QVBoxLayout(self.verticalFrame_2)
        self.verticalLayout_2.setContentsMargins(10, 18, 0, 30)
        self.verticalLayout_2.setSpacing(0)
        self.verticalLayout_2.setObjectName("verticalLayout_2")
        self.spacerItem = QtWidgets.QSpacerItem(20, 20, QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Expanding)
        self.label_5 = QtWidgets.QLabel(self.verticalFrame_2)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Minimum)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.label_5.sizePolicy().hasHeightForWidth())
        self.label_5.setSizePolicy(sizePolicy)
        font = QtGui.QFont()
        font.setFamily("Segoe UI")
        font.setPointSize(15)
        self.label_5.setFont(font)
        self.label_5.setAlignment(QtCore.Qt.AlignLeading | QtCore.Qt.AlignLeft | QtCore.Qt.AlignTop)
        self.label_5.setObjectName("label_5")
        self.label = QtWidgets.QLabel(self.verticalFrame_2)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Minimum)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.label.sizePolicy().hasHeightForWidth())
        self.label.setSizePolicy(sizePolicy)
        font = QtGui.QFont()
        font.setFamily("Segoe UI Semibold")
        font.setPointSize(20)
        self.label.setFont(font)
        self.label.setAlignment(QtCore.Qt.AlignLeading | QtCore.Qt.AlignLeft | QtCore.Qt.AlignTop)
        self.label.setObjectName("label")

        self.label.setText('')
        self.verticalLayout_2.addWidget(self.label)
        self.label_2 = QtWidgets.QLabel(self.verticalFrame_2)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Minimum)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.label_2.sizePolicy().hasHeightForWidth())
        self.label_2.setSizePolicy(sizePolicy)
        font = QtGui.QFont()
        font.setFamily("Segoe UI")
        font.setPointSize(16)
        self.label_2.setFont(font)
        self.label_2.setObjectName("label_2")
        self.verticalLayout_2.addWidget(self.label_2)
        self.label_3 = QtWidgets.QLabel(self.verticalFrame_2)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Minimum)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.label_3.sizePolicy().hasHeightForWidth())
        self.label_3.setSizePolicy(sizePolicy)
        font = QtGui.QFont()
        font.setFamily("Segoe UI")
        font.setPointSize(12)
        self.label_3.setFont(font)
        self.label_3.setObjectName("label_3")
        self.horizontalFrame_5 = QtWidgets.QFrame()
        self.horizontalLayout_1 = QtWidgets.QHBoxLayout()
        self.horizontalLayout_1.setContentsMargins(0, 0, 0, 0)
        self.horizontalLayout_1.setSpacing(5)
        self.horizontalFrame_5.setLayout(self.horizontalLayout_1)
        self.label_6 = QtWidgets.QLabel()
        self.label_6.setFixedSize(30, 30)
        friend_id = mainui.client.friendstatus.get(spotifylistener.friend_id)
        if friend_id:
            friend_id = friend_id.client_id
        self.label_6.setStyleSheet(f'border-image: url({forward_data_dir}icon{friend_id}.png) 0 0 0 0 '
                                   f'stretch stretch;')
        self.label_0 = QtWidgets.QLabel()
        font.setPointSize(15)
        self.label_0.setFont(font)
        self.update_listening_time()
        self.horizontalLayout_1.addWidget(self.label_6)
        self.horizontalLayout_1.addWidget(self.label_0)
        self.label_0.setSizePolicy(sizePolicy)
        self.verticalLayout_2.addWidget(self.label_3)
        self.label_7 = QtWidgets.QLabel()
        font.setPointSize(10)
        self.label_7.setFont(font)
        self.label_7.setSizePolicy(sizePolicy)
        self.label_7.setText('')
        self.label_7.setWordWrap(True)
        self.verticalLayout_2.addItem(self.spacerItem)
        self.verticalLayout_2.addWidget(self.label_7)
        self.verticalLayout_2.addWidget(self.label_5)
        self.verticalLayout_2.addWidget(self.horizontalFrame_5)
        self.horizontalLayout_2.addWidget(self.verticalFrame_2)
        self.verticalFrame_3 = QtWidgets.QFrame(self.horizontalFrame)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.verticalFrame_3.sizePolicy().hasHeightForWidth())
        self.verticalFrame_3.setSizePolicy(sizePolicy)
        self.verticalFrame_3.setObjectName("verticalFrame_3")
        self.verticalLayout_3 = QtWidgets.QVBoxLayout(self.verticalFrame_3)
        self.verticalLayout_3.setContentsMargins(0, 0, 0, 20)
        self.verticalLayout_3.setSpacing(0)
        self.verticalLayout_3.setObjectName("verticalLayout_3")
        self.spacerItem1 = QtWidgets.QSpacerItem(20, 20, QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Preferred)
        self.verticalLayout_3.addItem(self.spacerItem1)
        self.horizontalFrame_3 = QtWidgets.QFrame(self.verticalFrame_3)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.horizontalFrame_3.sizePolicy().hasHeightForWidth())
        self.horizontalFrame_3.setSizePolicy(sizePolicy)
        self.horizontalFrame_3.setObjectName("horizontalFrame_3")
        self.horizontalLayout_3 = QtWidgets.QHBoxLayout(self.horizontalFrame_3)
        self.horizontalLayout_3.setContentsMargins(0, 0, 0, 0)
        self.horizontalLayout_3.setSpacing(0)
        self.horizontalLayout_3.setObjectName("horizontalLayout_3")
        self.label_4 = QtWidgets.QLabel(self.horizontalFrame_3)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.label_4.sizePolicy().hasHeightForWidth())
        self.label_4.setSizePolicy(sizePolicy)
        self.label_4.setMinimumSize(QtCore.QSize(200, 200))
        self.label_4.setMaximumSize(QtCore.QSize(200, 200))
        try:
            self.label_4.setStyleSheet(f"border-image: url({forward_data_dir}album"
                                       f"{spotifysong.albumimagelink.split('/image/')[1]});")
        except AttributeError:
            try:
                albumimagelink = mainui.client.friendstatus[spotifylistener.friend_id].albumimagelink
                self.label_4.setStyleSheet(f'border-image: url({forward_data_dir}album'
                                           f'{albumimagelink.split("/image/")[1]};')
            except AttributeError:
                pass  # at this point anything is better than just crashing
        self.label_4.setText("")
        self.label_4.setObjectName("label_4")
        self.horizontalLayout_3.addWidget(self.label_4)
        self.verticalLayout_3.addWidget(self.horizontalFrame_3)
        self.spacerItem2 = QtWidgets.QSpacerItem(20, 40, QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Expanding)
        self.verticalLayout_3.addItem(self.spacerItem2)
        self.horizontalFrame_2 = QtWidgets.QFrame(self.verticalFrame_3)
        self.horizontalFrame_2.setMinimumSize(QtCore.QSize(0, 0))
        self.horizontalFrame_2.setObjectName("horizontalFrame_2")
        self.horizontalLayout_4 = QtWidgets.QHBoxLayout(self.horizontalFrame_2)
        self.horizontalLayout_4.setObjectName("horizontalLayout_4")
        self.horizontalFrame_4 = QtWidgets.QFrame(self.horizontalFrame_2)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.horizontalFrame_4.sizePolicy().hasHeightForWidth())
        self.horizontalFrame_4.setSizePolicy(sizePolicy)
        self.horizontalFrame_4.setMinimumSize(QtCore.QSize(0, 60))
        self.horizontalFrame_4.setMaximumSize(QtCore.QSize(16777215, 60))
        self.horizontalFrame_4.setAcceptDrops(False)
        self.horizontalFrame_4.setStyleSheet("QFrame {\n"
                                             "    border-radius: 8px;\n"
                                             f"    background-color: rgb{repr(text_color)};\n"
                                             "}")
        self.horizontalFrame_4.setObjectName("horizontalFrame_4")
        self.horizontalLayout_5 = QtWidgets.QHBoxLayout(self.horizontalFrame_4)
        self.horizontalLayout_5.setContentsMargins(10, -1, 10, -1)
        self.horizontalLayout_5.setSpacing(15)
        self.horizontalLayout_5.setObjectName("horizontalLayout_5")
        self.pushButton = QtWidgets.QPushButton(self.horizontalFrame_4)
        self.pushButton.setMinimumSize(QtCore.QSize(90, 40))
        self.pushButton.setMaximumSize(QtCore.QSize(90, 40))
        self.pushButton.setCursor(QtGui.QCursor(QtCore.Qt.PointingHandCursor))
        self.pushButton.setStyleSheet("QPushButton {\n"
                                      "    background: transparent;\n"
                                      f"    color: rgb{repr(dominant_color)};\n"
                                      "    text-align: right;\n"
                                      "    padding-left: 15px;\n"
                                      "    padding-right: 15px;\n"
                                      f"  background-image: url({forward_data_dir}icons/20x20/cil-loop-circular"
                                      f"{scaled}.png);\n"
                                      "    background-repeat: no-repeat;\n"
                                      "    background-position: left;\n"
                                      "    background-origin: content;\n"
                                      "}\n"
                                      "QPushButton:hover {\n"
                                      "    text-decoration: underline;\n"
                                      "}")
        self.pushButton.clicked.connect(spotifylistener.sync)
        self.pushButton.setObjectName("pushButton")
        font = QtGui.QFont('Segoe UI', 8)
        self.pushButton.setFont(font)
        self.horizontalLayout_5.addWidget(self.pushButton)
        self.pushButton_2 = QtWidgets.QPushButton(self.horizontalFrame_4)
        self.pushButton_2.setMinimumSize(QtCore.QSize(30, 30))
        self.pushButton_2.setMaximumSize(QtCore.QSize(30, 30))
        self.pushButton_2.setCursor(QtGui.QCursor(QtCore.Qt.PointingHandCursor))
        self.pushButton_2.setStyleSheet("background: transparent;\n"
                                        f"background-image: url({forward_data_dir}icons/20x20/cil-media-play"
                                        f"{scaled}.png);\n"
                                        f"background-repeat: no-repeat;\n"
                                        f"background-position: center;")
        self.pushButton_2.setText("")
        self.pushButton_2.setObjectName("pushButton_2")
        self.horizontalLayout_5.addWidget(self.pushButton_2)
        self.pushButton_3 = QtWidgets.QPushButton(self.horizontalFrame_4)
        self.pushButton_3.setMinimumSize(QtCore.QSize(90, 40))
        self.pushButton_3.setMaximumSize(QtCore.QSize(90, 40))
        self.pushButton_3.setCursor(QtGui.QCursor(QtCore.Qt.PointingHandCursor))
        self.pushButton_3.setStyleSheet("QPushButton {\n"
                                        "    background: transparent;\n"
                                        f"    color: rgb{repr(dominant_color)};\n"
                                        "    text-align: right;\n"
                                        "    padding-left: 15px;\n"
                                        "    padding-right: 15px;\n"
                                        f"   background-image: url({forward_data_dir}icons/20x20/cil-media-stop"
                                        f"{scaled}.png);\n"
                                        "    background-repeat: no-repeat;\n"
                                        "    background-position: left;\n"
                                        "    background-origin: content;\n"
                                        "}\n"
                                        "QPushButton:hover {\n"
                                        "    text-decoration: underline;\n"
                                        "}")

        def stop():
            try:
                spotifylistener.end(no_log=True)
            except Exception as _exc:
                logger.error('An error occured while trying to end the listen along session: ', exc_info=_exc)
            self.timer.stop()
            self.hide()
            new = ListeningToFriends()
            try:
                self.deleteLater()
            except RuntimeError:
                pass
            mainui.verticalLayout_38.replaceWidget(mainui.listentofriends, new)
            mainui.listentofriends.hide()
            mainui.listentofriends = new
            mainui.listentofriends.show()

        self.pushButton_3.clicked.connect(stop)
        self.pushButton_3.setObjectName("pushButton_3")
        self.pushButton_3.setFont(font)
        self.pushButton_3.clicked.connect(stop)
        self.pushButton_3.setObjectName("pushButton_3")
        self.pushButton_3.setFont(font)
        self.horizontalLayout_5.addWidget(self.pushButton_3)
        self.horizontalLayout_4.addWidget(self.horizontalFrame_4)
        self.verticalLayout_3.addWidget(self.horizontalFrame_2)
        self.horizontalLayout_2.addWidget(self.verticalFrame_3)
        self.verticalLayout.addWidget(self.horizontalFrame)
        self.horizontalLayout.addWidget(self.verticalFrame)
        self.label_5.setText('Listening Along to')
        self.label.setText(spotifysong.songname)
        self.label.setWordWrap(True)
        self.label_2.setText(", ".join(spotifysong.song_authors))
        self.label_2.setWordWrap(True)
        self.label_3.setText(spotifysong.albumname)
        self.label_3.setWordWrap(True)
        self.pushButton.setText('Sync')
        self.pushButton_3.setText('Stop')
        self.setLayout(self.horizontalLayout)

        def play_pause_button():
            try:
                self.pushButton_2.clicked.disconnect()
            except TypeError:
                pass
            except RuntimeError:
                return
            if spotifylistener.spotifyplayer.playing:
                command = spotifylistener.spotifyplayer.pause
                self.pushButton_2.setStyleSheet(self.pushButton_2.styleSheet().replace('play', 'pause'))
            else:
                command = spotifylistener.spotifyplayer.resume
                self.pushButton_2.setStyleSheet(self.pushButton_2.styleSheet().replace('pause', 'play'))

            self.pushButton_2.clicked.connect(lambda: Thread(target=spotifylistener.spotifyplayer.command,
                                                             args=(command,)).start())

        runner = Runnable()
        runner.callback.connect(play_pause_button)
        self.spotifylistener.spotifyplayer.add_event_reciever(runner)
        play_pause_button()

        self.timer = QtCore.QTimer()
        self.timer.setInterval(250)
        self.timer.timeout.connect(lambda: stop() if not self.spotifylistener.running else None)
        self.timer.start()

        self.last_song_uri = ''
        self.timer2 = QtCore.QTimer()
        self.timer2.setInterval(5000)
        self.timer2.timeout.connect(self.update_next)
        self.timer2.start()

        self.timer3 = QtCore.QTimer()
        self.timer3.setInterval(1000)
        self.timer3.timeout.connect(self.update_listening_time)
        self.timer3.start()

    def update_next(self):
        song_uri = ''
        for song_dict in mainui.client.spotifyplayer.queue:
            if 'track' in song_dict['uri']:
                song_uri = song_dict['uri']
                break
        if not song_uri:
            self.label_7.setText('Up Next: unknown')
        else:
            if song_uri == self.last_song_uri:
                return

            text = ''

            def set_text():
                try:
                    if sip.isdeleted(self.label_7):
                        return
                    self.label_7.setText(text)
                except RuntimeError:
                    pass

            runner = Runnable()
            runner.callback.connect(set_text)

            def success(name):
                nonlocal text
                n = name.json()['song_name']
                self.last_song_uri = song_uri
                text = f'Up Next: {n}'
                runner.run()

            def failure():
                nonlocal text
                text = 'Up Next: unknown'
                runner.run()

            Thread(target=mainui.client.invoke_request, args=(BASE_URL + f'/cache/name/{song_uri}', {}, 'GET',
                                                              lambda n: success(n), failure)).start()

    def update_listening_time(self):
        if not mainui.client.friendstatus.get(self.spotifylistener.friend_id) or sip.isdeleted(self.label_0):
            return
        delta = time.time() - self.spotifylistener.begin_listening_time
        minutes = int(delta // 60)
        seconds = int(delta % 60)
        listening_str = f'{minutes}m {seconds}s'
        username = mainui.client.friendstatus[self.spotifylistener.friend_id].clientusername
        self.label_0.setText(f'{username} for {listening_str}')


@adjust_sizing()
class DisconnectBanner(QtWidgets.QWidget):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.scaled = ''
        ratio = get_ratio()
        self.ratio = ratio
        if ratio != 1:
            self.ratio = ratio
            icons = [f'24x24{sep}cil-window-minimize', f'24x24{sep}cil-window-restore', f'24x24{sep}cil-window-maximize',
                     f'24x24{sep}cil-x', f'16x16{sep}cil-size-grip']
            scale_images(icons, ratio)
            self.scaled = 'scaled'
        self.setStyleSheet('background-color: rgb(30, 40, 50);')
        self.setWindowOpacity(0)
        self.setWindowFlags(QtCore.Qt.Tool | QtCore.Qt.FramelessWindowHint)
        self.animation = QtCore.QPropertyAnimation(self, b'windowOpacity')
        self.animation.setStartValue(0)
        self.animation.setEndValue(1)
        self.animation.setDuration(1000)
        self.animation.setEasingCurve(QtCore.QEasingCurve.InOutQuart)
        self.animation2 = QtCore.QPropertyAnimation(self, b'windowOpacity')
        self.animation2.setStartValue(1)
        self.animation2.setEndValue(0)
        self.animation2.setDuration(1000)
        self.animation2.setEasingCurve(QtCore.QEasingCurve.InOutQuart)
        self.setAttribute(QtCore.Qt.WA_TransparentForMouseEvents, True)
        self.horizontalLayout = QtWidgets.QHBoxLayout(self)
        self.horizontalLayout.setContentsMargins(0, 0, 0, 0)
        self.horizontalLayout.setSpacing(0)
        self.horizontalLayout.setObjectName("horizontalLayout")
        self.verticalFrame_2 = QtWidgets.QFrame(self)
        self.verticalFrame_2.setObjectName("verticalFrame_2")
        self.verticalLayout_2 = QtWidgets.QVBoxLayout(self.verticalFrame_2)
        self.verticalLayout_2.setContentsMargins(0, 0, 0, 0)
        self.verticalLayout_2.setSpacing(0)
        self.verticalLayout_2.setObjectName("verticalLayout_2")
        self.horizontalFrame = QtWidgets.QFrame(self.verticalFrame_2)
        self.horizontalFrame.setMinimumSize(QtCore.QSize(0, 43))
        self.horizontalFrame.setMaximumSize(QtCore.QSize(16777215, 43))
        self.horizontalFrame.setObjectName("horizontalFrame")
        self.horizontalFrame.setStyleSheet('QFrame { background-color: rgb(27, 29, 34); }')
        self.horizontalLayout_3 = QtWidgets.QHBoxLayout(self.horizontalFrame)
        self.horizontalLayout_3.setContentsMargins(12, 0, 0, 0)
        self.horizontalLayout_3.setSpacing(0)
        self.horizontalLayout_3.setObjectName("horizontalLayout_3")
        self.horizontalFrame3 = QtWidgets.QFrame(self.horizontalFrame)
        self.horizontalLayout_1 = QtWidgets.QHBoxLayout(self.horizontalFrame3)
        self.horizontalLayout_1.setContentsMargins(0, 0, 0, 0)
        self.label_1 = QtWidgets.QLabel()
        self.label_1.setPixmap(QtGui.QPixmap(data_dir + 'logo.ico').scaled
                               (24 * ratio, 24 * ratio, transformMode=QtCore.Qt.SmoothTransformation))
        self.label_3 = QtWidgets.QLabel()
        font = QtGui.QFont()
        font.setFamily("Segoe UI")
        font.setPointSize(10)
        font.setWeight(50)
        self.label_3.setFont(font)
        self.label_3.setText("SpotAlong")
        self.label_3.setStyleSheet("color: white;")
        self.horizontalLayout_1.addWidget(self.label_1)
        self.horizontalLayout_1.addWidget(self.label_3)
        self.horizontalLayout_3.addWidget(self.horizontalFrame3)
        self.spacerItem = QtWidgets.QLabel()
        self.spacerItem.setSizePolicy(QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding,
                                                            QtWidgets.QSizePolicy.Preferred))
        self.label_1.setMouseTracking(True)
        self.label_1.mouseDoubleClickEvent = lambda _: mainui.pushButton_3.click()
        self.label_3.setMouseTracking(True)
        self.label_3.mouseDoubleClickEvent = lambda _: mainui.pushButton_3.click()
        self.spacerItem.setMouseTracking(True)
        self.spacerItem.mouseDoubleClickEvent = lambda _: mainui.pushButton_3.click()
        self.horizontalLayout_3.addWidget(self.spacerItem)
        self.spacerItem.setMouseTracking(True)
        self.pushButton_4 = QtWidgets.QPushButton(self.horizontalFrame)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.pushButton_4.sizePolicy().hasHeightForWidth())
        self.pushButton_4.setSizePolicy(sizePolicy)
        self.pushButton_4.setMinimumSize(QtCore.QSize(43, 43))
        self.pushButton_4.setMaximumSize(QtCore.QSize(43, 43))
        font = QtGui.QFont()
        font.setFamily("Segoe UI")
        font.setPointSize(8)
        self.pushButton_4.setFont(font)
        self.pushButton_4.setLayoutDirection(QtCore.Qt.LeftToRight)
        self.pushButton_4.setStyleSheet("QPushButton {\n"
                                        "\n"
                                        "        background-position: center;\n"
                                        "        background-repeat: no-repeat;\n"
                                        "        border: none;\n"
                                        "        background-color: rgb(27, 29, 34);\n"
                                        "        }\n"
                                        "        QPushButton:hover {\n"
                                        "                background-color:rgb(49, 54, 65);\n"
                                        "        }\n"
                                        "        QPushButton:pressed {\n"
                                        f"background-color: rgb{mainui.accent_color};\n"
                                        "        }")
        self.pushButton_4.setText("")
        self.pushButton_4.setObjectName("pushButton_4")
        self.horizontalLayout_3.addWidget(self.pushButton_4)
        self.pushButton_3 = QtWidgets.QPushButton(self.horizontalFrame)
        self.pushButton_3.setSizePolicy(sizePolicy)
        self.pushButton_3.setMinimumSize(QtCore.QSize(43, 43))
        self.pushButton_3.setMaximumSize(QtCore.QSize(43, 43))
        self.pushButton_3.setStyleSheet("QPushButton {\n"
                                        "\n"
                                        "background-position: center;\n"
                                        "background-repeat: no-repeat;\n"
                                        "border: none;\n"
                                        "background-color: rgb(27, 29, 34);\n"
                                        "}\n"
                                        "QPushButton:hover {\n"
                                        "background-color:rgb(49, 54, 65);\n"
                                        "}\n"
                                        "QPushButton:pressed {\n"
                                        f"background-color: rgb{mainui.accent_color};\n"
                                        "}")
        self.pushButton_2 = QtWidgets.QPushButton(self.horizontalFrame)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.pushButton_2.sizePolicy().hasHeightForWidth())
        self.pushButton_2.setSizePolicy(sizePolicy)
        self.pushButton_2.setMinimumSize(QtCore.QSize(43, 43))
        self.pushButton_2.setMaximumSize(QtCore.QSize(43, 43))
        font = QtGui.QFont()
        font.setFamily("Segoe UI")
        font.setPointSize(8)
        self.pushButton_2.setFont(font)
        self.pushButton_2.setStyleSheet("QPushButton {\n"
                                        "\n"
                                        "background-position: center;\n"
                                        "background-repeat: no-repeat;\n"
                                        "border: none;\n"
                                        "background-color: rgb(27, 29, 34);\n"
                                        "}\n"
                                        "QPushButton:hover {\n"
                                        "background-color:rgb(49, 54, 65);\n"
                                        "}\n"
                                        "QPushButton:pressed {\n"
                                        f"background-color: rgb{mainui.accent_color};\n"
                                        "}")
        self.pushButton_2.setText("")
        self.pushButton_2.setObjectName("pushButton_2")
        self.pushButton_2.clicked.connect(lambda: (mainui.close(), self.hide(fast=True)))  # noqa
        self.horizontalLayout_3.addWidget(self.pushButton_3)
        self.horizontalLayout_3.addWidget(self.pushButton_2)
        self.pushButton_2.setIcon(QtGui.QIcon(data_dir + f'icons{sep}24x24{sep}cil-x{self.scaled}.png'))
        self.pushButton_2.setIconSize(QtCore.QSize(24 * ratio, 24 * ratio))
        self.maximized_check()
        self.pushButton_3.setIconSize(QtCore.QSize(24 * ratio, 24 * ratio))
        self.pushButton_4.setIcon(QtGui.QIcon(data_dir + f'icons{sep}24x24{sep}cil-window-minimize{self.scaled}.png'))
        self.pushButton_4.setIconSize(QtCore.QSize(24 * ratio, 24 * ratio))
        self.pushButton_3.clicked.connect(mainui.pushButton_3.click)
        self.pushButton_4.clicked.connect(mainui.showMinimized)
        self.verticalLayout_2.addWidget(self.horizontalFrame)
        self.horizontalFrame1 = QtWidgets.QFrame(self.verticalFrame_2)
        self.horizontalFrame1.setObjectName("horizontalFrame1")
        self.horizontalLayout_2 = QtWidgets.QHBoxLayout(self.horizontalFrame1)
        self.horizontalLayout_2.setContentsMargins(-1, 1, -1, 1)
        self.horizontalLayout_2.setObjectName("horizontalLayout_2")
        self.verticalFrame = QtWidgets.QFrame(self.horizontalFrame1)
        self.verticalFrame.setMaximumSize(QtCore.QSize(170, 200))
        self.verticalFrame.setObjectName("verticalFrame")
        self.verticalLayout = QtWidgets.QVBoxLayout(self.verticalFrame)
        self.verticalLayout.setObjectName("verticalLayout")
        self.label = QtWidgets.QLabel(self.verticalFrame)
        self.label.setMinimumSize(QtCore.QSize(0, 150))
        self.label.setMaximumSize(QtCore.QSize(16777215, 150))
        self.label.setText("")
        self.label.setStyleSheet(f'border-image: url({forward_data_dir}logo.ico) 0 0 0 0 stretch stretch;')
        self.label.setObjectName("label")
        self.verticalLayout.addWidget(self.label)
        self.label_2 = QtWidgets.QLabel(self.verticalFrame)
        self.label_2.setMaximumSize(QtCore.QSize(16777215, 30))
        font = QtGui.QFont()
        font.setFamily("Segoe UI Semilight")
        font.setPointSize(14)
        font.setItalic(True)
        self.label_2.setFont(font)
        self.label_2.setStyleSheet("color: white;\n"
                                   "")
        self.label_2.setText('Disconnected...')
        self.label_2.setAlignment(QtCore.Qt.AlignCenter)
        self.label_2.setObjectName("label_2")
        self.verticalLayout.addWidget(self.label_2)
        spacerItem1 = QtWidgets.QSpacerItem(20, 40, QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Expanding)
        self.verticalLayout.addItem(spacerItem1)
        self.horizontalLayout_2.addWidget(self.verticalFrame)
        self.verticalLayout_2.addWidget(self.horizontalFrame1)
        self.horizontalFrame2 = QtWidgets.QFrame(self.verticalFrame_2)
        self.horizontalFrame2.setMinimumSize(QtCore.QSize(0, 30))
        self.horizontalFrame2.setMaximumSize(QtCore.QSize(16777215, 30))
        self.horizontalFrame2.setObjectName("horizontalFrame2")
        self.horizontalLayout_4 = QtWidgets.QHBoxLayout(self.horizontalFrame2)
        self.horizontalLayout_4.setContentsMargins(0, 0, 0, 0)
        self.horizontalLayout_4.setSpacing(0)
        self.horizontalLayout_4.setObjectName("horizontalLayout_4")
        spacerItem2 = QtWidgets.QSpacerItem(10, 20, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum)
        self.horizontalLayout_4.addItem(spacerItem2)
        self.horizontalFrame2.setStyleSheet('QFrame { background: rgb(33, 37, 43); }')
        self.verticalLayout_2.addWidget(self.horizontalFrame2)
        self.horizontalLayout.addWidget(self.verticalFrame_2)
        self.fast = False
        self.horizontalFrame.setAttribute(QtCore.Qt.WA_TransparentForMouseEvents, True)
        self.horizontalFrame1.setAttribute(QtCore.Qt.WA_TransparentForMouseEvents, True)
        self.hide()

    def maximized_check(self):
        if mainui.isMaximized():
            self.pushButton_3.setIcon(QtGui.QIcon(data_dir + f'icons{sep}24x24{sep}cil-window-restore{self.scaled}.png'))
        else:
            self.pushButton_3.setIcon(QtGui.QIcon(data_dir + f'icons{sep}24x24{sep}cil-window-maximize{self.scaled}.png'))

    def show(self, fast=False):
        self.updateMask()
        self.fast = fast
        QtWidgets.QWidget.show(self)

    def showEvent(self, a0: QtGui.QShowEvent) -> None:
        QtWidgets.QWidget.showEvent(self, a0)
        if not self.fast:
            self.animation.start()
        else:
            self.setWindowOpacity(1)
        self.horizontalFrame.setAttribute(QtCore.Qt.WA_TransparentForMouseEvents, False)
        self.horizontalFrame1.setAttribute(QtCore.Qt.WA_TransparentForMouseEvents, False)

    def hide(self, fast=False) -> None:
        if not fast:
            self.animation2.start()
            QtCore.QTimer.singleShot(1000, lambda: QtWidgets.QWidget.hide(self))
            mainui.dragPos = None
        else:
            self.setWindowOpacity(0)
            QtWidgets.QWidget.hide(self)
        self.horizontalFrame.setAttribute(QtCore.Qt.WA_TransparentForMouseEvents, True)
        self.horizontalFrame1.setAttribute(QtCore.Qt.WA_TransparentForMouseEvents, True)

    def move_dialog_pos(self):
        global_coords = mainui.mapToGlobal(mainui.rect().topLeft())
        self.move(global_coords.x(), global_coords.y())

    def resizeEvent(self, a0: QtGui.QResizeEvent) -> None:
        QtWidgets.QWidget.resizeEvent(self, a0)
        self.updateMask()

    def updateMask(self):
        path = QtGui.QPainterPath()
        path.addRect(0, 0, self.width(), self.height() - 30)
        path.addRect(0, self.height() - 30, self.width() - 25, 30)
        poly = path.toFillPolygon().toPolygon()
        reg = QtGui.QRegion(poly)
        self.setMask(reg)


@adjust_sizing()
class SnackBar(QtWidgets.QWidget):
    """
        This is a QWidget that acts like an Android snack bar.
    """
    def __init__(self, text, log_button=False, error=False, *args, **kwargs):
        QtWidgets.QWidget.__init__(self, parent=mainui, *args, **kwargs)
        self.setObjectName("Form")
        self.setStyleSheet('background-color: transparent;')
        self.resize(496, 60)
        self.setWindowFlags(QtCore.Qt.Tool | QtCore.Qt.FramelessWindowHint)
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground, True)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Minimum)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.sizePolicy().hasHeightForWidth())
        self.setSizePolicy(sizePolicy)
        self.setStyleSheet("QPushButton {\n"
                           "    background-color: transparent;\n"
                           "}\n"
                           "\n"
                           "QPushButton:hover {\n"
                           "    text-decoration: underline;\n"
                           "}")
        self.shadow = QtWidgets.QGraphicsDropShadowEffect()
        self.shadow.setColor(QtGui.QColor(20, 20, 20, 200))
        self.shadow.setXOffset(0)
        self.shadow.setYOffset(5)
        self.shadow.setBlurRadius(5)
        self.verticalLayout_2 = QtWidgets.QVBoxLayout(self)
        self.verticalLayout_2.setContentsMargins(11, 0, 11, 20)
        self.verticalLayout_2.setObjectName("verticalLayout_2")
        self.verticalFrame = QtWidgets.QFrame(self)
        self.verticalFrame.setGraphicsEffect(self.shadow)
        self.verticalFrame.setMinimumSize(QtCore.QSize(0, 40))
        self.verticalFrame.setMaximumSize(QtCore.QSize(16777215, 40))
        accent_color = mainui.accent_color if not error else (255, 0, 0)
        dark_color = tuple([max(color - 30, 0) for color in accent_color])
        self.verticalFrame.setStyleSheet("#verticalFrame {\n"
                                         f"    background-color: rgb{accent_color};\n"
                                         "    border-radius: 10px;\n"
                                         f"    border: 3px solid rgb{dark_color};\n"
                                         "}")
        self.verticalFrame.setObjectName("verticalFrame")
        self.verticalLayout = QtWidgets.QVBoxLayout(self.verticalFrame)
        self.verticalLayout.setContentsMargins(11, 0, 11, 0)
        self.verticalLayout.setObjectName("verticalLayout")
        self.horizontalFrame = QtWidgets.QFrame(self.verticalFrame)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Expanding)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.horizontalFrame.sizePolicy().hasHeightForWidth())
        self.horizontalFrame.setSizePolicy(sizePolicy)
        self.horizontalFrame.setStyleSheet("color: white;\n"
                                           "")
        self.horizontalFrame.setObjectName("horizontalFrame")
        self.horizontalLayout = QtWidgets.QHBoxLayout(self.horizontalFrame)
        self.horizontalLayout.setContentsMargins(0, 0, 0, 0)
        self.horizontalLayout.setSpacing(7)
        self.horizontalLayout.setObjectName("horizontalLayout")
        self.label = QtWidgets.QLabel(self.horizontalFrame)
        self.label.setText(text)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Expanding)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.label.sizePolicy().hasHeightForWidth())
        self.label.setSizePolicy(sizePolicy)
        font = QtGui.QFont()
        font.setFamily("Segoe UI")
        font.setPointSize(12)
        self.label.setFont(font)
        self.label.setAlignment(QtCore.Qt.AlignLeading | QtCore.Qt.AlignLeft | QtCore.Qt.AlignTop)
        self.label.setObjectName("label")
        self.horizontalLayout.addWidget(self.label)
        self.pushButton = QtWidgets.QPushButton(self.horizontalFrame)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Expanding)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.pushButton.sizePolicy().hasHeightForWidth())
        self.pushButton.setSizePolicy(sizePolicy)
        self.pushButton.setMinimumSize(QtCore.QSize(80, 0))
        self.pushButton.setMaximumSize(QtCore.QSize(80, 16777215))
        font = QtGui.QFont()
        font.setFamily("Segoe UI")
        font.setPointSize(9)
        self.pushButton.setFont(font)
        self.pushButton.setCursor(QtGui.QCursor(QtCore.Qt.PointingHandCursor))
        self.pushButton.setStyleSheet("")
        self.pushButton.setObjectName("pushButton")
        self.pushButton.setText('View Logs')
        if log_button:
            self.horizontalLayout.addWidget(self.pushButton)
            self.pushButton.clicked.connect(mainui.pushButton_10.click)
        else:
            self.pushButton.hide()
        self.pushButton_2 = QtWidgets.QPushButton(self.horizontalFrame)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Expanding)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.pushButton_2.sizePolicy().hasHeightForWidth())
        self.pushButton_2.setSizePolicy(sizePolicy)
        self.pushButton_2.setMinimumSize(QtCore.QSize(50, 0))
        self.pushButton_2.setMaximumSize(QtCore.QSize(50, 16777215))
        font = QtGui.QFont()
        font.setFamily("Segoe UI")
        font.setPointSize(9)
        self.pushButton_2.setFont(font)
        self.pushButton_2.setText('Close')
        self.pushButton_2.setCursor(QtGui.QCursor(QtCore.Qt.PointingHandCursor))
        self.pushButton_2.setObjectName("pushButton_2")
        self.pushButton_2.clicked.connect(self.start_closing)
        self.horizontalLayout.addWidget(self.pushButton_2)
        self.verticalLayout.addWidget(self.horizontalFrame)
        self.verticalLayout_2.addWidget(self.verticalFrame)
        self.setWindowOpacity(0)

        self.animation = QtCore.QPropertyAnimation(self, b'windowOpacity')
        self.animation.setStartValue(0)
        self.animation.setEndValue(1)
        self.animation.setDuration(500)
        self.animation.setEasingCurve(QtCore.QEasingCurve.InOutQuart)

        self.closing_animation = QtCore.QPropertyAnimation(self, b'windowOpacity')
        self.closing_animation.setStartValue(1)
        self.closing_animation.setEndValue(0)
        self.closing_animation.setDuration(500)
        self.closing_animation.setEasingCurve(QtCore.QEasingCurve.InOutQuart)

    def showEvent(self, a0: QtGui.QShowEvent) -> None:
        QtWidgets.QWidget.showEvent(self, a0)
        self.setFixedWidth(self.minimumSizeHint().width())

    def start_pos(self):
        global_coords = mainui.mapToGlobal(mainui.rect().center())
        return QtCore.QPoint(global_coords.x() - self.width() // 2, global_coords.y() + mainui.height() // 2 - 80)

    def move_to_pos(self):
        self.move(self.start_pos())

    def start_closing(self):
        self.closing_animation.start()
        QtCore.QTimer.singleShot(500, self.hide)


class MainUpdateThread(QtCore.QThread):
    """
        This is a QThread that handles the main updating of the main user.
    """
    emitter = QtCore.pyqtSignal(object)

    def __init__(self, client, *args, **kwargs):
        super(MainUpdateThread, self).__init__(*args, **kwargs)
        self.client = client
        self.oldsongname = None
        self.oldpfp = None
        self.oldstatus = ''
        self.oldname = ''
        self.oldsongid = ''
        self.running = False

    def run(self):
        self.running = True
        self.oldsongname = self.client.mainstatus.songname
        self.oldpfp = self.client.mainstatus.clientavatar
        self.oldstatus = self.client.mainstatus.playing_status
        self.oldname = self.client.mainstatus.clientusername
        self.oldsongid = self.client.mainstatus.songid
        while not mainui.isInitialized:
            time.sleep(0.1)

        while self.running:
            try:
                update_reason = None
                if self.oldpfp != self.client.mainstatus.clientavatar:
                    update_reason = 'pfp'
                if self.oldsongname != self.client.mainstatus.songname or \
                        self.oldpfp != self.client.mainstatus.clientavatar or \
                        self.oldstatus.lower() != self.client.mainstatus.playing_status.lower() or \
                        self.oldname != self.client.mainstatus.clientusername or \
                        self.oldsongid != self.client.mainstatus.songid:

                    status = self.client.mainstatus.playing_status.lower()
                    self.oldsongname = self.client.mainstatus.songname
                    if update_reason == 'pfp':
                        self.oldpfp = self.client.mainstatus.clientavatar
                    self.oldstatus = self.client.mainstatus.playing_status
                    self.oldname = self.client.mainstatus.clientusername
                    self.oldsongid = self.client.mainstatus.songid
                    mainuserstatus = PartialBasicUserStatusWidget(status, self.client.mainstatus.clientavatar,
                                                                  self.client.mainstatus)
                    if self.client.spotifyplayer and self.client.spotifyplayer.isinitialized:
                        playbackcontroller = PartialPlaybackController(self.client.mainstatus,
                                                                       self.client.spotifyplayer,
                                                                       self.client)
                        self.emitter.emit(playbackcontroller)
                    else:
                        mainui.horizontalFrame5.setFixedHeight(0)
                    if mainui.partiallisteningtofriends and mainui.spotifylistener and mainui.spotifylistener.running:
                        listener = PartialListeningToFriends(False, '', mainui.spotifylistener, self.client.mainstatus,
                                                             mainuserstatus.dominant_color,
                                                             tuple(mainuserstatus.text_color),
                                                             tuple(mainuserstatus.dark_color))
                        self.emitter.emit(listener)
                    self.emitter.emit(mainuserstatus)
                    if status == 'listening':
                        self.client.send_queue_for_caching()
                        self.client.send_next_for_listening(force=True)
            except (requests.RequestException, Exception) as e:
                logger.error('An unexpected error has occured: ', exc_info=e)
            time.sleep(0.25)


class FriendUpdateThread(QtCore.QThread):
    """
        This is a QThread that handles the main updating of the friends list.
    """
    emitter = QtCore.pyqtSignal(object)

    def __init__(self, client, statuswidgets, ui, *args, **kwargs):
        super(FriendUpdateThread, self).__init__(*args, **kwargs)
        self.client = client
        self.statuswidgets = statuswidgets
        self.ui = ui
        self.running = False

    def run(self):
        self.running = True
        while not self.ui.isInitialized:
            time.sleep(0.1)
        while self.running:
            try:
                for id_, friend in self.client.friendstatus.items():
                    if id_ not in self.statuswidgets.copy():
                        status = friend.playing_status.lower()
                        statuswidget = PartialStatusWidget(status, friend.clientavatar, friend.client_id,
                                                           friend.clientusername, friend, id_, self.ui.accent_color)
                        listedstatuswidget = PartialListedFriendStatus(friend, status)
                        advancedstatuswidget = PartialAdvancedUserStatus(friend, status)
                        self.emitter.emit((statuswidget, statuswidget, listedstatuswidget, advancedstatuswidget))
                        self.update_friend_statuses()
                    elif friend.songid != self.statuswidgets[id_].spotifysong.songid or \
                            friend.clientavatar != self.statuswidgets[id_].spotifysong.clientavatar or \
                            friend.playing_status != self.statuswidgets[id_].spotifysong.playing_status or \
                            friend.clientusername != self.statuswidgets[id_].spotifysong.clientusername or \
                            friend.songname != self.statuswidgets[id_].spotifysong.songname:
                        if friend.playing_type not in ('None', 'ad', 'episode'):
                            status = friend.playing_status.lower()
                        else:
                            status = 'online' if friend.playing_status == 'Online' else 'offline'
                        statuswidget = PartialStatusWidget(status, friend.clientavatar, friend.client_id,
                                                           friend.clientusername, friend, id_, self.ui.accent_color)
                        listedstatuswidget = PartialListedFriendStatus(friend, status)
                        try:
                            advancedstatuswidget = PartialAdvancedUserStatus(friend, status)
                        except PIL.UnidentifiedImageError:
                            advancedstatuswidget = PartialAdvancedUserStatus(friend, status)
                        self.emitter.emit((statuswidget, statuswidget, listedstatuswidget, advancedstatuswidget))
                        QtCore.QTimer.singleShot(0, self.update_friend_statuses)
                for id_ in self.statuswidgets.copy():
                    if id_ not in self.client.friendstatus:
                        self.emitter.emit(DeleteWidget(id_))
                        QtCore.QTimer.singleShot(0, self.update_friend_statuses)
            except (requests.RequestException, Exception) as _exc:
                logger.error('An unexpected error occured: ', exc_info=_exc)
            time.sleep(0.25)

    def update_friend_statuses(self):
        listening_friends = len([status for status in self.client.friendstatus.values()
                                 if status.playing_status == 'Listening'])
        online_friends = len([status for status in self.client.friendstatus.values()
                              if status.playing_status == 'Online'])
        offline_friends = len([status for status in self.client.friendstatus.values()
                               if status.playing_status == 'Offline'])
        self.ui.label_27.setText(f'Listening - {listening_friends}')
        self.ui.label_28.setText(f'Online - {online_friends}')
        self.ui.label_29.setText(f'Offline - {offline_friends}')
        listening_friends = f'{listening_friends} friend' if listening_friends == 1 else f'{listening_friends} friends'
        online_friends = f'{online_friends} friend' if online_friends == 1 else f'{online_friends} friends'
        offline_friends = f'{offline_friends} friend' if offline_friends == 1 else f'{offline_friends} friends'
        for friend_id in mainui.client.listening_friends:
            if friend_id not in mainui.client.friends:
                try:
                    mainui.client.listening_friends.pop(mainui.client.listening_friends.index(friend_id))
                    mainui.client.listening_friends_time.pop(friend_id)
                except ValueError:
                    pass

        listen_along_friends = []
        listen_along_time_text = []
        for id_ in mainui.client.listening_friends:
            listen_along_friends.append(mainui.client.friends[id_].clientUsername)

            def _to_str(delta):
                return f'{int(delta // 60)}m {int(delta % 60)}s'

            listen_along_time_text.append(_to_str(time.time() - mainui.client.listening_friends_time[id_]))

        listen_along_text = ', '.join(listen_along_friends) + ' listening along'
        listen_along_time_text = '(' + ', '.join(listen_along_time_text) + ')'
        if mainui.client.listening_friends:
            parsed_text = f'<br><span style="color: rgb(252, 161, 40)">‎  {listen_along_text}  </span>' \
                          f'<br><span style="color: rgb(252, 161, 40)">‎  {listen_along_time_text}  </span>'
        else:
            parsed_text = ''
        self.ui.label_3.setText(
            f'<span style="color:rgb(29, 185, 84)">‎  {listening_friends} listening • </span>'
            f'<span style="color:rgb(33, 92, 255)">{online_friends} online • </span>'
            f'<span style="color:rgb(125, 125, 125)">{offline_friends} offline  </span>{parsed_text}')


class RequestUpdateThread(QtCore.QThread):
    """
        This is a QThread that handles the updating of inbound and outbound friend requests.
    """
    emitter = QtCore.pyqtSignal(object)

    def __init__(self, client, ui, *args, **kwargs):
        self.client = client
        self.ui = ui
        self.running = False
        self.last_requests = self.client.friend_requests.copy()
        self.outbound_last_requests = self.client.outbound_friend_requests.copy()
        super(RequestUpdateThread, self).__init__(*args, **kwargs)

    def run(self):
        self.running = True
        while not mainui.isInitialized:
            time.sleep(0.1)
        while self.running:
            try:
                for request, data in self.client.friend_requests.items():
                    if request not in self.last_requests:
                        friend_request = PartialInboundFriendRequest(data, request, self.ui, self.client)
                        logger.info('A new friend request has been recieved')
                        self.emitter.emit(friend_request)
                for request in self.last_requests:
                    if request not in self.client.friend_requests:
                        logger.info('A friend request has been removed')
                        self.emitter.emit(DeleteWidget(request))
                self.last_requests = self.client.friend_requests.copy()
                for request, data in self.client.outbound_friend_requests.items():
                    if request not in self.outbound_last_requests:
                        friend_request = PartialOutboundFriendRequest(data, request, self.ui, self.client)
                        self.emitter.emit(friend_request)
                for request in self.outbound_last_requests:
                    if request not in self.client.outbound_friend_requests.copy():
                        self.emitter.emit(DeleteWidget(request))
                self.outbound_last_requests = self.client.outbound_friend_requests.copy()
            except (requests.RequestException, Exception) as _exc:
                logger.error('An unexpected error occured: ', exc_info=_exc)
            time.sleep(0.25)


class FriendHistoryUpdateThread(QtCore.QThread):
    """
        This is a QThread that handles the updating of past user friend statuses.
    """
    emitter = QtCore.pyqtSignal(object)

    def __init__(self, client, ui, *args, **kwargs):
        super(FriendHistoryUpdateThread, self).__init__(*args, **kwargs)
        self.client = client
        self.ui = ui
        self.running = False
        self.last_friends = client.friendstatus.copy()

    def run(self):
        self.running = True
        while not mainui.isInitialized:
            time.sleep(0.1)
        while self.running:
            try:
                for id_, friend in self.client.friendstatus.items():
                    if id_ not in self.last_friends:
                        widget = PartialPastFriendStatus(friend)
                        self.emitter.emit(widget)
                    else:
                        if friend.songid != self.last_friends[id_].songid or \
                                friend.songname != self.last_friends[id_].songname:
                            try:
                                widget = PartialPastFriendStatus(friend)
                            except (requests.RequestException, Exception):
                                widget = PartialPastFriendStatus(friend)
                            self.emitter.emit(widget)
                for id_ in self.last_friends:
                    if id_ not in self.client.friendstatus.copy():
                        self.emitter.emit(DeleteWidget(id_))
                self.last_friends = self.client.friendstatus.copy()
            except (requests.RequestException, Exception) as _exc:
                logger.error('An unexpected error occured: ', exc_info=_exc)
            time.sleep(0.25)


class SocketListener(QtCore.QThread):
    """
        This is a QThread that listens to activity on port 49475, to prevent multiple instances being opened.
    """
    emitter = QtCore.pyqtSignal(bytes)

    def __init__(self, port, *args, **kwargs):
        super(SocketListener, self).__init__(*args, **kwargs)
        self.ADDR = 'localhost'
        self.PORT = port

    def run(self):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind((self.ADDR, self.PORT))
            except OSError as _exc:
                logger.error(f'An error occured while trying to bind to port {self.PORT}: ', exc_info=_exc)
                return
            while True:
                s.listen()
                conn, _ = s.accept()
                with conn:
                    data = conn.recv(1024)
                    if data == b'close':
                        s.close()
                        return
                    self.emitter.emit(data)


class DeleteWidget:
    """A class that shows a widget needs to be deleted through a pyqtSignal."""

    def __init__(self, *args):
        self.args = args
