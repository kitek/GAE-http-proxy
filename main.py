#!/usr/bin/env python

from google.appengine.api import memcache
from google.appengine.api import urlfetch
from google.appengine.ext import webapp
from google.appengine.ext.webapp import util
from google.appengine.runtime import apiproxy_errors
import hashlib
import logging


###################################################

DEBUG = False
MAX_CONTENT_SIZE = 10 ** 6
EXPIRATION_DELTA_SECONDS = 3600
HTTP_PREFIX = "http://YOUR_BASE_URL_TO_PROXY/"

IGNORE_HEADERS = frozenset([
  'set-cookie',
  'expires',
  'cache-control',
  'x-robots-tag',

  # Ignore hop-by-hop headers
  'connection',
  'keep-alive',
  'proxy-authenticate',
  'proxy-authorization',
  'te',
  'trailers',
  'transfer-encoding',
  'upgrade',
])

TRANSFORMED_CONTENT_TYPES = frozenset([
  "text/html",
  "text/css",
])

###################################################

def get_url_key_name(url):
	url_hash = hashlib.sha256()
	url_hash.update(url)
	return "hash_" + url_hash.hexdigest()

class BaseHandler(webapp.RequestHandler):
	def get_relative_url(self):
		slash = self.request.url.find("/", len(self.request.scheme + "://"))
		if slash == -1:
			return "/"
		return self.request.url[slash:]

class MirroredContent(object):
	def __init__(self, original_address, translated_address,
				 status, headers, data, base_url):
		self.original_address = original_address
		self.translated_address = translated_address
		self.status = status
		self.headers = headers
		self.data = data
		self.base_url = base_url

	@staticmethod
	def get_by_key_name(key_name):
		return memcache.get(key_name)

	@staticmethod
	def fetch_and_store(key_name, base_url, translated_address, mirrored_url):
		logging.debug("Fetching '%s'", mirrored_url)
		try:
			response = urlfetch.fetch(mirrored_url)
		except (urlfetch.Error, apiproxy_errors.Error):
			logging.exception("Could not fetch URL")
			return None

		adjusted_headers = {}
		for key, value in response.headers.iteritems():
			adjusted_key = key.lower()
			if adjusted_key not in IGNORE_HEADERS:
				adjusted_headers[adjusted_key] = value

		if response.status_code == 404:
			logging.exception("Could not fetch URL 404")
			return None

		content = response.content

		if len(content) > MAX_CONTENT_SIZE:
			logging.warning('Content is over 1MB; truncating')
			content = content[:MAX_CONTENT_SIZE]

		new_content = MirroredContent(
									  base_url=base_url,
									  original_address=mirrored_url,
									  translated_address=translated_address,
									  status=response.status_code,
									  headers=adjusted_headers,
									  data=content)
		if not memcache.add(key_name, new_content, time=EXPIRATION_DELTA_SECONDS):
			logging.error('memcache.add failed: key_name = "%s", '
						  'original_url = "%s"', key_name, mirrored_url)

		return new_content


class MainHandler(BaseHandler):
	def get(self, base_url):
		if base_url == '':
			logging.exception("Could not fetch URL: No base URL")
			return self.error(404)
		assert base_url
		logging.debug('User-Agent = "%s", Referrer = "%s"', self.request.user_agent, self.request.referer)
		logging.debug('Base_url = "%s", url = "%s"', base_url, self.request.url)
		translated_address = self.get_relative_url()[1:]
		mirrored_url = HTTP_PREFIX + translated_address
		key_name = get_url_key_name(mirrored_url)
		logging.info("Handling request for '%s' = '%s'", mirrored_url, key_name)
		content = MirroredContent.get_by_key_name(key_name)

		cache_miss = False
		if content is None:
			logging.debug("Cache miss")
			cache_miss = True
			content = MirroredContent.fetch_and_store(key_name, base_url, translated_address, mirrored_url)
		
		if content is None:
			return self.error(404)

		for key, value in content.headers.iteritems():
			self.response.headers[key] = value

		if not DEBUG:
			self.response.headers['cache-control'] = 'max-age=%d' % EXPIRATION_DELTA_SECONDS
		self.response.out.write(content.data)

def main():
	application = webapp.WSGIApplication([('/(.*)', MainHandler)], debug=DEBUG)
	util.run_wsgi_app(application)

if __name__ == '__main__':
	main()
