#!/usr/bin/python
# -*- coding: utf-8 -*-

import os, urllib, sys, urllib2, re, cookielib, json
import xbmc, xbmcgui, xbmcplugin, xbmcaddon
import CommonFunctions as common
from tccleaner import TextureCacheCleaner as tcc

PLUGIN_NAME   = 'Goodgame plugin'

common.plugin = PLUGIN_NAME

LIVE_PREVIEW_TEMPLATE = '%//hls.goodgame.ru/previews/%'  # sqlite LIKE pattern


try:handle = int(sys.argv[1])
except:pass

addon = xbmcaddon.Addon(id='plugin.video.evld.goodgame.ru')

Pdir = addon.getAddonInfo('path')
icon = xbmc.translatePath(os.path.join(Pdir, 'icon.png'))
fanart = xbmc.translatePath(os.path.join(Pdir, 'fanart.jpg'))
fcookies = xbmc.translatePath(os.path.join(Pdir, 'cookies.txt'))
cj = cookielib.MozillaCookieJar(fcookies)


xbmcplugin.setContent(handle, 'videos')

def get_html(url, params={}, post={}, noerror=False):
    headers = {'Accept':'application/json'}

    if post:
        headers['Content-Type'] = 'application/x-www-form-urlencoded'
        req = urllib2.Request('%s' % url, urllib.urlencode(post), headers=headers)
    else:
        req = urllib2.Request('%s?%s' % (url, urllib.urlencode(params)), headers=headers)

    html = ''

    try:
        conn = urllib2.urlopen(req)
        html = conn.read()
        conn.close()
    except urllib2.HTTPError, err:
        if not noerror:
            html = err.code

    return html


def do_login():
    if addon.getSetting('User'):
        post = {'login':addon.getSetting('User'), 'password':addon.getSetting('Password'), 'remember':1}
        get_html('https://goodgame.ru/api/4/login', post=post)

        cj.save(fcookies, True, True)

	xbmc.executebuiltin('Container.Refresh')


def checkauth():
    html = get_html('https://goodgame.ru/api/4/favorites')
    if isinstance(html, basestring):
        data = json.loads(html)

        if isinstance(data, list):
            return True
    return False


def list_streams(params):

    ids = ''

    if params['mode'] == 'favorites':
        html = get_html('https://goodgame.ru/api/4/favorites')
        data = json.loads(html)

        if isinstance(data, list):
            for f in data:
                ids = '%s,%s' % (ids, f['id'])
                f['streamer'] = f['streamer']['nickname']

        datav4 = {'streams':data}

    else:
        html = get_html('https://goodgame.ru/api/4/stream', {'ggonly':'1','onpage':25,'page':params['page'],'game':params.get('game', '')}) 
        if isinstance(html, basestring):
            datav4 = json.loads(html)
            for s in datav4['streams']:
                ids = '%s,%s' % (ids, s['id'])

    if ids == '':
        if params['page'] > 0:
            params['page'] = params['page'] - 1
            list_streams(params)
    else:
        html = get_html('http://api2.goodgame.ru/v2/streams', {'ids':ids})
        data = json.loads(html)
        for s in data['_embedded']['streams']:
            channel = s['channel']
            
            player = next((item for item in datav4['streams'] if item['id'] == s['id']), {'streamer':channel['key']})['streamer']

            title = '%s. %s' % (player, channel['title'])
            preview = 'https:' + channel['thumb']

            plot = common.replaceHTMLCodes(channel['description'])
            plot = plot.replace('<br>', '\n')
            plot = plot.replace('<br/>', '\n')
            plot = plot.replace('<b>', '[B]')
            plot = plot.replace('</b>', '[/B]')
            plot = common.stripTags(plot)
            plot = common.replaceHTMLCodes(plot)

            plot = '[B][COLOR yellow]%s[/COLOR][/B]\n%s' % (channel['games'][0]['title'], plot)

            player_id = channel['gg_player_src']

            if s['status'] == 'Dead':
                title = '[COLOR red]%s[/COLOR]' % title
                if '.jpg' in channel['img']:
                    preview = channel['img'].replace('.jpg', '_orig.jpg')
                elif '.png' in channel['img']:
                    preview = channel['img'].replace('.png', '_orig.png')
                else:
                    preview = 'https://goodgame.ru/images/stream-offline.png'
            
            add_item(title, {'mode':'play', 'url':'https://hls.goodgame.ru/hls/' + player_id}, icon=preview, poster=preview, fanart=fanart, plot=plot, isPlayable=True)


        qi = datav4.get('queryInfo')
        if qi:
            if datav4['queryInfo']['onPage'] > 0:
                page_count = datav4['queryInfo']['qty'] / datav4['queryInfo']['onPage'] + 1

                if page_count > datav4['queryInfo']['page']:
                    next_page = datav4['queryInfo']['page'] + 1
                    params['page'] = next_page
                    add_nav(u'Далее > %d из %d' % (next_page, page_count), params)

    xbmcplugin.endOfDirectory(handle, cacheToDisc=False)


def list_games(params):
    html = get_html('https://goodgame.ru/api/4/stream/games', {'page':params['page']}, noerror=False)
    if not isinstance(html, basestring):
        if params['page'] > 1:
            params['page'] = params['page'] - 1
            list_games(params)
    else:
        data = json.loads(html)
        for g in data['games']:
            add_item(g['title'], {'mode':'list', 'game':g['url']}, poster=g['poster'], fanart=fanart, isFolder=True)

        params['page'] = params['page'] + 1
        add_nav(u'Далее >', params)

    xbmcplugin.endOfDirectory(handle, cacheToDisc=False)


def main_menu(params):

    if params.get('game') == None:
        if params['page'] == 1:
            if checkauth():
                add_nav(u'[B]Избранные стримы[/B]', {'mode':'favorites'})
            add_nav(u'[B]Игры[/B]', {'mode':'games'})

    list_streams(params)


def play_stream(params):
    quality = {'1':'_720', '2':'_480', 1:'_720', 2:'_480'}

    q = addon.getSetting('Quality')

    if q == '3':
        dialog = xbmcgui.Dialog()
        ret = dialog.select('Качество потока', ['Источник', '720', '480'])
        if ret < 0: return
        postfix = quality.get(ret, '')
    else:
        postfix = quality.get(q, '')

    purl = params['url'] + postfix + '.m3u8'
    item = xbmcgui.ListItem(path=purl)
    xbmcplugin.setResolvedUrl(handle, True, item)


def add_nav(title, params={}):
    url = '%s?%s' % (sys.argv[0], urllib.urlencode(params))
    item = xbmcgui.ListItem(title)
    xbmcplugin.addDirectoryItem(handle, url=url, listitem=item, isFolder=True)
    

def add_item(title, params={}, icon='', banner='', fanart='', poster='', thumb='', plot='', isFolder=False, isPlayable=False, url=None):
    if url == None: url = '%s?%s' % (sys.argv[0], urllib.urlencode(params))

    item = xbmcgui.ListItem(title, iconImage = icon, thumbnailImage = thumb)
    item.setInfo(type='video', infoLabels={'Title': title, 'Plot': plot, 'watched':'False'})

    if isPlayable:
        item.setProperty('IsPlayable', 'true')
    
    if banner != '':
        item.setArt({'banner': banner})
    if fanart != '':
        item.setArt({'fanart': fanart})
    if poster != '':
        item.setArt({'poster': poster})
    if thumb != '':
        item.setArt({'thumb':  thumb})

    xbmcplugin.addDirectoryItem(handle, url=url, listitem=item, isFolder=isFolder)


try:
    cj.load(fcookies, True, True)
except:
    pass

hr = urllib2.HTTPCookieProcessor(cj)
opener = urllib2.build_opener(hr)
urllib2.install_opener(opener)


params = common.getParameters(sys.argv[2])
params['mode'] = mode = params.get('mode', 'list')
params['page'] = int(params.get('page', 1))

if mode == 'login':
    do_login()

elif mode == 'games':
    list_games(params)

elif mode == 'list':
    tcc().remove_like(LIVE_PREVIEW_TEMPLATE, False)
    main_menu(params)

elif mode == 'favorites':
    tcc().remove_like(LIVE_PREVIEW_TEMPLATE, False)
    params['page'] = 0
    list_streams(params)

elif mode == 'play':
    play_stream(params)
