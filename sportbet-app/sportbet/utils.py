"""
Utility functions to be used by multiple other files.
"""
import json
import secrets
from flask import Response, request, url_for
from werkzeug.exceptions import Forbidden, NotFound
from werkzeug.routing import BaseConverter

from sportbet.constants import SPORTBET_NAMESPACE, SPORTBET_API_KEY_NAME, JSON, MASON, ERROR_PROFILE
from sportbet.models import Event, Member, Game, Bet, ApiKey

def not_json_request(req):
    """ Check request content is JSON """
    if req.headers['Content-Type'] != JSON or not req.json:
        return True
    return False

def send_local_file(filename):
    """
    Return local file content in response.
        Parameters:
         -  filename: full path to the file
        Returns:
         - 200 and file contents if successful
         - 400 if file not found
    """
    try:
        with open(filename, "r", encoding='ANSI') as file:
            body = file.read() #.strip()
    except FileNotFoundError:
        return error_response(400, "Target file could not be read")
    content_type = "text/html"
    hdrs = {"Content-type": content_type}
    return Response(body, status = 200, headers=hdrs)

def debug_print(msg):
    """
    Debug function to print the given message to the console.
    Hard-coded, switch "pass" and print() to disable/enable debugging.
        Parameters:
        - msg: message string to be printed
        Returns:
        - none
    """
    return msg
    #print(msg)

def error_response(status, title, msg=None):
    """
    Crete MASON-error for failed requests.
        Parameters:
        - status: status code of the response
        - title: error title as string
        - msg: optional further explanation of the error
        Returns:
        - Response object for the error
    """
    target_url = request.path
    data = MasonBuilder(resource_url=target_url)
    data.add_error(title, msg)
    data.add_control("profile", href=ERROR_PROFILE)
    return Response(json.dumps(data), status, mimetype=MASON)

def require_admin_key(func):
    """
    Admin API-key validation wrapper function - not used currently.
    To be used for admin API functionality in the future versions of API.
    """
    def wrapper(*args, **kwargs):
        key_hash = ApiKey.key_hash(request.headers.get(SPORTBET_API_KEY_NAME, "").strip())
        db_key = ApiKey.query.filter_by(admin=True).first()
        if secrets.compare_digest(key_hash, db_key.key):
            return func(*args, **kwargs)
        raise Forbidden
    return wrapper

def validate_api_key(func):
    """
    API-key validation, use as wrapper for each resource method which needs to
    be protected from the outsiders.

    API-key is created by admin with click command "flask db-fill", save the
    printed key for client software.

    NOTE: enable/disable for testing (browser usually) by commenting/un-commenting
          the line "return func(self, *args, **kwargs)"
    """
    def wrapper(self, *args, **kwargs):
        # Enable browser testing by uncommenting next line
        # return func(self, *args, **kwargs)
        if SPORTBET_API_KEY_NAME in request.headers:
            key_hash = ApiKey.key_hash(request.headers.get(SPORTBET_API_KEY_NAME).strip())
            db_key = ApiKey.query.filter_by(admin=False).first()
            if db_key is not None and secrets.compare_digest(key_hash, db_key.key):
                return func(self, *args, **kwargs)
        raise Forbidden
    return wrapper


#-------------------------------- CONVERTERS -------------------------------
# Convert string-identifier <--> Python database object.
# Registered in __init.py__ for resources using object identifiers in URLs.
#---------------------------------------------------------------------------

class EventConverter(BaseConverter):
    """Conversions between Event object and Event name"""
    def to_python(self, value):
        db_obj = Event.query.filter_by(name=value).first()
        if db_obj is None:
            raise NotFound
        return db_obj
    def to_url(self, value):
        return value.name

class GameConverter(BaseConverter):
    """Conversions between Game object and Game name"""
    def to_python(self, value):
        db_obj = Game.query.filter_by(game_nbr=value).first()
        if db_obj is None:
            raise NotFound
        return db_obj
    def to_url(self, value):
        return value.game_nbr

class MemberConverter(BaseConverter):
    """Conversions between Member object and Member name"""
    def to_python(self, value):
        db_obj = Member.query.filter_by(nickname=value).first()
        if db_obj is None:
            raise NotFound
        return db_obj
    def to_url(self, value):
        if value is None:
            return ""
        return value.nickname

# ----------------- MASON BUILDERS ------------------------------------
# Base class MasonBuilder has been copied from:
# https://github.com/enkwolf/pwp-course-sensorhub-api-example/blob/\
#         master/sensorhub/utils.py
# ---------------------------------------------------------------------
class MasonBuilder(dict):
    """
    A base class re-used from PWP excercises.
    """

    def add_error(self, title, details):
        """
        Adds an error element to the object. Should only be used for the root
        object, and only in error scenarios.

        Note: Mason allows more than one string in the @messages property (it's
        in fact an array). However we are being lazy and supporting just one
        message.

        : param str title: Short title for the error
        : param str details: Longer human-readable description
        """

        self["@error"] = {
            "@message": title,
            "@messages": [details],
        }

    def add_namespace(self, namespace, uri="/api/"):
        """
        Adds a namespace element to the object. A namespace defines where our
        link relations are coming from. The URI can be an address where
        developers can find information about our link relations.

        : param str namespace: the namespace prefix
        : param str uri: the identifier URI of the namespace
        """

        if "@namespaces" not in self:
            self["@namespaces"] = {}

        self["@namespaces"][namespace] = {
            "name": uri
        }

    def add_control(self, ctrl_name, href, **kwargs):
        """
        Adds a control property to an object. Also adds the @controls property
        if it doesn't exist on the object yet. Technically only certain
        properties are allowed for kwargs but again we're being lazy and don't
        perform any checking.

        The allowed properties can be found from here
        https://github.com/JornWildt/Mason/blob/master/Documentation/Mason-draft-2.md

        : param str ctrl_name: name of the control (including namespace if any)
        : param str href: target URI for the control
        """

        if "@controls" not in self:
            self["@controls"] = {}

        self["@controls"][ctrl_name] = kwargs
        self["@controls"][ctrl_name]["href"] = href

    def add_control_post(self, ctrl_name, title, href, schema):
        """
        Utility method for adding POST type controls. The control is
        constructed from the method's parameters. Method and encoding are
        fixed to "POST" and "json" respectively.

        : param str ctrl_name: name of the control (including namespace if any)
        : param str href: target URI for the control
        : param str title: human-readable title for the control
        : param dict schema: a dictionary representing a valid JSON schema
        """

        self.add_control(
            ctrl_name,
            href,
            method="POST",
            encoding="json",
            title=title,
            schema=schema
        )

    def add_control_put(self, title, href, schema):
        """
        Utility method for adding PUT type controls. The control is
        constructed from the method's parameters. Control name, method and
        encoding are fixed to "edit", "PUT" and "json" respectively.

        : param str href: target URI for the control
        : param str title: human-readable title for the control
        : param dict schema: a dictionary representing a valid JSON schema
        """

        self.add_control(
            SPORTBET_NAMESPACE + ":edit",
            href,
            method="PUT",
            encoding="json",
            title=title,
            schema=schema
        )

    def add_control_delete(self, title, href):
        """
        Utility method for adding PUT type controls. The control is
        constructed from the method's parameters. Control method is fixed to
        "DELETE", and control's name is read from the class attribute
        *DELETE_RELATION* which needs to be overridden by the child class.

        : param str href: target URI for the control
        : param str title: human-readable title for the control
        """

        self.add_control(
            SPORTBET_NAMESPACE + ":delete",
            href,
            method="DELETE",
            title=title,
        )

class SportbetBuilder(MasonBuilder):
    """
    API-specific MASON-builder. Resources use these classes and methods to
    create hypertext-responses e.g. for automated clients.
    """
    # GET controls to show items
    def add_control_all_events(self):
        """ Go to event list """
        self.add_control(
            SPORTBET_NAMESPACE + ":events-all",
            url_for("api.eventcollection"),
            title="All events"
        )
    def add_control_single_event(self, event):
        """ Go to given event """
        self.add_control(
            SPORTBET_NAMESPACE + ":event-" + event.name,
            url_for("api.eventitem", event=event),
            title="Event " + event.name
        )
    def add_control_all_games(self, event):
        """ Go to games list """
        self.add_control(
            SPORTBET_NAMESPACE + ":games-all",
            url_for("api.gamecollection", event=event),
            title="Games in " + event.name
        )
    def add_control_single_game(self, event, game):
        """ Go to single game """
        self.add_control(
            SPORTBET_NAMESPACE + ":game-" + game.game_nbr,
            url_for("api.gameitem", event=event, game=game),
            title="Game #" + game.game_nbr
        )
    def add_control_all_bets(self, event):
        """ Go to all event bets """
        self.add_control(
            SPORTBET_NAMESPACE + ":bets-all",
            url_for("api.betsall", event=event),
            title="Bets in " + event.name
        )
    def add_control_member_bets(self, event, member):
        """ Go to single member's bets """
        self.add_control(
            SPORTBET_NAMESPACE + ":bets", #-" + member.nickname,
            url_for("api.betsmember", event=event, member=member),
            title=member.nickname + " bets in " + event.name
        )
    def add_control_game_bets(self, event, game):
        """ Go to single game's bets """
        control_name = ":bets-all"
        title = "Bets in " + event.name
        if game is not None:
            title = "Bets for game-" + game.game_nbr + " " +\
                game.home_team + " - " + game.guest_team
            control_name = ":bets-game-" + game.game_nbr
        self.add_control(
            SPORTBET_NAMESPACE + control_name,
            url_for("api.betsall", event=event, game=game),
            title=title
        )
    def add_control_all_members(self, event):
        """ Go to all members """
        self.add_control(
            SPORTBET_NAMESPACE + ":members-all",
            url_for("api.membercollection", event=event),
            title="Members in " + event.name
        )
    def add_control_single_member(self, event, member):
        """ Go to single member """
        self.add_control(
            SPORTBET_NAMESPACE + ":member-" + member.nickname,
            url_for("api.memberitem", event=event, member=member),
            title="Member " + member.nickname
        )
    def add_control_betting_status(self, event, member):
        """ Go to betting status for whole event or single member """
        control_name = ":status-all"
        title = "Betting status " + event.name
        if member is not None:
            title = member.nickname + " bet status " + event.name
            control_name = ":status-" + member.nickname
        self.add_control(
            SPORTBET_NAMESPACE + control_name,
            url_for("api.betstatus", event=event, member=member),
            title=title
        )

    # DELETE controls to delete items
    def add_control_delete_game(self, event, game):
        """ Delete given game """
        self.add_control_delete(
            "Delete game",
            url_for("api.gameitem", event=event, game=game)
        )
    def add_control_delete_member(self, event, member):
        """ Delete given member """
        self.add_control_delete(
            "Delete member",
            url_for("api.memberitem", event=event, member=member)
        )

    # POST controls to add items
    def add_control_add_member(self, event):
        """ Add new member """
        self.add_control_post(
            SPORTBET_NAMESPACE + ":add-member",
            "Add member to " + event.name,
            url_for("api.membercollection", event=event),
            Member.json_schema()
        )
    def add_control_add_game(self, event):
        """ Add new game """
        self.add_control_post(
            SPORTBET_NAMESPACE + ":add-game",
            "Add game to " + event.name,
            url_for("api.gamecollection", event=event),
            Game.json_schema(only_goals=False)
        )
    def add_control_add_bet(self, event, member):
        """ Add new bet """
        self.add_control_post(
            SPORTBET_NAMESPACE + ":add-bet",
            "Add bet for " + member.nickname,
            url_for("api.betsmember", event=event, member=member),
            Bet.json_schema(full_format=False)
        )

    # PUT controls for editing items
    def add_control_edit_result(self, event, game):
        """ Edit existing game goals """
        self.add_control_put(
            "Edit game",
            url_for("api.gameitem", event=event, game=game),
            Game.json_schema(only_goals=True)
        )
    def add_control_edit_bet(self, event, member):
        """ Edit existing bet goals """
        self.add_control_put(
            "Edit bet",
            url_for("api.betsmember", event=event, member=member),
            Bet.json_schema(full_format=False)
        )
