# -*- coding: utf-8 -*-
import urlparse

from ... import hoster
from PIL import Image

@hoster.host
class this:
    model = hoster.HttpHoster
    name = 'zdf.de'
    patterns = [
        hoster.Matcher('https?', '*.zdf.de', "!/ZDFmediathek/beitrag/video/<id>/<name>")
    ]
    search = dict(display='thumbs', tags='video, audio', empty=True)
    config = [
        hoster.cfg("best_only", True, bool, description="Only use best quality")
    ]

def load_icon(hostname):
    img = hoster.get_image("http://upload.wikimedia.org/wikipedia/commons/thumb/0/02/ZDF.svg/100px-ZDF.svg.png")
    new = Image.new("RGBA", (img.size[0], img.size[0]), (255, 255, 255, 0))
    new.paste(img, (0, (img.size[0]-img.size[1])//2))
    return new

def on_check(file):
    resp = file.account.get(
        "http://www.zdf.de/ZDFmediathek/xmlservice/web/beitragsDetails",
        params=dict(ak="web", id=file.pmatch.id)
    )
    
    videos = resp.soup.find_all("formitaet", attrs=dict(basetype="h264_aac_mp4_http_na_na"))
    if not videos:
        file.no_download_link()
    title = u"%s - {}p.mp4" % resp.soup.find("title").text
    q = dict()
    for video in videos:
        height = video.find("height").text
        if height and not height in q:
            url = video.find("url").text
            headers = file.account.get(url, stream=True).headers
            if not headers["content-type"] == "video/mp4":
                continue
            q[height] = {"url": url, "name": title.format(height)}
    if this.config.best_only:
        return [q[max(q)]]
    else:
        return q.values()

def on_search(ctx, query):
    resp = ctx.account.get('http://www.zdf.de/ZDFmediathek/suche', params=dict(sucheText=query, flash="off", offset=ctx.position))
    add_results(ctx, resp)
    next = resp.soup.find("a", attrs={"class": "forward"})
    if not next:
        ctx.next = None
    ctx.next = int(dict(
        urlparse.parse_qsl(
            urlparse.urlsplit(next["href"]).query
        ))["offset"])
    if ctx.next == ctx.position:
        ctx.next = None
    
def add_results(ctx, resp):
    for item in resp.soup("li"):
        thumbnail = item.find("img")
        if not thumbnail:
            continue
        else:
            thumbnail = thumbnail["src"]
            if not thumbnail.startswith("http"):
                thumbnail = "http://zdf.de" + thumbnail
        a = item("a")
        try:
            if a[0]["class"] == "orangeUpper":
                continue
        except KeyError:
            pass
        name = a[1].text.strip()
        desc = a[2].text.strip()
        t = a[3].text.strip()
        if "BEITR" in t:
            continue
        try:
            duration = t.split(", ")[1]
        except IndexError:
            duration = t
        ctx.add_result(
            title=name,
            description=desc,
            url="http://www.zdf.de" + a[0]["href"].split("?", 1)[0],
            thumb=thumbnail,
            duration=duration)
    
def on_search_empty(ctx):
    resp = ctx.account.get('http://www.zdf.de/ZDFmediathek/hauptnavigation/startseite?flash=off')
    add_results(ctx, resp)
