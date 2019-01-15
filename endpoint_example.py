#!/usr/bin/env python3
from flask import Flask, request, abort
import json
import socketio
import uuid

app = Flask(__name__)

ids = []


@app.route("/")
def hello_world():
    """
    USELESS
    """
    return "Hello, World!"


@app.route("/create", methods=["POST"])
def create():
    """
    create challenge

    generate a sufficiently random instance_id
    Return json wth a description containing any
    information needed to access the challenge
    and the instance_id
    """
    data = request.form or request.get_json()

    instance_id = str(uuid.uuid4())

    result = {"instance_id": instance_id, "details": "CHALLENGE_DETAILS"}
    ids.append(instance_id)

    return json.dumps(result)


@app.route("/attempt", methods=["POST"])
def check_solve():
    """
    check a solve, given an instance_id

    return with a 200 code on successful solve or abort on
    a failed solve attempt
    """
    data = request.form or request.get_json()

    try:
        instance_id = data["instance_id"]
    except KeyError:
        abort(401)

    if not instance_id in ids:
        abort(401)

    return "SUCCESS"


app.run(debug=True, threaded=True, host="127.0.0.1", port=4001)
