#
# QuoteURL - URL for Twitter Dialogues
#
# Copyright (c) 2009, Fabricio Zuardi
# All rights reserved.
#  
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions
# are met:
# 
#   * Redistributions of source code must retain the above copyright
#     notice, this list of conditions and the following disclaimer.
#   * Redistributions in binary form must reproduce the above copyright
#     notice, this list of conditions and the following disclaimer in
#     the documentation and/or other materials provided with the
#     distribution.
#   * Neither the name of the author nor the names of its contributors
#     may be used to endorse or promote products derived from this
#     software without specific prior written permission.
#  
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
__author__ = ('Fabricio Zuardi', 'fabricio@fabricio.org', 'http://fabricio.org')
__license__ = "BSD"

import os
import cgi
import wsgiref.handlers
import urllib

from google.appengine.api import users
from google.appengine.ext import db
from google.appengine.api import urlfetch
from google.appengine.api import memcache
from google.appengine.ext import webapp
from google.appengine.ext.webapp import template


#--- CONSTANTS ---
MAX_QUOTE_SIZE_SIGNED_OUT = 4
MAX_QUOTE_SIZE_SIGNED_IN  = 10
LOADED_TWEET_CACHE_TIME   = 60*60 # one hour


#--- MODELS ---
class TwitterUser(db.Model):
  description       = db.StringProperty()
  followers_count   = db.IntegerProperty()
  user_id           = db.StringProperty()
  numericuser_id    = db.IntegerProperty()
  location          = db.StringProperty()
  name              = db.StringProperty()
  profile_image_url = db.LinkProperty()
  protected         = db.BooleanProperty()
  screen_name       = db.StringProperty()
  url               = db.LinkProperty()
  json              = db.TextProperty()

class Tweet(db.Model):
  tweet_id                      = db.StringProperty()
  numeric_tweet_id              = db.IntegerProperty()
  created_at                    = db.DateTimeProperty()
  favorited                     = db.BooleanProperty()
  in_reply_to_screen_name       = db.StringProperty()
  in_reply_to_status_id         = db.StringProperty()
  numeric_in_reply_to_status_id = db.IntegerProperty()
  in_reply_to_user_id           = db.StringProperty()
  source                        = db.StringProperty()
  text                          = db.StringProperty()
  truncated                     = db.BooleanProperty()
  user                          = db.ReferenceProperty(TwitterUser)
  imported_date                 = db.DateTimeProperty(auto_now_add=True)
  json                          = db.TextProperty()

class Dialogue(db.Model):
  title             = db.StringProperty()
  status_id_list    = db.StringListProperty()
  authors           = db.StringProperty()
  author_list       = db.StringListProperty()
  quoted_by         = db.UserProperty()
  quoter_ip         = db.StringProperty()
  quoter_user_agent = db.StringProperty()
  alias             = db.StringProperty()
  created_date      = db.DateTimeProperty(auto_now_add=True)
  json              = db.TextProperty()


#--- HELPERS ---
class AccessHelper():
  def isProUser(User):
    return False


#--- ENTRYPOINTS ---

class MainPage(webapp.RequestHandler):
  def get(self):
    user = users.get_current_user()
    if not user:
      msg_help1 = 'Anonymous users can add up to <em id="quote-size-limit">'+str(MAX_QUOTE_SIZE_SIGNED_OUT)+'</em> Tweets per quote, <a href="/a/login">Sign-in</a> if you need more'
    else:
      msg_help1 = 'You can add up to <em id="quote-size-limit">'+str(MAX_QUOTE_SIZE_SIGNED_IN)+'</em> Tweets per quote. If you need more visit the <a href="/a/upgrade">upgrade membership</a> page.'
    
    template_values = {
      'msg_help1' : msg_help1
    }
    path = os.path.join(os.path.dirname(__file__), 'templates/index.html')
    self.response.out.write(template.render(path, template_values))

class LoadTweet(webapp.RequestHandler):
  def get(self):
    tweet_id    = cgi.escape(self.request.get('id'))
    fmt         = cgi.escape(self.request.get('fmt'))
    url         = 'http://twitter.com/statuses/show/'+ tweet_id +'.json'
    key         = 'tweet_'+ tweet_id +'.json'
    tweet_json  = memcache.get(key)
    if tweet_json is not None:
      self.response.out.write(tweet_json)
      return True
    else:
      result = urlfetch.fetch(url)
      if result.status_code == 200:
        self.response.out.write(result.content)
        memcache.add(key, result.content, LOADED_TWEET_CACHE_TIME)
        return True
      else:
        self.response.set_status(result.status_code)
        self.response.out.write(result.content)
        return False

class CreateQuote(webapp.RequestHandler):
  def post(self):
    status_list   = cgi.escape(self.request.get('statuses')).replace(',',' ').split()
    authors_list  = cgi.escape(self.request.get('authors')).replace(',',' ').split()
    json          = cgi.escape(self.request.get('json'))
    user          = users.get_current_user()
    ip            = os.environ['REMOTE_ADDR']
    ua            = os.environ['HTTP_USER_AGENT']
    dialogue = Dialogue()
    dialogue.title = ' '.join(status_list)
    dialogue.status_id_list = status_list
    dialogue.quoter = user
    dialogue.quoter_ip = ip
    dialogue.quoter_user_agent = ua
    dialogue.alias = None
    dialogue.authors = ' '.join(authors_list)
    dialogue.author_list = authors_list
    dialogue.json = json
    template_values = {
      'dialogue'    : dialogue
    }
    path = os.path.join(os.path.dirname(__file__), 'templates/show.html')
    # self.response.out.write(template.render(path, template_values))
    
class SignIn(webapp.RequestHandler):
  def get(self):
    user = users.get_current_user()
    self.redirect(users.create_login_url('/'))
    
class UpgradeMembership(webapp.RequestHandler):
  def get(self):
    template_values = {}
    path = os.path.join(os.path.dirname(__file__), 'templates/upgrade.html')
    self.response.out.write(template.render(path, template_values))


#--- MAPPINGS ---
def main():
  application = webapp.WSGIApplication(
  [
    ('/', MainPage),
    ('/a/login', SignIn),
    ('/a/upgrade', UpgradeMembership),
    ('/a/loadtweet', LoadTweet),
    ('/a/create', CreateQuote)
  ], debug=True)
  wsgiref.handlers.CGIHandler().run(application)

if __name__ == "__main__":
  main()