"""
Chess Game Mechanics
Handles game rules, checkmate detection, and game state management
"""

from chess_game import ChessBoard, Color, Position, PieceType
from chess_pieces import Pawn, Rook, Knight, Bishop, Queen, King
from typing import List, Optional, Tuple
from enum import Enum

class GameState(Enum):
    PLAYING = "playing"
    CHECK = "check"
    CHECKMATE = "checkmate"
    STALEMATE = "stalemate"
    DRAW = "draw"

class ChessGame:
    """Main chess game class that manages the complete game"""
    def __init__(self):
        self.board = ChessBoard()
        self.game_state = GameState.PLAYING
        self.selected_piece = None
        self.selected_position = None
        self.valid_moves = []
        self.setup_initial_position()
    
    def setup_initial_position(self):
        """Set up the initial chess position"""
        # Clear the board
        self.board.board = [[None for _ in range(8)] for _ in range(8)]
        
        # Place pawns
        for col in range(8):
            self.board.set_piece(Position(1, col), Pawn(Color.BLACK, Position(1, col)))
            self.board.set_piece(Position(6, col), Pawn(Color.WHITE, Position(6, col)))
        
        # Place other pieces
        piece_order = [Rook, Knight, Bishop, Queen, King, Bishop, Knight, Rook]
        
        for col, piece_class in enumerate(piece_order):
            # Black pieces
            self.board.set_piece(Position(0, col), piece_class(Color.BLACK, Position(0, col)))
            # White pieces
            self.board.set_piece(Position(7, col), piece_class(Color.WHITE, Position(7, col)))
        
        # Set king positions
        self.board.king_positions = {
            Color.WHITE: Position(7, 4),
            Color.BLACK: Position(0, 4)
        }
        
        # Reset game state
        self.board.current_player = Color.WHITE
        self.game_state = GameState.PLAYING
        self.selected_piece = None
        self.selected_position = None
        self.valid_moves = []
    
    def select_square(self, position: Position) -> bool:
        """Select a square on the board"""
        piece = self.board.get_piece(position)
        
        # If no piece is selected
        if not self.selected_piece:
            if piece and piece.color == self.board.current_player:
                self.selected_piece = piece
                self.selected_position = position
                self.valid_moves = self.board.get_valid_moves(piece)
                return True
            return False
        
        # If a piece is already selected
        else:
            # If clicking on the same square, deselect
            if position == self.selected_position:
                self.deselect()
                return True
            
            # If clicking on another friendly piece, select it instead
            if piece and piece.color == self.board.current_player:
                self.selected_piece = piece
                self.selected_position = position
                self.valid_moves = self.board.get_valid_moves(piece)
                return True
            
            # Try to make a move
            if position in self.valid_moves:
                success = self.make_move(self.selected_position, position)
                self.deselect()
                return success
            
            # Invalid move, deselect
            self.deselect()
            return False
    
    def deselect(self):
        """Deselect the currently selected piece"""
        self.selected_piece = None
        self.selected_position = None
        self.valid_moves = []
    
    def make_move(self, from_pos: Position, to_pos: Position) -> bool:
        """Make a move and update game state"""
        # Handle castling
        piece = self.board.get_piece(from_pos)
        if (piece and piece.piece_type == PieceType.KING and 
            abs(to_pos.col - from_pos.col) == 2):
            return self._handle_castling(from_pos, to_pos)
        
        # Make the move
        success = self.board.make_move(from_pos, to_pos)
        if success:
            # Handle pawn promotion
            self._handle_pawn_promotion(to_pos)
            
            # Update game state
            self._update_game_state()
        
        return success
    
    def _handle_castling(self, king_from: Position, king_to: Position) -> bool:
        """Handle castling move"""
        if not self.board.make_move(king_from, king_to):
            return False
        
        # Move the rook
        if king_to.col == 6:  # Kingside castling
            rook_from = Position(king_from.row, 7)
            rook_to = Position(king_from.row, 5)
        else:  # Queenside castling
            rook_from = Position(king_from.row, 0)
            rook_to = Position(king_from.row, 3)
        
        rook = self.board.get_piece(rook_from)
        if rook:
            self.board.set_piece(rook_to, rook)
            self.board.set_piece(rook_from, None)
            rook.move_to(rook_to)
        
        return True
    
    def _handle_pawn_promotion(self, position: Position):
        """Handle pawn promotion"""
        piece = self.board.get_piece(position)
        if (piece and piece.piece_type == PieceType.PAWN and 
            (position.row == 0 or position.row == 7)):
            # For now, always promote to queen
            # In a full implementation, this would prompt the player
            new_queen = Queen(piece.color, position)
            new_queen.has_moved = True
            self.board.set_piece(position, new_queen)
    
    def _update_game_state(self):
        """Update the game state after a move"""
        current_color = self.board.current_player
        
        # Check if current player is in check
        in_check = self.board.is_in_check(current_color)
        
        # Check if current player has any valid moves
        has_valid_moves = self._has_valid_moves(current_color)
        
        if in_check and not has_valid_moves:
            self.game_state = GameState.CHECKMATE
        elif not has_valid_moves:
            self.game_state = GameState.STALEMATE
        elif in_check:
            self.game_state = GameState.CHECK
        else:
            self.game_state = GameState.PLAYING
    
    def _has_valid_moves(self, color: Color) -> bool:
        """Check if a player has any valid moves"""
        for piece in self.board.get_all_pieces(color):
            if self.board.get_valid_moves(piece):
                return True
        return False
    
    def is_game_over(self) -> bool:
        """Check if the game is over"""
        return self.game_state in [GameState.CHECKMATE, GameState.STALEMATE, GameState.DRAW]
    
    def get_winner(self) -> Optional[Color]:
        """Get the winner of the game"""
        if self.game_state == GameState.CHECKMATE:
            # The player who is NOT in checkmate wins
            return Color.BLACK if self.board.current_player == Color.WHITE else Color.WHITE
        return None
    
    def get_game_status(self) -> str:
        """Get a string describing the current game status"""
        if self.game_state == GameState.CHECKMATE:
            winner = self.get_winner()
            return f"Checkmate! {winner.value.capitalize()} wins!"
        elif self.game_state == GameState.STALEMATE:
            return "Stalemate! Game is a draw."
        elif self.game_state == GameState.CHECK:
            return f"{self.board.current_player.value.capitalize()} is in check!"
        elif self.game_state == GameState.DRAW:
            return "Game is a draw!"
        else:
            return f"{self.board.current_player.value.capitalize()} to move"
    
    def get_move_history_algebraic(self) -> List[str]:
        """Get move history in algebraic notation"""
        moves = []
        for i, move in enumerate(self.board.move_history):
            move_str = self._move_to_algebraic(move)
            if i % 2 == 0:
                moves.append(f"{i//2 + 1}. {move_str}")
            else:
                moves[-1] += f" {move_str}"
        return moves
    
    def _move_to_algebraic(self, move) -> str:
        """Convert a move to algebraic notation"""
        piece = move['piece']
        from_pos = move['from']
        to_pos = move['to']
        captured = move['captured']
        
        # Basic piece notation
        if piece.piece_type == PieceType.PAWN:
            notation = ""
            if captured:
                notation = chr(ord('a') + from_pos.col) + "x"
        else:
            notation = piece.piece_type.value[0].upper()
            if captured:
                notation += "x"
        
        notation += to_pos.to_algebraic()
        
        # Add check/checkmate indicators
        # This would need to be determined based on the resulting position
        
        return notation
    
    def reset_game(self):
        """Reset the game to initial state"""
        self.__init__()
    
    def undo_last_move(self) -> bool:
        """Undo the last move (basic implementation)"""
        if not self.board.move_history:
            return False
        
        last_move = self.board.move_history.pop()
        
        # Restore the piece to original position
        piece = last_move['piece']
        self.board.set_piece(last_move['from'], piece)
        piece.position = last_move['from']
        
        # Restore captured piece if any
        if last_move['captured']:
            self.board.set_piece(last_move['to'], last_move['captured'])
        else:
            self.board.set_piece(last_move['to'], None)
        
        # Restore en passant target
        self.board.en_passant_target = last_move['en_passant_target']
        
        # Switch back the current player
        self.board.current_player = Color.BLACK if self.board.current_player == Color.WHITE else Color.WHITE
        
        # Update game state
        self._update_game_state()
        
        return True