# -*- coding: utf-8 -*-
import urlparse, time

from ... import hoster, core, download
from ...plugintools import between

@hoster.host
class this:
    model = hoster.HttpHoster
    name = 'arte.tv'
    patterns = [
        hoster.Matcher('http', 'videos.arte.tv', "!/<lang>/videos/<title>--<id>.html").set_tag("videos"),
        #hoster.Matcher('https', 'videos-secure.arte.tv', "!/<lang>/videos/<title>--<id>.html").set_tag("videos-secure"),
        hoster.Matcher('http', 'liveweb.arte.tv', "!/<lang>/video/<title>/").set_tag("liveweb"),
    ]
    search = dict(display='thumbs', tags='video')
    config = [
        hoster.cfg("best_only", True, bool, description="Add only best quality"),
        hoster.cfg("sd", False, bool, description="Add SD quality"),
        hoster.cfg("hd", True, bool, description="Add high quality"),
        hoster.cfg("lang", "de", str, description="Default Language", enum={"de": "German", "fr": "French"})
    ]

def load_icon(hostname):
    img = hoster.get_image("http://upload.wikimedia.org/wikipedia/commons/thumb/3/3b/Arte-Logo.svg/200px-Arte-Logo.svg.png")
    return img.crop((0, 0, 62, 62))

def liveweb_rtmp(link, swfurl):
    return download.rtmplink(
        link[:link.lower().find("mp4:")],
        playpath=link[link.lower().find("mp4:"):],
        swfurl=swfurl,
    )
    
def videos_rtmp(link, swfurl):
    return download.rtmplink(
        link[:link.lower().find("mp4:")],
        playpath=link[link.lower().find("mp4:"):],
        swfurl=swfurl
    )

def get_videos_liveweb(file, eventid, swfurl):
    config = file.account.get("http://download.liveweb.arte.tv/o21/liveweb/events/event-{}.xml?{}".format(eventid, int(time.time()*1000)))
    hd = config.soup.find("urlhd") or config.soup.find("urlHd")
    sd = config.soup.find("urlsd") or config.soup.find("urlSd")
    videos = dict()
    if hd:
        videos["hd"] = liveweb_rtmp(hd.text, swfurl)
    if sd:
        videos["sd"] = liveweb_rtmp(sd.text, swfurl)
    if not videos:
        file.no_download_link()
    return videos

def get_videos_byrefurl(file, configurl, swfurl):
    preconfigxml = file.account.get(configurl)
    preconfigsoup = preconfigxml.soup
    video = preconfigsoup.find("video", attrs={"lang": this.config.lang})
    if not video:
        video = preconfigsoup.find("video")
        if not video:
            file.no_download_link()
            return
    configxml = file.account.get(video["ref"])
    configsoup = configxml.soup
    urls = configsoup.find("video")
    if not urls:
        file.no_download_link()
    urls = urls('url')
    if not urls or len(urls)<=1:
        file.no_download_link()
    print urls[1:]
    return {u["quality"].lower(): videos_rtmp(u.text, swfurl) for u in urls[1:] if u.get("quality")}

def on_check_http(file, resp):
    swf = resp.soup.find("meta", attrs={"property": "og:video"})
    if not swf:
        file.no_download_link()
        return
    else:
        swf = swf["content"]
    title = resp.soup.find("meta", attrs={"name": "title"})
    if not title:
        title = resp.soup.find("meta", attrs={"property": "og:title"})
    if not title:
        title = resp.soup.find("title").text
    title = title["content"].split(" - ", 1)[0].encode("utf-8").replace("\"", "")
    us = urlparse.urlsplit(swf)
    params = dict(urlparse.parse_qsl(us.query))
    swfurl = "{}://{}{}".format(us.scheme, us.netloc, us.path)
    if "videorefFileUrl" in params:
        videos = get_videos_byrefurl(file, params["videorefFileUrl"], swfurl)
    elif swf.startswith("https://download-liveweb.arte.tv"):
        videos = get_videos_liveweb(file, params["eventId"], swfurl)
    else:
        file.no_download_link()
    if len(videos) == 1:
        links = [videos.items()[0]]
    elif not videos:
        file.no_download_link()
    else:
        if this.config.best_only and "hd" in videos:
            links = [("hd", videos["hd"])]
        else:
            links = [(q, videos[q]) for q in videos if this.config.get(q, False)]
        if not links:
            links = [videos.items()[0]]
    c = []
    for quality, link in links:
        name = "{}_{}.flv".format(title.replace(" ", "_").lower(), quality)
        print name, quality, link
        c.append(dict(name=name, url=link))
    core.add_links(c)
    file.delete_after_greenlet()
    
def on_search(ctx, query):
    if this.config.lang == "fr":
        url = 'https://videos-secure.arte.tv/fr/do_search/videos/recherche'
    else:
        url = 'https://videos-secure.arte.tv/de/do_search/videos/suche'
    resp = ctx.account.get(url, params=dict(q=query, itemsPerPage=50, pageNr=ctx.position or 1))
    videos = resp.soup("div", attrs={"class": "video"})
    if not videos:
        ctx.next = None
        return
    pages = resp.soup.find("ul", attrs={"class": "list"})
    if not pages:
        ctx.next = None
        return
    pages = pages("a")
    lastpage = pages[-1].text
    if lastpage.isdigit():
        ctx.next = None
    else:
        ctx.next = int(between(pages[-1]["href"], "pageNr=", "&"))
        
    for video in videos:
        url = video("a")[1]
        try:
            ctx.add_result(
                description = video.find("p", attrs={"class": "teaserText"}).text,
                thumb = u"https://videos-secure.arte.tv" + video.find("img", attrs={"class": "thumbnail"})["src"],
                title = url.text,
                url = u"http://videos.arte.tv" + url["href"],
            ) # duration is unknown
        except TypeError:
            print "type error: video was:"
            import traceback
            traceback.print_exc()
            print video