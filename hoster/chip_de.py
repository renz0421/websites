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

import os, re
import urlparse
from itertools import izip
from ... import hoster
from ...plugintools import Url, between

@hoster.host
class this:
    model = hoster.HttpHoster
    name = 'chip.de'
    patterns = [
        hoster.Matcher('https?', '*.chip.de', '!/downloads/<title>_<id>.html'),
    ]
    search = dict(display='thumbs', tags=['other', 'software'], empty=True)
    max_chunks = 1
    
def getlink(ctx):
    resp = ctx.account.get(ctx.url)
    a1 = resp.soup.find("div", class_="dl-btn")
    if not a1:
        ctx.no_download_link()
    a1 = a1.find("a")
    resp = resp.get(a1["href"])
    a2 = resp.soup.find("div", class_="dl-faktbox").find("a")
    resp = resp.get(a2["href"])
    link = resp.soup.find("div", class_="dl-getfile-description").find("a")["href"]
    return link
    
def on_check(file):
    url = getlink(file)
    name = os.path.split(Url(url).path)[1]
    hoster.check_download_url(file, url, name=name)
    
def on_download(chunk):
    return getlink(chunk)
    
def on_search(ctx, query):
    payload = {
        "q": query,
        "it": 1,
        "N": 62049,
        "No": ctx.position or 0,
    }
    resp = ctx.account.get("http://suche.chip.de/", params=payload)
    content = resp.soup.find("div", class_="mi-suche-content-v2")
    for x in content.find_all("li"):
        a = x.find("a", class_="record-title")
        u = urlparse.urlsplit(a["href"])
        d = dict(urlparse.parse_qsl(u.query))
        try:
            thumb = between(unicode(x), u"url(", ")")
        except ValueError:
            thumb = ""
        ctx.add_result(
            title = a["title"],
            url = d["url"],
            thumb = thumb,
            description = x.find("p").text.strip().split("\n")[1],
        )
    
    next = resp.soup.find("a", class_="page_next")
    if not next:
        ctx.next = None
    else:
        ctx.next = int(between(next["href"], "No=", "&"))

def on_search_empty(ctx):
    resp0 = ctx.account.get("http://www.chip.de/")
    toplink = resp0.soup.find("a", title="Download-Charts: Top 100 der Woche")
    resp = ctx.account.get(toplink["href"])
    linkre = re.compile(r"^http\:\/\/www\.chip\.de\/downloads\/.*")
    imgre = re.compile(r"^http\:\/\/www\.chip\.de\/ii/")
    images = resp.soup("img", src=imgre)
    links = resp.soup("a", href=linkre)
    for image, link in izip(images[:50], links[:50]):
        ctx.add_result(title=link["title"],
            url=link["href"],
            thumb=image["src"])