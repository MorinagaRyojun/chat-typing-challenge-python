# TikTok Typing Challenge Game
#
# HOW TO PLAY:
# 1. Make sure you have Python 3 installed.
# 2. Install the required libraries by running: pip install -r requirements.txt
# 3. IMPORTANT: This script requires FFmpeg to be installed on your system.
#    You can download it from https://ffmpeg.org/download.html
# 4. Change the TIKTOK_USERNAME variable below to your TikTok @username.
# 5. To change the game mode, modify the `game.game_mode` variable in the `if __name__ == "__main__"` block.
#    Available modes: "classic", "sentence", "emoji", "hard", "speed_up".
# 6. Run the script while you are LIVE on TikTok: python main.py
# 7. The game will start, and viewers can type the words in the chat to score points.

import asyncio
import time
import random
from TikTokLive import TikTokLiveClient
from TikTokLive.events import CommentEvent, ConnectEvent

class Game:
    def __init__(self):
        self.leaderboard = {}  # {user_id: {'nickname': str, 'score': int, 'strikes': int, 'penalized': bool}}
        self.current_word = None
        self.round_active = False
        self.round_start_time = 0
        self.round_winners = []  # List of (user_id, timestamp)
        self.word_lists = {
            "classic": ["apple", "banana", "cherry", "orange", "grape", "python", "tiktok", "live"],
            "sentence": ["The quick brown fox jumps over the lazy dog.", "Never gonna give you up.", "I like to move it, move it."],
            "emoji": ["🍎🍌🍇", "😀😂😍", "👍👎👌", "💻🖱️⌨️"],
            "speed_up": ["fast", "quick", "rush", "speed", "fly", "zoom", "blast", "go"],
        }
        self.game_mode = "classic" # Default mode. Can be changed to "sentence", "emoji", "hard", or "speed_up"
        self.round_time_seconds = 10 # Default time
        self.speed_up_start_time = 15
        self.speed_up_min_time = 5
        self.speed_up_decrement = 2

    def _get_or_add_user(self, user_id, nickname):
        """Adds a user to the leaderboard if they don't exist, and returns the user's data."""
        if user_id not in self.leaderboard:
            self.leaderboard[user_id] = {'nickname': nickname, 'score': 0, 'strikes': 0, 'penalized': False}
        # Update nickname in case it has changed
        self.leaderboard[user_id]['nickname'] = nickname
        return self.leaderboard[user_id]

    def _generate_word(self):
        """Generates a word based on the current game mode."""
        if self.game_mode == "hard":
            # Hard mode: shuffle some letters of a classic word
            word = random.choice(self.word_lists["classic"])
            word_list = list(word)
            if len(word_list) > 3:
                # Swap two random letters
                idx1, idx2 = random.sample(range(len(word_list)), 2)
                word_list[idx1], word_list[idx2] = word_list[idx2], word_list[idx1]
                return "".join(word_list), word
            return word, word # Original word is the answer

        word = random.choice(self.word_lists[self.game_mode])
        return word, word # Word to display, and the correct answer

    async def start_new_round(self):
        """Starts a new round of the game."""
        print("\n--- Starting New Round ---")
        self.round_active = True
        self.round_winners = []
        # Reset strikes for all players at the start of a round
        for user_id in self.leaderboard:
            self.leaderboard[user_id]['strikes'] = 0

        # Set round time based on mode
        if self.game_mode != 'speed_up':
            self.round_time_seconds = 10 # Reset to default for other modes

        display_word, correct_word = self._generate_word()
        self.current_word = correct_word

        print(f"Game Mode: {self.game_mode.capitalize()}")
        if self.game_mode == "hard":
            print(f"Unscramble this word: '{display_word}'")
        else:
            print(f"Type this: '{display_word}'")

        self.round_start_time = time.time()

        # Countdown timer
        # Ensure round_time_seconds is an integer for range()
        for i in range(int(self.round_time_seconds), 0, -1):
            print(f"Time left: {i}s")
            await asyncio.sleep(1)

        self.end_round()

    def end_round(self):
        """Ends the current round and calculates scores."""
        print("--- Round Over! ---")
        self.round_active = False

        if not self.round_winners:
            print("No one answered correctly in this round.")
            return

        # Sort winners by time
        self.round_winners.sort(key=lambda x: x[1])

        # Award points
        # 3 points for the fastest
        fastest_winner_id = self.round_winners[0][0]
        self.leaderboard[fastest_winner_id]['score'] += 3
        winner_nickname = self.leaderboard[fastest_winner_id]['nickname']
        print(f"🥇 {winner_nickname} was the fastest and gets 3 points!")

        # 1 point for the rest
        for winner_id, _ in self.round_winners[1:]:
            self.leaderboard[winner_id]['score'] += 1
            winner_nickname = self.leaderboard[winner_id]['nickname']
            print(f"🏅 {winner_nickname} answered correctly and gets 1 point!")

        self.display_leaderboard()
        self._prepare_for_next_round()

        # Handle Speed Up mode logic
        if self.game_mode == 'speed_up':
            new_time = self.round_time_seconds - self.speed_up_decrement
            self.round_time_seconds = max(new_time, self.speed_up_min_time)
            print(f"Ramping up the speed! Next round will be {self.round_time_seconds} seconds.")

    def check_answer(self, user_id, nickname, comment):
        """Checks if a user's comment is the correct answer."""
        if not self.round_active:
            return

        user_data = self._get_or_add_user(user_id, nickname)

        if user_data['penalized']:
            # This user is not allowed to play in this round
            return

        # Check if user has already won this round
        if any(winner[0] == user_id for winner in self.round_winners):
            return

        if comment.strip().lower() == self.current_word.lower():
            time_taken = time.time() - self.round_start_time
            self.round_winners.append((user_id, time_taken))
            print(f"✅ Correct answer from {nickname} in {time_taken:.2f} seconds!")
        else:
            user_data['strikes'] += 1
            print(f"❌ Wrong answer from {nickname}. Strikes: {user_data['strikes']}/3")
            if user_data['strikes'] >= 3:
                user_data['penalized'] = True
                print(f"🚫 {nickname} has been penalized for the next round due to 3 strikes.")

    def _prepare_for_next_round(self):
        """Resets penalties for penalized players."""
        for user_id in self.leaderboard:
            if self.leaderboard[user_id]['penalized']:
                self.leaderboard[user_id]['penalized'] = False
                print(f"👍 {self.leaderboard[user_id]['nickname']} can play in the next round.")

    def display_leaderboard(self):
        """Displays the current leaderboard."""
        print("\n--- Leaderboard ---")
        if not self.leaderboard:
            print("No players yet.")
            return

        sorted_leaderboard = sorted(self.leaderboard.items(), key=lambda item: item[1]['score'], reverse=True)

        for rank, (user_id, data) in enumerate(sorted_leaderboard, 1):
            print(f"#{rank}: {data['nickname']} - {data['score']} points")

# --- TikTok Integration ---

# The TikTok unique_id of the user you want to connect to
TIKTOK_USERNAME = "@ryojun_m"

# Instantiate the game
game = Game()

# Instantiate the TikTok client
client: TikTokLiveClient = TikTokLiveClient(unique_id=TIKTOK_USERNAME)

async def run_game_loop():
    """
    The main loop for the game, which starts new rounds periodically.
    """
    # Initial delay before starting the first round
    await asyncio.sleep(5)

    while True:
        # Start a new round and wait for it to finish
        await game.start_new_round()

        # Wait before starting the next round
        print("\nNext round will start in 15 seconds...")
        await asyncio.sleep(15)

@client.on(ConnectEvent)
async def on_connect(event: ConnectEvent):
    """
    Event that fires when the connection to the livestream is successful.
    """
    print(f"Successfully connected to @{event.unique_id} (Room ID: {client.room_id})")
    print("The game will start in a few seconds...")
    # Start the game loop once connected
    asyncio.create_task(run_game_loop())

@client.on(CommentEvent)
async def on_comment(event: CommentEvent):
    """
    Event that fires when a new comment is received in the TikTok livestream.
    """
    # Pass the comment to the game logic
    game.check_answer(user_id=event.user.unique_id, nickname=event.user.nickname, comment=event.comment)

if __name__ == "__main__":
    # --- Game Configuration ---
    # Change the game mode here before starting the script.
    # Available modes: "classic", "sentence", "emoji", "hard", "speed_up"
    game.game_mode = "classic"

    # If the mode is "speed_up", you might want to set the initial time.
    if game.game_mode == "speed_up":
        game.round_time_seconds = game.speed_up_start_time

    # --- Start the Game ---
    print("Starting TikTok Typing Challenge...")
    print(f"Attempting to connect to {TIKTOK_USERNAME}'s livestream.")
    print(f"Selected Game Mode: {game.game_mode.capitalize()}")
    print("Please make sure the user is LIVE and that FFmpeg is installed.")

    try:
        # Run the client. This is a blocking call that handles its own asyncio loop.
        client.run()
    except Exception as e:
        print(f"\nAn error occurred: {e}")
        print("This might be because the user is not currently live, the username is incorrect, or FFmpeg is not installed.")
        print("Please check these and try again.")
