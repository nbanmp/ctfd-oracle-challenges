from CTFd.plugins import register_plugin_assets_directory
from CTFd.plugins.flags import get_flag_class
from CTFd.plugins.challenges import (
    CTFdStandardChallenge,
    BaseChallenge,
    CHALLENGE_CLASSES,
)
from CTFd.models import (
    db,
    Solves,
    Fails,
    Flags,
    Challenges,
    ChallengeFiles,
    Tags,
    Hints,
)
from CTFd import utils
from CTFd.utils.user import get_ip, is_admin
from CTFd.utils.uploads import upload_file, delete_file
from CTFd.utils.decorators.visibility import check_challenge_visibility
from CTFd.utils.decorators import during_ctf_time_only, require_verified_emails
from flask import Blueprint, abort
from sqlalchemy.sql import and_
import six
import json
import requests


class OracleChallenge(BaseChallenge):
    id = "oracle"  # Unique identifier used to register challenges
    name = "oracle"  # Name of a challenge type
    templates = {  # Templates used for each aspect of challenge editing & viewing
        "create": "/plugins/oracle_challenges/assets/create.html",
        "update": "/plugins/oracle_challenges/assets/update.html",
        "view": "/plugins/oracle_challenges/assets/view.html",
    }
    scripts = {  # Scripts that are loaded when a template is loaded
        "create": "/plugins/oracle_challenges/assets/create.js",
        "update": "/plugins/oracle_challenges/assets/update.js",
        "view": "/plugins/oracle_challenges/assets/view.js",
    }
    # Route at which files are accessible. This must be registered using register_plugin_assets_directory()
    route = "/plugins/oracle_challenges/assets/"
    # Blueprint used to access the static_folder directory.
    blueprint = Blueprint(
        "oracle_challenges",
        __name__,
        template_folder="templates",
        static_folder="assets",
    )

    @staticmethod
    def create(request):
        """
        This method is used to process the challenge creation request.

        :param request:
        :return:
        """
        data = request.form or request.get_json()

        challenge = OracleChallenges(**data)

        db.session.add(challenge)
        db.session.commit()

        return challenge

    @staticmethod
    def read(challenge):
        """
        This method is in used to access the data of a challenge in a format processable by the front end.

        :param challenge:
        :return: Challenge object, data dictionary to be returned to the user
        """
        data = {
            "id": challenge.id,
            "name": challenge.name,
            "value": challenge.value,
            "description": challenge.description,
            "category": challenge.category,
            "state": challenge.state,
            "max_attempts": challenge.max_attempts,
            "type": challenge.type,
            "type_data": {
                "id": OracleChallenge.id,
                "name": OracleChallenge.name,
                "templates": OracleChallenge.templates,
                "scripts": OracleChallenge.scripts,
            },
        }
        return data

    @staticmethod
    def update(challenge, request):
        """
        This method is used to update the information associated with a challenge. This should be kept strictly to the
        Challenges table and any child tables.

        :param challenge:
        :param request:
        :return:
        """
        data = request.form or request.get_json()
        for attr, value in data.items():
            setattr(challenge, attr, value)

        db.session.commit()
        return challenge

    @staticmethod
    def delete(challenge):
        """
        This method is used to delete the resources used by a challenge.

        :param challenge:
        :return:
        """
        Fails.query.filter_by(challenge_id=challenge.id).delete()
        Solves.query.filter_by(challenge_id=challenge.id).delete()
        Flags.query.filter_by(challenge_id=challenge.id).delete()
        files = ChallengeFiles.query.filter_by(challenge_id=challenge.id).all()
        for f in files:
            delete_file(f.id)
        ChallengeFiles.query.filter_by(challenge_id=challenge.id).delete()
        Tags.query.filter_by(challenge_id=challenge.id).delete()
        Hints.query.filter_by(challenge_id=challenge.id).delete()
        Challenges.query.filter_by(id=challenge.id).delete()
        OracleChallenges.query.filter_by(id=challenge.id).delete()
        db.session.commit()

    @staticmethod
    def attempt(challenge, request):
        """
        This method is used to check whether a given input is right or wrong. It does not make any changes and should
        return a boolean for correctness and a string to be shown to the user. It is also in charge of parsing the
        user's input from the request itself.

        :param challenge: The Challenge object from the database
        :param request: The request the user submitted
        :return: (boolean, string)
        """
        data = request.form or request.get_json()
        submission = data["submission"].strip()

        instance_id = submission

        try:
            r = requests.post(
                str(challenge.endpoint) + "/attempt", json={"instance_id": instance_id}
            )
        except requests.exceptions.ConnectionError:
            return False, "Challenge endpoint is not available. Talk to an admin."

        if r.status_code == 200:
            return True, "Yay: " + str(challenge.endpoint)

        return False, "Fail"

        # flags = Flags.query.filter_by(challenge_id=challenge.id).all()
        # for flag in flags:
        #    if get_flag_class(flag.type).compare(flag, submission):
        #        return True, 'Correct'
        # return False, 'Incorrect'

    @staticmethod
    def solve(user, team, challenge, request):
        """
        This method is used to insert Solves into the database in order to mark a challenge as solved.

        :param team: The Team object from the database
        :param chal: The Challenge object from the database
        :param request: The request the user submitted
        :return:
        """
        data = request.form or request.get_json()
        submission = data["submission"].strip()
        solve = Solves(
            user_id=user.id,
            team_id=team.id if team else None,
            challenge_id=challenge.id,
            ip=get_ip(req=request),
            provided=submission,
        )
        db.session.add(solve)
        db.session.commit()
        db.session.close()

    @staticmethod
    def fail(user, team, challenge, request):
        """
        This method is used to insert Fails into the database in order to mark an answer incorrect.

        :param team: The Team object from the database
        :param chal: The Challenge object from the database
        :param request: The request the user submitted
        :return:
        """
        data = request.form or request.get_json()
        submission = data["submission"].strip()
        wrong = Fails(
            user_id=user.id,
            team_id=team.id if team else None,
            challenge_id=challenge.id,
            ip=get_ip(request),
            provided=submission,
        )
        db.session.add(wrong)
        db.session.commit()
        db.session.close()


def get_chal_class(class_id):
    """
    Utility function used to get the corresponding class from a class ID.

    :param class_id: String representing the class ID
    :return: Challenge class
    """
    cls = CHALLENGE_CLASSES.get(class_id)
    if cls is None:
        raise KeyError
    return cls


class OracleChallenges(Challenges):
    __mapper_args__ = {"polymorphic_identity": "oracle"}
    id = db.Column(None, db.ForeignKey("challenges.id"), primary_key=True)
    endpoint = db.Column(db.String, default="")

    def __init__(self, *args, **kwargs):
        super(OracleChallenges, self).__init__(**kwargs)
        self.endpoint = kwargs["endpoint"]


def load(app):
    app.db.create_all()
    CHALLENGE_CLASSES["oracle"] = OracleChallenge
    register_plugin_assets_directory(
        app, base_path="/plugins/oracle_challenges/assets/"
    )

    @check_challenge_visibility
    @during_ctf_time_only
    @require_verified_emails
    @app.route("/plugins/oracle_challenges/<challenge_id>", methods=["GET"])
    def request_new_challenge(challenge_id):
        if is_admin():
            challenge = OracleChallenges.query.filter(
                Challenges.id == challenge_id
            ).first_or_404()
        else:
            challenge = OracleChallenges.query.filter(
                OracleChallenges.id == challenge_id,
                and_(Challenges.state != "hidden", Challenges.state != "locked"),
            ).first_or_404()

        try:
            r = requests.post(str(challenge.endpoint) + "/create")
        except requests.exceptions.ConnectionError:
            return json.dumps(
                {
                    "details": "Challenge endpoint is not available. Talk to an admin.",
                    "instance_id": "ERROR",
                }
            )

        if r.status_code != 200:
            return json.dumps(
                {
                    "details": "Challenge endpoint is not available. Talk to an admin.",
                    "instance_id": "ERROR",
                }
            )

        return r.text
