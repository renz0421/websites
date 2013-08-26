
from ... import hoster, javascript
from ...plugintools import between
import json

@hoster.host
class this:
    model = hoster.HttpHoster
    name = 'ted.com'
    patterns = [
        hoster.Matcher('https?', '*.ted.com', "!/talks/<name>.html").set_tag("direct"),
    ]
    search = dict(display='thumbs', tags='video', empty=True)

def on_check(file):
    resp = file.account.get(file.url, headers={"Accept-Language": "en"})
    if file.pmatch.tag == "direct":
        name = resp.soup.find("meta", attrs={"property": "og:title"})
        if name is None:
            file.no_download_link()
        filename = file.pmatch.name + ".mp4"
        file.set_infos(name=filename)

def on_download(chunk):
    if chunk.pmatch.tag == "direct": # talkDetails
        resp = chunk.account.get(chunk.url, headers={"Accept-Language": "en"})
        try:
            data = json.loads(between(resp.text, "var talkDetails =", "</script>"))
        except ValueError:
            chunk.no_download_link()
        try:
            videos = {i["id"]: i["file"] for i in data["htmlStreams"]}
        except KeyError:
            chunk.no_download_link()
            
        if not videos:
            chunk.no_download_link()
            
        if "high" in videos:
            return videos["high"]
        else:
            return videos.values()[0]
    else:
        chunk.no_download_link()
        
# http://www.ted.com/search?cat=ss_talks&q=hunger&page=2
def on_search(ctx, query):
    resp = ctx.account.get('http://www.ted.com/search', params=dict(q=query, cat="ss_talks", page=ctx.position or 1))
    print "got response", resp.ok, resp.status_code
    talks = resp.soup("div", attrs={"class": "result video"})
    
    for t in talks:
        ctx.add_result(title=t.find("h5").text, 
                       url=t.find("a")["href"],
                       thumb=t.find("img")["src"],
                       description=t.find("p", attrs={"class": "desc"}).text)
    
    next = resp.soup.select("li.next a")
    print next
    if not next:
        ctx.next = None
    else:
        ctx.next = int(next[0]["href"].rsplit("page=", 1)[1].split("&")[0])
        
def on_search_empty(ctx):
    resp = ctx.account.get("http://www.ted.com/")
    data = between(resp.text, "/*<sl:translate_json>*/", "/*</sl:translate_json>*/")
    talks = javascript.execute(data + "JSON.stringify(gridAppJson)")
    for talk in json.loads(talks).get("talksArray", []):
        ctx.add_result(
            title=talk["tTitle"],
            thumb=talk["image"]+u"_240x180.jpg",
            duration=talk["talkDuration"],
            url="http://www.ted.com"+talk["talkLink"],
            description="Speaker: {}, Date: {}".format(talk["speaker"].strip(), talk["talkDate"])
        )