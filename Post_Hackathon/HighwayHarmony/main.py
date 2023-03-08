from dotenv import load_dotenv
import random
import time
import os
# Spotify Libraries
import spotipy
from spotipy.oauth2 import SpotifyOAuth
# GUI / WebApp libraries
from flask import Flask, render_template

# Create instance of a flask app
app = Flask(__name__)

# Test function for web app
@app.route('/')
def index():
    title = "Highway Harmony"
    return render_template("index.html", title=title)

# Load in system environment variables
load_dotenv()

# Save system environment variables
client_id = os.getenv('SPOTIPY_CLIENT_ID')
client_secret = os.getenv('SPOTIPY_CLIENT_SECRET')
client_redirect = os.getenv('SPOTIPY_REDIRECT_URI')

# We will track the length of the queue manually
queue_length = 0

# Global spotify object to sync multi threading
sp = None

# Player class tracks name, personal queue, and position in that queue
class Player:
    def __init__(self, given_name):
        self.name = given_name
        self.song_list = [] # Song list will contain Tracks
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
    

# Track class tracks the id and name of a song
class Track:
    def __init__(self, given_name, given_id):
        self.name = given_name
        self.id = given_id

# We use this list to track our players
player_list = []

# This function will select and random player and play their next song
def add_random_song(sp):
    global queue_length
    while True:
        num_players = len(player_list)
        # If there are no players, exit
        if num_players == 0: return False
        # choose a random player
        rand_player = random.randint(0,num_players-1)
        selected_player = player_list[rand_player]
        # Try to grab that player's next song
        selected_track = selected_player.next_song()
        # If a player is selected with no songs left, remove them from the list
        if selected_track == None:
            player_list.remove(selected_player)
        else:
            break
    # Find which device is the active device
    devices = sp.devices()
    active_device = devices["devices"][0]["id"]
    # Add the selected track to the spotify queue
    try:
        # This queue function may fail if the Spotify queue is already at 40 items
        sp.add_to_queue(selected_track.id, active_device)
        # Update length and output success message to screen
        queue_length += 1
        print(f"Added {selected_track.name} to the queue")
        return True
    except:
        # If something went wrong, reverse by one, so that song isn't skipped
        selected_player.prev_song()
    
def add_song():
    # Get current user
    name_input = "Placeholder"
    # Get song text
    song_input = "Placeholder"

    # Iterate through the players and check if in list
    which_player = None
    player_flag = False
    for player in player_list:
        if player.name == name_input:
            which_player = player
            player_flag = True
    if not player_flag:
        # If not, then make a new player and add it to the list
        new_player = Player(name_input)
        player_list.append(new_player)
        which_player = new_player
            
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
            song_name = search_result["tracks"]["items"][0]["name"]
            song_id = search_result["tracks"]["items"][0]["id"]
            # Build track object
            new_track = Track(song_name,song_id)

            # Add this song to the relevant Player
            which_player.song_list.append(new_track)

            # If our queue is low, queue up more songs
            while len(sp.queue()["queue"]) < 10:
                # Try to add a song, if it fails, break from loop
                added_status = add_random_song(sp)
                if not added_status:
                    break
                print(f"The queue is {queue_length} songs long")
                time.sleep(0.3)

def run():
    global sp

    # Define our requirements and attempt to authenticate with them
    scope = 'user-read-private user-read-playback-state user-modify-playback-state user-library-read'
    sp = spotipy.Spotify(auth_manager=SpotifyOAuth(scope=scope))

    # print success message
    print("run() function complete")
    


    
if __name__ == '__main__':
    # Start flasks dev server
    run()
    app.run(host="127.0.0.1", port=8080, debug=True)
    
