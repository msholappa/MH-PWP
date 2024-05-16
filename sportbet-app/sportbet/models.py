import click
import hashlib
from flask.cli import with_appcontext
from sportbet import db

# ----------------- DATABASE MODEL ----------------
#  API database classes.
# -------------------------------------------------

class ApiKey(db.Model):
    
    key = db.Column(db.String(32), nullable=False, unique=True, primary_key=True)
    event_id = db.Column(db.Integer, db.ForeignKey("event.id"), nullable=True)
    admin =  db.Column(db.Boolean, default=False)
    
    event = db.relationship("Event", uselist=False)
    
    @staticmethod
    def key_hash(key):
        return hashlib.sha256(key.encode()).digest()

# Members in events (n-to-n relation, used only when multiple events supported)
event_members = db.Table(
    "event_members",
    db.Column("event_id", db.Integer, db.ForeignKey("event.id"), primary_key=True),
    db.Column("member_id", db.Integer, db.ForeignKey("member.id"), primary_key=True)
)

# Event entity, parent class for members, games and bets
class Event(db.Model):

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), unique=True, nullable=False)
    
    games = db.relationship("Game", cascade="all, delete-orphan", back_populates="event")
    # members = db.relationship("Member", secondary=event_members, back_populates="event_members")
    members = db.relationship("Member", cascade="all, delete-orphan", back_populates="event")
    
    # from JSON to Python object
    def deserialize(self, dic):        
        try:
            self.name = dic["name"]
        except KeyError as e:
            raise BadRequest(description=str(e))
            
    # from Python object to JSON
    def serialize(self):
        return {
            "name": self.name,
        }
        
    @staticmethod
    def json_schema():
        schema = {
            "type": "object",
            "required": ["name"]
        }
        props = schema["properties"] = {}
        props["name"] = {
            "description": "Event name",
            "type": "string"
        }
        return schema

# Member in event, parent for member bets
class Member(db.Model):

    id = db.Column(db.Integer, primary_key=True)
    nickname = db.Column(db.String(64), unique=True, nullable=False)
    # email = db.Column(db.String(64), unique=True, nullable=False)
    event_id = db.Column(db.Integer, db.ForeignKey("event.id", ondelete="CASCADE"))
    
    bets = db.relationship("Bet", cascade="all, delete-orphan", back_populates="member")
    # events = db.relationship("Event", secondary=event_members, back_populates="members")
    event = db.relationship("Event", back_populates="members")
    
    # from JSON to Python object
    def deserialize(self, dic):        
        try:
            self.nickname = dic["nickname"]
        except KeyError as e:
            raise BadRequest(description=str(e))
    
    # from Python object to JSON
    def serialize(self):
        return {
            "nickname": self.nickname
        }
        
    @staticmethod
    def json_schema():
        schema = {
            "type": "object",
            "required": ["nickname"]
        }
        props = schema["properties"] = {}
        props["nickname"] = {
            "description": "Event participant nickname",
            "type": "string"
        }
        return schema

# Game in event, parent for game bets  
class Game(db.Model):

    id = db.Column(db.Integer, primary_key=True)
    event_id = db.Column(db.Integer, db.ForeignKey("event.id", ondelete="CASCADE"))
    game_nbr = db.Column(db.String(64), unique=True, nullable=False)
    home_team = db.Column(db.String(64), nullable=False)
    guest_team = db.Column(db.String(64), nullable=False)
    home_goals = db.Column(db.Integer, nullable=False)
    guest_goals = db.Column(db.Integer, nullable=False)
    
    event = db.relationship("Event", back_populates="games")
    bets = db.relationship("Bet", cascade="all, delete-orphan", back_populates="game")
    
    # from JSON to Python object
    def deserialize(self, dic, full_format=True):        
        try:
            self.home_goals = dic["home_goals"]
            self.guest_goals = dic["guest_goals"]
            if full_format:
                self.game_nbr = dic["game_nbr"]
                self.home_team = dic["home_team"]
                self.guest_team = dic["guest_team"]
        except KeyError as e:
            raise BadRequest(description=str(e))
            
    # from Python object to JSON
    def serialize(self):
        return {
            "game_nbr": self.game_nbr,
            "home_team": self.home_team,
            "guest_team": self.guest_team,
            "home_goals": self.home_goals,
            "guest_goals": self.guest_goals
        }
        
    @staticmethod
    def json_schema(only_goals=False):
        schema = {
            "type": "object",
            "required": ["home_goals", "guest_goals"]
        }
        if not only_goals:
            schema["required"] = ["game_nbr", "home_team", "guest_team", "home_goals", "guest_goals"]
        props = schema["properties"] = {}
        if not only_goals:
            props["game_nbr"] = {
                "description": "Game number in event",
                "type": "string"
            }
            props["home_team"] = {
                "description": "Home team's name",
                "type": "string"
            }
            props["guest_team"] = {
                "description": "Guest team's name",
                "type": "string"
            }
        props["home_goals"] = {
            "description": "Home team's goals",
            "type": "integer"
        }
        props["guest_goals"] = {
            "description": "Guest team's goals",
            "type": "integer"
        }
        return schema
   
# Bet for a member/game   
class Bet(db.Model):

    id = db.Column(db.Integer, primary_key=True)
    game_id = db.Column(db.Integer, db.ForeignKey("game.id", ondelete="CASCADE"))
    member_id = db.Column(db.Integer, db.ForeignKey("member.id", ondelete="CASCADE"))
    
    home_goals = db.Column(db.Integer, nullable=False)
    guest_goals = db.Column(db.Integer, nullable=False)
    
    member = db.relationship("Member", back_populates="bets")
    game = db.relationship("Game", back_populates="bets")
    
    # from JSON to Python object
    def deserialize(self, dic):        
        try:
            # game_nbr used only from client to API for avoiding URL-parameters
            self.game_nbr = dic["game_nbr"]
            self.home_goals = dic["home_goals"]
            self.guest_goals = dic["guest_goals"]
        except KeyError as e:
            raise BadRequest(description=str(e))
            
    # from Python object to JSON
    def serialize(self):
        return {
            "nickname": self.member.nickname,
            "game_nbr": self.game.game_nbr,
            "home_team": self.game.home_team,
            "guest_team": self.game.guest_team,
            "home_goals": self.home_goals,
            "guest_goals": self.guest_goals
        }
        
    @staticmethod
    def json_schema(full_format=True):
        schema = {
            "type": "object",
            "required": ["game_nbr", "home_goals", "guest_goals"]
        }
        if full_format:
            schema["required"] = ["nickname", "game_nbr", "home_team", "guest_team", "home_goals", "guest_goals"]
        props = schema["properties"] = {}
        if full_format:
            props["nickname"] = {
                "description": "Nickname of the bet giver",
                "type": "string"
            }
            props["home_team"] = {
            "description": "Home team's name",
            "type": "string"
            }
            props["guest_team"] = {
                "description": "Guest team's name",
                "type": "string"
            }
        props["game_nbr"] = {
            "description": "Game number for the bet",
            "type": "string"
        }        
        props["home_goals"] = {
            "description": "Home team's goals",
            "type": "integer"
        }
        props["guest_goals"] = {
            "description": "Guest team's goals",
            "type": "integer"
        }
        return schema

# ----------------------------------------------------------------------------
# ----------------- CLICK COMMANDS TO INIT, POPULATE AND CLEAR DATABASE ------
# ----------------------------------------------------------------------------        
@click.command("db-init")
@with_appcontext
def db_init():
    db.create_all()

@click.command("db-clear")
@with_appcontext
def db_clear():
    db.session.query(Bet).delete()
    db.session.query(Game).delete()
    db.session.query(Member).delete()
    db.session.query(Event).delete()
    db.session.query(ApiKey).delete()
    db.session.commit()
    db.session.remove()
    db.drop_all()

@click.command("db-fill")
@with_appcontext
def db_fill():
    
    # NOTE: this could be used to read events, members and games from a text file
    
    # Event and games
    e = Event(name="Bandy-MM-2024")
    game1 = Game(event=e, game_nbr="1", home_team="OPS", guest_team="OLS", home_goals=1, guest_goals=1)
    e.games.append(game1)
    game2 = Game(event=e, game_nbr="2", home_team="HIFK", guest_team="Botnia", home_goals=2, guest_goals=3)
    e.games.append(game2)
    e.games.append(Game(event=e, game_nbr="3", home_team="JPS", guest_team="Akilles", home_goals=3, guest_goals=4))
    e.games.append(Game(event=e, game_nbr="4", home_team="WP-35", guest_team="Kampparit", home_goals=-1, guest_goals=-1))
    db.session.add(e)
    
    # Members and bets
    nicknames = ["mholappa", "pohtonen", "ahilmola", "koja"]
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
    
    # Generate API-keys
    import secrets
    token = secrets.token_urlsafe()
    db_key_admin = ApiKey(
        key=ApiKey.key_hash(token),
        admin=True,
        event=e
    )
    db.session.add(db_key_admin)
    print("ADMIN-key: " + token)
    
    token = secrets.token_urlsafe()
    db_key_user = ApiKey(
        key=ApiKey.key_hash(token),
        admin=False,
        event = e
    )
    db.session.add(db_key_user)
    print("USER-key: " + token)
    
    # ADMIN-key: 0M7xu94E2argHrgEJS4tQdZWfaHmdIFW6IPZv82sQhU
    # USER-key: 4p9cZapvkQbjH_YtjJ5qQq0AttdyJZdjaiAPoa-odIk
    
    db.session.commit()
   
# ----------------------------------------------------------------------------
# ---------- CLICK COMMANDS TO EXPERIMENT WITH DOCUMENTATION (not used) ------
# ----------------------------------------------------------------------------        
   
@click.command("test-document")
@with_appcontext
def test_document_command():
    with app.app_context():
        event = Event.query.first()
        member = Member.query.first()
        game = Game.query.first()
        bet = Bet.query.first()
    document = SportbetBuilder()
    document.add_control_all_games(event)
    document.add_control_all_bets(event, member)
    document.add_control_add_bet(event, member)
    document.add_control_delete_game(event, game)
    print(document)

@click.command("test-schema")
@with_appcontext
def test_schema_command():
    with app.app_context():
        event = Event.query.first()
        member = Member.query.first()
        game = Game.query.first()
        bet = Bet.query.first()

    import yaml
    # from sensorhub import Sensor
    output = "\nEvent:\n" + yaml.dump(Event.json_schema())
    output += "Member:\n" + yaml.dump(Member.json_schema())
    output += "Game:\n" + yaml.dump(Game.json_schema(only_goals=False))
    output += "Bet:\n" + yaml.dump(Bet.json_schema())
    print(output)
    
@click.command("update-schemas")
def update_schemas_command():
    import yaml
    
    class literal_unicode(str): pass
    
    def literal_unicode_representer(dumper, data):
        return dumper.represent_scalar(u'tag:yaml.org,2002:str', data, style='|')
    yaml.add_representer(literal_unicode, literal_unicode_representer)

    filename = "doc/sportbet.yml" 
    with open(filename) as source:
        doc = yaml.safe_load(source)
    schemas = doc["components"]["schemas"] = {}
    for cls in [Event, Member, Game, Bet]:
        schemas[cls.__name__] = cls.json_schema()

    doc["info"]["description"] = literal_unicode(doc["info"]["description"])
    with open(filename, "w") as target:
        target.write(yaml.dump(doc, default_flow_style=False))
