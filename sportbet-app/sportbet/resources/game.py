"""
Resource classes to serve API-requests related to games.
"""
import json
from jsonschema import validate, ValidationError
from flask import Response, request, url_for
from flask_restful import Resource

from sportbet import db
from sportbet.models import Game
from sportbet.constants import SPORTBET_NAMESPACE, GAME_PROFILE, MASON
from sportbet.utils import SportbetBuilder, error_response, validate_api_key,\
                           debug_print, not_json_request

class GameCollection(Resource):
    """ Resource class for listing games in the event and adding new event. """
    @validate_api_key
    def get(self, event):
        """ Get games in given event. """
        body = SportbetBuilder()
        body.add_namespace(SPORTBET_NAMESPACE)
        body.add_control("self", url_for("api.gamecollection", event=event), title="This resource")
        body.add_control_single_event(event)
        body.add_control_add_game(event)
        body["items"] = []
        for game in event.games:
            item = SportbetBuilder(game.serialize())
            item.add_control("self",
                             url_for("api.gameitem", event=event, game=game),
                             title="Game #" + game.game_nbr + " " +\
                             game.home_team + " - " + game.guest_team)
            item.add_control("profile", GAME_PROFILE, title="Game profile")
            body["items"].append(item)
        return Response(json.dumps(body), 200, mimetype=MASON)

    @validate_api_key
    def post(self, event):
        """
        Add new game into event.
        Goals should be -1 when game is not yet played
        """
        if not_json_request(request):
            return error_response(415, "Unsupported media type", "JSON required")
        try:
            validate(request.json, Game.json_schema(only_goals=False))
            request_game = Game()
            request_game.deserialize(request.json, full_format=True)
            game = Game.query.filter_by(event=event, game_nbr=request_game.game_nbr).first()
            if game:
                return error_response(409, "Game with given number/name already exists")
            event.games.append(request_game)
            db.session.commit()
            debug_print(event.name + "/Game-" + request_game.game_nbr +\
                        " " + str(request_game) + "-" + str(request_game.guest_goals) + " added")
            hdrs = {"Location": url_for("api.gameitem", event=event, game=request_game)}
            return Response(status = 201, headers = hdrs)
        except ValidationError as exception:
            # handles also KeyError and ValueError
            return error_response(400, "Invalid JSON document", str(exception))

class GameItem(Resource):
    """ Resource class for getting, updating and deleting the given game. """
    @validate_api_key
    def get(self, event, game):
        """ Get the given game in the given event. """
        body = SportbetBuilder(game.serialize())
        body.add_namespace(SPORTBET_NAMESPACE)
        body.add_control("self",
                         url_for("api.gameitem", event=event, game=game),
                         title="This resource")
        body.add_control("profile", GAME_PROFILE, title="Game profile")
        body.add_control_all_games(event)
        body.add_control_game_bets(event, game)
        body.add_control_edit_result(event, game)
        body.add_control_delete_game(event, game)
        return Response(json.dumps(body), 200, mimetype=MASON)

    @validate_api_key
    def put(self, event, game):
        """ Update event game's data (actually only goals). """
        if not_json_request(request):
            return error_response(415, "Unsupported media type", "JSON required")
        try:
            validate(request.json, Game.json_schema(only_goals=True))
            game.deserialize(request.json, full_format=False)
            db.session.commit()
            debug_print(event.name + "/Game-" + game.game_nbr +\
                        " result " + str(game.home_goals) + "-" +\
                        str(game.guest_goals) + " saved")
            hdrs = {"Location": url_for("api.gameitem", event=event, game=game)}
            return Response(status = 204, headers = hdrs)
        except ValidationError as exception:
            # handles also KeyError and ValueError
            return error_response(400, "Invalid JSON document", str(exception))

    @validate_api_key
    def delete(self, event, game):
        """ Delete game in the event. """
        db.session.delete(game)
        db.session.commit()
        debug_print(event.name + "/Game-" + game.game_nbr + " deleted")
        return Response(status=204,
                        headers={"Location": url_for("api.gamecollection", event=event)})
