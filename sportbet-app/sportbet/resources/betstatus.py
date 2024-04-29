import json
from flask import Response, url_for
from flask_restful import Resource

from sportbet import db
from sportbet.models import Game
from sportbet.constants import *
from sportbet.utils import SportbetBuilder, validate_API_key, debug_print

class BetStatus(Resource):
    
    # Private method: calculate points for this bet
    def __betpoints(self, event, bet):
        game = Game.query.filter_by(event=event, game_nbr=bet.game.game_nbr).first()
        # Game not found
        if not game:
            return -1
        # Game not played yet
        if game.home_goals < 0:
            return 0
        # Exactly correct result
        if (bet.home_goals == game.home_goals) and (bet.guest_goals == game.guest_goals):
            return 3
        # Goal difference correct (also event result)
        elif (bet.home_goals-bet.guest_goals) == (game.home_goals-game.guest_goals):
            return 2
        # Winner correct
        else:
            if game.home_goals>game.guest_goals and bet.home_goals>bet.guest_goals:
                return 1
            elif game.home_goals<game.guest_goals and bet.home_goals<bet.guest_goals:
                return 1
            else:
                return 0
        
    @validate_API_key
    def get(self, event, member=None):
        """
        Get betting status of the event.
        Return members and their points ordered by total points (highest first).
        If member parameter is given, only bets for this member with detailed information are returned.
        """
        body = SportbetBuilder()
        body.add_namespace(SPORTBET_NAMESPACE, LINK_RELATIONS_URL)
        body.add_control("self", url_for("api.betstatus", event=event, member=member), title="This resource")
        body.add_control("profile", BETSTATUS_PROFILE, title="BetStatus profile")
        body.add_control_single_event(event)    
        body["items"] = []
        for m in event.members:
            # Show only wanted member's bets
            if member is not None and m != member:
                continue
            points = 0
            # Calculate points for all member's bets
            for bet in m.bets:
                pts = self.__betpoints(event, bet)
                if member is not None:
                    debug_print(member.nickname + " game-" + bet.game.game_nbr + " = " + str(pts))
                    # Detailed information for the given member
                    item = SportbetBuilder({"game_nbr": bet.game.game_nbr, 
                                            "points": pts, 
                                            "result": str(bet.game.home_goals) + "-" + str(bet.game.guest_goals),
                                            "bet": str(bet.home_goals) + "-" + str(bet.guest_goals)
                                            })
                    body["items"].append(item)
                points += pts
            # Only nicknames and points for all members
            if member is None:
                debug_print(m.nickname + " = " + str(points) + " points")
                item = SportbetBuilder({"nickname": m.nickname, "points": points})
                # item.add_control_betting_status(event, m)
                item.add_control("self", url_for("api.betstatus", event=event, member=m), title=m.nickname + " bet status")
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
