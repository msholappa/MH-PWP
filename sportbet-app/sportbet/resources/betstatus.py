"""
Resource class to serve API-requests related to betting status.
"""
import json
from flask import Response, url_for
from flask_restful import Resource

from sportbet.models import Game
from sportbet.constants import SPORTBET_NAMESPACE, BETSTATUS_PROFILE, MASON
from sportbet.utils import SportbetBuilder, validate_api_key, debug_print

# calculate points for the given bet
def _betpoints(event, bet):
    game = Game.query.filter_by(event=event, game_nbr=bet.game.game_nbr).first()
    points = 0
    # Game not played yet
    if game.home_goals < 0:
        points = 0
    # Exactly correct result
    elif (bet.home_goals == game.home_goals) and (bet.guest_goals == game.guest_goals):
        points = 3
    # Goal difference correct (also event result)
    elif (bet.home_goals-bet.guest_goals) == (game.home_goals-game.guest_goals):
        points = 2
    # Winner correct
    elif game.home_goals>game.guest_goals and bet.home_goals>bet.guest_goals:
        points = 1
    elif game.home_goals<game.guest_goals and bet.home_goals<bet.guest_goals:
        points = 1
    return points

class BetStatus(Resource):
    """ Resource class to build betting status (member ranking). """
    @validate_api_key
    def get(self, event, member=None):
        """
        Get betting status of the event.
        Return members and their points ordered by total points (highest first).
        If member parameter is given, only bets for this member with detailed
        information are returned.
        """
        body = SportbetBuilder()
        body.add_namespace(SPORTBET_NAMESPACE)
        body.add_control("self",
                         url_for("api.betstatus",
                                 event=event,
                                 member=member),
                                 title="This resource")
        body.add_control("profile", BETSTATUS_PROFILE, title="BetStatus profile")
        body.add_control_single_event(event)
        body["items"] = []
        for mem in event.members:
            # Show only wanted member's bets
            if member is not None and mem != member:
                continue
            points = 0
            # Calculate points for all member's bets
            for bet in mem.bets:
                pts = _betpoints(event, bet)
                if member is not None:
                    debug_print(member.nickname + " game-" + bet.game.game_nbr + " = " + str(pts))
                    # Detailed information for the given member
                    item = SportbetBuilder({"game_nbr": bet.game.game_nbr,
                                            "points": pts,
                                            "result": str(bet.game.home_goals) +\
                                            "-" + str(bet.game.guest_goals),
                                            "bet": str(bet.home_goals) + "-" + str(bet.guest_goals)
                                            })
                    body["items"].append(item)
                points += pts
            # Only nicknames and points for all members
            if member is None:
                debug_print(mem.nickname + " = " + str(points) + " points")
                item = SportbetBuilder({"nickname": mem.nickname, "points": points})
                # item.add_control_betting_status(event, mem)
                item.add_control("self",
                                 url_for("api.betstatus", event=event, member=mem),
                                 title=mem.nickname + " bet status")
                body["items"].append(item)
            else:
                body.add_control_betting_status(event, None)
        # Order to have highest points member first
        if member is None:
            body["items"] = sorted(body["items"], key=lambda d: d['points'], reverse=True)
        # Order according to game number
        else:
            body["items"] = sorted(body["items"], key=lambda d: d['game_nbr'])
        return Response(json.dumps(body), 200, mimetype=MASON)
