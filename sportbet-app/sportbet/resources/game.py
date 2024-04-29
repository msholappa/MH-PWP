import json
from jsonschema import validate, ValidationError
from flask import Response, request, url_for
from flask_restful import Resource

from sportbet import db
from sportbet.models import Game
from sportbet.constants import *
from sportbet.utils import SportbetBuilder, error_response, validate_API_key, debug_print

class GameCollection(Resource):
    
    @validate_API_key
    def get(self, event):
        """
        Get games in given event.
        """
        body = SportbetBuilder()
        body.add_namespace(SPORTBET_NAMESPACE, LINK_RELATIONS_URL)
        body.add_control("self", url_for("api.gamecollection", event=event), title="This resource")
        body.add_control_single_event(event)
        body.add_control_add_game(event)
        body["items"] = []
        for g in event.games:
            item = SportbetBuilder(g.serialize())
            item.add_control("self", 
                             url_for("api.gameitem", event=event, game=g), 
                             title="Game #" + g.game_nbr + " " + g.home_team + " - " + g.guest_team)
            item.add_control("profile", GAME_PROFILE, title="Game profile")
            body["items"].append(item)
        return Response(json.dumps(body), 200, mimetype=MASON)

    @validate_API_key
    def post(self, event):
        """
        Add new game into event.
        Goals should be set to -1 when game is not yet played
        """
        try:
            if not request.json:
                return error_response(415, "Unsupported media type", "JSON required")
            validate(request.json, Game.json_schema(only_goals=False))
            request_game = Game()
            request_game.deserialize(request.json, full_format=True)
            game = Game.query.filter_by(event=event, game_nbr=request_game.game_nbr).first()
            if game:
                return error_response(409, "Game with given number/name already exists")
            event.games.append(request_game)
            db.session.commit()
            debug_print(event.name + "/Game-" + request_game.game_nbr + " " + str(request_game) + "-" + str(request_game.guest_goals) + " added")
            hdrs = {"Location": url_for("api.gameitem", event=event, game=request_game)}
            return Response(status = 201, headers = hdrs)
        except ValidationError as e:
            return error_response(400, "Invalid JSON document", str(e))
        except KeyError:
            return error_response(400, "Missing parameter", "See schema requirements")
        except ValueError:
            return error_response(400, "Invalid parameter format", "See schema requirements")
    
# Single game
class GameItem(Resource):

    @validate_API_key
    def get(self, event, game):
        """
        Get the given game in the given event.
        """
        body = SportbetBuilder(game.serialize())
        body.add_namespace(SPORTBET_NAMESPACE, LINK_RELATIONS_URL)
        body.add_control("self", url_for("api.gameitem", event=event, game=game), title="This resource")
        body.add_control("profile", GAME_PROFILE, title="Game profile")
        body.add_control_all_games(event)
        body.add_control_game_bets(event, game)
        body.add_control_edit_result(event, game)
        body.add_control_delete_game(event, game)
        return Response(json.dumps(body), 200, mimetype=MASON)
        
    @validate_API_key
    def put(self, event, game):
        """
        Update event game's data (actually only goals).
        """
        try:
            if not request.json:
                return error_response(415, "Unsupported media type", "JSON required")
            validate(request.json, Game.json_schema(only_goals=True))
            game.deserialize(request.json, full_format=False)
            db.session.commit()
            debug_print(event.name + "/Game-" + game.game_nbr + " result " + str(game.home_goals) + "-" + str(game.guest_goals) + " saved")
            hdrs = {"Location": url_for("api.gameitem", event=event, game=game)}
            return Response(status = 204, headers = hdrs)
        except ValidationError as e:
            return error_response(400, "Invalid JSON document", str(e))
        except KeyError:
            return error_response(400, "Missing parameter", "See schema requirements")
        except ValueError:
            return error_response(400, "Invalid parameter format", "See schema requirements")
    
    @validate_API_key
    def delete(self, event, game):
        """
        Delete game in the event.
        """
        db.session.delete(game)
        db.session.commit()
        debug_print(event.name + "/Game-" + game.game_nbr + " deleted")
        return Response(status=204, headers={"Location": url_for("api.gamecollection", event=event)})
