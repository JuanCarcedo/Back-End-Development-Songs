from . import app
import os
import json
from flask import jsonify, request, make_response, abort, url_for  # noqa; F401
from pymongo import MongoClient
from bson import json_util
from pymongo.errors import OperationFailure
from pymongo.results import InsertOneResult
from bson.objectid import ObjectId
import sys

SITE_ROOT = os.path.realpath(os.path.dirname(__file__))
json_url = os.path.join(SITE_ROOT, "data", "songs.json")
songs_list: list = json.load(open(json_url))

# client = MongoClient(
#     f"mongodb://{app.config['MONGO_USERNAME']}:{app.config['MONGO_PASSWORD']}@localhost")
mongodb_service = os.environ.get('MONGODB_SERVICE')
mongodb_username = os.environ.get('MONGODB_USERNAME')
mongodb_password = os.environ.get('MONGODB_PASSWORD')
mongodb_port = os.environ.get('MONGODB_PORT')

print(f'The value of MONGODB_SERVICE is: {mongodb_service}')

if mongodb_service == None:
    app.logger.error('Missing MongoDB server in the MONGODB_SERVICE variable')
    # abort(500, 'Missing MongoDB server in the MONGODB_SERVICE variable')
    sys.exit(1)

if mongodb_username and mongodb_password:
    url = f"mongodb://{mongodb_username}:{mongodb_password}@{mongodb_service}"
else:
    url = f"mongodb://{mongodb_service}"


print(f"connecting to url: {url}")

try:
    client = MongoClient(url)
except OperationFailure as e:
    app.logger.error(f"Authentication error: {str(e)}")

db = client.songs
db.songs.drop()
db.songs.insert_many(songs_list)

def parse_json(data):
    return json.loads(json_util.dumps(data))


######################################################################
# INSERT CODE HERE
######################################################################
@app.route("/health", methods=["GET"])
def health_page() -> tuple:
    """
    Check that the connection is OK
    :return tuple:
        dict: status message
        http status code 200    --Code: OK
    """
    response: tuple = {"status": "OK"}, 200

    return response


@app.route("/count", methods=["GET"])
def count() -> tuple:
    """
    Check the number of documents available
    :return tuple:
        dict: Count of documents
        http status code 200    --Code: OK
    """
    count_documents = db.songs.count_documents({})

    response: tuple = {"count": count_documents}, 200
    return response


@app.route("/song", methods=["GET"])
def songs() -> tuple:
    """
    Retrieve the full list of songs/data.
    :return: tuple
        list of json: data
        http status code 200 if found -- Code: OK
    """
    get_all_songs: list = list(db.songs.find({}))  # Find all songs

    # parse_json needed, else 500 error
    response: tuple = {"songs": parse_json(get_all_songs)}, 200
    return response


@app.route("/song/<int:id>", methods=["GET"])
def get_song_by_id(id: int) -> tuple:
    """
    Retrieve song from the data using id.
    If the id does not exist, return error code and message.
    :param id: int id of the song for searching.
    :return: tuple
        dict: data (json) or message (json) if not found.
        http status code:
            200 Found                   -- Code: OK
            404 Not found/invalid id    -- Code: Not Found
    """
    get_requested_song = db.songs.find_one({"id": id})  # Find song

    if get_requested_song:
        response: tuple = {"songs": parse_json(get_requested_song)}, 200

    else:
        response: tuple = {"message": f"song with id ({id}) not found"}, 404

    return response


@app.route("/song", methods=["POST"])
def create_song() -> tuple:
    """
    Create a new song.
    Step 1) Check if song exists, if it does, then return error message and http 302
    Step 2) Only if 1 is False. Create new song.
    :return: tuple
        dict: data for new song (json) or message (json) if duplicated.
        http status code:
            201 song added           -- Code: Created
            302 song already exists  -- Code: Found
    """
    new_song = request.json  # New data
    id_new_song = new_song.get("id")

    # Check if the id already exists
    if db.songs.find_one({"id": id_new_song}):
        response: tuple = {"message": f"song with id {id_new_song} already present"}, 302

    else:
        inserted_data: InsertOneResult = db.songs.insert_one(new_song)

        response: tuple = {"inserted id": parse_json(inserted_data.inserted_id)}, 201

    return response


@app.route("/song/<int:id>", methods=["PUT"])
def update_song(id: int) -> tuple:
    """
    Update a song currently in the data.
    :param id: int. ID field of the song to be updated.
    :return: tuple
        dict: data for new song (json) or message (json) if not found.
        http status code:
            200 Song found, nothing updated     -- Code: OK
            201 Song updated                    -- Code: Created
            404 Song not found                  -- Code: Not Found
    """

    updated_data = request.json  # Updated data

    # Check if the id exists
    original_query = db.songs.find_one({"id": id})
    if original_query:
        # Update data
        set_data = {"$set": updated_data}
        result = db.songs.update_one(original_query, set_data)

        # Response
        if result.modified_count == 0:
            response: tuple = {"message": "song found, but nothing updated"}, 200

        else:
            response: tuple = parse_json(db.songs.find_one({"id": id})), 201

    else:
        # Not found
        response: tuple = {"message": f"song not found"}, 404

    return response


@app.route("/song/<int:id>", methods=["DELETE"])
def delete_song(id: int) -> tuple:
    """
    Delete a song if it is in the data.
    :return: tuple
        dict: empty body or message (json) if not found.
        http status code:
            204 Picture deleted    -- Code: No content
            404 Picture not found  -- Code: Not Found
    """
    deletion_result = db.songs.delete_one({"id": id})

    if deletion_result.deleted_count == 0:
        # No changes/ song not found
        response: tuple = {"message": f"song not found"}, 404

    else:
        response: tuple = {}, 204

    return response
