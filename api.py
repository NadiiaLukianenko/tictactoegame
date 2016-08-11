"""api.py - Create and configure the TicTacToe Game API exposing the resources.
"""

import endpoints
import math
from protorpc import remote, messages
from google.appengine.api import memcache
from google.appengine.api import taskqueue
from google.appengine.ext import ndb

from models import (
    User,
    Game,
    Statistic,
    Rating,
    History,
)
from models import (
    StringMessage,
    NewGameForm,
    GameForm,
    MakeMoveForm,
    StatisticForms,
    GameForms,
    RatingForms,
    RatingForm,
    HistoryForm,
)
from utils import get_by_urlsafe

NEW_GAME_REQUEST = endpoints.ResourceContainer(NewGameForm)
GET_GAME_REQUEST = endpoints.ResourceContainer(
        urlsafe_game_key=messages.StringField(1),)
MAKE_MOVE_REQUEST = endpoints.ResourceContainer(
    MakeMoveForm,
    urlsafe_game_key=messages.StringField(1),)
USER_REQUEST = endpoints.ResourceContainer(user_name=messages.StringField(1),
                                           email=messages.StringField(2))
MEMCACHE_RATING = 'RATING'


@endpoints.api(name='tictactoegame', version='v1')
class tictactoegame(remote.Service):
    """TicTacToe Game API"""
    @endpoints.method(request_message=USER_REQUEST,
                      response_message=StringMessage,
                      path='user',
                      name='create_user',
                      http_method='POST')
    def create_user(self, request):
        """Create a User. Requires a unique username"""
        if User.query(User.name == request.user_name).get():
            raise endpoints.ConflictException(
                    'A User with that name already exists!')
        user = User(name=request.user_name, email=request.email)
        user_key = user.put()
        statistic = Statistic(user=user_key, win=0, loss=0, draw=0)
        statistic.put()
        rating = Rating(user_name=request.user_name, rate=0, rank=0)
        rating.put()
        return StringMessage(message='User {} created!'.format(
                request.user_name))

    @endpoints.method(request_message=NEW_GAME_REQUEST,
                      response_message=GameForm,
                      path='game',
                      name='new_game',
                      http_method='POST')
    def new_game(self, request):
        """Creates new game"""
        user_x = User.query(User.name == request.user_name_x).get()
        user_o = User.query(User.name == request.user_name_o).get()
        if (not user_o) or (not user_x):
            raise endpoints.NotFoundException(
                    'A User with that name does not exist!')
        try:
            game = Game.new_game(user_x.key, user_o.key)
            history = History(game=game.key)
            history.put()
        except ValueError:
            raise endpoints.BadRequestException('Players should be '
                                                'different!')

        return game.to_form('Good luck playing TicTacToe!')

    @endpoints.method(request_message=GET_GAME_REQUEST,
                      response_message=GameForm,
                      path='game/{urlsafe_game_key}',
                      name='get_game',
                      http_method='GET')
    def get_game(self, request):
        """Return the current game status."""
        game = get_by_urlsafe(request.urlsafe_game_key, Game)
        if game is None:
            raise endpoints.NotFoundException('Game not found!')
        elif game.game_over:
            return game.to_form('Game is over!')
        else:
            return game.to_form('Game is running!')

    @endpoints.method(request_message=GET_GAME_REQUEST,
                      response_message=GameForm,
                      path='game/cancel/{urlsafe_game_key}',
                      name='cancel_game',
                      http_method='DELETE')
    def cancel_game(self, request):
        """Cancel the game"""
        game = get_by_urlsafe(request.urlsafe_game_key, Game)
        if game is None:
            raise endpoints.NotFoundException('Game not found!')
        elif game.game_over:
            return game.to_form('Game is over and it cannot be deleted!')
        else:
            game.key.delete()
            return game.to_form('Game is deleted successfully!')

    @endpoints.method(request_message=GET_GAME_REQUEST,
                      response_message=HistoryForm,
                      path='game/history/{urlsafe_game_key}',
                      name='get_game_history',
                      http_method='GET')
    def get_game_history(self, request):
        """Return game history."""
        game = get_by_urlsafe(request.urlsafe_game_key, Game)
        if game is None:
            raise endpoints.NotFoundException('Game not found!')
        else:
            return History.query(History.game == game.key).get().to_form()

    @endpoints.method(request_message=MAKE_MOVE_REQUEST,
                      response_message=GameForm,
                      path='game/{urlsafe_game_key}',
                      name='make_move',
                      http_method='PUT')
    def make_move(self, request):
        """Makes a move. Returns a game status with the message"""
        msg = 'Next move!'
        game = get_by_urlsafe(request.urlsafe_game_key, Game)
        history = History.query(History.game == game.key).get()
        if game.game_over:
            raise endpoints.ForbiddenException('Illegal action: '
                                               'Game is already over.')

        game_field_list = list(game.game_field)
        dim_size = int(math.sqrt(len(game_field_list)))
        i = request.i
        j = request.j

        msg = 'user is %s, and user_o is %s' % (request.user,
                                                game.user_o.get().name)
        if game_field_list[j + i * dim_size] != ' ':
            raise endpoints.ForbiddenException('Illegal action: '
                                               'the cell is already used.')

        if request.user == game.user_o.get().name:
            if game_field_list.count('x') - game_field_list.count('o') == 1:
                game_field_list[j + i * dim_size] = 'o'
                game_field_str = ''.join(game_field_list)
                msg = 'Game_field is %s' % (game_field_str,)
                game.game_field = game_field_str
                game.put()
                game = get_by_urlsafe(request.urlsafe_game_key, Game)
                # Check whether game is over and winner
                if check_winner(game_field_str, 'o', i, j):
                    game.end_game(game.user_o, game.user_x)
                    msg = 'Game is over! Winner-%s' % (game.user_o.get().name,)
                    # Task queue to update the leader
                    taskqueue.add(url='/tasks/_cache_current_leader')
                history.update_history(msg, game.user_o.get().name, i, j)
            else:
                return game.to_form('It is not your turn!')
        elif request.user == game.user_x.get().name:
            if game_field_list.count('x') - game_field_list.count('o') == 0:
                game_field_list[j + i * dim_size] = 'x'
                game_field_str = ''.join(game_field_list)
                msg = 'Game_field is %s' % (game_field_str,)
                game.game_field = game_field_str
                game.put()
                game = get_by_urlsafe(request.urlsafe_game_key, Game)
                # Check whether game is over and winner
                if check_winner(game_field_str, 'x', i, j):
                    game.end_game(game.user_x, game.user_o)
                    msg = 'Game is over! Winner-%s' % (game.user_x.get().name,)
                    # Task queue to update the leader
                    taskqueue.add(url='/tasks/_cache_current_leader')
                history.update_history(msg, game.user_x.get().name, i, j)
            else:
                raise endpoints.ForbiddenException('Illegal action: '
                                                   'It is not your turn!')

        if game.game_field.count(' ') == 0:
            game.end_game_draw(game.user_x, game.user_o)
            msg = 'Game is over! Draw game!'
            # Task queue to update the leader
            taskqueue.add(url='/tasks/_cache_current_leader')
            history.update_history(msg, '', i, j)
        return game.to_form(msg)

    @endpoints.method(request_message=USER_REQUEST,
                      response_message=GameForms,
                      path='games/user/{user_name}',
                      name='get_user_games',
                      http_method='GET')
    def get_user_games(self, request):
        """Returns all of an individual active User's games"""
        user = User.query(User.name == request.user_name).get()
        if not user:
            raise endpoints.NotFoundException(
                    'A User with that name does not exist!')
        games = Game.query(ndb.AND(Game.game_over is False,
                                   ndb.OR(Game.user_o == user.key,
                                    Game.user_x == user.key)))
        return GameForms(items=[game.to_form('') for game in games])

    @endpoints.method(response_message=StatisticForms,
                      path='statistic',
                      name='get_statistic',
                      http_method='GET')
    def get_statistic(self, request):
        """Return all statistics"""
        return StatisticForms(items=[statistic.to_form() for statistic in
                                     Statistic.query()])

    @endpoints.method(request_message=USER_REQUEST,
                      response_message=StatisticForms,
                      path='statistic/user/{user_name}',
                      name='get_user_statistic',
                      http_method='GET')
    def get_user_statistic(self, request):
        """Returns all of an individual User's statistic"""
        user = User.query(User.name == request.user_name).get()
        if not user:
            raise endpoints.NotFoundException(
                    'A User with that name does not exist!')
        statistics = Statistic.query(Statistic.user == user.key)
        return StatisticForms(items=[statistic.to_form() for statistic in
                                     statistics])

    @endpoints.method(request_message=USER_REQUEST,
                      response_message=RatingForm,
                      path='games/rating/user/{user_name}',
                      name='get_user_rate',
                      http_method='GET')
    def get_user_rate(self, request):
        """Get the users's rate"""
        user = User.query(User.name == request.user_name).get()
        if not user:
            raise endpoints.NotFoundException(
                    'A User with that name does not exist!')
        user_rate = Rating.query(Rating.user_name == request.user_name).get()
        return RatingForm(user_name=request.user_name, rate=user_rate.rate,
                          rank=user_rate.rank)

    @endpoints.method(response_message=RatingForms,
                      path='games/ranking',
                      name='get_rankings',
                      http_method='GET')
    def get_rankings(self, request):
        """Get all users rankings"""
        ratings = Rating.query().order(Rating.rank)
        return RatingForms(items=[rating.to_form() for rating in ratings])

    @staticmethod
    def _cache_current_leader():
        """Populates memcache with the current leader"""
        ratings = Rating.query(Rating.rank == 1).get()
        memcache.set(MEMCACHE_RATING, 'The leader is {} with rate={:.2f}'
                     .format(ratings.user_name, ratings.rate))

    @endpoints.method(request_message=StringMessage,
                      response_message=StringMessage,
                      path='games/leader',
                      name='get_leader',
                      http_method='GET')
    def get_leader(self, request):
        """Get the leader"""
        return StringMessage(message=memcache.get(MEMCACHE_RATING) or '')


def check_winner(game_field, symbol, i, j):
    """
    Args:
        game_field: the current status of the game
        symbol: x or o - the latest move
        i: the latest move vertical index
        j: the latest move horizontal index
    Returns: True if the game is over
    """
    dim_size = int(math.sqrt(len(game_field)))
    result_horizontal = True
    result_vertical = True
    result_diagonal = False
    result_diagonal2 = False
    # Check horizontal and vertical
    for index in range(dim_size):
        result_horizontal = result_horizontal and \
                            (game_field[i * dim_size + index] == symbol)
        result_vertical = result_vertical and \
                          (game_field[index * dim_size + j] == symbol)
    if result_horizontal or result_vertical:
        return True
    # Check diagonal1
    if i == j:
        result_diagonal = True
        for index in range(dim_size):
            result_diagonal = result_diagonal and \
                              (game_field[index + index * dim_size] == symbol)
    # Check diagonal2
    if (i + j) == dim_size - 1:
        result_diagonal2 = True
        for index in range(dim_size):
            result_diagonal2 = result_diagonal2 and \
            (game_field[(dim_size - index - 1) * dim_size + index] == symbol)
    if result_diagonal or result_diagonal2:
        return True
    return False


api = endpoints.api_server([tictactoegame])
