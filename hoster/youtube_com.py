# encoding: utf-8
"""
youtube_org.py
"""
import json
from urlparse import unquote
from ... import hoster, javascript, core
from ...hoster import cfg

@hoster.host
class this:
    model = hoster.HttpHoster
    name = 'youtube.com'
    use_check_cache = False
    patterns = [
        hoster.Matcher('https?', '*.youtu.be', '/(?P<id>.+)').set_tag('video'),
        hoster.Matcher('https?', '*.youtube.com', '/watch', v='id', list='|playlist').set_tag('video'),
        hoster.Matcher('https?', '*.youtube.com', '/playlist', list='playlist').set_tag('playlist'),
        hoster.Matcher('https?', '*.youtube.com', '/videoplayback', itag='itag').set_tag('download'),
    ]
    config = [
        cfg('parse_playlists', True, bool, description="Ask me, if I want to parse a playlist."),
        ['formats',
            cfg('flv', True, bool),
            cfg('3gp', True, bool),
            cfg('mp4', True, bool),
            cfg('webm', True, bool),
            cfg('mp3', True, bool)],
        ['quality',
            cfg('144p', True, bool),
            cfg('240p', True, bool),
            cfg('360p', True, bool),
            cfg('400p', True, bool),
            cfg('480p', True, bool),
            cfg('720p', True, bool),
            cfg('1080p', True, bool),
            cfg('3072p', True, bool)]]

    set_user_agent = True
    search = dict(display='thumbs', tags='video, audio', default_phrase="vevo")
    favicon_url = "http://s.ytimg.com/yts/img/favicon_32-vflWoMFGx.png"

formats = {
    5: ("flv", 400, 240, 1, False, '240p'),
    6: ("flv", 640, 400, 4, False, '400p'),
    17: ("3gp", 176, 144, 0, False, '144p'),
    18: ("mp4", 480, 360, 2, False, '360p'),
    22: ("mp4", 1280, 720, 8, False, '720p'),
    43: ("webm", 640, 360, 3, False, '360p'),
    34: ("flv", 640, 360, 4, False, '360p'),
    35: ("flv", 854, 480, 6, False, '480p'),
    36: ("3gp", 400, 240, 1, False, '240p'),
    37: ("mp4", 1920, 1080, 9, False, '1080p'),
    38: ("mp4", 4096, 3072, 10, False, '3072p'),
    44: ("webm", 854, 480, 5, False, '480p'),
    45: ("webm", 1280, 720, 7, False, '720p'),
    46: ("webm", 1920, 1080, 9, False, '1080p'),

    # 3d
    82: ("mp4", 640, 360, 3, True, '360p'),
    83: ("mp4", 400, 240, 1, True, '240p'),
    84: ("mp4", 1280, 720, 8, True, '720p'),
    85: ("mp4", 1920, 1080, 9, True, '1080p'),
    100: ("webm", 640, 360, 3, True, '360p'),
    101: ("webm", 640, 360, 4, True, '360p'),
    102: ("webm", 1280, 720, 8, True, '720p')
}

def normalize_url(url, pmatch):
    if pmatch.tag == 'download':
        return url
    elif pmatch.tag == 'video':
        if pmatch.get('playlist'):
            core.add_links(['http://www.youtube.com/playlist?list='+pmatch.playlist])
            del pmatch.playlist
        return 'http://www.youtube.com/watch?v='+pmatch.id
    elif pmatch.tag == 'playlist':
        return 'http://www.youtube.com/playlist?list='+pmatch.playlist
    else:
        raise RuntimeError('unknown pattern match')

def on_search(ctx, query):
    if ctx.position == 0:
        ctx.position = 1
    params = {'q': query, 'v': 2, 'format': 5, 'alt': 'jsonc', 'max-results': 50, 'start-index': ctx.position}
    resp = ctx.account.get('https://gdata.youtube.com/feeds/api/videos', params=params)
    j = resp.json()
    if 'data' not in j:
        return
    items = j['data'].get('items')
    if not items:
        return
    for r in items:
        url = 'http://www.youtube.com/watch?v={}'.format(r['id'])
        if "video" not in ctx.tags:
            url = 'ytmp3org://www.youtube.com/watch?v={}'.format(r['id'])
        ctx.add_result(title=r['title'], thumb=r['thumbnail']['sqDefault'].replace('http://', 'https://'), duration=r['duration'], url=url, extra="audio" in ctx.tags, description=r['description'])
    ctx.next = ctx.position + len(ctx.results)

def on_check(file):
    if file.pmatch.tag == 'download':
        return check_direct(file)
    elif file.pmatch.tag == 'playlist':
        return check_playlist(file)
    else:
        return check_video(file)

def check_direct(file, retry=False):
    resp = file.account.get(file.url, stream=True)
    resp.close()

    if 'Content-Length' not in resp.headers:
        if not retry and file.referer:
            with hoster.transaction:
                file.url = _check_video(file, file.referer, int(file.pmatch['itag']))
            return check_direct(file, True)
        file.no_download_link(msg='link expired?')

    file.set_infos(size=int(resp.headers['Content-Length']))

def parse_playlist_page(file, playlist_id):
    resp = file.account.get("http://www.youtube.com/playlist", params=dict(list=playlist_id))
    resp.raise_for_status()
    yield resp
    for item in resp.soup.select("li.playlist-video-item"):
        try:
            description = item.select("p.video-description")[0].text.strip()
            #thumb = item.find("link")["href"]
            link = item.find_all("a", class_="yt-uix-sessionlink")[1]
            ytid = hoster.between(link["href"], "v=", "&")
            title = link.text.strip()
            if title == u"[Deleted Video]":
                continue
            dur = item.find("span", class_="video-time").text.strip()
            count = item.find("span", class_="video-view-count").text.strip().split()[0]
            yield dict(title=title,
                       url="http://youtube.com/watch?v=" + ytid,
                       #thumb=thumb,
                       description=description,
                       duration=u"{} ({} views)".format(dur, count),
                       )
        except:
            continue

def check_playlist(file):
    data = parse_playlist_page(file, file.pmatch.playlist)
    if not data:
        file.no_download_link()
    resp = next(data)
    print "EXTRA", repr(file.extra)
    if file.extra:
        # add all links, as user requested.
        return [i["url"] for i in data]
    data = list(data)
    with hoster.search.Input("Youtube playlist", "list", "youtube.com") as add:
        #add.account = file.account
        playlist_desc = resp.soup.find("div", class_="yt-uix-expander-body")
        if not playlist_desc:
            desc = ""
        else:
            desc = playlist_desc.text.strip()
        add(title="Download all {} links".format(len(data)),
            url=file.url,
            extra=1,
            #thumb=data[0]["thumb"],
            description=desc)
        for i in data:
            add(**i)
    file.delete_after_greenlet()

def check_video(file):
    return _check_video(file, file.url)

def _add_mp3(file):
    core.add_links(['ytmp3org://www.youtube.com/watch?v={}'.format(file.pmatch.id)])

def _check_video(file, url, itag=None):
    resp = file.account.get(url)
    if resp.status_code == 404:
        file.set_offline()

    for script in resp.soup("script"):
        if script.text.startswith("var ytplayer = ytplayer"):
            break
    else:
        _add_mp3(file)
        if 'This video has been age-restricted based on our' in resp.text:
            file.fatal('age verification needed. only available with an account')
        else:
            file.plugin_out_of_date(msg='error getting youtube script')

    js = json.loads(javascript.execute(script.text.encode(resp.soup.original_encoding) + '; JSON.stringify(ytplayer.config);'))
    print "PLAYER CONFIG", js
    print resp.soup.find("h1", id="unavailable-message")

    try:
        name = js['args']['title']
        streams = [x.split('&') for x in js['args']['url_encoded_fmt_stream_map'].split(',')]
        streams = [dict((y.split('=', 1)) for y in x) for x in streams]
        streams = [(int(x['itag']), "%s&signature=%s" % (unquote(x['url']), x['sig'])) for x in streams]
    except KeyError:
        streams = []
        name = resp.soup.find('meta', property='og:title')
        if not name:
            name = u"yt {}".format(file.pmatch.id)
        else:
            name = name['content']
        print "no streams found"

    if itag is not None:
        for stream in streams:
            if stream[0] == itag:
                return stream[1]
        _add_mp3(file)
        file.no_download_link()

    links = list()
    all_links = list()
    for stream in streams:
        if not stream[0] in formats:
            file.log.warning('format {} not found'.format(stream[0]))
        ext, width, height, q, _3d, quality = formats[stream[0]]

        link = dict(url=stream[1], name=u'{} ({}).{}'.format(name, quality, ext), referer=url)
        all_links.append(link)

        if not this.config.formats[ext]:
            continue
        if not this.config.quality[quality]:
            continue

        links.append(link)
    if file.extra or this.config.formats["mp3"]:
        link = dict(url='ytmp3org://www.youtube.com/watch?v={}'.format(file.pmatch.id))
        if streams:
            link["name"] = u'{}.mp3'.format(name)
        links.append(link)
        all_links.append(link)
    if not links:
        links = all_links
    
    return links, name
    
def on_download(chunk):
    check_direct(chunk.file)
    return chunk.file.url

def on_initialize_account(account):
    account.headers["Accept-Language"] = "en"
    account.set_user_agent()
