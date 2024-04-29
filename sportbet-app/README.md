1. API INTRODUCTION

  A sports event betting hypermedia-based API implemented with Python and Flask.
  
  API entry-point is URL-path "/api/", it redirects to the first usable resource.

  Admin creates events, games and members to events. Members can then 
  give their bets for the game results (home and guest team goals).
  
  Admin inputs game results as soon the game has been played. Members can check 
  the updated betting status (members and their points) after each game result input.
  
  When the last game of the event has been played (result set for the game),
  the member with the highest total points from game bets wins the betting. 
  Correct result gives 3 points, correct goal-difference 2 points, and 
  correct winner 1 points.

2. INSTALLATION

  You can install this package with the following steps:

  1. Copy whole folder /sportbet-app to your preferred folder.
   * You must edit SERVER_NAME constant in /sportbet/constants.py and /client/client.py 

  2. Install all the required packages to your Python environment. File requirements.txt
     contains all the packages obtained via command: 
       "pip freeze > requirements.txt"
     You can install these with command:
       "pip install -r requirements.txt"

  3. Go to parent folder of /sportbet-app and install the package:
       "pip install -e sportbet-app"
     This command installs the sportbet-package to your system and utilizes file setup.py.

  4. For running the API-server, set Flask environment variable for the sportbet app: 
   * Windows PowerShell: $env:FLASK_APP="sportbet.py"
   * UNIX: set FLASK_APP="sportbet.py"

  5. Edit function db_fill() in file /sportbet/models.py (create event, games and members)

  6. Give the following commands in folder /sportbet-app to create and populate the database:
       "flask db-init"
       "flask db-fill" --> COPY-PASTE THE OUTPUT API-KEY to client.py constant SPORTBET_API_KEY_VALUE
       "flask run" --> API-server is now running and can be used by client-software
       "flask db-clear" --> the whole database is removed, run the previous commands again

3. TESTING

  Package has a subfolder /tests. Run Pytest in that folder with:
    "pytest"
  All the tests should pass with green color, without any error or warning messages.

  Testing is performed only to resources (API). Separate testing is 
  not relevant for database model or methods etc. API-testing covers
  all relevant lower level functionality.
  
  You can also use internet browser to test/debug the API. For this you need to edit
  function 
    *validate_API_key()*
  in file utils.py: disable API-key validation by uncommenting the line
    "return func(self, *args, **kwargs)"

4. CLIENT SOFTWARE

  Subfolder /client has a totally automated hypermedia client for testing the API.
  
  Client can be run with command
    "python client.py"
  
  Client software goes to the API entry-point, and lists possible actions/resources.
  User selects the action, and gives possible data required by the schema of the resource.
  
  User actions are asked as long as the user interrupts the client software (with CTRL+C).

5. HELP AND DOCUMENTATION

  SERVER_NAME + /link-relations/ describes the overall structure of the API, and visualizes possible 
  transitions between API-resources.
  
  SERVER_NAME + /profiles/{profile_name}/ gives resource descriptions (currently only dummy files).
  
  You can use file /sportbet/doc/sportbet.yml in OPEN-API tool to view the API's resources,
  methods, paths and schemas. E.g https://editor.swagger.io/. You can also use 
  SERVER_NAME + /apidocs/ to see the same information.
  
6. FURTHER DEVELOPMENT

  The following features are left to be implemented in the future:

  1. Support for multiple events at the same time.
  
  2. Support for a dedicated ADMIN-only API-key for ADMIN-actions.

  2. ADMIN-action: event-collection POST method to create events (now hard-coded event).

  3. ADMIN-action: import event games from a text file.

  4. Start times for games to allow betting only before the game has begun.

  5. PUT method for bets updates (update now via POST, non-standard approach)
  
  6. Member e-mail support and automatic betting status e-mails whenever new game result is input.
  
  7. Member-specific API-keys to allow only own bet manipulation.
  
  8. Proper profile descriptions (now only dummy files for the mechanism verification).