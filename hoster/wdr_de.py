# -*- coding: utf-8 -*-
from ... import hoster

@hoster.host
class this:
    model = hoster.HttpHoster
    name = 'wdr.de'
    patterns = [
        hoster.Matcher('https?', '*.wdr.de', "!/mediathek/video/sendungen/<sendung>/video<video>.html").set_tag("media"),
        hoster.Matcher("http", "*.mobile-ondemand.wdr.de").set_tag("ddl"),
    ]
    set_user_agent = dict(os="iphone")
    config = [
        hoster.cfg("best_only", True, bool, description="Add only best quality")
    ]
    
def normalize_url(url, pmatch):
    if pmatch.tag == "ddl":
        return url
    i1 = url.find("-videoplay")
    if i1>0:
        url = url[:i1]
    i2 = url.find(".html")
    if i2>0:
        url = url[:i2]
    return url + "-videoplayer_size-L.html"

qmap = ['webS',
 'webM',
 'webL']

header = {"User-Agent": \
"Mozilla/5.0 (iPhone; CPU iPhone OS 6_0 like Mac OS X) \
AppleWebKit/536.26 (KHTML, like Gecko) Version/6.0 Mobile/10A5376e Safari/8536.25"}

def on_check(file):
    if file.pmatch.tag == "ddl":
        hoster.check_download_url(file, file.url)
        return
    resp = file.account.get(file.url)
    resp.raise_for_status()
    links = {}
    best = None
    for l in resp.soup.find_all("a"):
        quality = l.get("rel", "")
        if not quality in qmap:
            continue
        links[quality] = l["href"]
        if not best or qmap.index(best) < qmap.index(quality):
            best = quality
    
    if not links:
        file.set_infos(name="{}: {}".format(file.pmatch.sendung, file.pmatch.sub.video))
        file.no_download_link()
    if this.config.best_only:
        return [links[best]]
    else:
        return links.values()

def on_download(chunk):
    print "requesting", chunk.url, header, chunk.pmatch
    resp = chunk.account.get(chunk.url, chunk=chunk, stream=True)
    print resp.headers
    print resp.request.headers
    return resp