"""models.py - This file contains the class definitions for the Datastore"""

from protorpc import messages
from google.appengine.ext import ndb
import json


class User(ndb.Model):
    """User profile"""
    name = ndb.StringProperty(required=True)
    email = ndb.StringProperty()


class Game(ndb.Model):
    """Game object"""
    game_over = ndb.BooleanProperty(required=True, default=False)
    game_field = ndb.StringProperty(required=True)
    user_x = ndb.KeyProperty(required=True, kind='User')
    user_o = ndb.KeyProperty(required=True, kind='User')
    date = ndb.DateTimeProperty(auto_now_add=True)

    @classmethod
    def new_game(cls, user_x, user_o):
        """Creates and returns a new game
        Args:
            user_x: user who plays X
            user_o: user who plays O
        """
        if user_x == user_o:
            raise ValueError('Players should be different')
        game = Game(user_x=user_x,
                    user_o=user_o,
                    game_field="         ",
                    game_over=False)
        game.put()
        return game

    def to_form(self, message):
        """Returns a GameForm representation of the Game"""
        form = GameForm()
        form.urlsafe_key = self.key.urlsafe()
        form.user_name_x = self.user_x.get().name
        form.user_name_o = self.user_o.get().name
        form.game_over = self.game_over
        form.date = self.date.strftime("%Y-%m-%d %H:%M:%S")
        form.message = message
        return form

    def end_game(self, user_winner, user_loser):
        """Ends the game - win/loss"""
        self.game_over = True
        self.put()
        update_statistic(user_winner, user_loser)

    def end_game_draw(self, user1, user2):
        """Ends the game - draw"""
        self.game_over = True
        self.put()
        update_statistic_draw(user1, user2)


class History(ndb.Model):
    """ History object - saves all moves for each game  """
    game = ndb.KeyProperty(required=True, kind='Game')
    moves = ndb.JsonProperty(repeated=True)

    def to_form(self):
        form = HistoryForm()
        form.moves = str(self.moves)
        return form

    def update_history(self, msg, player, i, j):
        self.moves.append(
            {'Game status': msg, 'Player': player, 'Move': '%d %d' % (i,j)})
        self.put()


class Statistic(ndb.Model):
    """Statistic object"""
    user = ndb.KeyProperty(required=True, kind='User')
    win = ndb.IntegerProperty(default=0)
    loss = ndb.IntegerProperty(default=0)
    draw = ndb.IntegerProperty(default=0)

    def to_form(self):
        form = StatisticForm()
        form.user_name = self.user.get().name
        form.win = self.win
        form.loss = self.loss
        form.draw = self.draw
        return form


class Rating(ndb.Model):
    """Rating object"""
    user_name = ndb.StringProperty(required=True)
    rate = ndb.IntegerProperty()
    rank = ndb.IntegerProperty()

    def to_form(self):
        form = RatingForm()
        form.user_name = self.user_name
        form.rate = self.rate
        form.rank = self.rank
        return form


def update_statistic(user_winner, user_loser):
    """
    update_statistic:
        Args:
        user_winner: who won
        user_loser: who lost
    """
    statistic_winner = Statistic.query(Statistic.user == user_winner).get()
    statistic_winner.win += 1
    statistic_winner.put()
    statistic_loser = Statistic.query(Statistic.user == user_loser).get()
    statistic_loser.loss += 1
    statistic_loser.put()
    update_rating()


def update_statistic_draw(user1, user2):
    """
    update_statistic_draw:
    Args:
        user1, user2 - draw game
    """
    statistic1 = Statistic.query(Statistic.user == user1).get()
    statistic1.draw += 1
    statistic1.put()
    statistic2 = Statistic.query(Statistic.user == user2).get()
    statistic2.draw += 1
    statistic2.put()
    update_rating()


def update_rating():
    """
        update_rating: recalculate rating and ranks for users
    """
    rankings = []
    dictionary = {}
    users = User.query().fetch()
    for user in users:
        statistics = Statistic.query(Statistic.user == user.key).get()
        rate = calculate_rate(statistics.win, statistics.draw,
                              statistics.loss)
        rankings.append((user.name, rate))
    rankings.sort(key=lambda tup: tup[1], reverse=True)
    rankings = list(enumerate(rankings, start=1))
    for ranking in rankings:
        dictionary[str(ranking[1][0])] = (ranking[1][1],
                                          int(ranking[0]))

    for name in dictionary.keys():
        rating = Rating.query(Rating.user_name == name).get()
        rating.rate = dictionary[name][0]
        rating.rank = dictionary[name][1]
        rating.put()


def calculate_rate(win, draw, loss):
    """
    Args:
        win: qty of wins
        draw: qty of draws
        loss: qty of losses
    Returns: Rate base on the qty win, draw, loss
    """
    return 2 * win + draw - loss


class GameForm(messages.Message):
    """GameForm for outbound game state information"""
    urlsafe_key = messages.StringField(1, required=True)
    game_over = messages.BooleanField(3, required=True)
    message = messages.StringField(4, required=True)
    user_name_x = messages.StringField(5, required=True)
    user_name_o = messages.StringField(6, required=True)
    date = messages.StringField(7, required=True)


class GameForms(messages.Message):
    """Return multiple GameForms"""
    items = messages.MessageField(GameForm, 1, repeated=True)


class NewGameForm(messages.Message):
    """Used to create a new game"""
    user_name_x = messages.StringField(1, required=True)
    user_name_o = messages.StringField(2, required=True)


class MakeMoveForm(messages.Message):
    """Used to make a move in an existing game"""
    i = messages.IntegerField(1, required=True)
    j = messages.IntegerField(2, required=True)
    user = messages.StringField(3, required=True)


class StatisticForm(messages.Message):
    """StatisticForm for outbound statistic information"""
    user_name = messages.StringField(1, required=True)
    win = messages.IntegerField(2)
    loss = messages.IntegerField(3)
    draw = messages.IntegerField(4)


class StatisticForms(messages.Message):
    """Return multiple StatisticForms"""
    items = messages.MessageField(StatisticForm, 1, repeated=True)


class RatingForm(messages.Message):
    """RatingForm for rating users"""
    user_name = messages.StringField(1, required=True)
    rate = messages.IntegerField(2)
    rank = messages.IntegerField(3)


class RatingForms(messages.Message):
    """Return multiple RatingForms"""
    items = messages.MessageField(RatingForm, 1, repeated=True)


class HistoryForm(messages.Message):
    """ Return history of game """
    moves = messages.StringField(1)


class StringMessage(messages.Message):
    """StringMessage-- outbound (single) string message"""
    message = messages.StringField(1, required=True)
