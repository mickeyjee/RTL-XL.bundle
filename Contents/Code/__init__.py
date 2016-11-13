# -*- coding: utf-8 -*-
TITLE = 'RTL XL'
XL_URL = 'http://www.rtlxl.nl/#!/u/%s'
FEED_URL = 'http://www.rtl.nl/system/s4m/ipadfd/d=a2t/fmt=progressive/ak=%s/'

###################################################################################################
def Start():

	ObjectContainer.title1 = TITLE
	HTTP.CacheTime = CACHE_1HOUR
	HTTP.Headers['User-Agent'] = 'RTL%20XL/2.1 CFNetwork/609.1.4 Darwin/13.0.0'

###################################################################################################
@handler('/video/rtlxl', TITLE)
def MainMenu():

	oc = ObjectContainer()

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

	oc = ObjectContainer(title2=letter)
	series = XML.ElementFromURL(FEED_URL.rsplit('/ak')[0]).xpath('//serienaam/text()[starts-with(., "%s") or starts-with(., "%s")]/../..' % (letter, letter.lower()))

	for s in series:
		title = s.xpath('./serienaam/text()')[0]
		serieskey = s.xpath('./serieskey/text()')[0]
		thumb = s.xpath('./seriescoverurl/text()')[0].split(',')[0]

		oc.add(DirectoryObject(
			key = Callback(Episodes, serieskey=serieskey, title=title),
			title = title,
			thumb = Resource.ContentsOfURLWithFallback(thumb)
		))

	oc.objects.sort(key=lambda obj: obj.title)
	return oc

###################################################################################################
@route('/video/rtlxl/episodes/{serieskey}')
def Episodes(serieskey, title):

	oc = ObjectContainer(title2=title)
	video = {}

	for item in XML.ElementFromURL(FEED_URL % serieskey).xpath('//item/classname[text()="uitzending"]/parent::item'):
		url = XL_URL % item.xpath('./id/text()')[0]
		title = item.xpath('./title/text()')[0]
		summary = item.xpath('./samenvattinglang/text()')[0].split(' Voor meer nieuws')[0]
		summary = item.xpath('./samenvattingkort/text()')[0].split(' Voor meer nieuws')[0] if summary == "" else summary
		thumb = item.xpath('./thumbnail/text()')[0]
		date = item.xpath('./broadcastdatetime/text()')[0]
		date = Datetime.ParseDate(date)
		timestamp = Datetime.TimestampFromDatetime(date)

		video[timestamp] = {'url': url, 'title': title, 'summary': summary, 'thumb': thumb, 'date': date}

	for key in sorted(video.iterkeys(), reverse=True):
		oc.add(VideoClipObject(
			url = video[key]['url'],
			title = video[key]['title'],
			summary = video[key]['summary'],
			thumb = Resource.ContentsOfURLWithFallback(video[key]['thumb']),
			originally_available_at = video[key]['date']
		))

	if len(oc) < 1:
		return ObjectContainer(header='Geen afleveringen', message='Deze serie bevat geen afleveringen')

	return oc
