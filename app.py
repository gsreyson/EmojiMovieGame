"""
Emoji Movie Guessing Game
A multiplayer web-based game where players guess movies from emojis
"""

from flask import Flask, render_template, request, jsonify, session
from flask_socketio import SocketIO, emit, join_room, leave_room
import secrets
import time
import random
from datetime import datetime



app = Flask(__name__)
app.config['SECRET_KEY'] = secrets.token_hex(16)
socketio = SocketIO(app, cors_allowed_origins="*")

# Game state
games = {}

# Movie database with emojis
MOVIE_DATABASE = [
    {"emojis": "🧊👨‍👩‍👦🐅", "answer": "Ice Age", "hints": ["Animated", "Prehistoric", "Scrat"]},
    {"emojis": "🟢👽🚲🌕", "answer": "E.T. the Extra-Terrestrial", "hints": ["Alien", "Bike", "Phone home"]},
    {"emojis": "🧑‍🚀🌕🚀🇺🇸", "answer": "Apollo 13", "hints": ["Space", "NASA", "True story"]},
    {"emojis": "🕶️💊🖥️", "answer": "The Matrix", "hints": ["Sci-fi", "Simulation", "Neo"]},
    {"emojis": "🧠💭🔄", "answer": "Inception", "hints": ["Dreams", "Heist", "Nolan"]},
    {"emojis": "🚓💥🏃‍♂️", "answer": "Fast & Furious", "hints": ["Cars", "Action", "Family"]},
    {"emojis": "🧔⚔️🐉", "answer": "Game of Thrones", "hints": ["Fantasy", "Dragons", "Iron Throne"]},
    {"emojis": "👨‍✈️🔥✈️", "answer": "Top Gun", "hints": ["Jets", "Navy", "Maverick"]},
    {"emojis": "🧑‍🍳🍔🍟", "answer": "The Menu", "hints": ["Food", "Thriller", "Fine dining"]},
    {"emojis": "👨‍🔬🧪🧟‍♂️", "answer": "World War Z", "hints": ["Zombies", "Pandemic", "Brad Pitt"]},
    {"emojis": "🦸‍♂️🛡️🇺🇸", "answer": "Captain America", "hints": ["Marvel", "Shield", "Avenger"]},
    {"emojis": "🧙‍♂️🏫✨", "answer": "Fantastic Beasts", "hints": ["Magic", "Creatures", "Harry Potter world"]},
    {"emojis": "👨‍👩‍👧‍👦🏠🎈", "answer": "Up", "hints": ["Pixar", "Adventure", "Balloons"]},
    {"emojis": "🤠🐍🏺", "answer": "Indiana Jones", "hints": ["Adventure", "Archaeology", "Whip"]},
    {"emojis": "👮‍♂️🐼🥋", "answer": "Kung Fu Panda", "hints": ["DreamWorks", "Martial arts", "Po"]},
    {"emojis": "👨‍⚖️⚡📜", "answer": "Thor", "hints": ["Marvel", "God of Thunder", "Hammer"]},
    {"emojis": "🧛‍♂️🩸🌙", "answer": "Twilight", "hints": ["Vampire", "Romance", "Werewolf"]},
    {"emojis": "👨‍🚀🌌🛰️", "answer": "Gravity", "hints": ["Space", "Survival", "Sandra Bullock"]},
    {"emojis": "🧑‍🎤🎸👑", "answer": "Bohemian Rhapsody", "hints": ["Queen", "Music", "Freddie Mercury"]},
    {"emojis": "👨‍💻💰📈", "answer": "The Social Network", "hints": ["Facebook", "Startup", "Zuckerberg"]},
    {"emojis": "🕵️‍♂️🔫🎯", "answer": "John Wick", "hints": ["Assassin", "Dog", "Action"]},
    {"emojis": "👨‍🚒🔥🏙️", "answer": "Backdraft", "hints": ["Firefighters", "Drama", "Rescue"]},
    {"emojis": "🧑‍🚀🪐🌽", "answer": "Interstellar", "hints": ["Space", "Time", "Love"]},
    {"emojis": "👩‍🎤🎤✨", "answer": "A Star is Born", "hints": ["Music", "Romance", "Lady Gaga"]},
    {"emojis": "🧑‍⚕️🧠💊", "answer": "Doctor Strange", "hints": ["Marvel", "Magic", "Multiverse"]},
]

TEAMS = [
    "Polaris",
    "B4M",
    "QA Automation",
    "Bike4Mind Enterprise",
    "Max",
    "Victor",
    "Illia",
    "DevOps",
    "Exacta",
    "Twinspires",
    "Quantum",
    "Bike4Mind Strategy",
    "Others"
]

FACILITATORS = [
    "Allan",
    "Angelo",
    "Ariel",
    "Arjey",
    "Chad",
    "Cleo",
    "Isao",
    "James",
    "Jason",
    "Jebie",
    "Joshua",
    "Jude",
    "Ken",
    "Kevin",
    "Kyle",
    "Lors",
    "Matt",
    "Max",
    "Nao",
    "Poy",
    "Rexen",
    "Rodel",
    "Victor",
    "Wilfred"
]

class Game:
    def __init__(self, room_code):
        self.room_code = room_code
        self.players = {}
        self.admin_id = None
        self.current_question = 0
        self.questions = random.sample(MOVIE_DATABASE, 13)
        self.is_active = False
        self.question_start_time = None
        self.answered_players = set()
        self.used_teams = []
        self.last_facilitator = None
        
    def add_player(self, player_id, player_name, is_admin=False):
        self.players[player_id] = {
            "name": player_name,
            "score": 0,
            "answered": False,
            "is_admin": is_admin
        }
    
    def remove_player(self, player_id):
        if player_id in self.players:
            del self.players[player_id]
    
    def start_question(self):
        self.question_start_time = time.time()
        self.answered_players = set()
        self.timed_out = False
        for player_id in self.players:
            self.players[player_id]["answered"] = False
    
    def check_answer(self, player_id, answer):
        if player_id in self.answered_players:
            return {"correct": False, "message": "You already answered this question"}
        
        correct_answer = ' '.join(self.questions[self.current_question]["answer"].lower().split())
        user_answer = ' '.join(answer.lower().split())

        if user_answer == correct_answer:
            elapsed_time = time.time() - self.question_start_time
            
            # Calculate points based on speed (max 100 points)
            if elapsed_time <= 10:
                points = max(50, int(100 - (elapsed_time * 5)))
            else:
                points = 0
            
            self.players[player_id]["score"] += points
            self.players[player_id]["answered"] = True
            self.answered_players.add(player_id)
            
            return {
                "correct": True,
                "points": points,
                "message": f"Correct! +{points} points"
            }
        else:
            return {"correct": False, "message": "Incorrect answer"}
    
    def next_question(self):
        self.current_question += 1
        if self.current_question >= len(self.questions):
            return False
        self.start_question()
        return True
    
    def get_leaderboard(self):
        sorted_players = sorted(
            [(pid, p) for pid, p in self.players.items() if not p.get("is_admin", False)],
            key=lambda x: x[1]["score"],
            reverse=True
        )
        return [
            {"name": p[1]["name"], "score": p[1]["score"]}
            for p in sorted_players
        ]

    def pick_team(self):
        remaining = [t for t in TEAMS if t not in self.used_teams]
        if not remaining:
            self.used_teams = []
            remaining = TEAMS[:]
        team = random.choice(remaining)
        self.used_teams.append(team)
        return team

    def get_all_players(self):
        return [
            {"name": p["name"], "is_admin": p.get("is_admin", False)}
            for p in self.players.values()
        ]
    
    def get_current_question(self):
        if self.current_question < len(self.questions):
            q = self.questions[self.current_question]
            return {
                "emojis": q["emojis"],
                "number": self.current_question + 1,
                "total": len(self.questions),
                "hints": q["hints"]
            }
        return None


@app.route('/')
def index():
    return render_template('index.html')

@socketio.on('create_game')
def handle_create_game(data):
    room_code = secrets.token_hex(3).upper()
    games[room_code] = Game(room_code)
    
    player_id = request.sid
    player_name = data.get('player_name', 'Player')

    games[room_code].admin_id = player_id
    games[room_code].add_player(player_id, player_name, is_admin=True)
    join_room(room_code)

    emit('game_created', {
        'room_code': room_code,
        'player_id': player_id
    })

    emit('player_joined', {
        'player_name': player_name,
        'players': games[room_code].get_all_players()
    }, room=room_code)

@socketio.on('join_game')
def handle_join_game(data):
    room_code = data.get('room_code', '').upper()
    player_name = data.get('player_name', 'Player')
    
    if room_code not in games:
        emit('error', {'message': 'Game not found'})
        return
    
    player_id = request.sid
    games[room_code].add_player(player_id, player_name)
    join_room(room_code)
    
    emit('game_joined', {
        'room_code': room_code,
        'player_id': player_id
    })
    
    emit('player_joined', {
        'player_name': player_name,
        'players': games[room_code].get_all_players()
    }, room=room_code)

@socketio.on('start_game')
def handle_start_game(data):
    room_code = data.get('room_code')

    if room_code not in games:
        emit('error', {'message': 'Game not found'})
        return

    game = games[room_code]

    # 👇 BLOCK NON-ADMINS
    if request.sid != game.admin_id:
        emit('error', {'message': 'Only admin can start the game'})
        return

    game.is_active = True
    game.start_question()

    question = game.get_current_question()

    emit('game_started', {
        'question': question,
        'timer': 10
    }, room=room_code)

@socketio.on('submit_answer')
def handle_submit_answer(data):
    room_code = data.get('room_code')
    answer = data.get('answer')
    player_id = request.sid
    
    if room_code not in games:
        emit('error', {'message': 'Game not found'})
        return
    
    game = games[room_code]

    if game.players.get(player_id, {}).get('is_admin', False):
        emit('error', {'message': 'Admin cannot submit answers'})
        return

    result = game.check_answer(player_id, answer)
    
    emit('answer_result', result)
    
    if result['correct']:
        # Notify all players about the correct answer
        emit('player_answered', {
            'player_name': game.players[player_id]['name'],
            'leaderboard': game.get_leaderboard()
        }, room=room_code)

@socketio.on('next_question')
def handle_next_question(data):
    room_code = data.get('room_code')

    if room_code not in games:
        return

    game = games[room_code]

    # 👇 ONLY ADMIN CAN PROCEED
    if request.sid != game.admin_id:
        emit('error', {'message': 'Only admin can proceed to next question'})
        return

    if game.next_question():
        question = game.get_current_question()
        emit('new_question', {
            'question': question,
            'timer': 10
        }, room=room_code)
    else:
        facilitator = random.choice(FACILITATORS)
        game.last_facilitator = facilitator

        emit('game_over', {
            'leaderboard': game.get_leaderboard(),
            'facilitator': facilitator
        }, room=room_code)

@socketio.on('time_up')
def handle_time_up(data):
    room_code = data.get('room_code')

    if room_code not in games:
        return

    game = games[room_code]

    if game.timed_out:
        return

    game.timed_out = True
    correct_answer = game.questions[game.current_question]['answer']

    emit('question_timeout', {
        'correct_answer': correct_answer,
        'leaderboard': game.get_leaderboard()
    }, room=room_code)

@socketio.on('select_team')
def handle_select_team(data):
    room_code = data.get('room_code')

    if room_code not in games:
        return

    game = games[room_code]

    if request.sid != game.admin_id:
        emit('error', {'message': 'Only admin can select a team'})
        return

    team = game.pick_team()

    emit('team_selected', {'team': team}, room=room_code)

@socketio.on('reroll_facilitator')
def handle_reroll_facilitator(data):
    room_code = data.get('room_code')

    if room_code not in games:
        return

    game = games[room_code]

    if request.sid != game.admin_id:
        emit('error', {'message': 'Only admin can reroll the facilitator'})
        return

    pool = [f for f in FACILITATORS if f != game.last_facilitator]
    if not pool:
        pool = FACILITATORS[:]

    facilitator = random.choice(pool)
    game.last_facilitator = facilitator

    emit('facilitator_rerolled', {'facilitator': facilitator}, room=room_code)

@socketio.on('disconnect')
def handle_disconnect():
    player_id = request.sid
    
    # Remove player from all games
    for room_code, game in list(games.items()):
        if player_id in game.players:
            player_name = game.players[player_id]['name']
            game.remove_player(player_id)
            
            emit('player_left', {
                'player_name': player_name,
                'players': game.get_leaderboard()
            }, room=room_code)
            
            # Delete game if no players left
            if len(game.players) == 0:
                del games[room_code]

if __name__ == '__main__':
    socketio.run(app, debug=True, host='0.0.0.0', port=5000)