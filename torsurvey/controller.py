#!/usr/bin/env python
"""
  cexbot.cexapi
"""

import sys
import os
import tempfile
import logging
from urlparse import urlparse
from urllib import urlencode
from BeautifulSoup import BeautifulSoup as bs
import re

class TorController(object):

  def __init__(self, ap, db):
    self.ap = ap
    self.db = db
    pass

  def write_cache(self, url, content):
    tmp_file = self.get_temp_path(url)
    print "temporary file at %s" % tmp_file
    with open(tmp_file, 'w') as fh:
      fh.write(content.encode('utf-8'))
      print "Wrote %s to %s" % (len(content), os.path.abspath(fh.name))

  def get_temp_filename(self, url):
    u = urlparse(url)
    if not hasattr(u, 'netloc'):
      logging.error("could not parse URL %s" % url)
      return False
    prefix = "%s_%s_%s" % ("torsurvey", u.netloc, u.path.replace('/', '_'))
    if u.query:
      prefix = "%s_%s" % (prefix, u.query.replace("=", "-").replace("&", ''))
    return prefix

  def get_temp_path(self, url):
    temp_dir = os.path.realpath(os.path.join(os.path.realpath('.'), 'cache'))
    if not os.path.isdir(temp_dir):
      os.mkdir(temp_dir)
    return os.path.join(temp_dir, self.get_temp_filename(url))

  def fetch_sitelist(self, url=None, cache=False):
    cache_path = self.get_temp_path(url)
    if os.path.isfile(cache_path) and cache:
      with open(cache_path, 'r') as fh:
        content = fh.read()
    else:
      r = self.ap.req(url)
      if r == False:
        return False
      content = r.text
      self.write_cache(url, content)
    print "Got length: %d" % (int(len(content)))
    return self.parse_content_for_urls(content)

  def read_sitelist(self, filepath):
    if not os.path.isfile(filepath):
      logging.error("Invalid file path: %s" % filepath)
    with open(filepath, 'r') as fh:
      content = fh.read()
    return self.parse_content_for_urls(content)

  def parse_content_for_urls(self, content):
    urls = re.findall(r'([a-z0-9]{16}\.onion)', content)
    urls = list(set(urls))
    urls_num = int(len(urls))
    print "Found %d urls" % urls_num
    inserted = 0
    for u in urls:
      r = self.db.insert_site(u)
      if r:
        inserted = inserted + 1
        print "Added %s" % u
    print "Inserted %d" % inserted

  def get_description(self, content):
    s = bs(content)

    desc = s.find('meta', attrs={'name': 'description'})

    if desc and 'content' in desc:
      return desc['content']

    return ""

  def get_title(self, content):
    s = bs(content)

    og_site_name = s.find('meta', property="og:site_name")
    og_title = s.find('meta', property="og:title")
    meta_appname = s.find('meta', attrs={'name': 'application-name'})
    site_title = s.title

    if og_site_name and hasattr(og_site_name, 'content'):
      return og_site_name['content']

    if og_title and hasattr(og_title, 'content'):
      return og_title['content']

    if meta_appname and hasattr(meta_appname, 'content'):
      return meta_appname['content']

    if site_title and hasattr(site_title, 'string'):
      return site_title.string

    return ""

  def survey(self):
    for sid, host in self.db.get_all():
      url = "http://%s" % host
      r = self.ap.req(url)
      title = self.get_title(r.text)
      description = self.get_description(r.text)
      print "%s - %s - %s - %s" % (host, r.status_code, len(r.text), title)
      self.db.update_site(sid, r.status_code, title, r.text, description)


