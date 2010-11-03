# -*- coding: utf-8 -*-
###################################################################################################
#
# RTL XL (RTL Gemist) plugin for Plex (by sander1)
# http://wiki.plexapp.com/index.php/RTL_XL
#
###################################################################################################

import re, time
from string import ascii_uppercase

###################################################################################################

TITLE         = 'RTL XL'
PREFIX        = '/video/rtlxl'

BASE_URL      = 'http://www.rtl.nl'
RTL_IPAD      = '%s/service/gemist/device/ipad/feed/index.xml' % (BASE_URL) # iPad/iptv website used for recent programmes (past 7 days)
PROGRAMMES_AZ = '%s/system/xl/feed/a-z.xml' % (BASE_URL)
EPISODES      = '%s/system/s4m/xldata/abstract/%%d.xml' % (BASE_URL)
VIDEO_PAGE    = '%s/xl/u/%%s' % (BASE_URL)
THUMB_URL     = 'http://data.rtl.nl/system/img//%d.jpg' # Double slash is intentional
BG_ART_URL    = 'http://rtlxl.img.plugins.plexapp.tv/?image=%s'

IPAD_UA       = 'Mozilla/5.0 (iPad; U; CPU OS 3_2 like Mac OS X; en-us) AppleWebKit/531.21.10 (KHTML, like Gecko) Version/4.0.4 Mobile/7B334b Safari/531.21.10'
DEFAULT_UA    = 'Mozilla/5.0 (Macintosh; U; Intel Mac OS X 10.6; en-US; rv:1.9.2.12) Gecko/20101026 Firefox/3.6.12'

WEEKDAY       = ['zondag','maandag','dinsdag','woensdag','donderdag','vrijdag','zaterdag']
MONTH         = ['', 'januari','februari','maart','april','mei','juni','juli','augustus','september','oktober','november','december']

# Default artwork and icon(s)
ART_DEFAULT   = 'art-default.jpg'
ICON_DEFAULT  = 'icon-default.png'

###################################################################################################

def Start():
  Plugin.AddPrefixHandler(PREFIX, MainMenu, TITLE, ICON_DEFAULT, ART_DEFAULT)
  Plugin.AddViewGroup('List', viewMode='List', mediaType='items')
  Plugin.AddViewGroup('InfoList', viewMode='InfoList', mediaType='items')

  # Set the default MediaContainer attributes
  MediaContainer.title1    = TITLE
  MediaContainer.viewGroup = 'List'
  MediaContainer.art       = R(ART_DEFAULT)
  MediaContainer.userAgent = IPAD_UA
  DirectoryItem.thumb      = R(ICON_DEFAULT)

  # Set HTTP headers
  HTTP.SetCacheTime = CACHE_1HOUR
  HTTP.Headers['User-Agent'] = DEFAULT_UA

###################################################################################################

def MainMenu():
  dir = MediaContainer()
  dir.Append(Function(DirectoryItem(RTLRecent, title='Recente uitzendingen', thumb=R(ICON_DEFAULT))))
  dir.Append(Function(DirectoryItem(RTLAllProgrammes, title='Alle RTL programma\'s', thumb=R(ICON_DEFAULT))))
  return dir

###################################################################################################

def RTLRecent(sender):
  dir = MediaContainer(title2=sender.itemTitle)

  dir.Append(Function(DirectoryItem(RTLDay, title='Maandag', thumb=R(ICON_DEFAULT)), day='1'))
  dir.Append(Function(DirectoryItem(RTLDay, title='Dinsdag', thumb=R(ICON_DEFAULT)), day='2'))
  dir.Append(Function(DirectoryItem(RTLDay, title='Woensdag', thumb=R(ICON_DEFAULT)), day='3'))
  dir.Append(Function(DirectoryItem(RTLDay, title='Donderdag', thumb=R(ICON_DEFAULT)), day='4'))
  dir.Append(Function(DirectoryItem(RTLDay, title='Vrijdag', thumb=R(ICON_DEFAULT)), day='5'))
  dir.Append(Function(DirectoryItem(RTLDay, title='Zaterdag', thumb=R(ICON_DEFAULT)), day='6'))
  dir.Append(Function(DirectoryItem(RTLDay, title='Zondag', thumb=R(ICON_DEFAULT)), day='7'))

  return dir

###################################################################################################

def RTLDay(sender, day):
  dir = MediaContainer(title2=sender.itemTitle, viewGroup='InfoList')

  for item in HTML.ElementFromURL(RTL_IPAD + '?day=' + day, errors='ignore', headers={'User-Agent':IPAD_UA}, cacheTime=600).xpath('/html/body//ul[@class="video_list"]/li'):
    title = item.xpath('./a[text()]/text()[1]')[0].strip()
    subtitle = item.xpath('./a/span')[0].text.strip() # <-- date & time
    video_url = item.xpath('./a')[0].get('href')
    thumb = video_url.rsplit('/',1)[1].replace('.mp4', '.poster.jpg')
    thumb = 'http://iptv.rtl.nl/nettv/imagestrip/default.aspx?&width=190&height=106&files=' + thumb

    dir.Append(VideoItem(video_url, title=title, subtitle=subtitle, thumb=Function(GetThumb, url=thumb)))

  if len(dir) == 0:
    dir.header = 'Geen programma\'s'
    dir.message = 'Er staan nog geen programma\'s online voor deze dag.'

  return dir

###################################################################################################

def RTLAllProgrammes(sender):
  dir = MediaContainer(title2=sender.itemTitle)

  # 0-9
  dir.Append(Function(DirectoryItem(RTLProgrammesByLetter, title='0-9')))

  # A to Z
  for char in list(ascii_uppercase):
    dir.Append(Function(DirectoryItem(RTLProgrammesByLetter, title=char), char=char))

  return dir

####################################################################################################

def RTLProgrammesByLetter(sender, char=None):
  dir = MediaContainer(title2=sender.itemTitle)

  if char in list(ascii_uppercase):
    xp = '//abstract/name[starts-with(.,"' + char + '") or starts-with(.,"' + char.lower() + '")]/parent::abstract'
  else:
    startswith = []
    for char in list('0123456789'):
      startswith.append('starts-with(.,"' + char + '")')
    xp = '//abstract/name[' + ' or '.join(startswith) + ']/parent::abstract'

  for programme in XML.ElementFromURL(PROGRAMMES_AZ, errors='ignore').xpath(xp):
    abstract_key = int( programme.get('key') )
    title = programme.xpath('./name')[0].text.encode('iso-8859-1').decode('utf-8')

    dir.Append(Function(DirectoryItem(RTLProgramme, title=title, thumb=R(ICON_DEFAULT), art=Function(GetArt, abstract_key=abstract_key)), abstract_key=abstract_key))

  if len(dir) == 0:
    dir.header = 'Geen programma\'s'
    dir.message = 'Deze categorie bevat geen programma\'s'

  return dir

####################################################################################################

def RTLProgramme(sender, abstract_key):
  dir = MediaContainer(title2=sender.itemTitle, art=str(Function(GetArt, abstract_key=abstract_key)))

  episodes = XML.ElementFromURL(EPISODES % (abstract_key), errors='ignore')
  use_seasons = True
  try:
    if episodes.xpath('//configurations/config')[0].get('use-seasons') == 'no':
      use_seasons = False
  except:
    pass

  # Use tablabels as categories if use-seasons is explicitly set to 'no'
  # If use-seasons is set to 'yes' or if the parameter is absent -> use the season info to create categories
  if use_seasons == False:
    tabs = []
    for tablabel in episodes.xpath('//material_list/material/tablabel'):
      label = tablabel.text.encode('iso-8859-1').decode('utf-8')
      if label not in tabs:
        tabs.append(label)
    tabs.sort() # Order alphabetically
    for label in tabs:
      dir.Append(Function(DirectoryItem(RTLEpisodes, title=label.title(), thumb=R(ICON_DEFAULT)), abstract_key=abstract_key, season_key=None, tablabel=label))

  else:
    seasons = []
    for season in episodes.xpath('//season-list/season'):
      item_number = int( season.xpath('./item_number')[0].text )
      title = season.xpath('./name[@type="long"]')[0].text.encode('iso-8859-1').decode('utf-8')
      if len(title) < 4 and title.isdigit():
        title = 'Seizoen ' + title
      season_key = season.get('key')
      seasons.append([item_number, title, season_key])
    seasons.sort()
    seasons.reverse()

    for item_number, title, season_key in seasons:
      dir.Append(Function(DirectoryItem(RTLEpisodes, title=title, thumb=R(ICON_DEFAULT)), abstract_key=abstract_key, season_key=season_key, tablabel=None))

  if len(dir) == 0:
    dir.header = 'Geen afleveringen'
    dir.message = 'Dit programma bevat geen afleveringen'

  return dir

####################################################################################################

def RTLEpisodes(sender, abstract_key, season_key, tablabel):
  dir = MediaContainer(title2=sender.itemTitle, viewGroup='InfoList', art=str(Function(GetArt, abstract_key=abstract_key)))
  episodes = XML.ElementFromURL(EPISODES % (abstract_key), errors='ignore')
  eps = []

  if season_key != None:
    e = episodes.xpath('//material_list/material[@season_key="' + season_key + '"]')
  elif tablabel != None:
    e = episodes.xpath('//material_list/material/tablabel[text()="' + tablabel + '"]/parent::material')

  for episode in e:
    if episode.xpath('./maintype')[0].text == 'video':
      material_key = episode.get('key')
      episode_key = episode.get('episode_key')

      # See if there is a title for this item, if not we lookup the 'name' tag of 'episode-list/episode' later in the code
      try:
        title = episode.xpath('./title')[0].text.encode('iso-8859-1').decode('utf-8')
      except:
        title = None

      # Format dates for use in infolabel and subtitle
      date_sort = int( episode.xpath('./broadcast_date_display')[0].text )
      date = time.gmtime(date_sort)
      infolabel = time.strftime('%d-%m', date)
      w = int( time.strftime('%w', date) )
      d = str( time.strftime('%d', date) ).lstrip('0')
      m = int( time.strftime('%m', date) )
      day = WEEKDAY[w]
      month = MONTH[m]
      date = ' '.join([day, d, month, time.strftime('%H:%M', date)]) # Same format as used on iPad site

      thumbnail_id = int( episode.xpath('./thumbnail_id')[0].text )
      thumb_url = THUMB_URL % (thumbnail_id)

      # Each 'material' element should at least have one corresponding 'episode' element.
      # If not -> don't add the current item to the list
      if episode_key:
        ep_list = episodes.xpath('//episode-list/episode[@key="' + episode_key + '"]')[0]
        item_number = int( ep_list.xpath('./item_number')[0].text )
        # If we didn't find a title in the 'material' element, use 'name'.
        # If name is empty, use the item_number as episode number
        if title == None:
          try:
            title = ep_list.xpath('./name')[0].text.encode('iso-8859-1').decode('utf-8')
            if title == '':
              title = 'Aflevering ' + str(item_number)
          except:
            title = 'Aflevering ' + str(item_number)
        try:
          summary = ep_list.xpath('./synopsis')[0].text.encode('iso-8859-1').decode('utf-8')
        except:
          summary = None
        video_url = VIDEO_PAGE % (material_key)

        eps.append([date_sort, title, summary, date, infolabel, thumb_url, video_url])

  eps.sort()
  eps.reverse()
  for episode in eps:
    date_sort, title, summary, date, infolabel, thumb_url, video_url = episode
    dir.Append(Function(WebVideoItem(PlayVideo, title=title, subtitle=date, infolabel=infolabel, summary=summary, thumb=Function(GetThumb, url=thumb_url)), url=video_url))

  if len(dir) == 0:
    dir.header = 'Geen afleveringen'
    dir.message = 'Deze categorie bevat geen afleveringen'

  return dir

####################################################################################################

def PlayVideo(sender, url):
  return Redirect(WebVideoItem(url))

####################################################################################################

def GetThumb(url):
  if url != None:
    try:
      image = HTTP.Request(url, cacheTime=CACHE_1MONTH).content
      return DataObject(image, 'image/jpeg')
    except:
      pass

  return Redirect(R(ICON_DEFAULT))

####################################################################################################

def GetArt(abstract_key):
  episodes = XML.ElementFromURL(EPISODES % (abstract_key), errors='ignore')
  try:
    css = episodes.xpath('//configurations/config/css')[0].text
    background = re.search('background-image:url\((.+?)\)', css).group(1)
    url = String.Quote(BASE_URL + background, usePlus=False)
    image = HTTP.Request(BG_ART_URL % (url), cacheTime=CACHE_1MONTH).content
    return DataObject(image, 'image/jpeg')
  except:
    pass

  return Redirect(R(ART_DEFAULT))
