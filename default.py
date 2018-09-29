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

xbmcplugin.setContent(handle, 'movies')

def get_html(url, params={}, post={}, noerror=True):
    headers = {'Accept':'application/json'}

    html = ''

    try:
        conn = urllib2.urlopen(urllib2.Request('%s?%s' % (url, urllib.urlencode(params)), headers=headers))
        html = conn.read()
        conn.close()
    except urllib2.HTTPError, err:
        if not noerror:
            html = err.code

    return html 


def list_streams(params):
    data = get_html('http://api2.goodgame.ru/v2/streams', {'only_gg':'1','page':params['page']}, noerror=False)

    if not isinstance(data, basestring):
        if params['page'] > 0:
            params['page'] = params['page'] - 1
            list_streams(params)
    else:
        data = json.loads(data)
        for s in data['_embedded']['streams']:
            channel = s['channel']
            title = channel['key'] + '. ' + channel['title']
            preview = 'http:' + channel['thumb']
        
            plot = common.replaceHTMLCodes(channel['description'])
            plot = plot.replace('<br>', '\n')
            plot = plot.replace('<br/>', '\n')
            plot = plot.replace('<b>', '[B]')
            plot = plot.replace('</b>', '[/B]')
            plot = common.stripTags(plot)
            plot = common.replaceHTMLCodes(plot)


            postfix = channel['gg_player_src'] # source quality
            if addon.getSetting('Quality') == '1':
                postfix = postfix + '_720'             
            if addon.getSetting('Quality') == '2':
                postfix = postfix + '_480'             

            add_item(title, url='https://hls.goodgame.ru/hls/' + postfix + '.m3u8', icon=preview, poster=preview, fanart=fanart, plot=plot, isFolder=False)

        if data['page_count'] > data['page']:
            next_page = data['page'] + 1
            add_nav(u'Далее > %d из %d' % (next_page, data['page_count']), params={'page':next_page})


def main_menu(params):

    list_streams(params)

    xbmcplugin.endOfDirectory(handle)


def add_nav(title, params={}):
    url = '%s?%s' % (sys.argv[0], urllib.urlencode(params))
    item = xbmcgui.ListItem(title)
    xbmcplugin.addDirectoryItem(handle, url=url, listitem=item, isFolder=True)
    

def add_item(title, params={}, icon='', banner='', fanart='', poster='', thumb='', plot='', isFolder=False, isPlayable=False, url=None):
    if url == None: url = '%s?%s' % (sys.argv[0], urllib.urlencode(params))

    item = xbmcgui.ListItem(title, iconImage = icon, thumbnailImage = thumb)
    item.setInfo(type='video', infoLabels={'Title': title, 'Plot': plot})

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


params = common.getParameters(sys.argv[2])

mode = params.get('mode', '')
page = params.get('page', 1)

if mode == '':
    tcc().remove_like(LIVE_PREVIEW_TEMPLATE, False)
    main_menu({'page':page})
