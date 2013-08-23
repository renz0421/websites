# encoding: utf-8

import gevent
from ... import hoster

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
    while 1:
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
            
    return resp