from dotenv import load_dotenv
import random
import time
import threading
import os
# Spotify Libraries
import spotipy
from spotipy.oauth2 import SpotifyOAuth
# Kivy Libraries
import kivy
kivy.require('2.1.0')
from kivy.app import App
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.image import Image
from kivy.uix.button import Button
from kivy.uix.textinput import TextInput

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
        self.name = given_name.upper()
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

def deminish_queue():
    global queue_length, sp
    while True:
        time.sleep(250)
        if queue_length > 0:
            queue_length -= 1

        # If our queue is low, queue up more songs
        while queue_length < 10:
            # Try to add a song, if it fails, break from loop
            added_status = add_random_song(sp)
            if not added_status:
                break
            print(f"The queue is {queue_length} songs long")

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
    


# Define our requirements and attempt to authenticate with them
scope = 'user-read-private user-read-playback-state user-modify-playback-state user-library-read'
sp = spotipy.Spotify(auth_manager=SpotifyOAuth(scope=scope))
    
class HighwayHarmony(App):
    def build(self):
        # Launch thread to slowly deplete our queue
        threading.Thread(target=deminish_queue, args=()).start()
        #returns a window object with all it's widgets
        self.window = GridLayout()
        self.window.cols = 1
        self.window.size_hint = (0.6, 0.7)
        self.window.pos_hint = {"center_x": 0.5, "center_y":0.5}

        # label widget
        self.song_label = Label(
                        text= "Please enter a song",
                        font_size= 24,
                        color= '#00FFCE'
                        )
        self.window.add_widget(self.song_label)

        # text input widget
        self.song_input = TextInput(
                    multiline= False,
                    padding_y= (20,20),
                    size_hint= (1, 0.5)
                    )
        self.window.add_widget(self.song_input)

        # label widget
        self.name_label = Label(
                        text= "What's your name?",
                        font_size= 24,
                        color= '#00FFCE'
                        )
        self.window.add_widget(self.name_label)

        # text input widget
        self.name_input = TextInput(
                    multiline= False,
                    padding_y= (20,20),
                    size_hint= (1, 0.5)
                    )

        self.window.add_widget(self.name_input)

        # button widget
        self.button = Button(
                      text= "QUEUE",
                      size_hint= (1,0.5),
                      bold= True,
                      background_color ='#CE00FF',
                      #remove darker overlay of background colour
                      # background_normal = ""
                      )
        self.button.bind(on_press=self.callback)
        self.window.add_widget(self.button)

        return self.window

    # This function is called when the button is clicked
    def callback(self, instance):
        # Grab the users username
        name_input = self.name_input.text
        self.name_input.text = self.name_input.text.upper()
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
                
        # Grab the users song request, and then fetch that song's ID
        song_input = self.song_input.text
        self.song_input.text = ""
        search_status = False
        try:
            search_result = sp.search(song_input)
            search_status = True
        except:
            pass


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
                while queue_length < 10:
                    # Try to add a song, if it fails, break from loop
                    added_status = add_random_song(sp)
                    if not added_status:
                        break
                    print(f"The queue is {queue_length} songs long")


if __name__ == '__main__':
    # Launch UI, which in turn calls a function that slowly empties the queue
    HighwayHarmony().run()
