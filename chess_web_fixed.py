# Chess game web interface for Flask
from flask import Flask, render_template_string, request, jsonify, session
from chess_mechanics import ChessGame
from chess_game import Position, Color, PieceType
import json
import time
import uuid

# Global game sessions for multiplayer
game_sessions = {}
session_cleanup_time = {}

def cleanup_old_sessions():
    """Remove game sessions older than 1 hour"""
    current_time = time.time()
    sessions_to_remove = []
    for session_id, cleanup_time in session_cleanup_time.items():
        if current_time - cleanup_time > 3600:  # 1 hour
            sessions_to_remove.append(session_id)
    
    for session_id in sessions_to_remove:
        if session_id in game_sessions:
            del game_sessions[session_id]
        if session_id in session_cleanup_time:
            del session_cleanup_time[session_id]

# Enhanced HTML template for interactive chess game with optimizations
CHESS_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Chess For My Bachas - Interactive Chess Game</title>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        /* Performance optimizations */
        * {
            box-sizing: border-box;
        }
        
        /* GPU acceleration for better performance */
        .chess-board, .chess-square, .chess-piece {
            transform: translateZ(0);
            backface-visibility: hidden;
            perspective: 1000px;
        }
        
        body { 
            font-family: 'Segoe UI', -apple-system, BlinkMacSystemFont, 'Roboto', sans-serif; 
            margin: 0; 
            padding: 20px;
            text-align: center; 
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            color: #2c3e50;
            display: flex;
            justify-content: center;
            align-items: flex-start;
            /* Performance optimizations */
            -webkit-font-smoothing: antialiased;
            -moz-osx-font-smoothing: grayscale;
            text-rendering: optimizeLegibility;
            will-change: transform;
            overflow-x: hidden;
        }
        
        .game-container {
            max-width: 1200px;
            margin: 20px auto;
            background: rgba(255, 255, 255, 0.95);
            backdrop-filter: blur(10px);
            border-radius: 25px;
            padding: 40px;
            box-shadow: 
                0 25px 50px rgba(0,0,0,0.15),
                0 10px 25px rgba(0,0,0,0.1),
                inset 0 1px 0 rgba(255,255,255,0.8);
            border: 1px solid rgba(255,255,255,0.2);
            width: 100%;
            box-sizing: border-box;
            /* Performance optimization */
            will-change: transform, box-shadow;
            transform: translateZ(0);
        }
        
        .game-title {
            font-size: 3.5em;
            font-weight: 700;
            margin-bottom: 40px;
            text-shadow: 
                0 4px 8px rgba(0,0,0,0.3),
                0 0 20px rgba(255,215,0,0.6);
            background: linear-gradient(135deg, #c9aa3a, #ffd700, #ffed4e, #ffd700, #b8860b);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
            color: #b8860b;
            background-size: 300% 100%;
            animation: goldShimmer 4s ease-in-out infinite;
            /* Performance optimization */
            will-change: background-position;
            transform: translateZ(0);
        }
        
        .chess-board { 
            display: grid;
            grid-template-columns: repeat(8, 68px);
            grid-template-rows: repeat(8, 68px);
            width: 544px;
            height: 544px;
            border: 10px solid #654321;
            border-radius: 20px;
            box-shadow: 
                0 30px 60px rgba(0,0,0,0.4),
                inset 0 0 40px rgba(139,69,19,0.3),
                0 0 0 6px #8b4513,
                0 0 0 12px rgba(139,69,19,0.2),
                0 0 100px rgba(101,67,33,0.3);
            background: 
                radial-gradient(circle at 25% 25%, rgba(255,255,255,0.1) 0%, transparent 50%),
                linear-gradient(135deg, #f0d9b5 0%, #ede0c8 100%);
            position: relative;
            gap: 0;
            transform: perspective(1500px) rotateX(2deg) rotateY(1deg);
            will-change: transform, box-shadow;
            transform-style: preserve-3d;
            contain: layout style paint;
            margin: 20px auto;
        }
        
        .chess-square {
            width: 68px;
            height: 68px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 54px;
            font-family: 'Segoe UI Symbol', 'Apple Color Emoji', 'Noto Color Emoji', monospace;
            cursor: pointer;
            transition: all 0.25s cubic-bezier(0.25, 0.46, 0.45, 0.94);
            position: relative;
            user-select: none;
            box-sizing: border-box;
            border: 1px solid rgba(0,0,0,0.1);
            will-change: transform, box-shadow, background;
            transform: translateZ(0);
            contain: layout style paint;
        }
        
        .chess-square.light {
            background: 
                radial-gradient(circle at 30% 30%, rgba(255,255,255,0.3) 0%, transparent 60%),
                linear-gradient(135deg, #fdfcf8 0%, #f0d9b5 50%, #ede0c8 100%);
            box-shadow: 
                inset 0 3px 6px rgba(255,255,255,0.4),
                inset 0 -2px 4px rgba(0,0,0,0.1);
        }
        
        .chess-square.dark {
            background: 
                radial-gradient(circle at 30% 30%, rgba(255,255,255,0.15) 0%, transparent 60%),
                linear-gradient(135deg, #d18b47 0%, #b58863 50%, #a67c52 100%);
            box-shadow: 
                inset 0 3px 6px rgba(0,0,0,0.25),
                inset 0 -2px 4px rgba(255,255,255,0.15);
        }
        
        .btn {
            padding: 12px 24px;
            font-size: 16px;
            border: none;
            border-radius: 8px;
            cursor: pointer;
            margin: 0 10px;
            transition: all 0.3s ease;
            font-weight: 600;
        }
        
        .btn-primary {
            background: linear-gradient(135deg, #007bff, #0056b3);
            color: white;
        }
        
        .btn-primary:hover {
            background: linear-gradient(135deg, #0056b3, #003d82);
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(0,123,255,0.3);
        }
        
        .btn-secondary {
            background: linear-gradient(135deg, #6c757d, #545b62);
            color: white;
        }
        
        .btn-secondary:hover {
            background: linear-gradient(135deg, #545b62, #383d41);
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(108,117,125,0.3);
        }
        
        .player-input {
            margin: 20px 0;
        }
        
        .player-input input {
            padding: 12px;
            margin: 5px;
            border: 2px solid #ddd;
            border-radius: 8px;
            font-size: 16px;
            width: 200px;
        }
        
        .hidden {
            display: none;
        }
        
        .game-id-display {
            background: #e9ecef;
            border-radius: 8px;
            padding: 15px;
            margin: 15px 0;
            font-family: monospace;
            font-size: 20px;
            font-weight: bold;
            color: #007bff;
        }
    </style>
</head>
<body>
    <div class="game-container">
        <h1 class="game-title">Chess For My Bachas</h1>
        <p style="font-size: 1.2em; color: #666; margin-bottom: 30px;">🌐 Multiplayer Online Chess</p>
        
        <!-- Connection Controls -->
        <div id="connectionControls" class="multiplayer-controls">
            <div class="player-input">
                <input type="text" id="playerName" placeholder="Enter your name" maxlength="20">
                <button id="createGameBtn" class="btn btn-primary">Create New Game</button>
                <input type="text" id="gameIdInput" placeholder="Game ID to join" maxlength="8">
                <button id="joinGameBtn" class="btn btn-secondary">Join Game</button>
            </div>
            <p style="color: #666; margin: 0;">Create a new game or enter a Game ID to join an existing game</p>
        </div>
        
        <!-- Game ID Display -->
        <div id="gameIdDisplay" class="game-id-display hidden">
            Game ID: <span id="currentGameId"></span>
            <p style="margin: 5px 0 0 0; font-size: 14px; font-weight: normal;">Share this ID with your friend to play together!</p>
        </div>
        
        <!-- Chess Board (will be populated by JavaScript) -->
        <div id="chessBoard" class="chess-board hidden"></div>
    </div>

    <script>
        console.log('JavaScript loading...');
        
        // Game state variables
        let gameId = null;
        let playerName = '';
        let playerColor = null;
        
        // Simple create game function
        function createGame() {
            console.log('createGame called');
            
            const nameInput = document.getElementById('playerName');
            if (!nameInput) {
                console.error('Name input not found');
                return;
            }
            
            const name = nameInput.value.trim();
            if (!name) {
                alert('Please enter your name first!');
                return;
            }
            
            console.log('Creating game for player:', name);
            
            // Show loading
            const btn = document.getElementById('createGameBtn');
            if (btn) {
                btn.textContent = 'Creating...';
                btn.disabled = true;
            }
            
            // Make API call
            fetch('/api/chess/multiplayer/create', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    player_name: name
                })
            })
            .then(response => {
                console.log('Response status:', response.status);
                return response.json();
            })
            .then(data => {
                console.log('Response data:', data);
                
                if (data.success) {
                    gameId = data.game_id;
                    playerColor = data.player_color;
                    playerName = name;
                    
                    // Update UI
                    document.getElementById('currentGameId').textContent = gameId;
                    document.getElementById('gameIdDisplay').classList.remove('hidden');
                    document.getElementById('connectionControls').classList.add('hidden');
                    document.getElementById('chessBoard').classList.remove('hidden');
                    
                    console.log('Game created successfully:', gameId);
                    alert('Game created! Game ID: ' + gameId + '\\nWaiting for opponent...');
                } else {
                    console.error('Failed to create game:', data.error);
                    alert('Failed to create game: ' + (data.error || 'Unknown error'));
                }
            })
            .catch(error => {
                console.error('Error creating game:', error);
                alert('Error creating game: ' + error.message);
            })
            .finally(() => {
                // Restore button
                if (btn) {
                    btn.textContent = 'Create New Game';
                    btn.disabled = false;
                }
            });
        }
        
        // Simple join game function
        function joinGame() {
            console.log('joinGame called');
            
            const nameInput = document.getElementById('playerName');
            const gameIdInput = document.getElementById('gameIdInput');
            
            if (!nameInput || !gameIdInput) {
                console.error('Required inputs not found');
                return;
            }
            
            const name = nameInput.value.trim();
            const gameIdToJoin = gameIdInput.value.trim();
            
            if (!name) {
                alert('Please enter your name first!');
                return;
            }
            
            if (!gameIdToJoin) {
                alert('Please enter a Game ID to join!');
                return;
            }
            
            console.log('Joining game:', gameIdToJoin, 'as player:', name);
            
            // Show loading
            const btn = document.getElementById('joinGameBtn');
            if (btn) {
                btn.textContent = 'Joining...';
                btn.disabled = true;
            }
            
            // Make API call
            fetch('/api/chess/multiplayer/join/' + gameIdToJoin, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    player_name: name
                })
            })
            .then(response => {
                console.log('Join response status:', response.status);
                return response.json();
            })
            .then(data => {
                console.log('Join response data:', data);
                
                if (data.success) {
                    gameId = data.game_id;
                    playerColor = data.player_color;
                    playerName = name;
                    
                    // Update UI
                    document.getElementById('currentGameId').textContent = gameId;
                    document.getElementById('gameIdDisplay').classList.remove('hidden');
                    document.getElementById('connectionControls').classList.add('hidden');
                    document.getElementById('chessBoard').classList.remove('hidden');
                    
                    console.log('Joined game successfully:', gameId);
                    alert('Joined game successfully! You are playing as ' + playerColor);
                } else {
                    console.error('Failed to join game:', data.error);
                    alert('Failed to join game: ' + (data.error || 'Unknown error'));
                }
            })
            .catch(error => {
                console.error('Error joining game:', error);
                alert('Error joining game: ' + error.message);
            })
            .finally(() => {
                // Restore button
                if (btn) {
                    btn.textContent = 'Join Game';
                    btn.disabled = false;
                }
            });
        }
        
        // Set up event listeners when DOM is ready
        document.addEventListener('DOMContentLoaded', function() {
            console.log('DOM ready, setting up event listeners');
            
            const createBtn = document.getElementById('createGameBtn');
            const joinBtn = document.getElementById('joinGameBtn');
            
            if (createBtn) {
                createBtn.addEventListener('click', createGame);
                console.log('Create button listener added');
            } else {
                console.error('Create button not found!');
            }
            
            if (joinBtn) {
                joinBtn.addEventListener('click', joinGame);
                console.log('Join button listener added');
            } else {
                console.error('Join button not found!');
            }
            
            console.log('Event listeners setup complete');
        });
        
        console.log('Script loaded');
    </script>
</body>
</html>
"""

def add_chess_routes(app):
    """Add chess game routes to Flask app"""
    
    # Initialize game session (in production, use proper session management)
    chess_game = ChessGame()
    
    def get_board_data():
        """Convert board to 2D array for JavaScript"""
        board_data = []
        board_string = chess_game.board.board_to_string()
        lines = board_string.strip().split('\\n')
        
        for line in lines:
            row = []
            for char in line:
                row.append(char)
            board_data.append(row)
        
        return board_data

    @app.route('/chess')
    def chess_game_route():
        """Chess game web interface"""
        try:
            board_data = get_board_data()
            current_player = chess_game.current_player
            game_status = chess_game.get_game_status()
            
            return render_template_string(
                CHESS_TEMPLATE,
                board_data=json.dumps(board_data),
                current_player=current_player,
                game_status=game_status,
                message=None,
                message_type=''
            )
        except Exception as e:
            return f"Error loading chess game: {e}", 500

    # Multiplayer Chess API Endpoints
    @app.route('/api/chess/multiplayer/create', methods=['POST'])
    def create_multiplayer_game():
        """Create a new multiplayer chess game"""
        try:
            cleanup_old_sessions()
            
            game_id = str(uuid.uuid4())[:8]  # Short game ID
            player_name = request.json.get('player_name', 'Player 1')
            
            game_sessions[game_id] = {
                'game': ChessGame(),
                'players': {
                    'white': {'name': player_name, 'last_seen': time.time()},
                    'black': None
                },
                'created_at': time.time(),
                'last_move_time': time.time()
            }
            session_cleanup_time[game_id] = time.time()
            
            return jsonify({
                'success': True,
                'game_id': game_id,
                'player_color': 'white',
                'player_name': player_name,
                'waiting_for_opponent': True
            })
            
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500

    @app.route('/api/chess/multiplayer/join/<game_id>', methods=['POST'])
    def join_multiplayer_game(game_id):
        """Join an existing multiplayer chess game"""
        try:
            if game_id not in game_sessions:
                return jsonify({'success': False, 'error': 'Game not found'}), 404
            
            game_session = game_sessions[game_id]
            player_name = request.json.get('player_name', 'Player 2')
            
            # Check if game is full
            if game_session['players']['black'] is not None:
                return jsonify({'success': False, 'error': 'Game is full'}), 400
            
            # Join as black player
            game_session['players']['black'] = {
                'name': player_name, 
                'last_seen': time.time()
            }
            
            return jsonify({
                'success': True,
                'game_id': game_id,
                'player_color': 'black',
                'player_name': player_name,
                'game_ready': True
            })
            
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500

    @app.route('/chess/multiplayer')
    def multiplayer_chess():
        """Multiplayer chess interface"""
        return render_template_string(CHESS_TEMPLATE)

    return app