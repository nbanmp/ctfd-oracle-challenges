# CTFd Oracle Challenges

When creating a challenge, an endpoint for an "oracle" is specified. This oracle handles challenge deployment and testing. It must respond to two a post request to `/create` and `/attempt`.

# Installation
Clone into CTFd plugins directory.

# Oracle API

## POST - `/create`
JSON will be provided with the integer `team_id` and boolean `force_new`.

The endpoint must ensure a challenge instance for the specified team exists, and return a string with details containing any information needed to interact with the deployed instance.

If `force_new` is true, the endpoint must create a new instance and may delete the old instance. If `force_new` is false, the endpoint should create a new instance only if no instance has been created, and should otherwise return the already existing instance.

## POST - `/attempt`
JSON will be provided with the integer `team_id`.

The endpoint must validate whether or not the team's challenge instance has reached a solved state. If the instance has been solved, a 200 code should be returned, if the instance has not been solved, a non-200 code should be returned.
