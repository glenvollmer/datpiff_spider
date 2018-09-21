import os
import pickle
import re
import requests
import scrapy
import string

class DatpiffSpider(scrapy.Spider):
    name = "datpiff"

    custom_settings = {
        'CONCURRENT_REQUESTS': 1,
        'USER_AGENT': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.10; rv:44.0) Gecko/20100101 Firefox/44.0',
        'TELNETCONSOLE_ENABLED': False,
        'ROBOTSTXT_OBEY': False
        }
    
    page_count = 0
    base_url = 'http://www.datpiff.com'
    cont_crawling = True
    

    # change this to where you would like to save all the mixtapes. make sure you have enough room!! it will be a lot.
    save_directory = '../../../../../../../Volumes/UNTITLED/datpiff_saves'
    
    def start_requests(self):
        while self.cont_crawling:
            yield scrapy.Request(
                    url=self.base_url + '/mixtapes.php?filter=all&p=' + str(self.page_count),
                    callback=self.get_mixtape_page)
            self.page_count += 1

    def get_mixtape_page(self, response):
        mixtapes = response.css('div.contentListing > div.contentItem')
        if len(mixtapes) == 0:
            self.cont_crawling = False
        else:
            for m in mixtapes:
                mixtape_url = m.css('div.contentThumb > a[href$=".html"]::attr(href)').extract()
                if not len(mixtape_url) == 0:
                    yield scrapy.Request(
                        url=self.base_url + mixtape_url[0],
                        callback=self.get_player,
                        dont_filter=True)
                
    def get_player(self, response):
        html_token = response.css('div[onclick*="openMixtape"]::attr(onclick)').extract()
        if len(html_token) > 0:
            token = re.findall(r'\s*\'(.*)\'', html_token[0])[0]
            
            yield scrapy.Request(
                url=self.base_url + '/player/' + token,
                callback=self.get_embed,
                dont_filter=True)

    def get_embed(self, response):
        embed_url = response.css('iframe::attr(src)').extract()

        yield scrapy.Request(
            url=embed_url[0],
            callback=self.get_mp3_links,
            dont_filter=True)

    def get_mp3_links(self, response):
        script = response.css('script[src="/js/player.js"]:first-of-type + script').extract()

        url_track_prefix = re.findall(r'\s*var trackPrefix = \'(.*?)\';', script[0])
        track_objs = re.findall(r'\s*playerData\.tracks\.push\((.*?)\);', script[0])
        mixtape_title = re.findall(r'\s*\"title\":\"(.*?)\"', script[0])[0].replace('\'', '')
        artist_name = re.findall(r'\s*\"artist\":\"(.*?)\"', script[0])[0].replace('\'', '')

        for t in track_objs:
            url_track =  re.findall(r'\s*concat\((.*?)\),', t)[0].strip().replace('\'', '')

            yield scrapy.Request(
                url=url_track_prefix[0] + url_track,
                callback=self.download_track,
                dont_filter=True,
                meta={
                    'mixtape_title': mixtape_title,
                    'artist_name': artist_name,
                    'url_track': url_track
                    })

    def download_track(self, response):
        for i in string.punctuation:
            clean_mix_title = response.meta['mixtape_title'].replace(i, '')

        mixtape_dir = self.save_directory + '/' + response.meta['artist_name'] + ' - ' + clean_mix_title
        file_path = mixtape_dir + '/' + response.meta['url_track']

        if not os.path.isdir(mixtape_dir):
            os.mkdir(mixtape_dir)

        with open(file_path, 'wb') as f:
            f.write(response.body)
            f.flush()
            os.fsync(f.fileno())
    