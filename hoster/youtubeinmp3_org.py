# -*- coding: utf-8 -*-
"""Copyright (C) 2013 COLDWELL AG

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program. If not, see <http://www.gnu.org/licenses/>.
"""

import gevent
from ... import hoster
import time

@hoster.host
class this:
    model = hoster.HttpHoster
    name = 'youtubeinmp3.org'
    patterns = [
        hoster.Matcher('ytinmp3', '*.youtube.com', "!/watch", v="id").set_tag("direct")
    ]
    max_chunks = 1

def on_check(file):
    if file.name is None:
        resp = file.account.get("http://www.youtube.com/watch?v="+file.pmatch.id)
        title = resp.soup.find("meta", property="og:title")["content"]
        file.set_infos(name=title+".mp3")

def on_download(chunk):
    file = chunk.file
    first = 0
    tx = 0
    try:
        while 1:
            tx = time.time() + 60.0
            with hoster.transaction:
                chunk.waiting = tx
            resp = file.account.get("http://youtubeinmp3.com/fetch/", 
                params=dict(video="http://www.youtube.com/watch?v="+file.pmatch.id),
                stream=True)
            if "/download/grabber/?mp3=" in resp.url:
                break
            else:
                if not first:
                    first = 1
                    for _ in resp.iter_content():
                        pass
                resp.close()
                gevent.sleep(3)
    finally:
        with hoster.transaction:
            chunk.waiting = None
    return resp