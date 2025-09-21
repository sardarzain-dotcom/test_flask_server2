# Chess game web interface for Flask
from flask import Flask, render_template_string, request, jsonify
from chess_mechanics import ChessGame
from chess_game import Position

# HTML template for web chess game
CHESS_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Online Chess Game</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; text-align: center; }
        .chess-board { 
            display: inline-block; 
            border: 2px solid #333; 
            background: #f0d9b5;
            font-family: monospace;
            font-size: 24px;
            line-height: 1.2;
            white-space: pre;
            padding: 10px;
        }
        .controls { margin: 20px; }
        input { padding: 5px; margin: 5px; }
        button { padding: 10px 15px; margin: 5px; cursor: pointer; }
        .message { margin: 10px; padding: 10px; background: #e7f3ff; border-radius: 5px; }
        .error { background: #ffebee; }
        .success { background: #e8f5e8; }
    </style>
</head>
<body>
    <h1>♔ Online Chess Game ♕</h1>
    
    <div class="chess-board">{{ board_display }}</div>
    
    <div class="controls">
        <h3>Current Player: {{ current_player }}</h3>
        <p>Game Status: {{ game_status }}</p>
        
        <form method="post">
            <input type="text" name="from_pos" placeholder="From (e.g., e2)" required>
            <input type="text" name="to_pos" placeholder="To (e.g., e4)" required>
            <button type="submit">Make Move</button>
        </form>
        
        <form method="post" style="display: inline;">
            <input type="hidden" name="action" value="restart">
            <button type="submit">New Game</button>
        </form>
    </div>
    
    {% if message %}
    <div class="message {{ message_type }}">{{ message }}</div>
    {% endif %}
    
    <div style="margin-top: 30px;">
        <h3>How to Play:</h3>
        <p>Enter moves in algebraic notation (e.g., e2 to e4)</p>
        <p>Examples: a2, h8, d4, etc.</p>
    </div>
</body>
</html>
"""

def add_chess_routes(app):
    """Add chess game routes to Flask app"""
    
    # Initialize game session (in production, use proper session management)
    chess_game = ChessGame()
    
    @app.route('/chess')
    def chess_game_page():
        """Chess game web interface"""
        try:
            board_display = str(chess_game.board)
            current_player = chess_game.board.current_player.value.title()
            game_status = chess_game.get_game_status()
            
            return render_template_string(
                CHESS_TEMPLATE,
                board_display=board_display,
                current_player=current_player,
                game_status=game_status,
                message=None,
                message_type=''
            )
        except Exception as e:
            return f"Error loading chess game: {e}", 500
    
    @app.route('/chess', methods=['POST'])
    def make_chess_move():
        """Handle chess moves"""
        try:
            # Check if it's a restart request
            if request.form.get('action') == 'restart':
                nonlocal chess_game
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
            board_display = str(chess_game.board)
            current_player = chess_game.board.current_player.value.title()
            game_status = chess_game.get_game_status()
            
            return render_template_string(
                CHESS_TEMPLATE,
                board_display=board_display,
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