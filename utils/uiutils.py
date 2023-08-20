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

import functools
import re
import time
from typing import Callable, Union

import PIL
from appdirs import user_data_dir
from PIL import Image
from PyQt5 import QtWidgets
from PyQt5.QtWidgets import QWidget, QLabel, QPushButton
from PyQt5.QtGui import QFont, QGuiApplication
from PyQt5 import QtCore

data_dir = user_data_dir('SpotAlong', 'CriticalElement') + '\\'

__all__ = ('limit_text', 'limit_text_smart', 'limit_text_rich', 'safe_color', 'Runnable', 'DpiFont', 'adjust_sizing',
           'adj', 'adj_style', 'screen_height', 'dpi', 'get_ratio', 'scale_images', 'scale_one')


def limit_text(text, limit_amount=20):
    """
        Extremely basic way to implement elided text that fits in limit_amount chars.
    """
    if len(text) > limit_amount:
        new_text = text[:limit_amount - 3] + '...'
    else:
        new_text = text
    return new_text


def limit_text_smart(text, label: Union[QLabel, QPushButton], width=None):
    """
        This uses Qt's fontMetrics to determine where text should be elided.
    """
    return label.fontMetrics().elidedText(text, QtCore.Qt.ElideRight, label.width() if not width else width)


def limit_text_rich(text: str, label: QLabel):
    """
        This function will try to look at a basic rich text string with strong text, and attempt to elide given the
        label's width.
    """
    normal, rich = text.split('<strong>')
    rich = rich.split('</strong>')[0] + ' '  # padding for recursive function

    def recurse(iterations=0):
        nonlocal rich
        normal_width = label.fontMetrics().boundingRect(normal).width()
        new_label = QLabel()
        new_label.setFont(label.font())
        new_font = new_label.font()
        new_font.setBold(True)
        new_label.setFont(new_font)
        rich_width = new_label.fontMetrics().boundingRect(rich).width() + 3  # padding
        total_width = normal_width + rich_width if iterations != 0 else 99999999  # some absurdly large number

        if normal_width > label.width():
            return limit_text_smart(normal, label)

        if total_width > label.width():
            rich = rich[:-1] + '...' if iterations == 0 else rich[:-4] + '...'
            return recurse(iterations + 1)
        else:
            if iterations == 1:
                rich = rich[:-3]
            elif rich[-4] == ' ':
                rich = rich[:-4] + '...'
            return f'{normal}<strong>{rich}</strong>'

    try:
        return recurse()
    except RuntimeError:
        return ''


def safe_color(cls):
    """
        This is a class decorator that will block an accidental change to the stylesheet while changing the accent
        color, if the colors in the stylesheet overlap with the accent color.
    """

    @functools.wraps(cls)
    def wrapper_safe_color(*args, **kwargs):
        widget_instance = cls(*args, **kwargs)
        widgets = [attr for attr in [getattr(widget_instance, a) for a in dir(widget_instance)]
                   if issubclass(type(attr), QWidget)]
        [widget.setStyleSheet(widget.styleSheet() + '/* NO ACCENT COLOR */') for widget in widgets]
        return widget_instance

    return wrapper_safe_color


class Runnable(QtCore.QThread):
    callback = QtCore.pyqtSignal(object)
    """
        This provides for an easy way for thread safe callbacks.
    """

    def __init__(self, runnable: Callable = lambda: None, *args, **kwargs):
        super(Runnable, self).__init__(*args, **kwargs)
        self.runnable = runnable

    def run(self):
        self.callback.emit(self.runnable())

    def __call__(self):
        self.start()


"""
These following classes / functions contain some of the weirdest witchcraft and functionality I've seen...
This app was developed at 1080p 120dpi (125% scaling on Windows)
"""


class DpiFont(QFont):
    """
        This class attempts to scale fonts according to the DPI and available pixels in the users' primary display.
    """

    def __init__(self, *args, **kwargs):
        super(DpiFont, self).__init__(*args, **kwargs)

    def setPointSize(self, a0: int) -> None:
        self.setPointSizeF(float(a0))

    def setPointSizeF(self, a0: float) -> None:
        ratio = 1
        if screen_height() != 1080 or dpi() != 120.0:
            if dpi() / 120 <= screen_height() / 1080:
                pass  # I figured this out by accident what
                # for some reason with these specific criteria the fonts do scale properly???
            else:
                ratio = 120 / dpi() * (screen_height() / 1080)
        super(DpiFont, self).setPointSizeF(a0 * ratio)


def adj(r, *args):
    """
        Clamp size values in a QWidget to be within "acceptable" bounds.
    """
    return [min(r * arg, 16777215) for arg in args]  # the random number is the maximum value for a qt widget, silence
    #                                                  warnings


def adj_style(r, stylesheet, p=False):
    """
        This function will scale pixel values in a stylesheet to match different screens.
    """
    if p:
        print(stylesheet)

    def scale_with_pad(num):
        # make sure something like a 1px border doesn't get truncated to 0
        n = int(int(num) * r)
        if n == 0 and not float(num) == 0:
            if float(num) > 0:
                n = 1
            else:
                n = -1
        return n

    # terrifying regexes that find common pixel values and adjust them accordingly
    matches = re.findall(r'([a-zA-Z-]+: )(-?\d+)(px)', stylesheet)
    for match in matches:
        if 'margin:' not in match[0]:
            new = scale_with_pad(match[1])
            stylesheet = stylesheet.replace(''.join(match), f'{match[0]}{new}{match[2]}')
    matches = re.findall(r'((-?\d+)(px)? (-?\d+)(px)? (-?\d+)(px)? (-?\d+)(px)?)', stylesheet)
    for match in matches:
        new = scale_with_pad(match[1]), scale_with_pad(match[3]), scale_with_pad(match[5]), scale_with_pad(match[7])
        stylesheet = stylesheet.replace(match[0], f'{new[0]}px {new[1]}px {new[2]}px {new[3]}px')
    if p:
        print(stylesheet)
    return stylesheet


def adjust_sizing():
    """
        This is a class decorator that will automatically scale every single widget in the class to match different
        screens.
    """

    class AdjustSizing:
        def __init__(self, cls):
            self.cls = cls

        def __call__(self, *args, **kwargs):
            ratio = get_ratio()
            if ratio != 1:
                widget = self.cls(*args, **kwargs)
                scaleable_attrs = dir(widget)
                scaleable_attrs = [attr for attr in [getattr(widget, attr) for attr in scaleable_attrs]
                                   if issubclass(type(attr), QWidget)]

                def adjust_widgets(w):
                    if hasattr(widget, 'widgets_to_ignore'):
                        if w in widget.widgets_to_ignore:
                            return
                    w.resize(*adj(ratio, w.size().width(), w.size().height()))
                    w.move(*adj(ratio, w.pos().x(), w.pos().y()))
                    w.setMinimumSize(*adj(ratio, w.minimumWidth(), w.minimumHeight()))
                    w.setMaximumSize(*adj(ratio, w.maximumWidth(), w.maximumHeight()))
                    if hasattr(widget, 'styles_to_ignore'):
                        if w in widget.styles_to_ignore:
                            return
                    w.setStyleSheet(adj_style(ratio, w.styleSheet()))

                def adjust_layouts(w):
                    if hasattr(widget, 'widgets_to_ignore'):
                        if w in widget.widgets_to_ignore:
                            return
                    if ratio > 1:
                        leftm = w.contentsMargins().left()
                        rightm = w.contentsMargins().right()
                        topm = w.contentsMargins().top()
                        bottomm = w.contentsMargins().bottom()
                        # account for default values that DO SCALE for some reason?????
                        if abs(leftm - round(11 * (dpi() / 120))) <= 1:
                            leftm = 11
                        if abs(rightm - round(11 * (dpi() / 120))) <= 1:
                            rightm = 11
                        if abs(topm - round(11 * (dpi() / 120))) <= 1:
                            topm = 11
                        if abs(bottomm - round(11 * (dpi() / 120))) <= 1:
                            bottomm = 11
                        w.setContentsMargins(leftm, topm, rightm, bottomm)
                        if abs(w.spacing() -
                               round(7 * (dpi() / 120))) <= 1:
                            w.setSpacing(7)
                    w.setContentsMargins(*adj(ratio, w.contentsMargins().left(), w.contentsMargins().top(),
                                              w.contentsMargins().right(), w.contentsMargins().bottom()))
                    w.setSpacing(*adj(ratio, w.spacing()))

                def adjust_spacers(w):
                    w.changeSize(*adj(ratio, w.geometry().width(), w.geometry().height()),
                                 w.sizePolicy().horizontalPolicy(), w.sizePolicy().verticalPolicy())

                [adjust_widgets(wi) for wi in scaleable_attrs]
                adjust_widgets(widget)
                scaleable_attrs = dir(widget)
                scaleable_attrs = [attr for attr in [getattr(widget, attr) for attr in scaleable_attrs]
                                   if issubclass(type(attr), QtWidgets.QBoxLayout)]
                [adjust_layouts(wi) for wi in scaleable_attrs]
                scaleable_attrs = dir(widget)
                scaleable_attrs = [attr for attr in [getattr(widget, attr) for attr in scaleable_attrs]
                                   if type == QtWidgets.QSpacerItem]
                [adjust_spacers(wi) for wi in scaleable_attrs]
                qr = widget.frameGeometry()
                cp = QtWidgets.QDesktopWidget().availableGeometry().center()
                qr.moveCenter(cp)
                widget.move(qr.topLeft())
                if hasattr(widget, 'widgets_to_adjust'):
                    [adjust_widgets(wid) for wid in widget.widgets_to_adjust]
                if hasattr(widget, 'show_after_adjust'):
                    widget.show()
                return widget
            else:
                widget = self.cls(*args, **kwargs)
                if hasattr(widget, 'show_after_adjust'):
                    widget.show()
                return widget

    return AdjustSizing


def screen_height():
    return QGuiApplication.primaryScreen().size().height()  # helper function to quickly get the screen height


def dpi():
    return QGuiApplication.primaryScreen().logicalDotsPerInch()  # helper function to quickly get the screen dpi


def get_ratio():
    """
        Helper function that returns the target ratio to scale to, in comparison to 1080p 120dpi.
    """

    ratio = 1
    if screen_height() != 1080 or dpi() != 120.0:
        ratio = min(dpi() / 120, screen_height() / 1080)
        ratio = max(ratio, 1 / 3)  # don't scale things down too far
    return ratio


def scale_images(icons, ratio):
    """
        Helper function that scales an icon to match different screens.
    """

    for icon in icons:
        try:
            img = Image.open(f'{data_dir}icons\\{icon}.png')
        except PIL.UnidentifiedImageError:
            time.sleep(0.5)  # wait for image to be closed by different thread
            img = Image.open(f'{data_dir}icons\\{icon}.png')
        img = img.resize((int(img.width * ratio), int(img.height * ratio)))
        img.save(f'{data_dir}icons\\{icon}scaled.png')


def scale_one(fp, ratio):
    """
        Like scale_images, but only scales one icon.
    """
    img = Image.open(f'{fp}.png')
    img = img.resize((int(img.width * ratio), int(img.height * ratio)))
    img.save(f'{fp}scaled.png')
