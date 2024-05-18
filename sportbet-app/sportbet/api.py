"""
Sportbet package resource (URL to resource class) initializations.
"""
from flask import Blueprint
from flask_restful import Api

from sportbet.resources.event import EventCollection, EventItem
from sportbet.resources.member import MemberCollection, MemberItem
from sportbet.resources.game import GameCollection, GameItem
from sportbet.resources.bet import BetsAll, BetsMember
from sportbet.resources.betstatus import BetStatus

URL_PRE = "/api"
api_bp = Blueprint("api", __name__, url_prefix=URL_PRE)
api = Api(api_bp)

api.add_resource(EventCollection, "/events/")
api.add_resource(EventItem, "/events/<event:event>/")

api.add_resource(MemberCollection, "/<event:event>/members/")
api.add_resource(MemberItem, "/<event:event>/members/<member:member>/")

api.add_resource(GameCollection, "/<event:event>/games/")
api.add_resource(GameItem, "/<event:event>/games/<game:game>/")

api.add_resource(BetsAll, "/<event:event>/bets/", "/<event:event>/bets/game/<game:game>/")
api.add_resource(BetsMember, "/<event:event>/bets/<member:member>/")

# GET: list betting points for all members (1st path) or given member (2nd path)
api.add_resource(BetStatus, "/<event:event>/betstatus/",
                            "/<event:event>/betstatus/<member:member>/")
