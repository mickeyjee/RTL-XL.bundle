# -*- coding: utf-8 -*-
TITLE = 'RTL XL'
ART = 'art-default.jpg'
ICON = 'icon-default.png'
XL_URL = 'http://www.rtl.nl/xl/#/u/%s'
FEED_URL = '/s%=ka/evitpada=tmf/dapi=d/dfdapi/m4s/metsys/ln.ltr.www//:ptth'[::-1]

###################################################################################################
def Start():

	Plugin.AddViewGroup('List', viewMode='List', mediaType='items')
	Plugin.AddViewGroup('InfoList', viewMode='InfoList', mediaType='items')

	ObjectContainer.art = R(ART)
	ObjectContainer.title1 = TITLE
	DirectoryObject.thumb = R(ICON)

	HTTP.CacheTime = CACHE_1HOUR
	HTTP.Headers['User-Agent'] = 'Mozilla/5.0 (iPad; CPU OS 6_0_1 like Mac OS X) AppleWebKit/536.26 (KHTML, like Gecko) Version/6.0 Mobile/10A523 Safari/8536.25'

###################################################################################################
@handler('/video/rtlxl', TITLE, thumb=ICON, art=ART)
def MainMenu():

	oc = ObjectContainer(view_group='List')
	series = XML.ElementFromURL(FEED_URL.rsplit('/ak')[0]).xpath('//serienaam/text()')
	letters = list(set([s.strip()[0].upper() for s in series]))
	letters.sort()

	for letter in letters:
		oc.add(DirectoryObject(
			key = Callback(Series, letter=letter),
			title = letter
		))

	return oc

###################################################################################################
@route('/video/rtlxl/series/{letter}')
def Series(letter):

	oc = ObjectContainer(title2=letter, view_group='List')
	series = XML.ElementFromURL(FEED_URL.rsplit('/ak')[0]).xpath('//serienaam/text()[starts-with(., "%s") or starts-with(., "%s")]/../..' % (letter, letter.lower()))

	for s in series:
		title = s.xpath('./serienaam/text()')[0]
		serieskey = s.xpath('./serieskey/text()')[0]
		thumb = s.xpath('./seriescoverurl/text()')[0].split(',')[0]

		oc.add(DirectoryObject(
			key = Callback(Episodes, serieskey=serieskey, title=title),
			title = title,
			thumb = Resource.ContentsOfURLWithFallback(thumb, fallback='icon-default.png')
		))

	oc.objects.sort(key=lambda obj: obj.title)
	return oc

###################################################################################################
@route('/video/rtlxl/episodes/{serieskey}')
def Episodes(serieskey, title):

	oc = ObjectContainer(title2=title, view_group='InfoList')
	result = {}

	@parallelize
	def GetEpisodes():

		try:
			episodes = XML.ElementFromURL(FEED_URL % serieskey).xpath('//item/classname[text()="uitzending"]/../contentid/text()')[:15]
		except:
			episodes = []

		for num in range(len(episodes)):
			episode = episodes[num]

			@task
			def GetEpisode(num=num, result=result, episode=episode):

				try:
					result[num] = URLService.MetadataObjectForURL(XL_URL % episode)
				except:
					pass

	if len(result) < 1:
		return ObjectContainer(header='Geen afleveringen', message='Deze serie bevat geen afleveringen')

	for key in result:
		oc.add(result[key])

	oc.objects.sort(key=lambda obj: obj.originally_available_at, reverse=True)
	return oc
