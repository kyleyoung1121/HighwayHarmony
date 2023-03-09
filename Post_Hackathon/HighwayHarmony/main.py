from dotenv import load_dotenv
import random
import time
import os
import threading
# Spotify Libraries
import spotipy
from spotipy.oauth2 import SpotifyOAuth
# GUI / WebApp libraries
from flask import Flask, render_template, request
 

# Create instance of a flask app
app = Flask(__name__)

# We use this list to track our players
player_list = []


# Host the main webapp html page here
@app.route('/')
def webpage_index():
    title = "Highway Harmony"
    return render_template("index.html", title=title, users=player_list)


# Use other routes to create button functionality
# Add user button
@app.route('/webpage_addremove_user/', methods=['POST', 'GET'])
def webpage_addremove_user():
    name_input = request.form.get('addremove_user_field')
    
    # Add user if requested
    if request.form['two_buttons'] == "add":
        new_player = Player(name_input)
        player_list.append(new_player)

    # Try to remove user if requested
    else:
        for player in player_list:
            if player.name == name_input:
                print(f"DEBUG: removing player {player.name}")
                player_list.remove(player)

    title = "Highway Harmony"
    return render_template("index.html", title=title, users=player_list)


# Add song button
@app.route('/webpage_add_song/', methods=['POST', 'GET'])
def webpage_add_song():
    name_input = request.form.get('users_dropdown')
    song_input = request.form.get('add_song_field')
    print(f"DEBUG: {name_input} is adding {song_input}")
    add_song(name_input, song_input)
    title = "Highway Harmony"
    return render_template("index.html", title=title, users=player_list)


# Add playlist button
@app.route('/webpage_add_playlist/', methods=['POST', 'GET'])
def webpage_add_playlist():
    name_input = request.form.get('users_dropdown')
    song_input = request.form.get('add_playlist_field')
    print(f"DEBUG: {name_input} is adding {song_input}")
    add_from_playlist(name_input, song_input)
    title = "Highway Harmony"
    return render_template("index.html", title=title, users=player_list)

# Load in system environment variables
load_dotenv()

# Save system environment variables
client_id = os.getenv('SPOTIPY_CLIENT_ID')
client_secret = os.getenv('SPOTIPY_CLIENT_SECRET')
client_redirect = os.getenv('SPOTIPY_REDIRECT_URI')

# Global spotify object to sync multi threading
sp = None


# Player class tracks name, personal queue, and position in that queue
class Player:
    def __init__(self, given_name):
        self.name = given_name
        self.song_list = [] # Song list will contain track ids
        self.list_pos = 0

    # Allow for getting the next song, iterating the list position too
    def next_song(self):
        self.list_pos += 1
        if self.list_pos < len(self.song_list)+1:
            return self.song_list[self.list_pos-1]
        else:
            return None

    # In case of an error, allow for going back to previous list_pos
    def prev_song(self):
        if self.list_pos >= 1: self.list_pos -= 1


# This function will select and random player and play their next song
def add_random_song():
    while True:
        num_players = len(player_list)
        # If there are no players, exit
        if num_players == 0: return False
        # choose a random player
        rand_player = random.randint(0,num_players-1)
        selected_player = player_list[rand_player]
        # Try to grab that player's next song
        selected_track_id = selected_player.next_song()
        # If a player is selected with no songs left, remove them from the list
        if selected_track_id == None:
            player_list.remove(selected_player)
        else:
            break
    # Find which device is the active device
    devices = sp.devices()
    active_device = devices["devices"][0]["id"]
    # Add the selected track to the spotify queue
    try:
        # This queue function may fail if the Spotify queue is already at 40 items
        sp.add_to_queue(selected_track_id, active_device)
        return True
    except:
        # If something went wrong, reverse by one, so that song isn't skipped
        selected_player.prev_song()
    
# Add one song to a individual user's queue
def add_song(name_input, song_input, id_provided = False):
    # Iterate through the players and check if in list
    which_player = None
    player_flag = False
    for player in player_list:
        if player.name == name_input:
            which_player = player
            player_flag = True
    if not player_flag:
        print(f"DEBUG: New player created")
        # If not, then make a new player and add it to the list
        new_player = Player(name_input)
        player_list.append(new_player)
        which_player = new_player

    # If the function is passed True for id_provided, treat the song_input as the id
    if id_provided:
        # Add this song's id to the relevant user
        which_player.song_list.append(song_input)

    # Otherwise, we will need to search for the id using the given song_input
    else:
        # Using song input, try to find a song on Spotify
        search_status = False
        try:
            search_result = sp.search(song_input)
            search_status = True
        except:
            pass

        # If we found something, continue
        if search_status:
            # Find the actual song id & name within search_result
            if len(search_result["tracks"]["items"]) > 0:
                # Pull id from the first search result
                song_id = search_result["tracks"]["items"][0]["id"]
                # Add this song's id to the relevant user
                which_player.song_list.append(song_id)
        # After adding a song, queue_up() if necessary
        queue_up()
        

# If we are adding from a playlist, extract all song ids and pass them to add_song()
def add_from_playlist(name_input, playlist_input):
    playlist = sp.playlist(playlist_input, fields=None, market=None, additional_types=('track', ))
    for track in playlist["tracks"]["items"]:
        track_id = track["track"]["id"]
        # print(track_id)
        add_song(name_input, track_id, id_provided=True) # Setting id_provided = True will treat 2nd parameter as an ID instead of a String name
        # After adding new songs, queue_up() if necessary
        queue_up()
    print(f"Playlist successfully added to {name_input}'s queue")

# Separate thread that will periodically queue up more songs if we are running low
def auto_queue():
    while True:
        queue_up()
        time.sleep(60)
        
# Queue up more songs if we are low. Called periodically by auto_queue() and also called upon adding songs or playlists
def queue_up():
    while len(sp.queue()["queue"]) < 15:   # Note that 15 here is misleading. In practice, 10 songs are queued.
        # Try to add a song, if it fails, break from loop
        added_status = add_random_song()
        if not added_status:
            break

# Initialize spotipy elements in webapp
def run():
    global sp
    scope = 'user-read-private user-read-playback-state user-modify-playback-state user-library-read'
    sp = spotipy.Spotify(auth_manager=SpotifyOAuth(scope=scope))
    print("run() setup complete!")
    auto_queue()

if __name__ == '__main__':
    # Initialize spotipy components
    t1 = threading.Thread(target=run)
 
    # starting thread 1
    t1.start()
 
    # Launch webapp
    app.run(host="127.0.0.1", port=8080, debug=True)

    # wait until thread 1 is completely executed
    t1.join()
