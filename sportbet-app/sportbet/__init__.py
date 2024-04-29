import os
from flask import Flask, Response, url_for
from flask_sqlalchemy import SQLAlchemy
from flask_caching import Cache
from sportbet.constants import *

db = SQLAlchemy()
cache = Cache()

# Based on http://flask.pocoo.org/docs/1.0/tutorial/factory/#the-application-factory
# Modified to use Flask SQLAlchemy
def create_app(test_config=None):

    app = Flask(__name__, instance_relative_config=True)
    
    from flasgger import Swagger, swag_from
    app.config["SWAGGER"] = {
        "title": "Sportbet API",
        "openapi": "3.0.3",
        "uiversion": 3,
        "doc_dir": "./doc",
    }
    swagger = Swagger(app, template_file="doc\\sportbet.yml")
    
    app.config.from_mapping(
        SECRET_KEY="dev",
        SERVER_NAME=SERVER_NAME,
        SQLALCHEMY_DATABASE_URI="sqlite:///" + os.path.join(app.instance_path, "development.db"),
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
        CACHE_TYPE="FileSystemCache",
        CACHE_DIR=os.path.join(app.instance_path, "cache"),
    )

    if test_config is None:
        app.config.from_pyfile("config.py", silent=True)
    else:
        app.config.from_mapping(test_config)

    try:
        os.makedirs(app.instance_path)
    except OSError:
        pass

    db.init_app(app)
    cache.init_app(app)

    from . import models
    from . import api
    from sportbet.utils import EventConverter
    from sportbet.utils import MemberConverter
    from sportbet.utils import GameConverter
    
    app.cli.add_command(models.db_init)
    app.cli.add_command(models.db_clear)
    app.cli.add_command(models.db_fill)
    app.cli.add_command(models.test_document_command)
    app.cli.add_command(models.test_schema_command)
    app.cli.add_command(models.update_schemas_command)

    # Add converters for URL-name <--> Python object mapping    
    app.url_map.converters["event"] = EventConverter
    app.url_map.converters["member"] = MemberConverter
    app.url_map.converters["game"] = GameConverter
    
    app.register_blueprint(api.api_bp)

    print("APP instance path: " + app.instance_path)
    
    # API entry point redirects to all events view
    @app.route("/api/")
    def api_entry():
        url = url_for("api.eventcollection")
        hdrs = {"Location": url}
        from sportbet.utils import debug_print
        debug_print("API-ENTRY --> redirect to " + url)    
        return Response(status=200, headers=hdrs)

    # Return given profile file content
    @app.route("/profiles/<profile_name>/")
    def send_profiles(profile_name):
        from sportbet.utils import send_local_file
        return send_local_file(os.getcwd() + "/sportbet/static/profiles/" + profile_name + ".html")
     
    # Return link-relations description either as image (default) or as text 
    @app.route(LINK_RELATIONS_URL)
    @app.route(LINK_RELATIONS_URL + "/<text>/")
    def send_link_relations(text=None):
        import os
        from flask import send_file
        try:
            if text:
                from sportbet.utils import send_local_file
                return send_local_file(os.getcwd() + "/sportbet/static" + LINK_RELATIONS_URL + "link-relations.html")
            else:
                return send_file(os.getcwd() + "/sportbet/static" + LINK_RELATIONS_URL + 'link-relations.png')
        except Exception as e:
            return str(e)
    """
    @app.route("/admin/")
    def admin_site():
        return app.send_static_file("html/admin.html")
    """
    
    return app
