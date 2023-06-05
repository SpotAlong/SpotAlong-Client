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

from .spotifysong import SpotifySong  # noqa


class SpotifyClient(object):
    def __init__(self, user_id, friend_code, user_data) -> None:
        """
            A class that represents a user and various related characteristics.
        """
        self.isInitialized = False
        self.friendCode = friend_code
        self.user_id = user_id
        self.user_data = user_data
        self.song_data = {}
        self.last_song = user_data['last_track']
        self.clientUsername = None
        self.clientAvatar = None
        self.user_update()
        self.isInitialized = True

    def spotifySongParse(self, track) -> SpotifySong:
        """
            Parse the Spotify track dict into a SpotifySong.
        """
        track_info = None
        if track:
            if track['currently_playing_type'] != 'ad' and track['item'] and not track['item']['is_local']:
                is_playing = track['is_playing']
                song_name = track['item']['name']
                song_id = track['item']['id']
                song_link = track['item']['external_urls']['spotify']
                try:
                    context_link = track['context']['external_urls']['spotify']
                    context_type = track['context']['type']
                    context_data = track['context']['href']
                except (TypeError, KeyError):
                    context_link = None
                    context_type = None
                    context_data = None
                progress = track['progress_ms'] / 1000
                duration = track['item']['duration_ms']
                album_name = track['item']['album']['name']
                album_link = track['item']['album']['external_urls']['spotify']
                album_image = track['item']['album']['images'][0]['url']
                song_authors_urls = []
                song_authors = []
                for info in track['item']['artists']:
                    song_authors_urls.append(info['external_urls']['spotify'])
                    song_authors.append(info['name'])
                playing_status = track['ex_data']['status']
                track_info = SpotifySong(song_name, song_id, song_link, context_type, context_data, context_link,
                                         progress, duration,
                                         album_name, album_link, album_image, song_authors_urls, song_authors,
                                         is_playing, 'track', self.clientUsername, self.clientAvatar, self.user_id,
                                         self.friendCode, playing_status, self.last_song)
            playing_status = track['ex_data']['status']
            if track['currently_playing_type'] == 'ad':
                track_info = SpotifySong(playing_type='ad',
                                         clientusername=self.clientUsername, clientavatar=self.clientAvatar,
                                         client_id=self.user_id, friend_code=self.friendCode,
                                         playing_status=playing_status, last_song=self.last_song)
            if track['item'] and track['item']['is_local']:
                is_playing = track['is_playing']
                song_name = track['item']['name']
                progress = track['progress_ms'] / 1000
                duration = track['item']['duration_ms']
                if track['item']['artists'][0]['name']:
                    song_authors = [track['item']['artists'][0]['name']]
                else:
                    song_authors = None
                playing_status = track['ex_data']['status']
                track_info = SpotifySong(songname=song_name, song_authors=song_authors, progress=progress,
                                         is_playing=is_playing, playing_type='local file',
                                         clientusername=self.clientUsername,
                                         clientavatar=self.clientAvatar, client_id=self.user_id,
                                         friend_code=self.friendCode, playing_status=playing_status,
                                         last_song=self.last_song, duration=duration)
        else:
            if self.user_data.get('ex_data', None):
                playing_status = self.user_data['ex_data']['status']
            else:
                playing_status = self.user_data['status']
            track_info = SpotifySong(playing_type='None',
                                     clientusername=self.clientUsername, clientavatar=self.clientAvatar,
                                     client_id=self.user_id, friend_code=self.friendCode, playing_status=playing_status,
                                     last_song=self.last_song)

        return track_info

    def spotifysong(self) -> typing.Optional[SpotifySong]:
        track_info = self.spotifySongParse(self.song_data)
        if track_info is None:
            if self.user_data.get('ex_data', None):
                playing_status = self.user_data['ex_data']['status']
            else:
                playing_status = self.user_data['status']
            track_info = SpotifySong(playing_type='None',
                                     clientusername=self.clientUsername, clientavatar=self.clientAvatar,
                                     client_id=self.user_id, friend_code=self.friendCode, playing_status=playing_status,
                                     last_song=self.last_song)
        return track_info

    def user_update(self):
        self.clientUsername = self.user_data['display_name']
        if self.user_data['images']:
            self.clientAvatar = self.user_data['images'][0]['url']
        else:
            self.clientAvatar = None
