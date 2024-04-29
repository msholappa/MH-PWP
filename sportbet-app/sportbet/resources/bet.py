import json
from jsonschema import validate, ValidationError
from flask import Response, request, url_for
from flask_restful import Resource

from sportbet import db
from sportbet.models import Game, Bet
from sportbet.constants import *
from sportbet.utils import SportbetBuilder, error_response, validate_API_key, debug_print

class BetsAll(Resource):

    @validate_API_key
    def get(self, event, game=None):
        """
        Get list of all bets in the event.
        """
        body = SportbetBuilder()
        body.add_namespace(SPORTBET_NAMESPACE, LINK_RELATIONS_URL)
        body.add_control("self", url_for("api.betsall", event=event, game=game), title="This resource")
        body.add_control_single_event(event)
        if game is not None:
            body.add_control_all_bets(event)
        else:
            body.add_control_betting_status(event, None)
        bets = Bet.query.join(Bet.game).filter_by(event=event).order_by(Game.game_nbr)
        body["items"] = []
        for bet in bets:
            if game is not None:
                if bet.game != game:
                    continue
            item = SportbetBuilder(bet.serialize())
            item.add_control("profile", BET_PROFILE, title="Bet profile")
            body["items"].append(item)
        return Response(json.dumps(body), 200, mimetype=MASON)

class BetsMember(Resource):

    @validate_API_key
    def get(self, event, member):
        """
        Get list of the given member's bets in the event.
        """
        body = SportbetBuilder()
        body.add_namespace(SPORTBET_NAMESPACE, LINK_RELATIONS_URL)
        body.add_control("self", url_for("api.betsmember", event=event, member=member), title="This resource")
        body.add_control_all_bets(event)
        body.add_control_add_bet(event, member)
        bets = Bet.query.filter_by(member=member).join(Bet.game).order_by(Game.game_nbr).all()
        body["items"] = []
        for bet in bets:
            item = SportbetBuilder(bet.serialize())
            item.add_control("profile", BET_PROFILE, title="Bet profile")
            body["items"].append(item)
        return Response(json.dumps(body), 200, mimetype=MASON)
     
    @validate_API_key
    def post(self, event, member):
        """
        Add new bet if not existing for this member for the given game.
        If bet is already found, update bet data (PUT method not needed).
        """
        try:
            if not request.json:
                return error_response(415, "Unsupported media type", "JSON required")
            validate(request.json, Bet.json_schema(full_format=False))
            request_bet = Bet()
            request_bet.deserialize(request.json)
            if request_bet.home_goals < 0 or request_bet.guest_goals < 0:
                return error_response(401, "Bet goals must not be negative")
            game = Game.query.filter_by(event=event, game_nbr=request_bet.game_nbr).first()
            if not game:
                return error_response(404, "Game not found")
            # create new bet if old not found
            bet = Bet.query.filter_by(game=game, member=member).first()
            status_code = 204
            if not bet:
                status_code = 201
                bet = Bet(member=member, game=game)
                db.session.add(bet)
            bet.home_goals = request_bet.home_goals
            bet.guest_goals = request_bet.guest_goals
            db.session.commit()
            debug_print(event.name + "/Game-" + game.game_nbr + "/" + member.nickname + "/" + game.home_team + "-" + game.guest_team + " " + str(bet.home_goals) + "-" + str(bet.guest_goals) + " bet saved")
            hdrs = {"Location": url_for("api.betsmember", event=event, member=member)}
            return Response(status = status_code, headers = hdrs)
        except ValidationError as e:
            return error_response(400, "Invalid JSON document", str(e))
        except KeyError:
            return error_response(400, "Missing parameter", "See schema requirements")
        except ValueError:
            return error_response(400, "Invalid parameter format", "See schema requirements")
