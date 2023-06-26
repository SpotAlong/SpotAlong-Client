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

import time
import logging
from datetime import datetime
from threading import Thread

from appdirs import user_data_dir

from spotifyclient.spotifyplayer import SpotifyPlayer  # noqa
from spotifyclient.spotifysong import SpotifySong  # noqa
from mainclient import MainClient  # noqa


logger = logging.getLogger(__name__)

data_dir = user_data_dir('SpotAlong', 'CriticalElement')


class SpotifyListener:
    """
        This is the class that allows you to listen to your friends on SpotAlong.
    """
    def __init__(self, spotifyplayer: SpotifyPlayer, client: MainClient, friend_id: str):
        self.spotifyplayer = spotifyplayer
        self.client = client
        self.friend_id = friend_id
        self.running = False
        self.handling = False
        self.external_handle = 0
        self.last_sync = time.time()
        self.begin_listening_time = datetime.utcnow().timestamp()
        self.play_song(client.friendstatus[friend_id])

    def play_song(self, song: SpotifySong):
        def runner():
            logger.info(f'SpotifyListener is now playing {song.songname}')
            self.handling = True
            while self.client.mainstatus.playing_type == 'ad':
                time.sleep(0.1)
            self.handling = False
            Thread(target=self.listener).start()

        self.running = True
        Thread(target=runner).start()

    def queue(self, song: SpotifySong):
        logger.info(f'SpotifyListener queued {song.songname}')
        Thread(target=self.spotifyplayer.add_to_queue, args=(song.songid,)).start()

    def end(self, reason='', no_log=False):
        if no_log:
            self.running = False
            self.client.client.emit('end_listening', namespace='/api/authorization')
            return
        reason = f' because {reason}' if reason else ''
        self.client.ui.show_snack_bar_threadsafe(f'The listening along session ended{reason}.')
        logger.info(f'The listening along session ended{reason}.')
        self.running = False
        self.client.client.emit('end_listening', namespace='/api/authorization')

    def listener(self):
        """
            This function will periodically check for changes in the playback state of the host, and try to match those
            changes if not already caught by the MainClient.
        """
        self.running = True
        try:
            while True:
                while self.external_handle:
                    time.sleep(2)

                if self.spotifyplayer.disconnected:
                    time.sleep(2)
                    if self.spotifyplayer.disconnected:
                        self.end('the SpotifyPlayer was disconnected, please try again later')
                        return
                if self.friend_id not in self.client.friendstatus:
                    self.end('1')
                    return
                if self.client.friendstatus[self.friend_id].playing_type != 'track':
                    self.end('the host stopped listening to a playable track')
                    return
                if not self.running:
                    self.end(no_log=True)
                    return
                if self.client.mainstatus and self.client.friendstatus[self.friend_id] and \
                        self.client.mainstatus.songid == self.client.friendstatus[self.friend_id].songid and \
                        self.client.mainstatus.songid:
                    if self.client.friendstatus[self.friend_id].progress and self.client.mainstatus.progress:
                        diff = self.client.friendstatus[self.friend_id].progress - self.client.mainstatus.progress
                        if abs(diff) > 3:
                            self.sync()
                    if not self.running:
                        self.end('2')
                        return
                    time.sleep(1)
                else:
                    if self.friend_id not in self.client.friendstatus:
                        self.end('3')
                        return
                    if not self.client.friendstatus[self.friend_id].songid:
                        self.end('the host stopped listening to a playable track')
                        return
                    if self.client.friendstatus[self.friend_id].playing_type != 'track':
                        self.end('the host stopped listening to a playable track')
                        return
                    if not self.running:
                        self.end(no_log=True)
                        return
                    while self.client.mainstatus.playing_type == 'ad':
                        time.sleep(0.1)
                    if not self.handling:

                        def wait_for_song_to_end():
                            for _ in range(3):
                                self.last_sync = time.time()
                                time.sleep(1)
                                if self.external_handle:
                                    return
                            if self.client.mainstatus.songid != self.client.friendstatus[self.friend_id].songid:
                                self.spotifyplayer.command(
                                    self.spotifyplayer.play(self.client.friendstatus[self.friend_id].songid))

                        if not self.client.mainstatus.duration or \
                                self.client.mainstatus.duration / 1000 - self.client.mainstatus.progress < 3:
                            wait_for_song_to_end()
                        else:
                            friend_status = self.client.friendstatus[self.friend_id]
                            if not friend_status.duration or friend_status.duration / 1000 - friend_status.progress < 3:
                                wait_for_song_to_end()
                            else:
                                self.spotifyplayer.command(
                                    self.spotifyplayer.play(self.client.friendstatus[self.friend_id].songid))
                    while self.client.mainstatus.songid != self.client.friendstatus[self.friend_id].songid:
                        time.sleep(1)
                        if not self.running:
                            self.end('4')
                            return
        except (Exception, KeyError):
            self.end()

    def sync(self):
        if time.time() - self.last_sync > 2 and not self.handling:
            self.last_sync = time.time()
            if not self.client.friendstatus[self.friend_id].is_playing and self.client.mainstatus.is_playing:
                Thread(target=self.spotifyplayer.command, args=(self.spotifyplayer.pause,)).start()
            if self.client.friendstatus[self.friend_id].is_playing and not self.client.mainstatus.is_playing:
                Thread(target=self.spotifyplayer.command, args=(self.spotifyplayer.resume,)).start()
            Thread(target=self.spotifyplayer.command, args=(self.spotifyplayer.seek_to(
                self.client.friendstatus[self.friend_id].progress * 1000),)).start()
