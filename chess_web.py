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
        
        /* Square Styling for Multiplayer Board */
        .square {
            width: 68px;
            height: 68px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 52px;
            cursor: pointer;
            transition: all 0.2s ease;
            border: 2px solid transparent;
            position: relative;
        }
        
        .square.light {
            background: linear-gradient(135deg, #f0d9b5, #ede0c8, #f5e6d3);
            box-shadow: inset 0 1px 3px rgba(255,255,255,0.4);
        }
        
        .square.dark {
            background: linear-gradient(135deg, #b58863, #a97c50, #9d7043);
            box-shadow: inset 0 1px 3px rgba(255,255,255,0.2);
        }
        
        .square:hover {
            transform: scale(1.05);
            border-color: #007bff;
            box-shadow: 0 4px 12px rgba(0, 123, 255, 0.3);
            z-index: 10;
        }
        
        .square.selected {
            background: linear-gradient(135deg, #ffd700, #ffed4e) !important;
            border-color: #ff6b6b;
            box-shadow: 0 0 20px rgba(255, 215, 0, 0.6);
            transform: scale(1.08);
        }
        
        /* Chess Piece Styling */
        .chess-piece {
            font-size: 52px;
            transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
            cursor: pointer;
            user-select: none;
            position: relative;
            display: inline-block;
            font-weight: bold;
        }

        .chess-piece.white {
            color: #ffffff;
            text-shadow: 
                0 2px 4px rgba(0,0,0,0.8),
                0 4px 8px rgba(0,0,0,0.4),
                0 1px 0 rgba(128,128,128,0.8),
                0 0 20px rgba(255,255,255,0.3);
            filter: drop-shadow(0 3px 6px rgba(0,0,0,0.5));
        }

        .chess-piece.black {
            color: #2c2c2c;
            text-shadow: 
                0 2px 4px rgba(255,255,255,0.6),
                0 4px 8px rgba(255,255,255,0.2),
                0 1px 0 rgba(255,255,255,0.4),
                0 0 15px rgba(0,0,0,0.8);
            filter: drop-shadow(0 3px 6px rgba(0,0,0,0.3));
        }

        .chess-piece:hover {
            transform: scale(1.1) translateY(-2px);
            transition: all 0.2s ease;
        }

        .chess-piece.white:hover {
            text-shadow: 
                0 3px 6px rgba(0,0,0,0.9),
                0 6px 12px rgba(0,0,0,0.5),
                0 0 25px rgba(255,255,255,0.5);
            filter: drop-shadow(0 4px 8px rgba(0,0,0,0.6));
        }

        .chess-piece.black:hover {
            text-shadow: 
                0 3px 6px rgba(255,255,255,0.8),
                0 6px 12px rgba(255,255,255,0.3),
                0 0 20px rgba(0,0,0,0.9);
            filter: drop-shadow(0 4px 8px rgba(0,0,0,0.4));
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
        <div style="display:flex; align-items:center; justify-content:space-between; gap:16px; margin-bottom:10px;">
            <h1 class="game-title" style="margin:0;">Chess For My Bachas</h1>
            <div>
                <a href="/chess/ai" class="btn btn-primary" style="text-decoration:none;">🤖 Play vs AI</a>
            </div>
        </div>
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
        let boardData = [];
        
        // Initialize board with starting position
        function initializeBoard() {
            boardData = [
                ['r', 'n', 'b', 'q', 'k', 'b', 'n', 'r'],
                ['p', 'p', 'p', 'p', 'p', 'p', 'p', 'p'],
                [' ', ' ', ' ', ' ', ' ', ' ', ' ', ' '],
                [' ', ' ', ' ', ' ', ' ', ' ', ' ', ' '],
                [' ', ' ', ' ', ' ', ' ', ' ', ' ', ' '],
                [' ', ' ', ' ', ' ', ' ', ' ', ' ', ' '],
                ['P', 'P', 'P', 'P', 'P', 'P', 'P', 'P'],
                ['R', 'N', 'B', 'Q', 'K', 'B', 'N', 'R']
            ];
        }
        
        function getPieceSymbol(ch) {
            const symbols = { 
                'K':'♔','Q':'♕','R':'♖','B':'♗','N':'♘','P':'♙',
                'k':'♚','q':'♛','r':'♜','b':'♝','n':'♞','p':'♟' 
            };
            return symbols[ch] || '';
        }
        
        function renderBoard() {
            const el = document.getElementById('chessBoard');
            if (!el) {
                console.error('Board element not found!');
                return;
            }
            console.log('Multiplayer renderBoard called, boardData:', boardData);
            el.innerHTML = '';
            let pieceCount = 0;
            for (let r = 0; r < 8; r++) {
                for (let c = 0; c < 8; c++) {
                    const sq = document.createElement('div');
                    sq.className = 'square ' + ((r + c) % 2 === 0 ? 'light' : 'dark');
                    sq.dataset.row = r;
                    sq.dataset.col = c;
                    const ch = boardData[r]?.[c] || ' ';
                    if (ch !== ' ') {
                        const symbol = getPieceSymbol(ch);
                        const isWhite = ch === ch.toUpperCase();
                        const piece = document.createElement('span');
                        piece.className = 'chess-piece ' + (isWhite ? 'white' : 'black');
                        piece.textContent = symbol;
                        sq.appendChild(piece);
                        pieceCount++;
                    }
                    el.appendChild(sq);
                }
            }
            console.log('Board rendered with', el.children.length, 'squares and', pieceCount, 'pieces');
        }
        
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
                    
                    // Initialize and render the board
                    initializeBoard();
                    renderBoard();
                    
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
                    
                    // Initialize and render the board
                    initializeBoard();
                    renderBoard();
                    
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
            console.log('DOM ready, setting up event listeners - VERSION 2');
            
            const createBtn = document.getElementById('createGameBtn');
            const joinBtn = document.getElementById('joinGameBtn');
            
            console.log('createBtn element:', createBtn);
            console.log('joinBtn element:', joinBtn);
            
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

# Single Player vs AI template
CHESS_AI_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Chess - Play vs AI</title>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        body { font-family: 'Segoe UI', Arial, sans-serif; margin: 0; padding: 20px; background: #f7f7fb; color: #333; }
        .container { max-width: 1100px; margin: 0 auto; background: #fff; padding: 20px; border-radius: 10px; }
        .header { display: flex; align-items: center; justify-content: space-between; position: relative; z-index: 10; }
        .title { font-size: 2.2em; font-weight: 700; }
        .controls { margin: 15px 0; padding: 12px; background: #fff; border: 1px solid #eee; border-radius: 10px; display: flex; gap: 12px; align-items: center; flex-wrap: wrap; }
        .chess-board { 
            display: grid !important; 
            grid-template-columns: repeat(8, 64px) !important; 
            grid-template-rows: repeat(8, 64px) !important; 
            width: 512px !important; 
            height: 512px !important; 
            border: 8px solid #654321 !important; 
            border-radius: 12px; 
            box-shadow: 0 10px 30px rgba(0,0,0,0.1); 
            margin: 20px auto !important; 
            background: #b58863 !important;
            visibility: visible !important;
            opacity: 1 !important;
        }
        .square { 
            width: 64px !important; 
            height: 64px !important; 
            display: flex !important; 
            align-items: center; 
            justify-content: center; 
            font-size: 44px; 
            cursor: pointer; 
            user-select: none; 
        }
        .light { background: #f0d9b5; }
        .dark { background: #b58863; }
        .square.selected { outline: 3px solid #4caf50; }
        .panel { background: #fff; border: 1px solid #eee; border-radius: 10px; padding: 12px 16px; min-height: 50px; }
        .status { font-weight: 600; }
        .hidden { display: none; }
        .btn { padding: 8px 14px; border: none; border-radius: 8px; background: #007bff; color:#fff; cursor:pointer; font-weight:600; }
        .btn.secondary { background: #6c757d; }
        select, input { padding: 6px 10px; border:1px solid #ddd; border-radius: 8px; }
        .layout { display:flex; gap: 24px; margin-top: 20px; flex-wrap: wrap; align-items: flex-start; }
        .right { min-width: 280px; flex:1; }
    </style>
    <script>
        // Initialize game state variables
        const gameState = {
            boardData: {{ board_array|tojson|safe }},
            selected: null,
            currentPlayer: {{ current_player|tojson|safe }},
            aiColor: {{ ai_color|tojson|safe }},
            gameStatus: {{ game_status|tojson|safe }},
            gameStarted: {{ game_started|tojson|safe }}
        };
        
        let boardData = gameState.boardData;
        let selected = gameState.selected;
        let currentPlayer = gameState.currentPlayer;
        let aiColor = gameState.aiColor;
        let gameStatus = gameState.gameStatus;
        let gameStarted = gameState.gameStarted;

        function boardStringToArray(boardString) {
            const lines = boardString.trim().split('\n');
            const res = [];
            for (let i = 0; i < 8; i++) {
                res[i] = [];
                const line = lines[i] || '';
                for (let j = 0; j < 8; j++) res[i][j] = line[j] || ' ';
            }
            return res;
        }

        function getPieceSymbol(ch) {
            const symbols = { 'K':'♔','Q':'♕','R':'♖','B':'♗','N':'♘','P':'♙','k':'♚','q':'♛','r':'♜','b':'♝','n':'♞','p':'♟' };
            return symbols[ch] || '';
        }

        function renderBoard() {
            const el = document.getElementById('board');
            if (!el) {
                console.error('Board element not found!');
                return;
            }
            console.log('AI renderBoard called, boardData:', boardData);
            console.log('boardData length:', boardData.length, 'first row:', boardData[0]);
            el.innerHTML='';
            
            let squareCount = 0;
            let pieceCount = 0;
            for (let r=0;r<8;r++) {
                for (let c=0;c<8;c++) {
                    const sq = document.createElement('div');
                    sq.className = 'square ' + ((r+c)%2===0?'light':'dark');
                    sq.dataset.row=r; sq.dataset.col=c;
                    sq.style.cssText = 'width:64px;height:64px;display:flex;align-items:center;justify-content:center;';
                    
                    const ch = boardData[r]?.[c] || ' ';
                    if (ch !== ' ' && ch !== '.') {
                        const piece = document.createElement('span');
                        const symbol = getPieceSymbol(ch);
                        piece.textContent = symbol;
                        piece.style.cssText = 'font-size:48px;user-select:none;pointer-events:none;';
                        sq.appendChild(piece);
                        pieceCount++;
                        if (r === 0 || r === 7) console.log(`Square [${r},${c}]: '${ch}' -> '${symbol}'`);
                    }
                    sq.onclick = () => onSquareClick(r,c);
                    el.appendChild(sq);
                    squareCount++;
                }
            }
            const cpEl = document.getElementById('currentPlayer');
            const gsEl = document.getElementById('gameStatus');
            if (cpEl) cpEl.textContent = currentPlayer;
            if (gsEl) gsEl.textContent = gameStatus;
            console.log('Board rendered successfully, squares:', squareCount, 'pieces:', pieceCount);
        }

        function algebraic(row,col){ return String.fromCharCode(97+col) + (8-row); }

        function clearSelection(){ selected=null; document.querySelectorAll('.square').forEach(s=>s.classList.remove('selected')); }

        function onSquareClick(r,c){
            if (!gameStarted) return;
            if (aiColor.toLowerCase()===currentPlayer.toLowerCase()) { return; } // wait AI turn
            const sq = document.querySelector(`.square[data-row="${r}"][data-col="${c}"]`);
            if (!selected) { selected={r,c}; sq.classList.add('selected'); return; }
            const from = algebraic(selected.r, selected.c);
            const to = algebraic(r,c);
            fetch('/api/chess/ai/move', { method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({from_pos: from, to_pos: to}) })
             .then(r=>r.json())
             .then(data=>{
                if (!data.success) { alert(data.message||'Invalid move'); clearSelection(); return; }
                boardData = boardStringToArray(data.board_string);
                currentPlayer = data.current_player; gameStatus = data.game_status;
                renderBoard(); clearSelection();
                if (data.ai_move) {
                    console.log('AI moved', data.ai_move);
                }
             }).catch(e=>{ alert('Error: '+e.message); clearSelection(); });
        }

        function startGame(){
            const color = document.getElementById('aiColor').value;
            const depth = parseInt(document.getElementById('aiDepth').value||'2',10);
            fetch('/chess/ai/start', { method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({ ai_color: color, depth: depth }) })
              .then(r=>r.json()).then(data=>{
                if (!data.success) { alert(data.error||'Start failed'); return; }
                boardData = boardStringToArray(data.board_string);
                currentPlayer = data.current_player; gameStatus = data.game_status; aiColor = data.ai_color; gameStarted = true;
                document.getElementById('preGame').classList.add('hidden');
                document.getElementById('inGame').classList.remove('hidden');
                renderBoard();
              });
        }

                        function quickStartGame(){
                                // Start with safe defaults even if pre-game panel is hidden
                                const defaultColor = 'black';
                                const defaultDepth = 2;
                                startWithOptions(defaultColor, defaultDepth);
                        }

                        function quickStartGameWith(depth){
                                // Start with chosen difficulty from header, AI color from header select if present
                                const colorSel = document.getElementById('aiColorHeader');
                                const color = colorSel ? colorSel.value : 'black';
                                startWithOptions(color, parseInt(depth,10));
                        }

                        function startWithOptions(color, depth){
                                fetch('/chess/ai/start', { method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({ ai_color: color, depth: depth }) })
                                    .then(r=>r.json()).then(data=>{
                                        if (!data.success) { alert(data.error||'Start failed'); return; }
                                        boardData = boardStringToArray(data.board_string);
                                        currentPlayer = data.current_player; gameStatus = data.game_status; aiColor = data.ai_color; gameStarted = true;
                                        const pre = document.getElementById('preGame');
                                        const ing = document.getElementById('inGame');
                                        if (pre) pre.classList.add('hidden');
                                        if (ing) ing.classList.remove('hidden');
                                        renderBoard();
                                    }).catch(err=>alert('Error starting game: '+err.message));
                        }

        function restartGame(){ fetch('/chess/ai/restart', {method:'POST'}).then(()=>location.reload()); }
        
        function openPreGame(){
            // Show the pre-game controls so the Start button is visible
            try {
                const pre = document.getElementById('preGame');
                const ing = document.getElementById('inGame');
                if (pre) pre.classList.remove('hidden');
                if (ing) ing.classList.add('hidden');
                gameStarted = false;
            } catch (e) { console.warn('openPreGame error', e); }
        }

        function shouldAutoStart(){
            try {
                const params = new URLSearchParams(window.location.search);
                const v = params.get('autostart') ?? params.get('auto');
                if (v === '0' || v === 'false' || v === 'no') return false;
            } catch (_) {}
            return true;
        }

        document.addEventListener('DOMContentLoaded', ()=>{ 
            console.log('DOMContentLoaded fired');
            console.log('Initial boardData:', boardData);
            
            // Always render the board first with initial position
            renderBoard(); 
            
            // Safety: if for any reason Start panel is hidden, provide a way to reveal it
            if (!gameStarted) { openPreGame(); }

            // Health ping to detect offline backend and inform the user
            fetch('/api/health', {cache:'no-store'}).then(r=>{
                if (!r.ok) throw new Error('health not ok');
                return r.json();
            }).then(()=>{
                const b = document.getElementById('offlineBanner');
                if (b) b.style.display='none';
            }).catch(()=>{
                const b = document.getElementById('offlineBanner');
                if (b) b.style.display='block';
            });

            // Auto-start a default game unless disabled via ?autostart=0
            if (!gameStarted && shouldAutoStart()) {
                console.log('Auto-starting game...');
                const colorSel = document.getElementById('aiColorHeader');
                const color = colorSel ? colorSel.value : 'black'; // default AI=black, human plays white
                const defaultDepth = 2; // Medium
                setTimeout(() => startWithOptions(color, defaultDepth), 100);
            }
        });
    </script>
    </head>
    <body>
        <div class="container">
            <div id="offlineBanner" class="panel" style="display:none;background:#ffe3e3;border-color:#ff8a8a;color:#b00020;margin-bottom:10px;">
                Backend is offline. Buttons won’t work. Please start the server and refresh this page.
            </div>
            <div class="header">
                <div class="title">♟️ Play vs AI</div>
                <div style="display:flex; gap:8px; align-items:center; flex-wrap:wrap;">
                    <div class="panel" style="padding:6px 10px; display:flex; gap:8px; align-items:center;">
                        <label>AI plays:</label>
                        <select id="aiColorHeader">
                            <option value="black">Black</option>
                            <option value="white">White</option>
                        </select>
                        <span style="opacity:0.7;">Quick start:</span>
                        <button class="btn" onclick="quickStartGameWith(1)">Easy</button>
                        <button class="btn" onclick="quickStartGameWith(2)">Medium</button>
                        <button class="btn" onclick="quickStartGameWith(3)">Hard</button>
                    </div>
                    <button class="btn" onclick="quickStartGame()">▶ Start Game</button>
                    <button class="btn" onclick="openPreGame()">🆕 New Game</button>
                    <button class="btn" onclick="location.href='/chess/multiplayer'">🌐 Multiplayer</button>
                    <button class="btn secondary" onclick="location.href='/'">Home</button>
                </div>
            </div>
            <div class="layout">
                <div class="panel" style="padding:20px;">
                    <div id="board" class="chess-board" style="display:grid !important; visibility:visible !important; opacity:1 !important;"></div>
                </div>
                <div class="right">
                    <div id="preGame" class="panel {{ '' if not game_started else 'hidden' }}">
                        <div class="controls">
                            <label>AI plays:</label>
                            <select id="aiColor">
                                <option value="black" {{ 'selected' if ai_color=='black' else '' }}>Black</option>
                                <option value="white" {{ 'selected' if ai_color=='white' else '' }}>White</option>
                            </select>
                            <label>Difficulty:</label>
                            <select id="aiDepth">
                                <option value="1">Easy (depth 1)</option>
                                <option value="2" selected>Medium (2)</option>
                                <option value="3">Hard (3)</option>
                            </select>
                            <button class="btn" onclick="startGame()">Start Game</button>
                        </div>
                    </div>
                    <div id="inGame" class="panel {{ '' if game_started else 'hidden' }}">
                        <div class="status">Current: <span id="currentPlayer">{{ current_player }}</span></div>
                        <div style="margin-top:8px;">Status: <span id="gameStatus">{{ game_status }}</span></div>
                        <div style="margin-top:12px;">
                            <button class="btn secondary" onclick="restartGame()">Restart</button>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </body>
    </html>
"""

def add_chess_routes(app):
    """Add chess game routes to Flask app"""
    
    # Initialize game session (in production, use proper session management)
    chess_game = ChessGame()

    # In-memory single-player AI games per session
    ai_games = {}
    DEFAULT_AI_DEPTH = 2
    
    def _ensure_ai_session():
        if 'ai_session_id' not in session:
            session['ai_session_id'] = str(uuid.uuid4())
        return session['ai_session_id']
    
    def _get_or_create_ai_game() -> dict:
        sid = _ensure_ai_session()
        if sid not in ai_games:
            ai_games[sid] = {
                'game': ChessGame(),
                'ai_color': 'black',
                'depth': DEFAULT_AI_DEPTH,
            }
        return ai_games[sid]
    
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

    # Single-player (vs AI) UI
    @app.route('/chess/ai', methods=['GET'])
    def chess_ai_page():
        # Show pre-game panel by default so the Start Game button is visible.
        # We don't create an AI game session until the user clicks Start.
        dummy = ChessGame()
        board_str = dummy.board.board_to_string()
        # Convert board string to a 2D array for JavaScript
        board_array = []
        for line in board_str.split('\n'):
            board_array.append(list(line))
        
        return render_template_string(
            CHESS_AI_TEMPLATE,
            board_array=board_array,
            current_player=dummy.current_player,
            game_status=dummy.get_game_status(),
            ai_color='black',
            game_started=False
        )

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

    # ----- AI Endpoints -----
    @app.route('/chess/ai/start', methods=['POST'])
    def start_ai_game():
        try:
            data = request.get_json(force=True, silent=True) or {}
            ai_color = data.get('ai_color', 'black').lower()
            depth = int(data.get('depth', DEFAULT_AI_DEPTH))

            slot = _get_or_create_ai_game()
            slot['game'] = ChessGame()  # fresh game
            slot['ai_color'] = 'white' if ai_color == 'white' else 'black'
            slot['depth'] = max(1, min(4, depth))

            game = slot['game']

            # If AI is white, let AI make the first move immediately
            if choose_ai_move and slot['ai_color'] == 'white' and game.board.current_player == Color.WHITE:
                move = choose_ai_move(game, slot['depth'])
                if move:
                    from_pos, to_pos = move
                    game.make_move(from_pos, to_pos)

            return jsonify({
                'success': True,
                'board_string': game.board.board_to_string(),
                'current_player': game.current_player,
                'game_status': game.get_game_status(),
                'ai_color': slot['ai_color']
            })
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500

    @app.route('/api/chess/ai/move', methods=['POST'])
    def api_ai_move():
        try:
            slot = _get_or_create_ai_game()
            game: ChessGame = slot['game']
            data = request.get_json(force=True) or {}
            from_pos = Position.from_algebraic(data.get('from_pos'))
            to_pos = Position.from_algebraic(data.get('to_pos'))

            # Human move
            res = game.make_move(from_pos, to_pos)
            if not (isinstance(res, dict) and res.get('success')):
                return jsonify({'success': False, 'message': res.get('message', 'Invalid move') if isinstance(res, dict) else 'Invalid move'}), 200

            ai_moved = None
            # If game continues and it's AI's turn, make AI move
            if not game.is_game_over():
                ai_color = slot['ai_color']
                if (ai_color == 'white' and game.board.current_player == Color.WHITE) or (ai_color == 'black' and game.board.current_player == Color.BLACK):
                    if choose_ai_move:
                        move = choose_ai_move(game, slot['depth'])
                    else:
                        move = None
                    if move:
                        f, t = move
                        game.make_move(f, t)
                        ai_moved = {'from': f.to_algebraic(), 'to': t.to_algebraic()}

            return jsonify({
                'success': True,
                'board_string': game.board.board_to_string(),
                'current_player': game.current_player,
                'game_status': game.get_game_status(),
                'ai_move': ai_moved
            })
        except Exception as e:
            return jsonify({'success': False, 'message': str(e)}), 500

    @app.route('/chess/ai/restart', methods=['POST'])
    def ai_restart():
        slot = _get_or_create_ai_game()
        slot['game'] = ChessGame()
        return jsonify({'success': True})

    return app