#!/usr/bin/env python

"""main.py - This file contains handlers that are called by taskqueue and/or
cronjobs."""

import webapp2
from google.appengine.api import mail, app_identity
from api import tictactoegame
from models import Game
from google.appengine.ext import ndb
from models import User


class SendReminderEmail(webapp2.RequestHandler):
    def get(self):
        """Send a reminder email to each User with an email about games.
         Called every day using a cron job"""
        app_id = app_identity.get_application_id()
        subject = 'This is a reminder!'
        users = User.query(User.email != None)
        for user in users:
            active_games = Game.query(Game.game_over == False).\
            filter(ndb.OR(Game.user_x == user.key, Game.user_o == user.key))\
                .count()
            if active_games != 0:
                body = 'Hello {}, you have incomplete game!'.format(user.name)
                # This will send test emails, the arguments to send_mail are:
                # from, to, subject, body
                mail.send_mail('noreply@{}.appspotmail.com'.format(app_id),
                               user.email, subject, body)


class UpdateCurrentLeader(webapp2.RequestHandler):
    def post(self):
        """Update game announcement in memcache."""
        tictactoegame._cache_current_leader()
        self.response.set_status(204)


app = webapp2.WSGIApplication([
    ('/crons/send_reminder', SendReminderEmail),
    ('/tasks/_cache_current_leader', UpdateCurrentLeader),], debug=True)
