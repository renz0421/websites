# -*- coding: utf-8 -*-
from ... import hoster, download

@hoster.host
class this:
    model = hoster.HttpHoster
    name = '3sat.de'
    patterns = [
        hoster.Matcher('https?', '*.3sat.de', "!/mediathek/index.php", obj="id"),
    ]
    config = [
        hoster.cfg("best_only", True, bool, description="Add only best quality")
    ]

qmap = ['low',
 'high',
 'veryhigh',
 'hd']

def on_check(file):
    resp = file.account.get(file.url)
    if '>Beitrag nicht verf&uuml;gbar<' in resp.text:
        file.no_download_link()
    xmlurl = hoster.between(resp.text, 'playerBottomFlashvars.mediaURL = "', '"')
    xmlsoup = file.account.get(xmlurl).soup
    links = {}
    best = None
    sendung = hoster.between(resp.text, '>Sendung: ', '<')
    video = hoster.between(resp.text, '>Video: ', '<')
    title = '{} - {}'.format(sendung, video)
    for v in xmlsoup('video'):
        pg = xmlsoup.find('paramgroup', attrs={'xml:id': v['paramgroup']})
        print pg
        s = {i['name']:i['value'] for i in pg('param')}
        protos = s['protocols'].split(',')
        if 'rtmp' in protos:
            url = 'rtmp://{host}/{app}'.format(**s)
        elif 'rtmpt' in protos:
            url = 'rtmpt://{host}/{app}'.format(**s)
        quality = v.find('param', attrs={'name': 'quality'})['value'].replace('-', '')
        if quality in qmap:
            try:
                if not best or qmap.index(best) < qmap.index(quality):
                    best = quality
            except ValueError:
                if not best:
                    best = quality
        links[quality] = download.rtmplink(url, playpath=v['src'])

    if not links:
        file.set_infos(name=title)
        file.no_download_link()
    if this.config.best_only:
        return [dict(name='{}.flv'.format(title), url=links[best])]
    else:
        return [dict(name='{} ({}).flv'.format(title, q), url=url) for q, url in links.items()]