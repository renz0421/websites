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

import re
from ... import hoster, torrent

@hoster.host
class this:
    model = hoster.HttpHoster
    name = 'legittorrents.info'
    patterns = [
        hoster.Matcher('https?', '*.legittorrents.info', "!/index.php", page=("page", "=torrent-details"), id="id"),
    ]
    search = dict(display='thumbs', tags=['other'])
    max_chunks = 1

def on_check_http(file, resp):
    a = resp.soup.find("a", href=re.compile("^download.php.*"))
    if not a:
        file.no_download_link()
    torrentlink = "http://www.legittorrents.info/" + a["href"]
    resp = file.account.get(torrentlink)
    torrent.add_torrent(resp.content, file)
    file.delete_after_greenlet()
    
def on_search(ctx, query):
    payload = {
        "search": query,
        "order": 3,
        "by": 2,
        "active": 1,
        "page": "torrents",
        "pages": ctx.position or 1,
    }
    resp = ctx.account.get("http://www.legittorrents.info/index.php", params=payload)
    try:
        content = resp.soup.find_all("table", class_="lista")[3].find_all("tr")
    except IndexError:
        ctx.next = None
        return
        
    for x in content[1:]:
        a = x.find_all("a")[1]
        ctx.add_result(
            title = a.text,
            url = "http://www.legittorrents.info/" + a["href"],
            thumb = x.find("img").get("src", ""),
            description = " ",
        )
    
    next = resp.soup.find("select", class_="drop_pager")
    if next is None:
        return
    options = next.find_all("option")
    selected = int(next.find("option", selected="selected").text)
    if selected == len(options):
        ctx.next = None
    else:
        ctx.next = selected + 1
