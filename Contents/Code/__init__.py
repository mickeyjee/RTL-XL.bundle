# -*- coding: utf-8 -*-
###################################################################################################
#
# RTL XL (RTL Gemist) plugin for Plex (by sander1)
# http://wiki.plexapp.com/index.php/RTL_XL
#
###################################################################################################

import re, time

###################################################################################################

PLUGIN_TITLE                = 'RTL XL'
PLUGIN_PREFIX               = '/video/rtlxl'

BASE_URL                    = 'http://www.rtl.nl'
RTL_GEMIST_HOME             = '%s/service/gemist/home/' % BASE_URL
PROGRAM_INDEX               = '%s/service/index/' % BASE_URL
SL_PLAYER                   = 'http://www.plexapp.com/player/silverlight.php?stream=%s&width=%s&height=%s'

# iPad/iptv website used for recent programmes (last 7 days)
RTL_GEMIST_IPAD             = '%s/service/gemist/device/ipad/feed/index.xml' % BASE_URL

MENU_PATH                   = '%s/system/video/menu%%s' % BASE_URL
DEFAULT_XML                 = '/videomenu.xml'
URL_CATEGORIES              = ['actueel', 'automotor', 'films', 'financien', 'games', 'gezondheid', 'huistuinkeuken', 'programma', 'reality', 'reizen', 'shows', 'soaps', 'sport']

EXCLUDE_URLS_CONTAINING = [
  'rtlvideo',      # Reason: isn't part of RTL Gemist, it's another service
  'grandprix',     # Reason: RTL GP uses "rtl_gp", not "grandprix"
  'rtl_sport',     # Reason: "rtl_sport" looks like an old entry, all sport items are covered by "rtl_gp" and "rtlvoetbal"
  '4me',           # Reason: part of RTL gezond
  'chirurgenwerk', # Reason: part of RTL gezond
  'rtlgezond',     # Reason: will be added manually to INCLUDE_PROGRAMS to prevent duplicates and unnecessary lookups
  'projectcatwalk' # Reason: correct name is "rtlprojectcatwalk"
]

INCLUDE_PROGRAMS = [
  [u'RTL GP', 'sport', 'rtl_gp'],
  [u'RTL Gezond', 'gezondheid', 'rtlgezond'],
  [u'RTL Experience', 'experience', 'rtlnl'],
  [u'Videosnacks', 'service', 'videosnacks'],
  [u'Project Catwalk', 'reality', 'rtlprojectcatwalk']
]

XPATH_PROGRAMS              = '/html/body/div[@id="pos0"]//a[%s]'
XPATH_PROGRAMS_CONTAINS     = 'contains(@href,"%s")'

# Default artwork and icon(s)
PLUGIN_ARTWORK              = 'art-default.jpg'
PLUGIN_ICON_DEFAULT         = 'icon-default.png'

###################################################################################################

def Start():
  Plugin.AddPrefixHandler(PLUGIN_PREFIX, MainMenu, PLUGIN_TITLE, PLUGIN_ICON_DEFAULT, PLUGIN_ARTWORK)
  Plugin.AddViewGroup('_List', viewMode='List', mediaType='items')
  Plugin.AddViewGroup('_InfoList', viewMode='InfoList', mediaType='items')

  # Set the default MediaContainer attributes
  MediaContainer.title1     = PLUGIN_TITLE
  MediaContainer.viewGroup  = '_List'
  MediaContainer.art        = R(PLUGIN_ARTWORK)
  MediaContainer.userAgent  = ''

  # Set HTTP headers
  HTTP.Headers['User-agent'] = 'Mozilla/5.0 (Macintosh; U; Intel Mac OS X 10.6; en-US; rv:1.9.2.4) Gecko/20100611 Firefox/3.6.4'

###################################################################################################

def MainMenu():
#  dir = MediaContainer()
#  dir.Append(Function(DirectoryItem(RTLRecent, title='Recente uitzendingen', thumb=R(PLUGIN_ICON_DEFAULT))))
#  dir.Append(Function(DirectoryItem(RTLAllPrograms, title='Alle RTL Gemist programma\'s', thumb=R(PLUGIN_ICON_DEFAULT))))
  dir = RTLRecent(None)
  return dir

###################################################################################################

def RTLRecent(sender):
#  dir = MediaContainer(title2=sender.itemTitle)
  dir = MediaContainer()

  dir.Append(Function(DirectoryItem(RTLDay, title='Maandag', thumb=R(PLUGIN_ICON_DEFAULT)), day='1'))
  dir.Append(Function(DirectoryItem(RTLDay, title='Dinsdag', thumb=R(PLUGIN_ICON_DEFAULT)), day='2'))
  dir.Append(Function(DirectoryItem(RTLDay, title='Woensdag', thumb=R(PLUGIN_ICON_DEFAULT)), day='3'))
  dir.Append(Function(DirectoryItem(RTLDay, title='Donderdag', thumb=R(PLUGIN_ICON_DEFAULT)), day='4'))
  dir.Append(Function(DirectoryItem(RTLDay, title='Vrijdag', thumb=R(PLUGIN_ICON_DEFAULT)), day='5'))
  dir.Append(Function(DirectoryItem(RTLDay, title='Zaterdag', thumb=R(PLUGIN_ICON_DEFAULT)), day='6'))
  dir.Append(Function(DirectoryItem(RTLDay, title='Zondag', thumb=R(PLUGIN_ICON_DEFAULT)), day='7'))

  return dir

###################################################################################################

def RTLDay(sender, day):
  dir = MediaContainer(title2=sender.itemTitle, viewGroup='_InfoList')

  for item in HTML.ElementFromURL(RTL_GEMIST_IPAD + '?day=' + day, errors='ignore', cacheTime=600).xpath('/html/body//ul[@class="video_list"]/li'):
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

def RTLAllPrograms(sender):
  dir = MediaContainer(title2=sender.itemTitle)

  for title, cat, prog in AvailablePrograms():
    url = MENU_PATH % ('/' + cat + '/' + prog + DEFAULT_XML)
    dir.Append(Function(DirectoryItem(RTLProgram, title=title, thumb=R(PLUGIN_ICON_DEFAULT)), url=url))

  return dir

####################################################################################################

def RTLProgram(sender, url):
  dir = MediaContainer(title2=sender.itemTitle)

  for item in HTML.ElementFromURL(url, cacheTime=1800).xpath('//ul/li'):
    title = unicode( item.xpath('./text()')[0].strip() )

    if item.get('class') == 'folder':
      url = MENU_PATH % item.get('rel')
      dir.Append(Function(DirectoryItem(RTLProgram, title=title, thumb=R(PLUGIN_ICON_DEFAULT)), url=url))
    elif item.get('class') == 'video':
      url = item.get('rel')
      # Try to filter out non-free videos as much as possible
      drmPaidProfile = re.compile("s4m[^.]{1,}|\.rtlvideo\.").search(url)
      if drmPaidProfile == None:
        if Is404(url, CACHE_1DAY) == False:
          if item.get('thumb') != None:
            thumb = BASE_URL + item.get('thumb')
          else:
            thumb = None
          wvx = item.get('link')
          if wvx[0:4] != 'http':
            wvx = BASE_URL + wvx

          vidDate = time.gmtime( int( item.get('ctime') ) )
          vidDate = time.strftime('%d/%m/%Y', vidDate)
          dir.Append(Function(WebVideoItem(PlayVideo, title=title, infolabel=vidDate, thumb=Function(GetThumb, url=thumb)), url=url, wvx=wvx))

  if len(dir) == 0:
    dir.header = 'Geen video\'s'
    dir.message = 'Deze locatie bevat geen video\'s'

  return dir

####################################################################################################

def PlayVideo(sender, url, wvx):
  if url[0:4] != 'http':
    url = BASE_URL + url

  content = HTTP.Request(url, cacheTime=CACHE_1DAY).content
  if content != None:
    vid = re.compile("bandwidth:'(.+?)'.+?width:'(.+?)'.+?height:'(.+?)'", re.DOTALL).findall(content)

    # If multiple streams are available, check if the user wants high or low bitrate videos and get info for that one
    if len(vid) > 0:
      bandwidth = vid[0][0]
      index = 0
      for i in range( 1, len(vid) ):
        if Prefs['lowbitrate'] == False:
          if int(vid[i][0]) > int(bandwidth):
            bandwidth = vid[i][0]
            index = i
        else:
          if int(vid[i][0]) < int(bandwidth):
            bandwidth = vid[i][0]
            index = i

      wvx = wvx.replace('max.wvx', bandwidth + '.wvx')
      Log('wvx --> ' + wvx)

      # Check if the video has DRM
      # If not: use the Plexapp Silverlight player
      # If it has DRM: use the original RTL Silveright player
      #drm = re.compile("\.alleen_nl|\.s4m").search(wvx)
      drm = True # Forget the DRM check for now and use the RTL Silverlight player for all videos
      if drm == None:
        video_url = SL_PLAYER % ( String.Quote(wvx, usePlus=True), vid[index][1], vid[index][2] )
      else:
        # Find the Silverlight player (.xap)
        xap = re.compile("defaultXAPPath.+?(http://.+?\.xap)").search(content).group(1)

        # vid[index][1] is the width of the best stream available, check if video is widescreen or full frame
        if int(vid[index][1]) == 540:
          ar = 'full'
        else:
          ar = 'wide'

        # 'ar' determines which site config is used (full frame or widescreen)
        # 'xap' is the RTL Silverlight player
        # 'wvx' is used as the asx url for Silverlight
        video_url = url + '#' + ar + '||' + xap + '||' + wvx

      return Redirect(WebVideoItem(video_url))

  return None

####################################################################################################

def AvailablePrograms():
  allPrograms = []
  for program in INCLUDE_PROGRAMS:
    allPrograms.append(program)

  contains = []
  for i in range( 0, len(URL_CATEGORIES) ):
    contains.append( XPATH_PROGRAMS_CONTAINS % URL_CATEGORIES[i] )

  for program in HTML.ElementFromURL(PROGRAM_INDEX, cacheTime=CACHE_1WEEK).xpath( XPATH_PROGRAMS % ( ' or '.join(contains) )):
    path = program.get('href').split('/',5)
    if path[4] not in EXCLUDE_URLS_CONTAINING:
      url = MENU_PATH % ('/' + path[3] + '/' + path[4] + DEFAULT_XML)

      try:
        v = HTTP.Request(url, cacheTime=CACHE_1WEEK).content
        title = unicode( program.xpath('./text()')[0].strip() )
        allPrograms.append([title, path[3], path[4]])
      except:
        pass

  allPrograms.sort()
  return allPrograms

####################################################################################################

def GetImageBaseUrl():
#  content = HTTP.Request(RTL_GEMIST_HOME).content
#  baseurl = re.compile('var image_size=\'(.+)\';').search(content).group(1)
#  return baseurl + '/'
  base = 'http://data.rtl.nl/system/img//' # Temporary(?) The double slash at the end is intentionally
  return base

####################################################################################################

def GetThumb(url):
  if url != None:
    if url[0:4] != 'http':
      url = GetImageBaseUrl() + url

    try:
      thumb = HTTP.Request(url, cacheTime=CACHE_1MONTH).content
      return DataObject(thumb, 'image/jpeg')
    except:
      pass

  return Redirect(R(PLUGIN_ICON_DEFAULT))

####################################################################################################

def Is404(url, cacheTime):
  if url[0:4] != 'http':
    url = BASE_URL + url

  try:
    check = HTTP.Request(url, cacheTime=cacheTime).headers
    return False
  except:
    return True
