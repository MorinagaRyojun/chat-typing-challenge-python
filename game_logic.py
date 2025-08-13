import asyncio
import time
import random

class Game:
    def __init__(self, manager):
        self.manager = manager
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
        self.game_mode = "classic"
        self.round_time_seconds = 10
        self.speed_up_start_time = 15
        self.speed_up_min_time = 5
        self.speed_up_decrement = 2

    def _get_or_add_user(self, user_id, nickname):
        if user_id not in self.leaderboard:
            self.leaderboard[user_id] = {'nickname': nickname, 'score': 0, 'strikes': 0, 'penalized': False}
        self.leaderboard[user_id]['nickname'] = nickname
        return self.leaderboard[user_id]

    def _generate_word(self):
        if self.game_mode == "hard":
            word = random.choice(self.word_lists["classic"])
            word_list = list(word)
            if len(word_list) > 3:
                idx1, idx2 = random.sample(range(len(word_list)), 2)
                word_list[idx1], word_list[idx2] = word_list[idx2], word_list[idx1]
                return "".join(word_list), word
            return word, word
        word = random.choice(self.word_lists[self.game_mode])
        return word, word

    async def start_new_round(self):
        self.round_active = True
        self.round_winners = []
        for user_id in self.leaderboard:
            self.leaderboard[user_id]['strikes'] = 0

        if self.game_mode != 'speed_up':
            self.round_time_seconds = 10

        display_word, correct_word = self._generate_word()
        self.current_word = correct_word

        await self.manager.broadcast({
            "type": "new_round",
            "mode": self.game_mode.capitalize(),
            "word": display_word,
            "round_time": int(self.round_time_seconds)
        })

        self.round_start_time = time.time()

        for i in range(int(self.round_time_seconds), 0, -1):
            await self.manager.broadcast({"type": "timer_update", "time": i})
            await asyncio.sleep(1)

        await self.end_round()

    async def end_round(self):
        self.round_active = False

        if not self.round_winners:
            await self.manager.broadcast({"type": "round_over", "winners": []})
            return

        self.round_winners.sort(key=lambda x: x[1])

        winners_data = []
        # Award points
        fastest_winner_id = self.round_winners[0][0]
        self.leaderboard[fastest_winner_id]['score'] += 3
        winners_data.append({"nickname": self.leaderboard[fastest_winner_id]['nickname'], "points": 3})

        for winner_id, _ in self.round_winners[1:]:
            self.leaderboard[winner_id]['score'] += 1
            winners_data.append({"nickname": self.leaderboard[winner_id]['nickname'], "points": 1})

        await self.manager.broadcast({"type": "round_over", "winners": winners_data})
        await self.manager.broadcast({"type": "leaderboard_update", "leaderboard": self.get_leaderboard_data()})

        self._prepare_for_next_round()

        if self.game_mode == 'speed_up':
            new_time = self.round_time_seconds - self.speed_up_decrement
            self.round_time_seconds = max(new_time, self.speed_up_min_time)

    async def check_answer(self, user_id, nickname, comment):
        if not self.round_active:
            return

        user_data = self._get_or_add_user(user_id, nickname)

        if user_data['penalized']:
            return

        if any(winner[0] == user_id for winner in self.round_winners):
            return

        if comment.strip().lower() == self.current_word.lower():
            time_taken = time.time() - self.round_start_time
            self.round_winners.append((user_id, time_taken))
            await self.manager.broadcast({
                "type": "correct_answer",
                "nickname": nickname,
                "time": f"{time_taken:.2f}"
            })
        else:
            user_data['strikes'] += 1
            await self.manager.broadcast({
                "type": "wrong_answer",
                "nickname": nickname,
                "strikes": user_data['strikes']
            })
            if user_data['strikes'] >= 3:
                user_data['penalized'] = True
                await self.manager.broadcast({"type": "user_penalized", "nickname": nickname})

    def _prepare_for_next_round(self):
        for user_id in self.leaderboard:
            if self.leaderboard[user_id]['penalized']:
                self.leaderboard[user_id]['penalized'] = False

    def get_leaderboard_data(self):
        if not self.leaderboard:
            return []
        sorted_leaderboard = sorted(self.leaderboard.values(), key=lambda item: item['score'], reverse=True)
        return sorted_leaderboard
