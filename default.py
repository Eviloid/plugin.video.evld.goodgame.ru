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

def get_html(url, params={}, post={}, noerror=True):
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
    html = get_html('https://goodgame.ru/api/4/favorites', noerror=False)
    if isinstance(html, basestring):
        data = json.loads(html)

        if isinstance(data, list):
            return True
    return False


def list_streams(params):
    data = get_html('https://api2.goodgame.ru/v2/streams', {'only_gg':'1','page':params['page'],'ids':params.get('ids', ''),'game':params.get('game', '')}, noerror=False)

    if not isinstance(data, basestring):
        if params['page'] > 0:
            params['page'] = params['page'] - 1
            list_streams(params)
    else:
        data = json.loads(data)
        for s in data['_embedded']['streams']:
            channel = s['channel']
            title = '%s. %s' % (channel['key'], channel['title'])
            preview = 'https:' + channel['thumb']

            plot = common.replaceHTMLCodes(channel['description'])
            plot = plot.replace('<br>', '\n')
            plot = plot.replace('<br/>', '\n')
            plot = plot.replace('<b>', '[B]')
            plot = plot.replace('</b>', '[/B]')
            plot = common.stripTags(plot)
            plot = common.replaceHTMLCodes(plot)

            if addon.getSetting('ShowGame') == 'true':
                plot = '[B][COLOR yellow]%s[/COLOR][/B]\n%s' % (channel['games'][0]['title'], plot)

            player_id = channel['gg_player_src']

            if addon.getSetting('GetStreamerName') == 'true':
                player = get_html('https://api2.goodgame.ru/v2/player/' + player_id, noerror=False)
            
                if isinstance(player, basestring):
                    player = json.loads(player)
                    title = '%s. %s' % (player['streamer_name'], channel['title'])

            if s['status'] == 'Dead':
                title = '[COLOR red]%s[/COLOR]' % title
                if '.jpg' in channel['img']:
                    preview = channel['img'].replace('.jpg', '_orig.jpg')
                elif '.png' in channel['img']:
                    preview = channel['img'].replace('.png', '_orig.png')
                else:
                    preview = 'https://goodgame.ru/images/stream-offline.png'
            
            add_item(title, {'mode':'play', 'url':'https://hls.goodgame.ru/hls/' + player_id}, icon=preview, poster=preview, fanart=fanart, plot=plot, isPlayable=True)

        if data['page_count'] > data['page']:
            next_page = data['page'] + 1
            params['page'] = next_page
            add_nav(u'Далее > %d из %d' % (next_page, data['page_count']), params)


def list_favorites(params):

    html = get_html('https://goodgame.ru/api/4/favorites', noerror=False)
    if isinstance(html, basestring):
        data = json.loads(html)
        ids = ''

        if isinstance(data, list):
            for f in data:
                ids = '%s,%s' % (ids, f['channelkey'])
            params['ids'] = ids

            list_streams(params)

    xbmcplugin.endOfDirectory(handle, cacheToDisc=False)


def main_menu(params):

    if checkauth() and params['page'] == 1:
        add_nav(u'[B]Избранные стримы[/B]', {'mode':'favorites'})

    list_streams(params)

    xbmcplugin.endOfDirectory(handle, cacheToDisc=False)


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
params['page'] = params.get('page', 1)

if mode == 'login':
    do_login()

elif mode == 'list':
    tcc().remove_like(LIVE_PREVIEW_TEMPLATE, False)
    main_menu(params)

elif mode == 'favorites':
    tcc().remove_like(LIVE_PREVIEW_TEMPLATE, False)
    list_favorites(params)

elif mode == 'play':
    play_stream(params)