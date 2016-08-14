"""models.py - This file contains the class definitions for the Datastore"""

from protorpc import messages
from google.appengine.ext import ndb


class User(ndb.Model):
    """User profile"""
    name = ndb.StringProperty(required=True)
    email = ndb.StringProperty()
    win = ndb.IntegerProperty(default=0)
    loss = ndb.IntegerProperty(default=0)
    draw = ndb.IntegerProperty(default=0)
    rank = ndb.IntegerProperty()
    rate = ndb.ComputedProperty(lambda self:
                                2 * self.win + self.draw - self.loss)

    def user_to_form(self):
        form = UserForm()
        form.name = self.name
        form.email = self.email
        return form

    def statistic_to_form(self):
        form = StatisticForm()
        form.name = self.name
        form.win = self.win
        form.loss = self.loss
        form.draw = self.draw
        return form

    def rate_to_form(self):
        form = RatingForm()
        form.name = self.name
        form.rate = self.rate
        form.rank = self.rank
        return form


class Game(ndb.Model):
    """Game object"""
    game_over = ndb.BooleanProperty(required=True, default=False)
    game_field = ndb.StringProperty(required=True, default="         ")
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
                    user_o=user_o
                    )
        game.put()
        return game

    def to_form(self, message):
        """Returns a GameForm representation of the Game
        Args:
            message: returns current state
        """
        form = GameForm()
        form.urlsafe_key = self.key.urlsafe()
        form.user_name_x = self.user_x.get().name
        form.user_name_o = self.user_o.get().name
        form.game_over = self.game_over
        form.date = self.date.strftime("%Y-%m-%d %H:%M:%S")
        form.message = message
        return form

    def end_game(self, user_winner, user_loser):
        """Ends the game - win/loss
        Args:
            user_winner: winner of the game
            user_loser: loser of the game
        """
        self.game_over = True
        self.put()
        update_statistic(user_winner, user_loser)

    def end_game_draw(self, user1, user2):
        """Ends the game - draw
        Args:
            user1, user2: players of the game
            """
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
        """ Updates history of the game
        Args:
            msg: game state
            player: current player
            i, j: coordinates of cell in grid
        Returns:
        """
        self.moves.append(
            {'Game state': msg, 'Player': player, 'Move': '%d %d' % (i,j)})
        self.put()


def update_statistic(user_winner, user_loser):
    """
    update_statistic:
        Args:
        user_winner: who won
        user_loser: who lost
    """
    winner = User.query(User.name == user_winner.get().name).get()
    winner.win += 1
    winner.put()
    loser = User.query(User.name == user_loser.get().name).get()
    loser.loss += 1
    loser.put()
    update_rating()


def update_statistic_draw(user1, user2):
    """
    update_statistic_draw:
    Args:
        user1, user2 - draw game
    """
    user = User.query(User.name == user1.get().name).get()
    user.draw += 1
    user.put()
    user = User.query(User.name == user2.get().name).get()
    user.draw += 1
    user.put()
    update_rating()


def update_rating():
    """ update_rating: recalculate rating and ranks for users"""
    rank = 1
    users = User.query().order(-User.rate)
    for user in users:
        user.rank = rank
        user.put()
        rank += 1


class GameForm(messages.Message):
    """GameForm for outbound game state information"""
    urlsafe_key = messages.StringField(1, required=True)
    game_over = messages.BooleanField(3, required=True)
    message = messages.StringField(4, required=True)
    user_name_x = messages.StringField(5, required=True)
    user_name_o = messages.StringField(6, required=True)
    date = messages.StringField(7, required=True)


class GameForms(messages.Message):
    """GameForms for multiple GameForm"""
    items = messages.MessageField(GameForm, 1, repeated=True)


class NewGameForm(messages.Message):
    """Used to create a new game"""
    user_name_x = messages.StringField(1, required=True)
    user_name_o = messages.StringField(2, required=True)


class UserForm(messages.Message):
    """UserForm for outbound user data"""
    name = messages.StringField(1)
    email = messages.StringField(2)
    win = messages.IntegerField(3)
    loss = messages.IntegerField(4)
    draw = messages.IntegerField(5)


class UserForms(messages.Message):
    """Return multiple UserForm"""
    items = messages.MessageField(UserForm, 1, repeated=True)


class MakeMoveForm(messages.Message):
    """Used to make a move in an existing game"""
    i = messages.IntegerField(1, required=True)
    j = messages.IntegerField(2, required=True)
    user = messages.StringField(3, required=True)


class StatisticForm(messages.Message):
    """StatisticForm for outbound statistic information"""
    name = messages.StringField(1, required=True)
    win = messages.IntegerField(2)
    loss = messages.IntegerField(3)
    draw = messages.IntegerField(4)


class StatisticForms(messages.Message):
    """Return multiple StatisticForm"""
    items = messages.MessageField(StatisticForm, 1, repeated=True)


class RatingForm(messages.Message):
    """RatingForm for rating users"""
    name = messages.StringField(1, required=True)
    rate = messages.IntegerField(2)
    rank = messages.IntegerField(3)


class RatingForms(messages.Message):
    """Return multiple RatingForms"""
    items = messages.MessageField(RatingForm, 1, repeated=True)


class HistoryForm(messages.Message):
    """Return history of the game"""
    moves = messages.StringField(1)


class StringMessage(messages.Message):
    """StringMessage -- outbound (single) string message"""
    message = messages.StringField(1, required=True)
