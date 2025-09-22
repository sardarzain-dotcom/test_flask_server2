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

# Enhanced HTML template for interactive chess game
CHESS_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Chess For My Bachas - Interactive Chess Game</title>
    <meta charset="utf-8">
    <style>
        body { 
            font-family: 'Segoe UI', Arial, sans-serif; 
            margin: 0; 
            padding: 20px;
            text-align: center; 
            background: #ffffff;
            min-height: 100vh;
            color: #333333;
            display: flex;
            justify-content: center;
            align-items: flex-start;
        }
        
        .game-container {
            max-width: 1200px;
            margin: 20px auto;
            background: #ffffff;
            border-radius: 20px;
            padding: 40px;
            box-shadow: 
                0 10px 30px rgba(0,0,0,0.1),
                0 4px 10px rgba(0,0,0,0.05);
            border: 2px solid #f0f0f0;
            width: 100%;
            box-sizing: border-box;
        }
        
        .game-title {
            font-size: 3.2em;
            font-weight: bold;
            margin-bottom: 40px;
            text-shadow: 
                0 2px 4px rgba(0,0,0,0.3),
                0 0 10px rgba(255,215,0,0.5);
            background: linear-gradient(135deg, #b8860b, #ffd700, #ffed4e, #ffd700, #b8860b);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
            color: #b8860b;
            background-size: 200% 100%;
            animation: goldShimmer 3s ease-in-out infinite;
        }
        
        @keyframes goldShimmer {
            0%, 100% { 
                background-position: 0% 50%; 
            }
            50% { 
                background-position: 100% 50%; 
            }
        }
        
        .chess-board-container {
            display: flex;
            justify-content: center;
            align-items: center;
            margin: 30px auto;
            position: relative;
            width: 100%;
            padding: 20px;  /* Added padding for better spacing */
            background: radial-gradient(ellipse at center, rgba(139,69,19,0.1) 0%, transparent 70%);  /* Subtle background */
        }
        
        .chess-board { 
            display: grid;
            grid-template-columns: repeat(8, 64px);  /* Slightly larger squares */
            grid-template-rows: repeat(8, 64px);
            width: 512px;  /* Updated to match new square size */
            height: 512px;
            border: 8px solid #654321;  /* Thicker, richer brown border */
            border-radius: 16px;  /* More rounded corners */
            box-shadow: 
                0 20px 40px rgba(0,0,0,0.6),  /* Deeper shadow */
                inset 0 0 30px rgba(139,69,19,0.4),
                0 0 0 4px #8b4513,  /* Additional border ring */
                0 0 0 8px rgba(139,69,19,0.3);
            background: linear-gradient(135deg, #f0d9b5 0%, #ede0c8 100%);  /* Gradient background */
            position: relative;
            gap: 0;
            transform: perspective(1200px) rotateX(3deg);  /* Enhanced 3D effect */
        }
        
        .chess-square {
            width: 64px;  /* Updated to match board */
            height: 64px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 48px;  /* Increased to match piece size */
            font-family: 'Segoe UI Symbol', 'DejaVu Sans', monospace;
            cursor: pointer;
            transition: all 0.3s cubic-bezier(0.25, 0.46, 0.45, 0.94);
            position: relative;
            user-select: none;
            box-sizing: border-box;
            border: 1px solid rgba(0,0,0,0.15);  /* Slightly more visible borders */
        }
        
        .chess-square.light {
            background: linear-gradient(135deg, #faf7f2 0%, #f0d9b5 50%, #ede0c8 100%);
            box-shadow: 
                inset 0 2px 4px rgba(255,255,255,0.5),
                inset 0 -1px 2px rgba(0,0,0,0.1);
        }
        
        .chess-square.dark {
            background: linear-gradient(135deg, #d18b47 0%, #b58863 50%, #a67c52 100%);
            box-shadow: 
                inset 0 2px 4px rgba(0,0,0,0.3),
                inset 0 -1px 2px rgba(255,255,255,0.1);
        }
        
        .chess-square:hover {
            background: linear-gradient(135deg, #fff799 0%, #ffeb3b 50%, #fdd835 100%) !important;
            transform: scale(1.05) translateY(-1px);  /* Reduced from 1.08 for subtlety */
            z-index: 10;
            box-shadow: 
                0 8px 20px rgba(0,0,0,0.3),  /* Reduced shadow intensity */
                inset 0 0 15px rgba(255,255,255,0.6),
                0 0 0 2px #4a90e2;  /* Thinner border */
            filter: brightness(1.1) contrast(1.05);  /* Reduced intensity */
        }
        
        .chess-square.selected {
            background: linear-gradient(135deg, #4caf50 0%, #66bb6a 50%, #4caf50 100%) !important;
            box-shadow: 
                inset 0 0 20px rgba(0,0,0,0.5),
                0 0 25px rgba(76,175,80,0.7),
                0 0 0 3px #2e7d32;  /* Added border ring */
            animation: pulse 1.5s infinite;
            transform: scale(1.02);  /* Slight scale to make it stand out */
        }
        
        @keyframes pulse {
            0% { box-shadow: inset 0 0 15px rgba(0,0,0,0.5), 0 0 20px rgba(76,175,80,0.6); }
            50% { box-shadow: inset 0 0 20px rgba(0,0,0,0.7), 0 0 30px rgba(76,175,80,0.8); }
            100% { box-shadow: inset 0 0 15px rgba(0,0,0,0.5), 0 0 20px rgba(76,175,80,0.6); }
        }
        
        .chess-square.possible-move {
            background-color: #81c784 !important;
            animation: moveHint 2s infinite;
        }
        
        .chess-square.possible-move::after {
            content: '';
            position: absolute;
            width: 24px;
            height: 24px;
            background: radial-gradient(circle, #4caf50 0%, #2e7d32 70%, transparent 100%);
            border-radius: 50%;
            opacity: 0.8;
            animation: dotPulse 1.5s infinite;
        }
        
        @keyframes moveHint {
            0% { background-color: #81c784 !important; }
            50% { background-color: #a5d6a7 !important; }
            100% { background-color: #81c784 !important; }
        }
        
        @keyframes dotPulse {
            0% { transform: scale(0.8); opacity: 0.6; }
            50% { transform: scale(1.2); opacity: 1; }
            100% { transform: scale(0.8); opacity: 0.6; }
        }
        
        @keyframes moveComplete {
            0% { 
                transform: scale(1.2);
                box-shadow: 0 0 30px rgba(76,175,80,0.8);
            }
            50% { 
                transform: scale(1.05);
                box-shadow: 0 0 20px rgba(76,175,80,0.6);
            }
            100% { 
                transform: scale(1);
                box-shadow: none;
            }
        }
        
        .chess-square.move-animation {
            animation: moveComplete 0.8s ease-out;
        }
        
        @keyframes pieceGlow {
            0%, 100% { 
                filter: drop-shadow(0 0 12px rgba(255,255,255,0.7));
                transform: scale(1);
            }
            50% { 
                filter: drop-shadow(0 0 25px rgba(255,255,255,1.0));
                transform: scale(1.02);  /* Slight pulsing */
            }
        }
        
        /* Enhanced piece placement animation */
        @keyframes piecePlacement {
            0% { 
                transform: scale(0.5) translateY(-20px) rotateY(180deg);
                opacity: 0;
            }
            50% {
                transform: scale(1.1) translateY(-5px) rotateY(90deg);
                opacity: 0.8;
            }
            100% { 
                transform: scale(1) translateY(0) rotateY(0deg);
                opacity: 1;
            }
        }
        
        .chess-piece.placed {
            animation: piecePlacement 0.6s ease-out;
        }
        
        /* Piece capture animation */
        @keyframes pieceCapture {
            0% { 
                transform: scale(1);
                opacity: 1;
            }
            50% {
                transform: scale(1.3) rotate(15deg);
                opacity: 0.5;
            }
            100% { 
                transform: scale(0) rotate(45deg);
                opacity: 0;
            }
        }
        
        .chess-piece.captured {
            animation: pieceCapture 0.4s ease-in forwards;
        }
        
        .chess-piece.glow {
            animation: pieceGlow 2s ease-in-out infinite;
        }
        
        .chess-piece {
            cursor: grab;
            transition: all 0.3s ease;
            font-size: 52px;  /* Increased from 48px for even better visibility */
            line-height: 1;
            text-align: center;
            width: 100%;
            height: 100%;
            display: flex;
            align-items: center;
            justify-content: center;
            font-weight: bold;
            filter: 
                drop-shadow(4px 4px 8px rgba(0,0,0,0.6))
                drop-shadow(0 0 10px rgba(255,255,255,0.2));  /* Dual shadow effect */
            transform-origin: center;
            font-family: 'Segoe UI Symbol', 'Noto Color Emoji', 'Apple Color Emoji', 'DejaVu Sans', serif;
            /* 3D effect */
            background: radial-gradient(ellipse at center top, rgba(255,255,255,0.3) 0%, transparent 70%);
            border-radius: 50%;
        }
        
        .chess-piece.white {
            color: #ffffff;
            text-shadow: 
                4px 4px 8px rgba(0,0,0,1.0),  /* Strong black outline */
                0 0 12px rgba(255,255,255,0.9),  /* Inner white glow */
                0 0 20px rgba(255,255,255,0.7),  /* Outer white glow */
                0 0 30px rgba(220,220,255,0.5),  /* Blue aura */
                2px 2px 0px rgba(0,0,0,0.8),     /* Crisp edge definition */
                -2px -2px 0px rgba(255,255,255,0.3);  /* Highlight edge */
            filter: 
                drop-shadow(4px 4px 10px rgba(0,0,0,0.7))
                drop-shadow(0 0 15px rgba(255,255,255,0.4));
            /* Subtle 3D gradient overlay */
            background: radial-gradient(ellipse at 30% 30%, rgba(255,255,255,0.4) 0%, transparent 60%);
        }
        
        .chess-piece.black {
            color: #1a1a1a;
            text-shadow: 
                3px 3px 6px rgba(255,255,255,0.7),  /* White outline for contrast */
                0 0 10px rgba(0,0,0,1.0),           /* Strong black inner glow */
                0 0 15px rgba(0,0,0,0.8),           /* Black aura */
                0 0 20px rgba(60,60,60,0.6),        /* Gray outer glow */
                1px 1px 0px rgba(255,255,255,0.4),  /* Crisp light edge */
                -1px -1px 0px rgba(0,0,0,0.9);      /* Dark definition edge */
            filter: 
                drop-shadow(3px 3px 8px rgba(255,255,255,0.4))
                drop-shadow(0 0 12px rgba(0,0,0,0.8));
            /* Subtle 3D gradient overlay */
            background: radial-gradient(ellipse at 30% 30%, rgba(120,120,120,0.3) 0%, transparent 60%);
        }
        
        .chess-piece:hover {
            transform: scale(1.25) translateY(-4px) rotateX(10deg);  /* Enhanced 3D effect */
            filter: 
                drop-shadow(6px 10px 16px rgba(0,0,0,0.8))
                drop-shadow(0 0 20px rgba(255,255,255,0.6));
            z-index: 100;
            transition: all 0.2s ease-out;
            /* Enhanced glow effect on hover */
            animation: pieceHoverGlow 0.3s ease-out forwards;
        }
        
        @keyframes pieceHoverGlow {
            0% { filter: drop-shadow(4px 4px 8px rgba(0,0,0,0.6)) drop-shadow(0 0 10px rgba(255,255,255,0.2)); }
            100% { filter: drop-shadow(6px 10px 16px rgba(0,0,0,0.8)) drop-shadow(0 0 25px rgba(255,255,255,0.8)); }
        }
        
        .chess-piece.white:hover {
            text-shadow: 
                3px 3px 8px rgba(0,0,0,1.0),
                0 0 15px rgba(255,255,255,1.0),
                0 0 25px rgba(255,255,255,0.8),
                0 0 35px rgba(200,200,255,0.6);  /* Enhanced glow */
        }
        
        .chess-piece.black:hover {
            text-shadow: 
                2px 2px 6px rgba(255,255,255,0.8),
                0 0 12px rgba(0,0,0,1.0),
                0 0 20px rgba(0,0,0,0.8),
                0 0 30px rgba(80,80,80,0.7);  /* Enhanced glow */
        }
        
        .chess-piece.dragging {
            cursor: grabbing;
            transform: scale(1.4) rotate(8deg);  /* Larger scale and more rotation */
            z-index: 1000;
            pointer-events: none;
            filter: drop-shadow(6px 12px 20px rgba(0,0,0,0.8));  /* Deeper shadow */
            opacity: 0.9;  /* Slight transparency while dragging */
        }
        
        /* Checkmate Modal Styles */
        .checkmate-modal {
            display: none;
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(0, 0, 0, 0.8);
            backdrop-filter: blur(10px);
            z-index: 10000;
            animation: modalFadeIn 0.5s ease-out;
        }
        
        .checkmate-modal.show {
            display: flex;
            align-items: center;
            justify-content: center;
        }
        
        .checkmate-content {
            background: linear-gradient(135deg, #ffffff 0%, #f8f9fa 100%);
            border-radius: 20px;
            padding: 40px;
            text-align: center;
            box-shadow: 
                0 20px 60px rgba(0,0,0,0.5),
                0 0 0 1px rgba(255,255,255,0.1);
            max-width: 450px;
            width: 90%;
            animation: modalSlideIn 0.5s ease-out;
            position: relative;
            overflow: hidden;
        }
        
        .checkmate-content::before {
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            height: 5px;
            background: linear-gradient(90deg, #ffd700, #ffed4e, #ffd700);
            animation: goldShimmer 2s infinite;
        }
        
        .checkmate-title {
            font-size: 2.5em;
            color: #d32f2f;
            margin-bottom: 20px;
            text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
            font-weight: bold;
        }
        
        .checkmate-winner {
            font-size: 1.8em;
            color: #1976d2;
            margin-bottom: 20px;
            font-weight: bold;
        }
        
        .checkmate-details {
            color: #666;
            margin-bottom: 30px;
            font-size: 1.1em;
            line-height: 1.6;
        }
        
        .checkmate-buttons {
            display: flex;
            gap: 15px;
            justify-content: center;
            flex-wrap: wrap;
        }
        
        .checkmate-btn {
            padding: 12px 24px;
            border: none;
            border-radius: 8px;
            font-size: 1em;
            font-weight: bold;
            cursor: pointer;
            transition: all 0.3s ease;
            min-width: 120px;
        }
        
        .checkmate-btn.primary {
            background: linear-gradient(135deg, #4caf50 0%, #66bb6a 100%);
            color: white;
            box-shadow: 0 4px 15px rgba(76,175,80,0.4);
        }
        
        .checkmate-btn.primary:hover {
            transform: translateY(-2px);
            box-shadow: 0 6px 20px rgba(76,175,80,0.6);
        }
        
        .checkmate-btn.secondary {
            background: linear-gradient(135deg, #2196f3 0%, #42a5f5 100%);
            color: white;
            box-shadow: 0 4px 15px rgba(33,150,243,0.4);
        }
        
        .checkmate-btn.secondary:hover {
            transform: translateY(-2px);
            box-shadow: 0 6px 20px rgba(33,150,243,0.6);
        }
        
        @keyframes modalFadeIn {
            from { opacity: 0; }
            to { opacity: 1; }
        }
        
        @keyframes modalSlideIn {
            from { 
                transform: scale(0.7) translateY(-50px);
                opacity: 0;
            }
            to { 
                transform: scale(1) translateY(0);
                opacity: 1;
            }
        }
        
        @keyframes goldShimmer {
            0% { background-position: -200px 0; }
            100% { background-position: 200px 0; }
        }
        }
        

        .controls { 
            margin: 30px 0;
            background: rgba(255, 255, 255, 0.1);
            padding: 20px;
            border-radius: 15px;
            backdrop-filter: blur(5px);
        }
        
        .game-info {
            display: flex;
            justify-content: space-around;
            margin: 20px 0;
            flex-wrap: wrap;
        }
        
        .info-card {
            background: #f8f9fa;
            padding: 20px 25px;
            border-radius: 12px;
            margin: 8px;
            min-width: 150px;
            border: 1px solid #e9ecef;
            box-shadow: 0 2px 8px rgba(0,0,0,0.05);
        }
        
        .info-card h3 {
            color: #495057;
            margin-bottom: 10px;
            font-size: 1.1em;
        }
        
        input, button { 
            padding: 12px 20px; 
            margin: 8px; 
            border: none;
            border-radius: 8px;
            font-size: 16px;
            cursor: pointer;
            transition: all 0.2s ease;
        }
        
        button {
            background: linear-gradient(45deg, #ff6b6b, #ee5a24);
            color: white;
            font-weight: bold;
        }
        
        button:hover {
            transform: translateY(-2px);
            box-shadow: 0 5px 15px rgba(0,0,0,0.2);
        }
        
        input {
            background: rgba(255, 255, 255, 0.9);
            color: #333;
        }
        
        .message { 
            margin: 15px; 
            padding: 15px; 
            border-radius: 8px; 
            font-weight: bold;
            animation: fadeIn 0.5s ease;
        }
        
        @keyframes fadeIn {
            from { opacity: 0; transform: translateY(-10px); }
            to { opacity: 1; transform: translateY(0); }
        }
        
        .notification {
            position: fixed;
            top: 20px;
            right: 20px;
            padding: 15px 25px;
            border-radius: 10px;
            color: white;
            font-weight: bold;
            z-index: 1000;
            animation: slideIn 0.5s ease, fadeOut 0.5s ease 4.5s;
            box-shadow: 0 4px 12px rgba(0,0,0,0.3);
        }
        
        .notification.white-move {
            background: linear-gradient(45deg, #4caf50, #45a049);
        }
        
        .notification.black-move {
            background: linear-gradient(45deg, #2196f3, #1976d2);
        }
        
        .notification.warning {
            background: linear-gradient(45deg, #ff9800, #f57c00);
        }
        
        .notification.victory {
            background: linear-gradient(45deg, #9c27b0, #7b1fa2);
        }
        
        .notification.info {
            background: linear-gradient(45deg, #607d8b, #455a64);
        }
        
        @keyframes slideIn {
            from { transform: translateX(300px); opacity: 0; }
            to { transform: translateX(0); opacity: 1; }
        }
        
        @keyframes fadeOut {
            from { opacity: 1; }
            to { opacity: 0; }
        }
        
        .error { 
            background: linear-gradient(45deg, #ff6b6b, #ee5a24); 
            color: white;
        }
        
        .success { 
            background: linear-gradient(45deg, #51cf66, #40c057); 
            color: white;
        }
        
        .instructions {
            margin-top: 30px;
            background: rgba(255, 255, 255, 0.1);
            padding: 20px;
            border-radius: 15px;
            backdrop-filter: blur(5px);
        }
        
        .instructions h3 {
            color: #ffeb3b;
            margin-bottom: 15px;
        }
    </style>
</head>
<body>
    <div class="game-container">
        <h1 class="game-title">♔ ♕ Chess For My Bachas ♛ ♚</h1>
        
        <div class="game-info">
            <div class="info-card">
                <h3>Current Player</h3>
                <div id="current-player">{{ current_player }}</div>
            </div>
            <div class="info-card">
                <h3>Game Status</h3>
                <div id="game-status">{{ game_status }}</div>
            </div>
            <div class="info-card">
                <h3>Move Count</h3>
                <div id="move-count">0</div>
            </div>
        </div>
        
        <div class="chess-board-container">
            <div class="chess-board" id="chess-board">
                <!-- Board will be populated by JavaScript -->
            </div>
        </div>
        
        <div class="controls">
            <div style="margin-bottom: 20px;">
                <h3>Manual Move Entry</h3>
                <form method="post" id="move-form">
                    <input type="text" name="from_pos" id="from-pos" placeholder="From (e.g., e2)" required>
                    <input type="text" name="to_pos" id="to-pos" placeholder="To (e.g., e4)" required>
                    <button type="submit">Make Move</button>
                </form>
            </div>
            
            <form method="post" style="display: inline;">
                <input type="hidden" name="action" value="restart">
                <button type="submit">New Game</button>
            </form>
        </div>
        
        {% if message %}
        <div class="message {{ message_type }}" id="message">{{ message }}</div>
        {% endif %}
        
        <div class="instructions">
            <h3>How to Play:</h3>
            <p><strong>Mouse:</strong> Click a piece to select it, then click destination square</p>
            <p><strong>Keyboard:</strong> Enter moves in algebraic notation (e.g., e2 to e4)</p>
            <p><strong>Examples:</strong> a2, h8, d4, castling, en passant</p>
        </div>
    </div>

    <script>
        // Chess game state
        let gameState = {{ board_data | safe }};
        let selectedSquare = null;
        let currentPlayer = '{{ current_player }}';
        
        // Debug: Log initial game state
        console.log('Initial game state:', gameState);
        console.log('Current player:', currentPlayer);
        
        // Piece symbols mapping - Using solid symbols for both, differentiated by CSS color
        const pieceSymbols = {
            'P': '♙', 'R': '♖', 'N': '♘', 'B': '♗', 'Q': '♕', 'K': '♔',  // White pieces (outlined symbols)
            'p': '♟', 'r': '♜', 'n': '♞', 'b': '♝', 'q': '♛', 'k': '♚'   // Black pieces (filled symbols)
        };
        
        // Initialize the chess board
        function initializeBoard() {
            const board = document.getElementById('chess-board');
            board.innerHTML = '';
            
            for (let row = 0; row < 8; row++) {
                for (let col = 0; col < 8; col++) {
                    const square = document.createElement('div');
                    square.className = `chess-square ${(row + col) % 2 === 0 ? 'light' : 'dark'}`;
                    square.dataset.row = row;
                    square.dataset.col = col;
                    square.dataset.square = String.fromCharCode(97 + col) + (8 - row);
                    
                    // Add piece if present
                    if (gameState && gameState[row] && gameState[row][col]) {
                        const piece = gameState[row][col];
                        const pieceElement = document.createElement('span');
                        const isWhitePiece = piece === piece.toUpperCase();
                        pieceElement.className = `chess-piece ${isWhitePiece ? 'white' : 'black'}`;
                        pieceElement.textContent = getPieceSymbol(piece);
                        square.appendChild(pieceElement);
                    }
                    
                    // Add click event listener
                    square.addEventListener('click', handleSquareClick);
                    
                    board.appendChild(square);
                }
            }
        }
        
        // Get Unicode symbol for piece
        function getPieceSymbol(piece) {
            return pieceSymbols[piece] || piece;
        }
        
        // Handle square click
        function handleSquareClick(event) {
            const square = event.currentTarget;
            const row = parseInt(square.dataset.row);
            const col = parseInt(square.dataset.col);
            const squareName = square.dataset.square;
            
            if (selectedSquare === null) {
                // Select piece if there's one and it belongs to current player
                if (gameState && gameState[row] && gameState[row][col]) {
                    const piece = gameState[row][col];
                    if (isCurrentPlayerPiece(piece)) {
                        selectSquare(square);
                        selectedSquare = { row, col, square: squareName };
                    }
                }
            } else {
                // Make move
                const fromSquare = selectedSquare.square;
                const toSquare = squareName;
                
                if (fromSquare === toSquare) {
                    // Deselect if clicking same square
                    deselectSquare();
                } else {
                    // Attempt move
                    makeMove(fromSquare, toSquare);
                }
            }
        }
        
        // Check if piece belongs to current player
        function isCurrentPlayerPiece(piece) {
            const isWhitePiece = piece === piece.toUpperCase();
            return (currentPlayer === 'White' && isWhitePiece) || 
                   (currentPlayer === 'Black' && !isWhitePiece);
        }
        
        // Select square
        function selectSquare(square) {
            clearSelection();
            square.classList.add('selected');
        }
        
        // Deselect square
        function deselectSquare() {
            clearSelection();
            selectedSquare = null;
        }
        
        // Clear all selections
        function clearSelection() {
            document.querySelectorAll('.chess-square').forEach(sq => {
                sq.classList.remove('selected', 'possible-move');
            });
        }
        
        // Make move via AJAX
        function makeMove(from, to) {
            console.log('Making move:', from, 'to', to);
            
            fetch('/chess/move', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    from_pos: from,
                    to_pos: to
                })
            })
            .then(response => {
                if (!response.ok) {
                    throw new Error(`HTTP error! status: ${response.status}`);
                }
                return response.json();
            })
            .then(data => {
                console.log('Move response:', data);
                if (data.success) {
                    const previousPlayer = currentPlayer; // Store who made the move
                    gameState = data.board_data;
                    currentPlayer = data.current_player;
                    document.getElementById('current-player').textContent = currentPlayer;
                    document.getElementById('game-status').textContent = data.game_status;
                    
                    // Update move count
                    const moveCountElement = document.getElementById('move-count');
                    const currentMoveCount = parseInt(moveCountElement.textContent) + 1;
                    moveCountElement.textContent = currentMoveCount;
                    
                    showMessage(data.message, 'success');
                    
                    // Show move notification with move details
                    showMoveNotification(previousPlayer, {
                        from: from,
                        to: to,
                        moveNumber: currentMoveCount,
                        gameStatus: data.game_status
                    });
                    
                    // Show special game notifications
                    if (data.game_status.includes('Check') && !data.game_status.includes('Checkmate')) {
                        showGameNotification(`${currentPlayer} is in Check!`, 'warning');
                    } else if (data.game_status.includes('Checkmate')) {
                        // Show checkmate modal instead of simple notification
                        setTimeout(() => {
                            showCheckmateModal(previousPlayer, { moveCount: currentMoveCount });
                        }, 500);  // Small delay for better UX
                    } else if (data.game_status.includes('Stalemate')) {
                        showGameNotification('Stalemate! Game is a draw.', 'info');
                    }
                    
                    initializeBoard();
                } else {
                    showMessage(data.message, 'error');
                }
                deselectSquare();
            })
            .catch(error => {
                console.error('Error:', error);
                showMessage('Network error occurred: ' + error.message, 'error');
                deselectSquare();
            });
        }
        
        // Show message
        function showMessage(message, type) {
            const messageDiv = document.getElementById('message') || document.createElement('div');
            messageDiv.id = 'message';
            messageDiv.className = `message ${type}`;
            messageDiv.textContent = message;
            
            if (!document.getElementById('message')) {
                document.querySelector('.controls').appendChild(messageDiv);
            }
            
            // Auto-hide after 3 seconds
            setTimeout(() => {
                messageDiv.style.opacity = '0';
                setTimeout(() => {
                    if (messageDiv.parentNode) {
                        messageDiv.parentNode.removeChild(messageDiv);
                    }
                }, 500);
            }, 3000);
        }
        
        // Show move notification
        function showMoveNotification(playerWhoMoved, moveDetails) {
            const notification = document.createElement('div');
            notification.className = `notification ${playerWhoMoved.toLowerCase()}-move`;
            
            const nextPlayer = playerWhoMoved === 'White' ? 'Black' : 'White';
            notification.innerHTML = `
                <strong>${playerWhoMoved} moved!</strong><br>
                <small>Move ${moveDetails.moveNumber}: ${moveDetails.from} → ${moveDetails.to}</small><br>
                <strong>${nextPlayer}, it's your turn!</strong>
            `;
            
            document.body.appendChild(notification);
            
            // Auto-remove after 5 seconds
            setTimeout(() => {
                if (notification.parentNode) {
                    notification.parentNode.removeChild(notification);
                }
            }, 5000);
        }
        
        // Show game event notifications (check, checkmate, etc.)
        function showGameNotification(message, type = 'info') {
            const notification = document.createElement('div');
            notification.className = `notification ${type}`;
            notification.innerHTML = `<strong>${message}</strong>`;
            
            document.body.appendChild(notification);
            
            setTimeout(() => {
                if (notification.parentNode) {
                    notification.parentNode.removeChild(notification);
                }
            }, 6000);
        }
        
        // Reset game state for new game
        function resetGameState() {
            document.getElementById('move-count').textContent = '0';
            selectedSquare = null;
            clearSelection();
            // Show new game notification
            showGameNotification('New game started! White goes first.', 'info');
        }
        
        // Initialize board on page load
        document.addEventListener('DOMContentLoaded', initializeBoard);
        
        // Handle form submission
        document.getElementById('move-form').addEventListener('submit', function(e) {
            e.preventDefault();
            const from = document.getElementById('from-pos').value.trim();
            const to = document.getElementById('to-pos').value.trim();
            if (from && to) {
                makeMove(from, to);
                document.getElementById('from-pos').value = '';
                document.getElementById('to-pos').value = '';
            }
        });
        
        // Checkmate Modal Functions
        function showCheckmateModal(winner, gameStats) {
            const modal = document.getElementById('checkmateModal');
            const winnerElement = document.getElementById('checkmateWinner');
            const moveCountElement = document.getElementById('moveCount');
            
            // Set winner text with appropriate emoji
            if (winner.toLowerCase() === 'white') {
                winnerElement.innerHTML = '⚪ White Player Wins! ⚪';
                winnerElement.style.color = '#1976d2';
            } else if (winner.toLowerCase() === 'black') {
                winnerElement.innerHTML = '⚫ Black Player Wins! ⚫';
                winnerElement.style.color = '#d32f2f';
            } else {
                winnerElement.innerHTML = `👑 ${winner} Wins! 👑`;
                winnerElement.style.color = '#ff6f00';
            }
            
            // Set move count
            if (gameStats && gameStats.moveCount) {
                moveCountElement.textContent = gameStats.moveCount;
            } else {
                // Try to get from page element
                const pageMovCount = document.getElementById('move-count');
                if (pageMovCount) {
                    moveCountElement.textContent = pageMovCount.textContent || '0';
                }
            }
            
            // Show modal with animation
            modal.classList.add('show');
            
            // Add celebration confetti effect
            setTimeout(() => {
                createConfetti();
            }, 300);
        }
        
        function closeCheckmateModal() {
            const modal = document.getElementById('checkmateModal');
            modal.classList.remove('show');
        }
        
        function startNewGame() {
            closeCheckmateModal();
            // Restart the game
            fetch('/chess', {
                method: 'POST',
                headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
                body: 'action=restart'
            }).then(() => {
                location.reload();
            });
        }
        
        function createConfetti() {
            // Simple confetti animation
            for (let i = 0; i < 30; i++) {
                setTimeout(() => {
                    const confetti = document.createElement('div');
                    confetti.style.cssText = `
                        position: fixed;
                        top: -10px;
                        left: ${Math.random() * 100}%;
                        width: 10px;
                        height: 10px;
                        background: ${['#ffd700', '#ff6b6b', '#4ecdc4', '#45b7d1', '#96ceb4'][Math.floor(Math.random() * 5)]};
                        pointer-events: none;
                        z-index: 15000;
                        border-radius: 50%;
                        animation: confettiFall 3s linear forwards;
                    `;
                    document.body.appendChild(confetti);
                    
                    setTimeout(() => confetti.remove(), 3000);
                }, i * 50);
            }
        }
        
        // Add confetti animation CSS
        const confettiStyle = document.createElement('style');
        confettiStyle.textContent = `
            @keyframes confettiFall {
                to {
                    transform: translateY(100vh) rotate(360deg);
                    opacity: 0;
                }
            }
        `;
        document.head.appendChild(confettiStyle);
    </script>
    
    <!-- Checkmate Modal -->
    <div id="checkmateModal" class="checkmate-modal">
        <div class="checkmate-content">
            <h2 class="checkmate-title">🏆 CHECKMATE! 🏆</h2>
            <div class="checkmate-winner" id="checkmateWinner">Player Wins!</div>
            <div class="checkmate-details" id="checkmateDetails">
                <p>Congratulations on a brilliant game!</p>
                <p id="gameStats">Game completed in <span id="moveCount">0</span> moves.</p>
            </div>
            <div class="checkmate-buttons">
                <button class="checkmate-btn primary" onclick="startNewGame()">🔄 New Game</button>
                <button class="checkmate-btn secondary" onclick="closeCheckmateModal()">📊 Review Game</button>
            </div>
        </div>
    </div>
</body>
</html>
"""

# Multiplayer Chess Template (HTTP Polling-based)
MULTIPLAYER_CHESS_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Chess For My Bachas - Multiplayer Chess</title>
    <meta charset="utf-8">
    <style>
        body { 
            font-family: 'Segoe UI', Arial, sans-serif; 
            margin: 0; 
            padding: 20px;
            text-align: center; 
            background: #ffffff;
            min-height: 100vh;
            color: #333333;
            display: flex;
            justify-content: center;
            align-items: flex-start;
        }
        
        .game-container {
            max-width: 1200px;
            margin: 20px auto;
            background: #ffffff;
            border-radius: 20px;
            padding: 40px;
            box-shadow: 
                0 10px 30px rgba(0,0,0,0.1),
                0 4px 10px rgba(0,0,0,0.05);
            border: 2px solid #f0f0f0;
            width: 100%;
            box-sizing: border-box;
        }
        
        .game-title {
            font-size: 3.2em;
            font-weight: bold;
            margin-bottom: 40px;
            text-shadow: 
                0 2px 4px rgba(0,0,0,0.3),
                0 0 10px rgba(255,215,0,0.5);
            background: linear-gradient(135deg, #b8860b, #ffd700, #ffed4e, #ffd700, #b8860b);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
            background-size: 200% 200%;
            animation: shimmer 3s ease-in-out infinite;
        }
        
        @keyframes shimmer {
            0%, 100% { background-position: 0% 50%; }
            50% { background-position: 100% 50%; }
        }
        
        .multiplayer-controls {
            background: #f8f9fa;
            border-radius: 15px;
            padding: 20px;
            margin-bottom: 30px;
            border: 1px solid #e9ecef;
        }
        
        .player-input {
            display: flex;
            gap: 10px;
            align-items: center;
            justify-content: center;
            margin-bottom: 15px;
            flex-wrap: wrap;
        }
        
        .player-input input {
            padding: 12px 16px;
            border: 2px solid #ddd;
            border-radius: 8px;
            font-size: 16px;
            min-width: 200px;
        }
        
        .btn {
            color: white;
            border: none;
            padding: 12px 24px;
            border-radius: 8px;
            cursor: pointer;
            font-size: 16px;
            font-weight: 600;
            transition: all 0.3s ease;
            text-decoration: none;
            display: inline-block;
        }
        
        .btn:hover {
            transform: translateY(-2px);
        }
        
        .btn-primary {
            background: linear-gradient(135deg, #28a745, #20c997);
        }
        
        .btn-primary:hover {
            box-shadow: 0 4px 12px rgba(40, 167, 69, 0.3);
        }
        
        .btn-secondary {
            background: linear-gradient(135deg, #6c757d, #5a6268);
        }
        
        .btn-secondary:hover {
            box-shadow: 0 4px 12px rgba(108, 117, 125, 0.3);
        }
        
        .connection-status {
            padding: 15px;
            border-radius: 8px;
            margin-bottom: 20px;
            font-weight: 600;
        }
        
        .status-connected {
            background: #d4edda;
            color: #155724;
            border: 1px solid #c3e6cb;
        }
        
        .status-waiting {
            background: #fff3cd;
            color: #856404;
            border: 1px solid #ffeaa7;
        }
        
        .status-error {
            background: #f8d7da;
            color: #721c24;
            border: 1px solid #f5c6cb;
        }
        
        .player-info {
            display: flex;
            justify-content: space-between;
            margin-bottom: 20px;
            gap: 20px;
        }
        
        .player-card {
            flex: 1;
            background: #f8f9fa;
            border-radius: 10px;
            padding: 15px;
            border: 2px solid #e9ecef;
        }
        
        .player-card.active {
            border-color: #007bff;
            background: #e7f3ff;
        }
        
        .player-card.white {
            border-left: 5px solid #28a745;
        }
        
        .player-card.black {
            border-left: 5px solid #6c757d;
        }
        
        .chess-board {
            display: grid;
            grid-template-columns: repeat(8, 1fr);
            gap: 0;
            width: 640px;
            height: 640px;
            margin: 30px auto;
            border: 4px solid #8B4513;
            border-radius: 12px;
            box-shadow: 
                0 8px 32px rgba(139, 69, 19, 0.3),
                inset 0 0 0 2px rgba(255, 255, 255, 0.1);
            background: linear-gradient(45deg, #8B4513, #A0522D);
            padding: 8px;
        }
        
        .square {
            width: 80px;
            height: 80px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 48px;
            cursor: pointer;
            transition: all 0.2s ease;
            border: 2px solid transparent;
            position: relative;
        }
        
        .square.light {
            background: linear-gradient(135deg, #f0d9b5, #ede0c8);
        }
        
        .square.dark {
            background: linear-gradient(135deg, #b58863, #a97c50);
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
        
        /* Notification styles */
        .notification {
            position: fixed;
            top: 20px;
            right: -400px;
            background: white;
            border-radius: 12px;
            padding: 20px;
            box-shadow: 0 8px 32px rgba(0,0,0,0.15);
            border-left: 5px solid #007bff;
            z-index: 1000;
            transition: right 0.5s ease-in-out;
            max-width: 350px;
            min-width: 300px;
        }
        
        .notification.show {
            right: 20px;
        }
        
        .notification.white-move {
            border-left-color: #28a745;
        }
        
        .notification.black-move {
            border-left-color: #6c757d;
        }
        
        .notification-header {
            font-weight: bold;
            font-size: 16px;
            margin-bottom: 8px;
            color: #333;
        }
        
        .notification-content {
            color: #666;
            font-size: 14px;
            line-height: 1.4;
        }
        
        .game-info {
            background: #f8f9fa;
            border-radius: 15px;
            padding: 20px;
            margin-top: 30px;
            border: 1px solid #e9ecef;
        }
        
        .current-turn {
            font-size: 1.5em;
            font-weight: bold;
            margin-bottom: 15px;
            padding: 15px;
            border-radius: 10px;
            background: linear-gradient(135deg, #e3f2fd, #bbdefb);
            border: 2px solid #2196f3;
        }
        
        .game-controls {
            margin-top: 20px;
        }
        
        .game-controls button {
            background: linear-gradient(135deg, #dc3545, #c82333);
            color: white;
            border: none;
            padding: 12px 24px;
            border-radius: 8px;
            cursor: pointer;
            font-size: 16px;
            font-weight: 600;
            margin: 0 10px;
            transition: all 0.3s ease;
        }
        
        .game-controls button:hover {
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(220, 53, 69, 0.3);
        }
        
        .hidden {
            display: none;
        }
        
        .game-id-display {
            background: #e9ecef;
            border-radius: 8px;
            padding: 10px;
            margin: 10px 0;
            font-family: monospace;
            font-size: 18px;
            font-weight: bold;
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
                <button onclick="createGame()" class="btn btn-primary">Create New Game</button>
                <input type="text" id="gameIdInput" placeholder="Game ID to join" maxlength="8">
                <button onclick="joinGame()" class="btn btn-secondary">Join Game</button>
            </div>
            <p style="color: #666; margin: 0;">Create a new game or enter a Game ID to join an existing game</p>
        </div>
        
        <!-- Game ID Display -->
        <div id="gameIdDisplay" class="game-id-display hidden">
            Game ID: <span id="currentGameId"></span>
            <p style="margin: 5px 0 0 0; font-size: 14px; font-weight: normal;">Share this ID with your friend to play together!</p>
        </div>
        
        <!-- Connection Status -->
        <div id="connectionStatus" class="connection-status status-waiting hidden">
            Connecting...
        </div>
        
        <!-- Player Information -->
        <div id="playerInfo" class="player-info hidden">
            <div id="whitePlayer" class="player-card white">
                <h3>⚪ White Player</h3>
                <p id="whitePlayerName">Waiting...</p>
            </div>
            <div id="blackPlayer" class="player-card black">
                <h3>⚫ Black Player</h3>
                <p id="blackPlayerName">Waiting...</p>
            </div>
        </div>
        
        <!-- Chess Board -->
        <div id="chessBoard" class="chess-board hidden"></div>
        
        <!-- Game Information -->
        <div id="gameInfo" class="game-info hidden">
            <div id="currentTurn" class="current-turn">Waiting for players...</div>
            <div class="game-controls">
                <button onclick="newGame()">New Game</button>
                <button onclick="leaveGame()">Leave Game</button>
            </div>
        </div>
        
        <!-- Notification container -->
        <div id="notification" class="notification">
            <div class="notification-header" id="notificationHeader"></div>
            <div class="notification-content" id="notificationContent"></div>
        </div>
    </div>

    <script>
        // Game state
        let gameId = null;
        let playerName = '';
        let playerColor = null;
        let gameOverNotificationShown = false;
        let lastGameStatus = 'ongoing';
        let currentPlayer = 'white';
        let selectedSquare = null;
        let boardData = [];
        let gamePollingInterval = null;
        let lastMoveTime = 0;
        
        // Initialize when page loads
        document.addEventListener('DOMContentLoaded', function() {
            document.getElementById('playerName').focus();
        });
        
        // Create new game
        async function createGame() {
            playerName = document.getElementById('playerName').value.trim();
            if (!playerName) {
                alert('Please enter your name!');
                return;
            }
            
            try {
                const response = await fetch('/api/chess/multiplayer/create', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ player_name: playerName })
                });
                
                const data = await response.json();
                if (data.success) {
                    gameId = data.game_id;
                    playerColor = data.player_color;
                    gameOverNotificationShown = false; // Reset for new game
                    lastGameStatus = 'ongoing'; // Reset for new game
                    
                    document.getElementById('currentGameId').textContent = gameId;
                    document.getElementById('gameIdDisplay').classList.remove('hidden');
                    document.getElementById('connectionControls').classList.add('hidden');
                    
                    updateConnectionStatus('Game created! Waiting for opponent...', 'waiting');
                    showGameElements();
                    startGamePolling();
                } else {
                    alert('Failed to create game: ' + data.error);
                }
            } catch (error) {
                alert('Error creating game: ' + error.message);
            }
        }
        
        // Join existing game
        async function joinGame() {
            playerName = document.getElementById('playerName').value.trim();
            const gameIdToJoin = document.getElementById('gameIdInput').value.trim();
            
            if (!playerName) {
                alert('Please enter your name!');
                return;
            }
            
            if (!gameIdToJoin) {
                alert('Please enter a Game ID!');
                return;
            }
            
            try {
                const response = await fetch('/api/chess/multiplayer/join/' + gameIdToJoin, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ player_name: playerName })
                });
                
                const data = await response.json();
                if (data.success) {
                    gameId = data.game_id;
                    playerColor = data.player_color;
                    gameOverNotificationShown = false; // Reset for new game
                    lastGameStatus = 'ongoing'; // Reset for new game
                    
                    document.getElementById('currentGameId').textContent = gameId;
                    document.getElementById('gameIdDisplay').classList.remove('hidden');
                    document.getElementById('connectionControls').classList.add('hidden');
                    
                    updateConnectionStatus('Joined game! Both players ready.', 'connected');
                    updatePlayerNames(data.opponent_name, playerName);
                    showGameElements();
                    startGamePolling();
                } else {
                    alert('Failed to join game: ' + data.error);
                }
            } catch (error) {
                alert('Error joining game: ' + error.message);
            }
        }
        
        // Start polling for game updates
        function startGamePolling() {
            if (gamePollingInterval) clearInterval(gamePollingInterval);
            
            gamePollingInterval = setInterval(async () => {
                try {
                    const response = await fetch('/api/chess/multiplayer/' + gameId + '/status');
                    const data = await response.json();
                    
                    if (data.success) {
                        // Check if board has changed
                        if (data.last_move_time > lastMoveTime) {
                            updateBoard(data.board);
                            currentPlayer = data.current_player;
                            updateCurrentTurn();
                            
                            // Show move notification if it's a new move from opponent
                            if (lastMoveTime > 0 && data.current_player !== playerColor) {
                                const opponentColor = playerColor === 'white' ? 'black' : 'white';
                                const opponentName = data.players[opponentColor];
                                showNotification(
                                    opponentColor.charAt(0).toUpperCase() + opponentColor.slice(1) + ' Move',
                                    opponentName + ' made a move!',
                                    opponentColor
                                );
                            }
                            
                            lastMoveTime = data.last_move_time;
                        }
                        
                        // Update player info if both players are connected
                        if (data.game_ready && data.players.white && data.players.black) {
                            updatePlayerNames(data.players.white, data.players.black);
                            if (document.getElementById('connectionStatus').textContent.includes('Waiting')) {
                                updateConnectionStatus('Both players connected! Game ready.', 'connected');
                                showNotification('Game Ready!', 'Both players are connected. Let the game begin!', 'game');
                            }
                        }
                        
                        // Check for game over
                        if (data.game_status && data.game_status !== 'ongoing' && !gameOverNotificationShown) {
                            showNotification('Game Over!', data.game_status, 'game');
                            gameOverNotificationShown = true;
                        }
                    }
                } catch (error) {
                    console.error('Polling error:', error);
                }
            }, 1000); // Poll every second
        }
        
        // Make a move
        async function makeMove(from, to) {
            if (!gameId || currentPlayer !== playerColor) return false;
            
            try {
                const response = await fetch('/api/chess/multiplayer/' + gameId + '/move', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        from: from,
                        to: to,
                        player_color: playerColor
                    })
                });
                
                const data = await response.json();
                if (data.success) {
                    updateBoard(data.board);
                    currentPlayer = data.current_player;
                    updateCurrentTurn();
                    lastMoveTime = data.last_move_time;
                    return true;
                } else {
                    showNotification('Invalid Move', data.error, 'error');
                    return false;
                }
            } catch (error) {
                showNotification('Error', 'Failed to make move: ' + error.message, 'error');
                return false;
            }
        }
        
        // Update connection status
        function updateConnectionStatus(message, type) {
            const statusEl = document.getElementById('connectionStatus');
            statusEl.textContent = message;
            statusEl.className = 'connection-status status-' + type;
            statusEl.classList.remove('hidden');
        }
        
        // Update player names
        function updatePlayerNames(whiteName, blackName) {
            document.getElementById('whitePlayerName').textContent = whiteName;
            document.getElementById('blackPlayerName').textContent = blackName;
        }
        
        // Show game elements
        function showGameElements() {
            document.getElementById('playerInfo').classList.remove('hidden');
            document.getElementById('chessBoard').classList.remove('hidden');
            document.getElementById('gameInfo').classList.remove('hidden');
        }
        
        // Update current turn display
        function updateCurrentTurn() {
            const turnEl = document.getElementById('currentTurn');
            const isMyTurn = currentPlayer === playerColor;
            const turnText = isMyTurn ? "Your Turn!" : currentPlayer.charAt(0).toUpperCase() + currentPlayer.slice(1) + "'s Turn";
            turnEl.textContent = turnText + ' (You are ' + playerColor + ')';
            
            // Update player card active state
            document.getElementById('whitePlayer').classList.toggle('active', currentPlayer === 'white');
            document.getElementById('blackPlayer').classList.toggle('active', currentPlayer === 'black');
        }
        
        // Update chess board
        function updateBoard(boardString) {
            boardData = [];
            const lines = boardString.trim().split('\\n');
            
            for (let i = 0; i < 8; i++) {
                boardData[i] = [];
                const line = lines[i] || '';
                for (let j = 0; j < 8; j++) {
                    boardData[i][j] = line[j] || ' ';
                }
            }
            
            renderBoard();
        }
        
        // Render chess board
        function renderBoard() {
            const boardEl = document.getElementById('chessBoard');
            boardEl.innerHTML = '';
            
            for (let row = 0; row < 8; row++) {
                for (let col = 0; col < 8; col++) {
                    const square = document.createElement('div');
                    square.className = 'square ' + ((row + col) % 2 === 0 ? 'light' : 'dark');
                    square.dataset.row = row;
                    square.dataset.col = col;
                    square.onclick = handleSquareClick;
                    
                    const piece = boardData[row][col];
                    if (piece !== ' ') {
                        square.textContent = getPieceSymbol(piece);
                    }
                    
                    boardEl.appendChild(square);
                }
            }
        }
        
        // Get piece Unicode symbol
        function getPieceSymbol(piece) {
            const symbols = {
                'K': '♔', 'Q': '♕', 'R': '♖', 'B': '♗', 'N': '♘', 'P': '♙',
                'k': '♚', 'q': '♛', 'r': '♜', 'b': '♝', 'n': '♞', 'p': '♟'
            };
            return symbols[piece] || piece;
        }
        
        // Handle square click
        function handleSquareClick(event) {
            if (!gameId || currentPlayer !== playerColor) {
                if (currentPlayer !== playerColor) {
                    showNotification('Not Your Turn', "Wait for your opponent's move", 'error');
                }
                return;
            }
            
            const square = event.currentTarget;
            const row = parseInt(square.dataset.row);
            const col = parseInt(square.dataset.col);
            
            if (selectedSquare) {
                // Make move
                const fromPos = positionToAlgebraic(selectedSquare.row, selectedSquare.col);
                const toPos = positionToAlgebraic(row, col);
                
                makeMove(fromPos, toPos).then(success => {
                    if (success) {
                        clearSelection();
                    }
                });
            } else {
                // Select piece (only if it's the player's piece)
                const piece = boardData[row][col];
                if (piece !== ' ') {
                    const isWhitePiece = piece === piece.toUpperCase();
                    if ((playerColor === 'white' && isWhitePiece) || (playerColor === 'black' && !isWhitePiece)) {
                        selectedSquare = { row: row, col: col };
                        square.classList.add('selected');
                    }
                }
            }
        }
        
        // Clear selection
        function clearSelection() {
            selectedSquare = null;
            document.querySelectorAll('.square').forEach(function(sq) {
                sq.classList.remove('selected');
            });
        }
        
        // Convert position to algebraic notation
        function positionToAlgebraic(row, col) {
            const file = String.fromCharCode(97 + col); // a-h
            const rank = 8 - row; // 8-1
            return file + rank;
        }
        
        // Show notification
        function showNotification(header, content, type) {
            const notification = document.getElementById('notification');
            const headerEl = document.getElementById('notificationHeader');
            const contentEl = document.getElementById('notificationContent');
            
            headerEl.textContent = header;
            contentEl.textContent = content;
            
            // Remove existing type classes
            notification.classList.remove('white-move', 'black-move');
            
            // Add type-specific class
            if (type === 'white') {
                notification.classList.add('white-move');
            } else if (type === 'black') {
                notification.classList.add('black-move');
            }
            
            // Show notification
            notification.classList.add('show');
            
            // Hide after 4 seconds
            setTimeout(function() {
                notification.classList.remove('show');
            }, 4000);
        }
        
        // New game function
        function newGame() {
            if (confirm('Start a new game? This will create a fresh game.')) {
                leaveGame();
                document.getElementById('connectionControls').classList.remove('hidden');
                document.getElementById('gameIdDisplay').classList.add('hidden');
            }
        }
        
        // Leave game function
        function leaveGame() {
            if (gamePollingInterval) {
                clearInterval(gamePollingInterval);
                gamePollingInterval = null;
            }
            
            gameId = null;
            playerColor = null;
            selectedSquare = null;
            boardData = [];
            
            document.getElementById('connectionControls').classList.remove('hidden');
            document.getElementById('gameIdDisplay').classList.add('hidden');
            document.getElementById('connectionStatus').classList.add('hidden');
            document.getElementById('playerInfo').classList.add('hidden');
            document.getElementById('chessBoard').classList.add('hidden');
            document.getElementById('gameInfo').classList.add('hidden');
            
            // Clear inputs
            document.getElementById('playerName').value = '';
            document.getElementById('gameIdInput').value = '';
        }
        
        // Checkmate Modal Functions (same as single-player)
        function showCheckmateModal(winner, gameStats) {
            const modal = document.getElementById('checkmateModal');
            const winnerElement = document.getElementById('checkmateWinner');
            const moveCountElement = document.getElementById('moveCount');
            
            // Set winner text with appropriate emoji
            if (winner.toLowerCase() === 'white') {
                winnerElement.innerHTML = '⚪ White Player Wins! ⚪';
                winnerElement.style.color = '#1976d2';
            } else if (winner.toLowerCase() === 'black') {
                winnerElement.innerHTML = '⚫ Black Player Wins! ⚫';
                winnerElement.style.color = '#d32f2f';
            } else {
                winnerElement.innerHTML = `👑 ${winner} Wins! 👑`;
                winnerElement.style.color = '#ff6f00';
            }
            
            // Set move count from multiplayer data
            if (gameStats && gameStats.moveCount) {
                moveCountElement.textContent = gameStats.moveCount;
            } else {
                moveCountElement.textContent = moveCount || '0';
            }
            
            // Show modal with animation
            modal.classList.add('show');
            
            // Add celebration confetti effect
            setTimeout(() => {
                createConfetti();
            }, 300);
        }
        
        function closeCheckmateModal() {
            const modal = document.getElementById('checkmateModal');
            modal.classList.remove('show');
        }
        
        function startNewGame() {
            closeCheckmateModal();
            // Reload page to start fresh
            location.reload();
        }
        
        function createConfetti() {
            // Simple confetti animation
            for (let i = 0; i < 30; i++) {
                setTimeout(() => {
                    const confetti = document.createElement('div');
                    confetti.style.cssText = `
                        position: fixed;
                        top: -10px;
                        left: ${Math.random() * 100}%;
                        width: 10px;
                        height: 10px;
                        background: ${['#ffd700', '#ff6b6b', '#4ecdc4', '#45b7d1', '#96ceb4'][Math.floor(Math.random() * 5)]};
                        pointer-events: none;
                        z-index: 15000;
                        border-radius: 50%;
                        animation: confettiFall 3s linear forwards;
                    `;
                    document.body.appendChild(confetti);
                    
                    setTimeout(() => confetti.remove(), 3000);
                }, i * 50);
            }
        }
        
        // Add confetti animation CSS
        const confettiStyle = document.createElement('style');
        confettiStyle.textContent = `
            @keyframes confettiFall {
                to {
                    transform: translateY(100vh) rotate(360deg);
                    opacity: 0;
                }
            }
        `;
        document.head.appendChild(confettiStyle);
    </script>
    
    <!-- Checkmate Modal -->
    <div id="checkmateModal" class="checkmate-modal">
        <div class="checkmate-content">
            <h2 class="checkmate-title">🏆 CHECKMATE! 🏆</h2>
            <div class="checkmate-winner" id="checkmateWinner">Player Wins!</div>
            <div class="checkmate-details" id="checkmateDetails">
                <p>Congratulations on a brilliant multiplayer game!</p>
                <p id="gameStats">Game completed in <span id="moveCount">0</span> moves.</p>
            </div>
            <div class="checkmate-buttons">
                <button class="checkmate-btn primary" onclick="startNewGame()">🔄 New Game</button>
                <button class="checkmate-btn secondary" onclick="closeCheckmateModal()">📊 Review Game</button>
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
    
    def get_board_data():
        """Convert board to 2D array for JavaScript"""
        try:
            board_data = []
            for row in range(8):
                board_row = []
                for col in range(8):
                    piece = chess_game.board.board[row][col]
                    if piece:
                        # Convert piece to simple character representation
                        symbols = {
                            PieceType.PAWN: 'P',
                            PieceType.ROOK: 'R',
                            PieceType.KNIGHT: 'N',
                            PieceType.BISHOP: 'B',
                            PieceType.QUEEN: 'Q',
                            PieceType.KING: 'K'
                        }
                        symbol = symbols.get(piece.piece_type, '?')
                        board_row.append(symbol if piece.color == Color.WHITE else symbol.lower())
                    else:
                        board_row.append(None)
                board_data.append(board_row)
            return board_data
        except Exception as e:
            print(f"Error generating board data: {e}")
            # Return empty 8x8 board as fallback
            return [[None for _ in range(8)] for _ in range(8)]
    
    @app.route('/chess')
    def chess_game_page():
        """Chess game web interface"""
        try:
            board_data = get_board_data()
            current_player = chess_game.current_player.title()
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
    
    @app.route('/chess/move', methods=['POST'])
    def make_chess_move_ajax():
        """Handle chess moves via AJAX"""
        try:
            data = request.get_json()
            from_pos = data.get('from_pos', '').strip().lower()
            to_pos = data.get('to_pos', '').strip().lower()
            
            if not from_pos or not to_pos:
                return jsonify({
                    'success': False,
                    'message': 'Please provide both from and to positions'
                })
            
            # Convert algebraic notation to Position objects
            try:
                from_position = Position.from_algebraic(from_pos)
                to_position = Position.from_algebraic(to_pos)
                
                # Make the move
                result = chess_game.make_move(from_position, to_position)
                
                if result['success']:
                    return jsonify({
                        'success': True,
                        'message': f'Move {from_pos} to {to_pos} successful!',
                        'board_data': get_board_data(),
                        'current_player': chess_game.current_player.title(),
                        'game_status': chess_game.get_game_status(),
                        'move_notation': result.get('move_notation', ''),
                        'move_count': chess_game.move_count
                    })
                else:
                    return jsonify({
                        'success': False,
                        'message': result.get('message', f'Invalid move: {from_pos} to {to_pos}')
                    })
            except Exception as e:
                return jsonify({
                    'success': False,
                    'message': f'Invalid position format: {e}'
                })
                
        except Exception as e:
            return jsonify({
                'success': False,
                'message': f'Error processing move: {e}'
            }), 500
    
    @app.route('/chess', methods=['POST'])
    def make_chess_move():
        """Handle chess moves from form submission"""
        try:
            nonlocal chess_game
            
            # Check if it's a restart request
            if request.form.get('action') == 'restart':
                chess_game = ChessGame()
                message = "New game started!"
                message_type = "success"
            else:
                # Handle move
                from_pos = request.form.get('from_pos', '').strip().lower()
                to_pos = request.form.get('to_pos', '').strip().lower()
                
                if not from_pos or not to_pos:
                    message = "Please enter both from and to positions"
                    message_type = "error"
                else:
                    # Convert algebraic notation to Position objects
                    try:
                        from_position = Position.from_algebraic(from_pos)
                        to_position = Position.from_algebraic(to_pos)
                        
                        # Make the move
                        result = chess_game.make_move(from_position, to_position)
                        if result['success']:
                            message = f"Move {from_pos} to {to_pos} successful!"
                            message_type = "success"
                        else:
                            message = result.get('message', f"Invalid move: {from_pos} to {to_pos}")
                            message_type = "error"
                    except Exception as e:
                        message = f"Invalid position format: {e}"
                        message_type = "error"
            
            # Render updated board
            board_data = get_board_data()
            current_player = chess_game.current_player.title()
            game_status = chess_game.get_game_status()
            
            return render_template_string(
                CHESS_TEMPLATE,
                board_data=json.dumps(board_data),
                current_player=current_player,
                game_status=game_status,
                message=message,
                message_type=message_type
            )
            
        except Exception as e:
            return f"Error processing move: {e}", 500
    
    @app.route('/api/chess/status')
    def chess_api_status():
        """API endpoint for chess game status"""
        try:
            return jsonify({
                'current_player': chess_game.current_player,
                'game_status': chess_game.get_game_status(),
                'board': str(chess_game.board),
                'move_count': chess_game.move_count
            })
        except Exception as e:
            return jsonify({'error': str(e)}), 500

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
            cleanup_old_sessions()
            
            if game_id not in game_sessions:
                return jsonify({'success': False, 'error': 'Game not found'}), 404
            
            player_name = request.json.get('player_name', 'Player 2')
            game_session = game_sessions[game_id]
            
            # Check if game is full
            if game_session['players']['black'] is not None:
                return jsonify({'success': False, 'error': 'Game is full'}), 400
            
            # Add black player
            game_session['players']['black'] = {
                'name': player_name, 
                'last_seen': time.time()
            }
            
            return jsonify({
                'success': True,
                'game_id': game_id,
                'player_color': 'black',
                'player_name': player_name,
                'opponent_name': game_session['players']['white']['name'],
                'game_ready': True
            })
            
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500
    
    @app.route('/api/chess/multiplayer/<game_id>/status', methods=['GET'])
    def get_multiplayer_game_status(game_id):
        """Get current status of a multiplayer game"""
        try:
            cleanup_old_sessions()
            
            if game_id not in game_sessions:
                return jsonify({'success': False, 'error': 'Game not found'}), 404
            
            game_session = game_sessions[game_id]
            game = game_session['game']
            
            return jsonify({
                'success': True,
                'board': game.board.board_to_string(),
                'current_player': game.current_player,
                'game_status': game.get_game_status(),
                'move_count': game.move_count,
                'players': {
                    'white': game_session['players']['white']['name'] if game_session['players']['white'] else None,
                    'black': game_session['players']['black']['name'] if game_session['players']['black'] else None
                },
                'game_ready': game_session['players']['black'] is not None,
                'last_move_time': game_session['last_move_time']
            })
            
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500
    
    @app.route('/api/chess/multiplayer/<game_id>/move', methods=['POST'])
    def make_multiplayer_move(game_id):
        """Make a move in a multiplayer game"""
        try:
            cleanup_old_sessions()
            
            if game_id not in game_sessions:
                return jsonify({'success': False, 'error': 'Game not found'}), 404
            
            game_session = game_sessions[game_id]
            game = game_session['game']
            
            from_pos = request.json.get('from')
            to_pos = request.json.get('to')
            player_color = request.json.get('player_color')
            
            # Validate it's the player's turn
            if player_color != game.current_player:
                return jsonify({'success': False, 'error': 'Not your turn'}), 400
            
            # Convert positions
            from_position = Position.from_algebraic(from_pos)
            to_position = Position.from_algebraic(to_pos)
            
            # Make the move
            result = game.make_move(from_position, to_position)
            
            if result['success']:
                game_session['last_move_time'] = time.time()
                
                return jsonify({
                    'success': True,
                    'board': game.board.board_to_string(),
                    'current_player': game.current_player,
                    'game_status': game.get_game_status(),
                    'move_count': game.move_count,
                    'move_notation': result.get('move_notation', ''),
                    'last_move_time': game_session['last_move_time']
                })
            else:
                return jsonify({'success': False, 'error': result.get('message', 'Invalid move')}), 400
                
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500

    @app.route('/chess/multiplayer')
    def multiplayer_chess():
        """Multiplayer chess game page"""
        return render_template_string(MULTIPLAYER_CHESS_TEMPLATE)