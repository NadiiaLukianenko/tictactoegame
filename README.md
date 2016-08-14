# TicTacToe Game

## Game Description:
- Tic-tac-toe (also known as Noughts and crosses or Xs and Os) is a game 
 for two players, X and O, who take turns marking the spaces in a 3×3 grid. 
 The player who succeeds in placing three of their marks in a horizontal, 
 vertical, or diagonal row wins the game:
- Create new user, using the `create_user` endpoint
- Use `create_game` to create a game. Copy the `urlsafe_key` property for 
later use. Each game can be retrieved or played by using the path parameter 
`urlsafe_game_key`.
- X-Player starts game with the `make_move` endpoint by setting 
(i, j) - coordinates of marked space in grid.
- O-Player continues game with the `make_move` endpoint and selects free 
space in grid.
- After each move the proper vertical, horizontal and diagonal lines are 
evaluated and the `make_move` reply contains message either 'Game field is ...'
 or 'Game is over. Winner-..' or  or 'Game is over! Draw game!'
- For each player the quantity of wins, losses and draws are saved. The values
  can be retrieved by the `get_user_statistic` endpoint for all users or by the 
   `get_user_statistic` for specified user. They updated after game is over for 
  proper players. 
- The rating is calculated base on formula 2 * wins + draws - losses:
   2 points for each win, 1 point for each draw and -1 point for each loss.


## Files Included:
 - api.py: Contains endpoints and game playing logic
 - app.yaml: App configuration
 - cron.yaml: Cronjob configuration
 - main.py: Handler for taskqueue handler
 - models.py: Entity and message definitions including helper methods
 - utils.py: Helper function for retrieving ndb.Models by urlsafe Key string

## Endpoints Included:
 - **create_user**
    - Path: 'user'
    - Method: POST
    - Parameters: user_name, email (optional)
    - Returns: Message confirming creation of the User
    - Description: Creates a new User. user_name provided must be unique. Will 
    raise a ConflictException if a User with that user_name already exists
    
 - **get_users**
    - Path: 'users'
    - Method: GET
    - Parameters: None 
    - Returns: UserForms
    - Description: Returns all users
    
 - **new_game**
    - Path: 'game'
    - Method: POST
    - Parameters: user_name_x, user_name_o
    - Returns: GameForm with initial game state
    - Description: Creates a new Game. user_name_x, user_name_o provided must 
    correspond to existing users - will raise a NotFoundException if not.
    Also creates a history to track game moves
     
 - **get_game**
    - Path: 'game'
    - Method: GET
    - Parameters: urlsafe_game_key
    - Returns: GameForm with current game status
    - Description: Returns the current status of a game
    
 - **cancel_game**
    - Path: 'game/cancel'
    - Method: DELETE
    - Parameters: urlsafe_game_key
    - Returns: GameForm with game status
    - Description: Delete the game

 - **get_game_history**
    - Path: 'game/history'
    - Method: GET
    - Parameters: urlsafe_game_key
    - Returns: HistoryForm with history all moves for requested game
    - Description: Returns the history of the game
        
 - **make_move**
    - Path: 'game'
    - Method: PUT
    - Parameters: urlsafe_game_key, i, j
    - Returns: GameForm with new game status
    - Description: Accepts i,j-indices in grid and returns the updated status 
    of the game. Controls whether the move is correct. If the game is over,
    updates history, statistic, add task to queue with info about the 
    current leader and rate
     
 - **get_user_games**
    - Path: 'games/user'
    - Method: GET
    - Parameters: user_name
    - Returns: GameForms
    - Description: Returns all user's Games in the database (unordered)
    
 - **get_user_statistic**
    - Path: 'statistic/user'
    - Method: GET
    - Parameters: None
    - Returns: StatisticForms 
    - Description: Returns statistic data for all players (unordered)

 - **get_user_rate**
    - Path: 'games/rating/user'
    - Method: GET
    - Parameters: user_name
    - Returns: RatingForm
    - Description: Returns rating and rank for one player

 - **get_rankings**
    - Path: 'games/ranking'
    - Method: GET
    - Parameters: None
    - Returns: RatingForms
    - Description: Returns ratings and ranks for all players
    
 - **get_leader**
    - Path: 'games/leader'
    - Method: GET
    - Parameters: None
    - Returns: StringMessage
    - Description: Returns the current leader with rate data from 
    a previously cached memcache key

## Models Included:
 - **User**
    - Stores unique user_name and (optional) email address.
    
 - **Game**
    - Stores unique game states. Associated with User model via KeyProperty.
    
 - **History**
    - Records all moves for games. Associated with Game model via KeyProperty.
    
## Forms Included:
 - **GameForm**
    - Representation of a Game's state (urlsafe_key, game_over, message, 
    user_name_x, user_name_o, date)
 - **GameForms**
    - Multiple GameForm container
 - **NewGameForm**
    - Used to create a new game (user_name_x, user_name_o)
 - **UserForm**
    - Representation of a User's data with statistic 
    (name, email, win, loss, draw)
 - **UserForms**
    - Multiple UserForm container
 - **MakeMoveForm**
    - Inbound make move form (i, j, user)
 - **StatisticForm**
    - Statistic for user (name, win, loss, draw)
 - **StatisticForms**
    - Multiple StatisticForm container
 - **RatingForm**
    - Rating for user with calculated rate and rank (name, rate, rank)
 - **RatingForms**
    - Multiple RatingForm container
 - **HistoryForm**
    - History for game (moves)
 - **StringMessage**
    - General purpose String container
    