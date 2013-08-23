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

from ... import hoster

@hoster.host
class this:
    model = hoster.HttpHoster
    name = 'softonic.de'
    patterns = [
        hoster.Matcher('https?', '~^(?!www)(?P<name>.*?).softonic.de$'),
    ]
    url_template = 'http://{name}.softonic.de/download'
    search = dict(display='thumbs', tags=['other', 'software'])

def on_check_http(file, resp):
    h = resp.soup.find(id='program_title')
    title = h.find('strong').text.strip()
    info = h.find('em')
    if info and info.text.strip():
        title = '{} ({})'.format(title, info.text.strip())
    url = resp.soup.find(id='download-button').get('href') # old id: free_download_alt_button
    return dict(links=[url], package_name=title)
    
def on_search(ctx, query):
    url = 'http://www.softonic.de/s/'+query
    if not ctx.position:
        ctx.position = 1
    elif ctx.position > 1:
        url += '/'+str(ctx.position)
    resp = ctx.account.get(url)
    items = resp.soup.select('#program_list td.basic-data')
    if not items:
        return
    for item in items:
        result = dict()
        h5 = item.find('h5')
        result['url'] = h5.find('a').get('href')

        info = h5.find('span').extract().text.strip()
        title = h5.find('strong').text.strip()
        result['title'] = '{} ({})'.format(title, info)

        result['thumb'] = item.find(class_='thumbnail').find('img').get('src')
        result['description'] = item.find('dd', class_='description').text
        ctx.add_result(**result)

    next = resp.soup.find("i", class_="icon-caret-right")
    if next:
        ctx.next = ctx.position + 1
