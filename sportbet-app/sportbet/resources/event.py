"""
Resource classes to serve API-requests related to events.
"""
import json
from flask import Response, url_for
from flask_restful import Resource

from sportbet.models import Event
from sportbet.constants import SPORTBET_NAMESPACE, LINK_RELATIONS_URL, EVENT_PROFILE, MASON
from sportbet.utils import SportbetBuilder, validate_api_key

class EventCollection(Resource):
    """ Resource class to list events in the system. """
    @validate_api_key
    def get(self):
        """
        Get list of events in the system.
        Events are returned in body["items"] list.
        """
        body = SportbetBuilder()
        body.add_namespace(SPORTBET_NAMESPACE, LINK_RELATIONS_URL)
        body.add_control("self", url_for("api.eventcollection"), title="All events")
        events = Event.query.all()
        body["items"] = []
        for event in events:
            item = SportbetBuilder(event.serialize())
            item.add_control("self", url_for("api.eventitem", event=event), title=event.name)
            item.add_control("profile", EVENT_PROFILE, title="Event profile")
            body["items"].append(item)
        return Response(json.dumps(body), 200, mimetype=MASON)

class EventItem(Resource):
    """ Resource class to get given event in the system. """
    @validate_api_key
    def get(self, event):
        """ Get given event in the system. """
        body = SportbetBuilder(event.serialize())
        body.add_namespace(SPORTBET_NAMESPACE, LINK_RELATIONS_URL)
        body.add_control("self", url_for("api.eventitem", event=event), title="This resource")
        body.add_control("profile", EVENT_PROFILE, title="Event profile")
        body.add_control_all_events()
        #body.add_control("sportbet:events-all", url_for("api.eventcollection"), title="All events")
        body.add_control_all_games(event)
        body.add_control_all_members(event)
        body.add_control_all_bets(event)
        body.add_control_betting_status(event, None)
        return Response(json.dumps(body), 200, mimetype=MASON)
