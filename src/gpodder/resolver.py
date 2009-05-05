# -*- coding: utf-8 -*-
#
# gPodder - A media aggregator and podcast client
# Copyright (c) 2005-2009 Thomas Perl and the gPodder Team
#
# gPodder is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
# (at your option) any later version.
#
# gPodder is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
#  resolver.py -- YouTube and related magic
#  Justin Forest <justin.forest@gmail.com> 2008-10-13
#
# TODO:
#
#   * Channel covers.
#   * Support for Vimeo, maybe blip.tv and others.

import re
import urllib
import urllib2
import gtk
import gobject

import gpodder
from xml.sax import saxutils
from gpodder.liblogger import log
from gpodder.util import proxy_request

def get_real_download_url(url, proxy=None):
    # IDs from http://forum.videohelp.com/topic336882-1800.html#1912972
    if gpodder.interface == gpodder.MAEMO:
        # Use 3GP with AAC on Maemo
        fmt_id = 17
    else:
        # Use MP4 with AAC by default
        fmt_id = 18

    vid = get_youtube_id(url)
    if vid is not None:
        page = None
        url = 'http://www.youtube.com/watch?v=' + vid

        while page is None:
            req = proxy_request(url, proxy, method='GET')
            if 'location' in req.msg:
                url = req.msg['location']
            else:
                page = req.read()

        r2 = re.compile('.*"t"\:\s+"([^"]+)".*').search(page)

        if gpodder.interface != gpodder.MAEMO:
            # Try to find the best video format available
            r3 = re.compile('.*"fmt_map"\:\s+"([^"]+)".*').search(page)
            formats = r3.group(1).split(",")
            if '18/512000/9/0/115' in formats: #[avc1]  480x270
                  fmt_id = 18
            elif '35/640000/9/0/115' in formats: #[H264]  480x360
                    fmt_id = 35
            elif '34/0/9/0/115' in formats: #[H264]  320x240
                    fmt_id = 34
            elif '5/0/7/0/0' in formats: #[FLV1]  320x240
                    fmt_id = 5

        if r2:
            next = 'http://www.youtube.com/get_video?video_id=' + vid + '&t=' + r2.group(1) + '&fmt=%d' % fmt_id
            log('YouTube link resolved: %s => %s', url, next)
            return next

    return url

def get_youtube_id(url):
    r = re.compile('http://(?:[a-z]+\.)?youtube\.com/v/(.*)\.swf', re.IGNORECASE).match(url)
    if r is not None:
        return r.group(1)

    r = re.compile('http://(?:[a-z]+\.)?youtube\.com/watch\?v=([^&]*)', re.IGNORECASE).match(url)
    if r is not None:
        return r.group(1)

    return None

def get_real_channel_url(url):
    r = re.compile('http://(?:[a-z]+\.)?youtube\.com/user/([a-z0-9]+)', re.IGNORECASE)
    m = r.match(url)

    if m is not None:
        next = 'http://www.youtube.com/rss/user/'+ m.group(1) +'/videos.rss'
        log('YouTube link resolved: %s => %s', url, next)
        return next

    r = re.compile('http://(?:[a-z]+\.)?youtube\.com/profile?user=([a-z0-9]+)', re.IGNORECASE)
    m = r.match(url)

    if m is not None:
        next = 'http://www.youtube.com/rss/user/'+ m.group(1) +'/videos.rss'
        log('YouTube link resolved: %s => %s', url, next)
        return next

    return url

def get_real_cover(url):
    log('Cover: %s', url)

    r = re.compile('http://www\.youtube\.com/rss/user/([a-z0-9]+)/videos\.rss', re.IGNORECASE)
    m = r.match(url)

    if m is not None:
        data = urllib2.urlopen('http://www.youtube.com/user/'+ m.group(1)).read()
        data = data[data.find('id="user-profile-image"'):]
        data = data[data.find('src="') + 5:]

        next = data[:data.find('"')]

        if next.strip() == '':
            return None

        log('YouTube userpic for %s is: %s', url, next)
        return next

    return None

def get_real_episode_length(episode):
    url = get_real_download_url(episode.url)

    if url != episode.url:
        try:
            info = urllib2.urlopen(url).info()
            if 'content-length' in info:
                return info['content-length']
        except urllib2.HTTPError:
            pass

    return 0

def find_youtube_channels(string):
    # FIXME: Make proper use of the YouTube API instead
    # of screen-scraping the YouTube website
    url = 'http://www.youtube.com/results?search_query='+ urllib.quote(string, '') +'&search_type=search_users&aq=f'

    r = re.compile('>\s+<')
    data = r.sub('><', urllib.urlopen(url).read())

    r1 = re.compile('<a href="/user/([^"]+)"[^>]*>([^<]+)</a>')
    m1 = r1.findall(data)

    r2 = re.compile('\s+')

    model = gtk.ListStore(gobject.TYPE_BOOLEAN, gobject.TYPE_STRING, gobject.TYPE_STRING)

    found_users = []
    for (name, title) in m1:
        if name not in found_users:
            found_users.append(name)
            link = 'http://www.youtube.com/rss/user/'+ name +'/videos.rss'
            model.append([False, name, link])

    return model
