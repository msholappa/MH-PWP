"""
Sportbet-API tests.

Run "pytest" in this file's folder.

For test coverage, use "pytest --cov-report term-missing --cov=sportbet"
in folder /sportbet-app.

NOTE: when implementing tests, you must know which objects 
      are generated in _populate_db() - because tests are
      performed for existing and non-existing objects!
"""
import json
import os
import pytest
import tempfile
import time
from flask.testing import FlaskClient
from jsonschema import validate
from sqlalchemy.engine import Engine
from sqlalchemy import event
from werkzeug.datastructures import Headers

from sportbet import create_app, db
from sportbet.models import Event, Member, Game, Bet, ApiKey

SPORTBET_NAMESPACE = "sportbet"
SPORTBET_API_KEY_NAME = 'Sportbet-Api-Key'
TEST_KEY = "thisIsOnlyTestKey"
TEST_EVENT_NAME = "Test-Bandy-MM-2024"

# https://stackoverflow.com/questions/16416001/set-http-headers-for-all-requests-in-a-flask-test
class AuthHeaderClient(FlaskClient):

    def open(self, *args, **kwargs):
        api_key_headers = Headers({
            SPORTBET_API_KEY_NAME: TEST_KEY
        })
        headers = kwargs.pop('headers', Headers())
        headers.extend(api_key_headers)
        kwargs['headers'] = headers
        return super().open(*args, **kwargs)
    
@event.listens_for(Engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()

# based on http://flask.pocoo.org/docs/1.0/testing/
# we don't need a client for database testing, just the db handle
@pytest.fixture
def client():
    
    db_fd, db_fname = tempfile.mkstemp()
    config = {
        "SQLALCHEMY_DATABASE_URI": "sqlite:///" + db_fname,
        "TESTING": True
    }
    
    app = create_app(config)
    with app.app_context():
        db.create_all()
        _populate_db()
        
    app.test_client_class = AuthHeaderClient
    yield app.test_client()
    
    os.close(db_fd)
    # Following line causes the error below, remove unlink():
    # PermissionError: [WinError 32] Prosessi ei voi käyttää tiedostoa, koska se on toisen prosessin käytössä: 'C:\\Users\\mikko\\AppData\\Local\\Temp\\tmp7fmm8470'
    # os.unlink(db_fname)

def _populate_db():

    # Event (1) and games (4)
    e = Event(name=TEST_EVENT_NAME)
    game1 = Game(event=e, game_nbr="1", home_team="OPS", guest_team="OLS", home_goals=1, guest_goals=1)
    e.games.append(game1)
    game2 = Game(event=e, game_nbr="2", home_team="HIFK", guest_team="Botnia", home_goals=2, guest_goals=3)
    e.games.append(game2)
    e.games.append(Game(event=e, game_nbr="3", home_team="JPS", guest_team="Akilles", home_goals=3, guest_goals=4))
    e.games.append(Game(event=e, game_nbr="4", home_team="WP-35", guest_team="Kampparit", home_goals=-1, guest_goals=-1))
    db.session.add(e)
    
    # Members (3) and bets (2 per member, for game1 and game2)
    nicknames = ["mholappa", "pohtonen", "ahilmola"]
    idx = 1
    for name in nicknames:
        member = Member(nickname=name)
        e.members.append(member)
        bet1 = Bet(game=game1, home_goals=idx, guest_goals=idx)
        game1.bets.append(bet1)
        member.bets.append(bet1)
        bet2 = Bet(game=game2, home_goals=idx+1, guest_goals=idx+1)
        game2.bets.append(bet2)
        member.bets.append(bet2)
        db.session.add(member)
        idx += 2
    
    # Test key for security mechanism validation
    db_key = ApiKey(
        key=ApiKey.key_hash(TEST_KEY),
        admin=False,
        event=e
    )
    db.session.add(db_key)        
    
    db.session.commit()

def _get_member_json(nickname="mholappa"):
    """
    Creates a valid member JSON object to be used for PUT and POST tests.
    """
    return {"nickname": nickname}

def _get_game_json(number="1", full_format=False):
    """
    Creates a valid game JSON object to be used for PUT and POST tests.
    """
    # POST = add new game
    if full_format:
        return {"game_nbr": number, "home_team": "OPS", "guest_team": "OLS", "home_goals": int(number), "guest_goals": int(number)}
    # PUT = update only result (goals)
    else:
        return {"game_nbr": number, "home_goals": int(number), "guest_goals": int(number)}

def _get_bet_json(game_nbr="1", home_goals=1, guest_goals=1):
    """
    Creates a valid bet JSON object to be used for POST (also update) tests.
    """
    return {"game_nbr": game_nbr, "home_goals": home_goals, "guest_goals":guest_goals}

def _check_namespace(client, response):
    """
    Checks that the correct namespace is found from the response body, and
    that its "name" attribute is a URL that can be accessed.
    """
    ns_href = response["@namespaces"][SPORTBET_NAMESPACE]["name"]
    resp = client.get(ns_href)
    assert resp.status_code == 200
    
def _check_control_get_method(ctrl, client, obj):
    """
    Checks a GET type control from a JSON object be it root document or an item
    in a collection. Also checks that the URL of the control can be accessed.
    """
    href = obj["@controls"][ctrl]["href"]
    resp = client.get(href)
    assert resp.status_code == 200
    
def _check_control_delete_method(ctrl, client, obj):
    """
    Checks a DELETE type control from a JSON object be it root document or an
    item in a collection. Checks the control's method in addition to its "href".
    Also checks that using the control results in the correct status code of 204.
    """
    href = obj["@controls"][ctrl]["href"]
    method = obj["@controls"][ctrl]["method"].lower()
    assert method == "delete"
    resp = client.delete(href)
    assert resp.status_code == 204

def _check_control_put_method(ctrl, client, obj, body):
    """
    Checks a PUT type control from a JSON object be it root document or an item
    in a collection. In addition to checking the "href" attribute, also checks
    that method, encoding and schema can be found from the control. Also
    validates a valid item against the schema of the control to ensure that
    they match. Finally checks that using the control results in the correct
    status code of 204.
    """
    ctrl_obj = obj["@controls"][ctrl]
    href = ctrl_obj["href"]
    method = ctrl_obj["method"].lower()
    encoding = ctrl_obj["encoding"].lower()
    schema = ctrl_obj["schema"]
    assert method == "put"
    assert encoding == "json"
    validate(body, schema)
    resp = client.put(href, json=body)
    assert resp.status_code == 204
    
def _check_control_post_method(ctrl, client, obj, body, ignore_items_self):
    """
    Checks a POST type control from a JSON object be it root document or an item
    in a collection. In addition to checking the "href" attribute, also checks
    that method, encoding and schema can be found from the control. Also
    validates a valid item against the schema of the control to ensure that
    they match. Finally checks that using the control results in the correct
    status code of 201.
    """
    ctrl_obj = obj["@controls"][ctrl]
    href = ctrl_obj["href"]
    method = ctrl_obj["method"].lower()
    encoding = ctrl_obj["encoding"].lower()
    schema = ctrl_obj["schema"]
    assert method == "post"
    assert encoding == "json"
    validate(body, schema)
    resp = client.post(href, json=body)
    assert resp.status_code == 201

# Common GET-test for all resources
def _common_test_get(client, valid_url, invalid_url, post_ctrl_name=None, item_cnt=None, post_object=None, ignore_items_self=False):
    
    resp = client.get(invalid_url)
    assert resp.status_code == 404
    
    resp = client.get(valid_url)
    assert resp.status_code == 200
    body = json.loads(resp.data)
    _check_control_get_method("self", client, body)
    _check_namespace(client, body)
    
    # test collection post if supported
    if post_object is not None and post_ctrl_name is not None:
        _check_control_post_method(post_ctrl_name, client, body, post_object, ignore_items_self)
    
    # test collection items if present
    if item_cnt is not None:
        assert len(body["items"]) == item_cnt
        if not ignore_items_self:
            for item in body["items"]:
                _check_control_get_method("self", client, item)
                #_check_control_get_method("profile", client, item)
            
    return body

# Common DELETE-test for all resources
def _common_test_delete(client, valid_url, invalid_url):
    resp = client.delete(valid_url)
    assert resp.status_code == 204
    resp = client.delete(valid_url)
    assert resp.status_code == 404
    resp = client.delete(invalid_url)
    assert resp.status_code == 404

# Common PUT-test for all resources
def _common_test_put(client, valid_url, invalid_url, item_object, remove_field):
    # test with wrong content type
    resp = client.put(valid_url, data="notjson", headers=Headers({"Content-Type": "text"}))
    assert resp.status_code in (400, 415)
    
    # test with invalid URL
    resp = client.put(invalid_url, json=item_object)
    assert resp.status_code == 404
    
    # test with valid item
    resp = client.put(valid_url, json=item_object)
    assert resp.status_code == 204
    
    # remove field for 400 or 415 (last field removed)
    item_object.pop(remove_field)
    resp = client.put(valid_url, json=item_object)
    assert resp.status_code in (400, 415)

# Common POST-test for all resources
def _common_test_post(client, resource_url, invalid_url, item_object, item_identifier, remove_field):
    # test with wrong content type
    resp = client.post(resource_url, data="notjson", headers=Headers({"Content-Type": "text"}))
    assert resp.status_code == 415
    
    # test with invalid URL
    resp = client.put(invalid_url, json=item_object)
    assert resp.status_code == 404
    
    # post item and see that it exists afterward
    resp = client.post(resource_url, json=item_object)
    assert resp.status_code == 201
    if item_identifier is not None:
        assert resp.headers["Location"].endswith(resource_url + item_identifier + "/")
    else:
        assert resp.headers["Location"] == resource_url
    resp = client.get(resp.headers["Location"])
    assert resp.status_code == 200
    
    # send same data (existing item) again for 409
    resp = client.post(resource_url, json=item_object)
    assert resp.status_code == 409
    
    # remove item field for 400 or 415 (if last field removed)
    item_object.pop(remove_field)
    resp = client.post(resource_url, json=item_object)
    assert resp.status_code in (400, 415)

"""
EventCollection and EventItem tests
"""      
class TestEventCollection(object):
    
    RESOURCE_URL = "/api/events/"
    INVALID_URL = "/api/eventss/"

    def test_get(self, client):
        event_cnt = 1
        _common_test_get(client, self.RESOURCE_URL, self.INVALID_URL, "self", event_cnt)
    
class TestEventItem(object):
    
    RESOURCE_URL = "/api/events/" + TEST_EVENT_NAME + "/"
    INVALID_URL = "/api/events/non-existing-event-name/"
    
    def test_get(self, client):
        body = _common_test_get(client, self.RESOURCE_URL, self.INVALID_URL, "self")
        _check_control_get_method("sportbet:events-all", client, body)
        _check_control_get_method("sportbet:members-all", client, body)
        _check_control_get_method("sportbet:games-all", client, body)
        _check_control_get_method("sportbet:bets-all", client, body)
        _check_control_get_method("sportbet:status-all", client, body)

"""
MemberCollection and MemberItem tests
"""      
class TestMemberCollection(object):
    
    RESOURCE_URL = "/api/" + TEST_EVENT_NAME + "/members/"
    INVALID_URL = "/api/" + TEST_EVENT_NAME + "/_members/"

    def test_get(self, client):
        body = _common_test_get(client,
                                self.RESOURCE_URL,
                                self.INVALID_URL,
                                "sportbet:add-member",
                                3, # item_cnt from db-populate
                                _get_member_json("newMemberName"))
        _check_control_get_method("sportbet:event-" + TEST_EVENT_NAME, client, body)

    def test_post(self, client):
        item_object = _get_member_json("jsmith")
        # add foo key (nickname is the only key, when removed, 415 raised --> no 400 raised ever without foo key)
        item_object["foo"] = "foo"
        remove_field = "nickname"
        _common_test_post(client, self.RESOURCE_URL, self.INVALID_URL, item_object, item_object["nickname"], remove_field)
    
class TestMemberItem(object):
    
    RESOURCE_URL = "/api/" + TEST_EVENT_NAME + "/members/mholappa/"
    INVALID_URL = "/api/" + TEST_EVENT_NAME + "/members/mholappax/"
    
    def test_get(self, client):
        body = _common_test_get(client, self.RESOURCE_URL, self.INVALID_URL, "self")
        _check_control_get_method("sportbet:members-all", client, body)
        _check_control_get_method("sportbet:bets", client, body)
        _check_control_get_method("sportbet:status-mholappa", client, body)
        _check_control_delete_method("sportbet:delete", client, body)
        
    def test_delete(self, client):
        _common_test_delete(client, self.RESOURCE_URL, self.INVALID_URL)

"""
GameCollection and GameItem tests
"""      
class TestGameCollection(object):
    
    RESOURCE_URL = "/api/" + TEST_EVENT_NAME + "/games/"
    INVALID_URL = "/api/" + TEST_EVENT_NAME + "/ggames/"

    def test_get(self, client):
        _common_test_get(client,
                         self.RESOURCE_URL,
                         self.INVALID_URL,
                         "sportbet:add-game",
                         4, # item_cnt from db-populate
                         _get_game_json("5", full_format=True))

    def test_post(self, client):
        item_object = _get_game_json("6", full_format=True)
        remove_field = "game_nbr"
        _common_test_post(client, self.RESOURCE_URL, self.INVALID_URL, item_object, item_object["game_nbr"], remove_field)
        
class TestGameItem(object):
    
    RESOURCE_URL = "/api/" + TEST_EVENT_NAME + "/games/1/"
    INVALID_URL = "/api/" + TEST_EVENT_NAME + "/games/666/"
    
    def test_get(self, client):
        body = _common_test_get(client, self.RESOURCE_URL, self.INVALID_URL, "self")
        _check_control_get_method("sportbet:games-all", client, body)
        _check_control_put_method("sportbet:edit", client, body, _get_game_json("1", full_format=False))
        _check_control_delete_method("sportbet:delete", client, body)
        
    def test_put(self, client):
        item_object = _get_game_json("1", full_format=False)
        remove_field = "home_goals"
        _common_test_put(client, self.RESOURCE_URL, self.INVALID_URL, item_object, remove_field)
        
    def test_delete(self, client):
        _common_test_delete(client, self.RESOURCE_URL, self.INVALID_URL)

"""
BetsAll and BetsMember tests
"""      
class TestBetsAllCollection(object):
    
    RESOURCE_URL = "/api/" + TEST_EVENT_NAME + "/bets/"
    INVALID_URL = "/api/" + TEST_EVENT_NAME + "/betss/"

    def test_get(self, client):
        body = _common_test_get(client,
                                self.RESOURCE_URL,
                                self.INVALID_URL,
                                None,
                                6, # item_cnt from db-populate (3 members x 2 bets)
                                None,
                                True # no item resource path exists
                               )
        _check_control_get_method("sportbet:event-" + TEST_EVENT_NAME, client, body)
        
class TestBetsMemberCollection(object):
    
    RESOURCE_URL = "/api/" + TEST_EVENT_NAME + "/bets/mholappa/"
    INVALID_URL = "/api/" + TEST_EVENT_NAME + "/bets/mholappa_/"

    def test_get(self, client):
        body = _common_test_get(client,
                                self.RESOURCE_URL,
                                self.INVALID_URL,
                                "sportbet:add-bet",
                                2, # member bet item_cnt from db-populate
                                _get_bet_json("3", 6, 6), # bet not existing yet for this game, posted now
                                True # no item resource path exists
                               )
        _check_control_get_method("sportbet:bets-all", client, body)
        
    # test POST for adding a new bet
    def test_post(self, client):
        # test negative goals
        item_object = _get_bet_json("4", -1, 0)
        resp = client.post(self.RESOURCE_URL, json=item_object)
        assert resp.status_code == 401
        # test not existing game
        item_object = _get_bet_json("100", 7, 7)
        resp = client.post(self.RESOURCE_URL, json=item_object)
        assert resp.status_code == 404
        # test generally
        item_object = _get_bet_json("4", 7, 7)
        remove_field = "home_goals"
        _common_test_post(client, self.RESOURCE_URL, self.INVALID_URL, item_object, None, remove_field)
        
    # test PUT for updating an existing bet
    def test_put(self, client):
        # test negative goals
        item_object = _get_bet_json("2", 0, -1)
        resp = client.put(self.RESOURCE_URL, json=item_object)
        assert resp.status_code == 401
        # test non-existing game
        item_object = _get_bet_json("100", 1, 1)
        resp = client.put(self.RESOURCE_URL, json=item_object)
        assert resp.status_code == 404
        # test non-existing bet (game 4)
        item_object = _get_bet_json("4", 1, 1)
        resp = client.put(self.RESOURCE_URL, json=item_object)
        assert resp.status_code == 404
        # test generally
        item_object = _get_bet_json("2", 8, 8)
        remove_field = "home_goals"
        _common_test_put(client, self.RESOURCE_URL, self.INVALID_URL, item_object, remove_field)

class TestBetsGameCollection(object):
    
    RESOURCE_URL = "/api/" + TEST_EVENT_NAME + "/bets/game/1/"
    INVALID_URL = "/api/" + TEST_EVENT_NAME + "/bets/game/666/"

    def test_get(self, client):
        body = _common_test_get(client,
                                self.RESOURCE_URL,
                                self.INVALID_URL,
                                None, # no bet POST for this resource
                                3, # 3 members each betted for this game in db-populate
                                None,
                                True # no item resource path exists
                               )
        _check_control_get_method("sportbet:event-" + TEST_EVENT_NAME, client, body)
        _check_control_get_method("sportbet:bets-all", client, body)

"""
BetStatus for all members tests
"""      
class TestBetStatusAllCollection(object):
    
    RESOURCE_URL = "/api/" + TEST_EVENT_NAME + "/betstatus/"
    INVALID_URL = "/api/" + TEST_EVENT_NAME + "/betstatuss/"
    
    def test_get(self, client):
        body = _common_test_get(client,
                                self.RESOURCE_URL,
                                self.INVALID_URL,
                                None,
                                3, # member count from db-populate
                                None,
                               )
        _check_control_get_method("sportbet:event-" + TEST_EVENT_NAME, client, body)

"""
BetStatus for a single member tests
"""      
class TestBetStatusMemberCollection(object):
    
    RESOURCE_URL = "/api/" + TEST_EVENT_NAME + "/betstatus/mholappa/"
    INVALID_URL = "/api/" + TEST_EVENT_NAME + "/betstatus/non-existing-member/"
    
    def test_get(self, client):
        body = _common_test_get(client,
                                self.RESOURCE_URL,
                                self.INVALID_URL,
                                None,
                                2, # bet count from db-populate
                                None,
                                True # no item 'self' control for bet status
                               )
        _check_control_get_method("sportbet:event-" + TEST_EVENT_NAME, client, body)
        _check_control_get_method("sportbet:status-all", client, body)
