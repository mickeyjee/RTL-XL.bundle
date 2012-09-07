# -*- coding: utf-8 -*-
import re, time
from string import ascii_uppercase

###################################################################################################
TITLE = 'RTL XL'

BASE_URL = 'http://www.rtl.nl'
PROGRAMMES_AZ = '%s/system/xl/feed/a-z.xml' % (BASE_URL)
EPISODES = '%s/system/s4m/xldata/abstract/%%d.xml' % (BASE_URL)
VIDEO_PAGE = '%s/xl/#/u/%%s' % (BASE_URL)
THUMB_URL = 'http://data.rtl.nl/system/img//%d.jpg' # Double slash is intentional

WEEKDAY = ['zondag','maandag','dinsdag','woensdag','donderdag','vrijdag','zaterdag']
MONTH = ['', 'januari','februari','maart','april','mei','juni','juli','augustus','september','oktober','november','december']

# Default artwork and icon(s)
ART = 'art-default.jpg'
ICON = 'icon-default.png'

###################################################################################################
def Start():

  Plugin.AddPrefixHandler('/video/rtlxl', MainMenu, TITLE, ICON, ART)
  Plugin.AddViewGroup('List', viewMode='List', mediaType='items')
  Plugin.AddViewGroup('InfoList', viewMode='InfoList', mediaType='items')

  # Set the default MediaContainer attributes
  MediaContainer.title1 = TITLE
  MediaContainer.viewGroup = 'List'
  MediaContainer.art = R(ART)
  DirectoryItem.thumb = R(ICON)

  # Set HTTP headers
  HTTP.CacheTime = CACHE_1HOUR
  HTTP.Headers['User-Agent'] = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.7; rv:12.0) Gecko/20100101 Firefox/12.0'

###################################################################################################
def MainMenu():

  dir = MediaContainer()
  dir.Append(Function(DirectoryItem(RtlAllProgrammes, title='Alle RTL programma\'s')))

  return dir

###################################################################################################
def RtlAllProgrammes(sender):

  dir = MediaContainer(title2=sender.itemTitle)

  # 0-9
  dir.Append(Function(DirectoryItem(RtlProgrammesByLetter, title='0-9')))

  # A to Z
  for char in list(ascii_uppercase):
    dir.Append(Function(DirectoryItem(RtlProgrammesByLetter, title=char), char=char))

  return dir

####################################################################################################
def RtlProgrammesByLetter(sender, char=None):

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

    dir.Append(Function(DirectoryItem(RtlProgramme, title=title), abstract_key=abstract_key))

  if len(dir) == 0:
    dir.header = 'Geen programma\'s'
    dir.message = 'Deze categorie bevat geen programma\'s'

  return dir

####################################################################################################
def RtlProgramme(sender, abstract_key):

  dir = MediaContainer(title2=sender.itemTitle)

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
      label = tablabel.text
      if label:
        label = label.encode('iso-8859-1').decode('utf-8')
        if label not in tabs:
          tabs.append(label)
    tabs.sort() # Order alphabetically
    for label in tabs:
      dir.Append(Function(DirectoryItem(RtlEpisodes, title=label.title()), abstract_key=abstract_key, season_key=None, tablabel=label))

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
      dir.Append(Function(DirectoryItem(RtlEpisodes, title=title), abstract_key=abstract_key, season_key=season_key, tablabel=None))

  if len(dir) == 0:
    dir.header = 'Geen afleveringen'
    dir.message = 'Dit programma bevat geen afleveringen'

  return dir

####################################################################################################
def RtlEpisodes(sender, abstract_key, season_key, tablabel):

  dir = MediaContainer(title2=sender.itemTitle, viewGroup='InfoList')
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
    (date_sort, title, summary, date, infolabel, thumb_url, video_url) = episode
    dir.Append(Function(WebVideoItem(PlayVideo, title=title, subtitle=date, infolabel=infolabel, summary=summary, thumb=Function(GetThumb, url=thumb_url)), url=video_url))

  if len(dir) == 0:
    dir.header = 'Geen afleveringen'
    dir.message = 'Deze categorie bevat geen afleveringen'

  return dir

####################################################################################################
def PlayVideo(sender, url):

  Log(' --> URL: %s' % url)
  return Redirect(WebVideoItem(url))

####################################################################################################
def GetThumb(url):

  if url != None:
    try:
      image = HTTP.Request(url, cacheTime=CACHE_1MONTH).content
      return DataObject(image, 'image/jpeg')
    except:
      pass

  return Redirect(R(ICON))
