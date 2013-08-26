# -*- coding: utf-8 -*-
import re
import os
try:
    import pytz
except ImportError:
    pytz = None
    
from collections import defaultdict
from datetime import datetime
import dateutil.parser

from ... import hoster, download

@hoster.host
class this:
    model = hoster.HttpHoster
    name = 'ardmediathek.de'
    patterns = [
        hoster.Matcher('https?', '*.ardmediathek.de', "!/<sender>/<sendung>", documentId="id"),
        hoster.Matcher('https?', '*.ardmediathek.de', "!/<sender>/<sendung>/<title>", documentId="id"),
        hoster.Matcher('https?', 'mediathek.daserste.de', "!/<cat>/<dc>_<sendung>/<id>_<title>").set_tag("daserste"),
    ]
    search = dict(display='thumbs', tags='video, audio', empty=True)
    config = [
        hoster.cfg("best_only", True, bool, description="Add only best quality"),
        hoster.cfg("low", False, bool, description="Add low quality"),
        hoster.cfg("mid", False, bool, description="Add mid quality"),
        hoster.cfg("high", True, bool, description="Add high quality"),
    ]
    favicon_url = "http://www.ard.de/favicon.ico"
    
def normalize_url(url, pmatch):
    if pmatch.tag == "daserste":
        return "http://www.ardmediathek.de/das-erste/{}/{}?documentId={}".format(pmatch.sendung, pmatch.titel, pmatch.id)
    else:
        return url

def get_data(resp):
    data = [(int(q), int(i), rtmp, path, t) for q, i, rtmp, path, t in re.findall(r'mediaCollection.addMediaStream\((.*?), (.*?), "(.*?)", "(.*?)", "(.*?)\"\)', resp.text)]
    data.sort(reverse=True)
    return data

def on_check_http(file, resp):
    data = get_data(resp)
    name = resp.soup.find("meta", attrs={"property": "og:title"})["content"]
    file.set_infos(name=name)
    if not data:
        if pytz and resp.soup.find("div", attrs={"class": "fsk"}): # ard blocks fsk protected content from 6 to 22
            germany_tz = pytz.timezone("Europe/Berlin")
            now_germany = datetime.now(germany_tz)
            germany22 = datetime(now_germany.year, now_germany.month, now_germany.day, 22, 0, 1, 0, germany_tz)
            delta = germany22 - now_germany
            file.retry("FSK Protected. Waiting till 10 pm German time.", delta.seconds)
        file.no_download_link()
    try:
        name = name.split("-Clip ", 1)[1]
    except IndexError:
        pass
    videos = defaultdict(list)
    for q, i, rtmp, path, t in data:
        fname, ext = os.path.splitext(path)
        if ext == ".m3u8": # iOS streaming? ni
            continue
        fname = os.path.basename(fname)
        ext = path[path.rfind("."):]
        if rtmp:
            link = download.rtmplink(rtmp, playpath=path)
        else:
            link = path
        try:
            quality = ["low", "mid", "high"][i]
        except IndexError:
            quality = str(i)
        displayname = u"{}-{}{}".format(name, quality, ext)
        print "displayname will be", displayname
        
        link = {
            "url": link,
            "name": displayname,
        }
        videos[i].append(link)
        
    print "all", videos
    if not videos:
        #file.set_infos(name=name)
        file.no_download_link()
        return
    check = list()
    if this.config.best_only:
        check = videos[max(videos)]
    else:
        for q, links in videos.iteritems():
            if this.config[["low", "mid", "high"][i]]:
                check.extend(links)
        if not check:
            check = videos[max(videos)]
    print "tocheck:", check
    checked = {}
    rtmp = []
    for link in check:
        if not link["url"].startswith("rtmp"):
            checked[link["name"]] = link
        else:
            rtmp.append(link)
            
    for link in rtmp:
        if not link["name"] in checked:
            checked[link["name"]] = link
    if not checked:
        file.no_download_url()
    print "adding:", checked.values()
    return checked.values()

def on_search(ctx, query):
    resp = ctx.account.get('http://www.ardmediathek.de/suche', params=dict(s=query, detail=40, goto=ctx.position or 1))
    print "got response", resp.ok, resp.status_code
    soup = resp.soup
    form = soup.find("form", attrs={"id": "searchpaging"})
    if not form:
        print "nothing found"
        ctx.next = None
        return
    pages = form("option")[-1].text
    current = form.find("option", attrs={"selected": "selected"}).text
    print "Pages: {}, Current: {}".format(pages, current)
    items = soup.find("div", attrs={"id": "mt-box-suche-clips-inner"})
    items = items("li")
    print "items:", len(items)
    for i in items:
        link = i.find("a")
        try:
            duration = i.find("span", attrs={"class": "mt-airtime"}).text
        except AttributeError:
            duration = ""
        try:
            duration = duration.split(u" \xb7 ")[1]
        except IndexError:
            pass
        title = link.text
        try:
            title = title.split("-Clip ", 1)[1]
        except IndexError:
            pass
        try:
            args = dict(title=title,
                description=i.find("p").text,
                url="http://www.ardmediathek.de" + link["href"],
                thumb="http://www.ardmediathek.de" + i.find("img")["src"],
                duration=duration)
        except (AttributeError, KeyError):
            continue
        ctx.add_result(**args)
        print "added", args
    if current == pages:
        ctx.next = None
    else:
        ctx.next = int(current) + 1
        
def on_search_empty(ctx):
    resp0 = ctx.account.get("http://www.ardmediathek.de/")
    smard = hoster.between(resp0.text, 'aSMARD_Config["Mediathek"] = "', '";')
    resp = ctx.account.get(u"http://www.ardmediathek.de" + smard)
    for clip in resp.soup("clip"):
        ctx.add_result(
            title=clip.find("name").text,
            description = dateutil.parser.parse(clip.find("airdate").text).strftime("Ausgestrahlt am: %d.%m.%y %H:%M"),
            thumb=clip.find("image")["url"],
            url=clip.find("link")["url"],
            duration=clip.find("length").text
        )