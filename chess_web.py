# Chess game web interface for Flask
from flask import Flask, render_template_string, request, jsonify
from chess_mechanics import ChessGame
from chess_game import Position, Color, PieceType
import json

# Enhanced HTML template for interactive chess game
CHESS_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Interactive Chess Game</title>
    <meta charset="utf-8">
    <style>
        body { 
            font-family: 'Segoe UI', Arial, sans-serif; 
            margin: 20px; 
            text-align: center; 
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            color: white;
        }
        
        .game-container {
            max-width: 1200px;
            margin: 0 auto;
            background: rgba(255, 255, 255, 0.1);
            border-radius: 20px;
            padding: 30px;
            backdrop-filter: blur(10px);
            box-shadow: 
                0 25px 50px rgba(0,0,0,0.3),
                inset 0 1px 0 rgba(255,255,255,0.2);
            border: 1px solid rgba(255,255,255,0.1);
        }
        
        .game-title {
            font-size: 3em;
            font-weight: bold;
            margin-bottom: 30px;
            text-shadow: 
                0 0 20px rgba(255,255,255,0.5),
                0 5px 15px rgba(0,0,0,0.3);
            background: linear-gradient(135deg, #ffd700, #ffed4e, #ffd700);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
            color: transparent;
        }
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
        }
        
        .chess-board-container {
            display: inline-block;
            margin: 20px;
            position: relative;
        }
        
        .chess-board { 
            display: grid;
            grid-template-columns: repeat(8, 60px);
            grid-template-rows: repeat(8, 60px);
            width: 480px;
            height: 480px;
            border: 6px solid #8b4513;
            border-radius: 12px;
            box-shadow: 
                0 15px 35px rgba(0,0,0,0.5),
                inset 0 0 20px rgba(139,69,19,0.3);
            background: #f0d9b5;
            position: relative;
            gap: 0;
            transform: perspective(1000px) rotateX(2deg);
        }
        
        .chess-square {
            width: 60px;
            height: 60px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 42px;
            font-family: 'Segoe UI Symbol', 'DejaVu Sans', monospace;
            cursor: pointer;
            transition: all 0.3s cubic-bezier(0.25, 0.46, 0.45, 0.94);
            position: relative;
            user-select: none;
            box-sizing: border-box;
            border: 1px solid rgba(0,0,0,0.1);
        }
        
        .chess-square.light {
            background: linear-gradient(135deg, #f7f1e8 0%, #f0d9b5 50%, #ede0c8 100%);
            box-shadow: inset 0 1px 3px rgba(255,255,255,0.4);
        }
        
        .chess-square.dark {
            background: linear-gradient(135deg, #c4956c 0%, #b58863 50%, #a67c52 100%);
            box-shadow: inset 0 1px 3px rgba(0,0,0,0.2);
        }
        
        .chess-square:hover {
            background: linear-gradient(135deg, #fff176 0%, #ffeb3b 50%, #fdd835 100%) !important;
            transform: scale(1.08) translateY(-2px);
            z-index: 10;
            box-shadow: 
                0 12px 30px rgba(0,0,0,0.4),
                inset 0 0 20px rgba(255,255,255,0.4),
                0 0 0 3px #4a90e2;
            filter: brightness(1.15) contrast(1.1);
        }
        
        .chess-square.selected {
            background-color: #4caf50 !important;
            box-shadow: 
                inset 0 0 15px rgba(0,0,0,0.5),
                0 0 20px rgba(76,175,80,0.6);
            animation: pulse 1.5s infinite;
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
                filter: drop-shadow(0 0 10px rgba(255,255,255,0.6));
            }
            50% { 
                filter: drop-shadow(0 0 20px rgba(255,255,255,0.9));
            }
        }
        
        .chess-piece.glow {
            animation: pieceGlow 2s ease-in-out infinite;
        }
        
        .chess-piece {
            cursor: grab;
            transition: all 0.3s ease;
            font-size: 42px;
            line-height: 1;
            text-align: center;
            width: 100%;
            height: 100%;
            display: flex;
            align-items: center;
            justify-content: center;
            font-weight: bold;
            filter: drop-shadow(2px 2px 4px rgba(0,0,0,0.4));
            transform-origin: center;
        }
        
        .chess-piece.white {
            color: #ffffff;
            text-shadow: 
                2px 2px 4px rgba(0,0,0,0.8),
                0 0 8px rgba(255,255,255,0.6),
                0 0 12px rgba(255,255,255,0.4);
        }
        
        .chess-piece.black {
            color: #1a1a1a;
            text-shadow: 
                1px 1px 3px rgba(255,255,255,0.5),
                0 0 6px rgba(0,0,0,0.8),
                0 0 10px rgba(0,0,0,0.6);
        }
        
        .chess-piece:hover {
            transform: scale(1.15) translateY(-2px);
            filter: drop-shadow(3px 6px 8px rgba(0,0,0,0.6));
            z-index: 100;
        }
        
        .chess-piece.white:hover {
            text-shadow: 
                2px 2px 6px rgba(0,0,0,0.9),
                0 0 12px rgba(255,255,255,0.8),
                0 0 20px rgba(255,255,255,0.6);
        }
        
        .chess-piece.black:hover {
            text-shadow: 
                1px 1px 4px rgba(255,255,255,0.7),
                0 0 10px rgba(0,0,0,0.9),
                0 0 16px rgba(0,0,0,0.8);
        }
        
        .chess-piece.dragging {
            cursor: grabbing;
            transform: scale(1.3) rotate(5deg);
            z-index: 1000;
            pointer-events: none;
            filter: drop-shadow(4px 8px 12px rgba(0,0,0,0.8));
        }
        }
        
        .board-coordinates {
            position: absolute;
            font-weight: bold;
            color: #8b4513;
            font-size: 14px;
        }
        
        .coord-file {
            bottom: -25px;
            width: 60px;
            text-align: center;
        }
        
        .coord-rank {
            left: -25px;
            height: 60px;
            display: flex;
            align-items: center;
            justify-content: center;
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
            background: rgba(255, 255, 255, 0.2);
            padding: 15px 25px;
            border-radius: 10px;
            margin: 5px;
            min-width: 150px;
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
        <h1 class="game-title">♔ ♕ Elite Chess Grandmaster ♛ ♚</h1>
        
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
                <h3>Selected Square</h3>
                <div id="selected-square">None</div>
            </div>
        </div>
        
        <div class="chess-board-container">
            <div class="chess-board" id="chess-board">
                <!-- Board will be populated by JavaScript -->
            </div>
            
            <!-- Board coordinates -->
            <div class="board-coordinates">
                <div class="coord-file" style="left: 4px;">a</div>
                <div class="coord-file" style="left: 64px;">b</div>
                <div class="coord-file" style="left: 124px;">c</div>
                <div class="coord-file" style="left: 184px;">d</div>
                <div class="coord-file" style="left: 244px;">e</div>
                <div class="coord-file" style="left: 304px;">f</div>
                <div class="coord-file" style="left: 364px;">g</div>
                <div class="coord-file" style="left: 424px;">h</div>
                
                <div class="coord-rank" style="top: 4px;">8</div>
                <div class="coord-rank" style="top: 64px;">7</div>
                <div class="coord-rank" style="top: 124px;">6</div>
                <div class="coord-rank" style="top: 184px;">5</div>
                <div class="coord-rank" style="top: 244px;">4</div>
                <div class="coord-rank" style="top: 304px;">3</div>
                <div class="coord-rank" style="top: 364px;">2</div>
                <div class="coord-rank" style="top: 424px;">1</div>
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
            'P': '♟', 'R': '♜', 'N': '♞', 'B': '♝', 'Q': '♛', 'K': '♚',  // White pieces (solid symbols, white color)
            'p': '♟', 'r': '♜', 'n': '♞', 'b': '♝', 'q': '♛', 'k': '♚'   // Black pieces (solid symbols, black color)
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
                        document.getElementById('selected-square').textContent = squareName;
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
            document.getElementById('selected-square').textContent = 'None';
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
                    gameState = data.board_data;
                    currentPlayer = data.current_player;
                    document.getElementById('current-player').textContent = currentPlayer;
                    document.getElementById('game-status').textContent = data.game_status;
                    showMessage(data.message, 'success');
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
            current_player = chess_game.board.current_player.value.title()
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
                if chess_game.make_move(from_position, to_position):
                    return jsonify({
                        'success': True,
                        'message': f'Move {from_pos} to {to_pos} successful!',
                        'board_data': get_board_data(),
                        'current_player': chess_game.board.current_player.value.title(),
                        'game_status': chess_game.get_game_status()
                    })
                else:
                    return jsonify({
                        'success': False,
                        'message': f'Invalid move: {from_pos} to {to_pos}'
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
                        if chess_game.make_move(from_position, to_position):
                            message = f"Move {from_pos} to {to_pos} successful!"
                            message_type = "success"
                        else:
                            message = f"Invalid move: {from_pos} to {to_pos}"
                            message_type = "error"
                    except Exception as e:
                        message = f"Invalid position format: {e}"
                        message_type = "error"
            
            # Render updated board
            board_data = get_board_data()
            current_player = chess_game.board.current_player.value.title()
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
                'current_player': chess_game.board.current_player.value,
                'game_status': chess_game.get_game_status(),
                'board': str(chess_game.board),
                'move_count': len(chess_game.move_history)
            })
        except Exception as e:
            return jsonify({'error': str(e)}), 500