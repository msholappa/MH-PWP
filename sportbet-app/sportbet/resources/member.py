import json
from jsonschema import validate, ValidationError
from flask import Response, request, url_for
from flask_restful import Resource
from sqlalchemy.exc import IntegrityError

from sportbet import db
from sportbet.models import Member
from sportbet.constants import *
from sportbet.utils import SportbetBuilder, error_response, validate_API_key, debug_print

# List of members
class MemberCollection(Resource):
    
    @validate_API_key
    def get(self, event):
        """
        Show list of members in the given event.
        Members are returned in body["items"] list.
        """
        body = SportbetBuilder()
        body.add_namespace(SPORTBET_NAMESPACE, LINK_RELATIONS_URL)
        body.add_control("self", url_for("api.membercollection", event=event), title="This resource")
        body.add_control_single_event(event)
        body.add_control_add_member(event)
        body["items"] = []
        for m in event.members:
            item = SportbetBuilder(m.serialize())
            item.add_control("self", url_for("api.memberitem", event=event, member=m), title="Member " + m.nickname)
            item.add_control("profile", MEMBER_PROFILE, title="Member profile")
            body["items"].append(item)            
        return Response(json.dumps(body), 200, mimetype=MASON)
   
    @validate_API_key
    def post(self, event):
        """
        Add new member if not existing in this event.
        Redirect to event member listing.
        """
        try:
            if not request.json:
                 return error_response(415, "Unsupported media type", "JSON required")
            validate(request.json, Member.json_schema())
            member = Member(event=event)
            member.deserialize(request.json)
            debug_print("Add member " + member.nickname + " to event " + event.name)
            db.session.add(member)
            db.session.commit()
            return Response(status=201, headers={"Location": url_for("api.memberitem", event=event, member=member)})
        except ValidationError as e:
            return error_response(400, "Invalid JSON document", str(e))
        except KeyError:
            return error_response(400, "Missing parameter", "See schema requirements")
        except ValueError:
            return error_response(400, "Invalid parameter format", "See schema requirements")
        except IntegrityError:
            return error_response(409, "Nickname already in use")

# Single member
class MemberItem(Resource):
    
    @validate_API_key
    def get(self, event, member):
        """
        Get the given member in the given event.
        """
        body = SportbetBuilder(member.serialize())
        body.add_namespace(SPORTBET_NAMESPACE, LINK_RELATIONS_URL)
        body.add_control("self", url_for("api.memberitem", event=event, member=member), title="This resource")
        body.add_control("profile", MEMBER_PROFILE, title="Member profile")
        body.add_control_all_members(event)
        body.add_control_member_bets(event, member)
        body.add_control_betting_status(event, member)
        body.add_control_delete_member(event, member)
        return Response(json.dumps(body), 200, mimetype=MASON)
    
    @validate_API_key
    def delete(self, event, member):
        """
        Delete member in event.
        Redirect to event member listing.
        """
        debug_print("Delete member " + member.nickname + " from event " + event.name)
        db.session.delete(member)
        db.session.commit()
        return Response(status=204, headers={"Location": url_for("api.membercollection", event=event)})
