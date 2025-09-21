"""
Chess Game Implementation
A complete chess game with GUI using Python and Pygame
"""

from enum import Enum
from typing import List, Optional, Tuple, Dict
import copy

class Color(Enum):
    WHITE = "white"
    BLACK = "black"

class PieceType(Enum):
    PAWN = "pawn"
    ROOK = "rook"
    KNIGHT = "knight"
    BISHOP = "bishop"
    QUEEN = "queen"
    KING = "king"

class Position:
    """Represents a position on the chess board"""
    def __init__(self, row: int, col: int):
        self.row = row
        self.col = col
    
    def __eq__(self, other):
        if other is None:
            return False
        return self.row == other.row and self.col == other.col
    
    def __str__(self):
        return f"({self.row}, {self.col})"
    
    def __repr__(self):
        return f"Position({self.row}, {self.col})"
    
    def is_valid(self) -> bool:
        """Check if position is within board bounds"""
        return 0 <= self.row < 8 and 0 <= self.col < 8
    
    def to_algebraic(self) -> str:
        """Convert to algebraic notation (e.g., 'e4')"""
        return chr(ord('a') + self.col) + str(8 - self.row)

class Piece:
    """Base class for all chess pieces"""
    def __init__(self, color: Color, position: Position):
        self.color = color
        self.position = position
        self.has_moved = False
        self.piece_type = None
    
    def __str__(self):
        return f"{self.color.value} {self.piece_type.value if self.piece_type else 'piece'}"
    
    def get_possible_moves(self, board) -> List[Position]:
        """Get all possible moves for this piece"""
        raise NotImplementedError("Subclasses must implement get_possible_moves")
    
    def is_valid_move(self, target: Position, board) -> bool:
        """Check if a move to target position is valid"""
        possible_moves = self.get_possible_moves(board)
        return target in possible_moves
    
    def move_to(self, target: Position):
        """Move piece to target position"""
        self.position = target
        self.has_moved = True

class ChessBoard:
    """Represents the chess board and manages piece positions"""
    def __init__(self):
        self.board: List[List[Optional[Piece]]] = [[None for _ in range(8)] for _ in range(8)]
        self.current_player = Color.WHITE
        self.move_history: List[Dict] = []
        self.captured_pieces: Dict[Color, List[Piece]] = {Color.WHITE: [], Color.BLACK: []}
        self.king_positions = {Color.WHITE: Position(7, 4), Color.BLACK: Position(0, 4)}
        self.en_passant_target: Optional[Position] = None
        
    def get_piece(self, position: Position) -> Optional[Piece]:
        """Get piece at given position"""
        if not position.is_valid():
            return None
        return self.board[position.row][position.col]
    
    def set_piece(self, position: Position, piece: Optional[Piece]):
        """Set piece at given position"""
        if position.is_valid():
            self.board[position.row][position.col] = piece
            if piece:
                piece.position = position
    
    def remove_piece(self, position: Position) -> Optional[Piece]:
        """Remove and return piece at given position"""
        piece = self.get_piece(position)
        if piece:
            self.board[position.row][position.col] = None
        return piece
    
    def is_empty(self, position: Position) -> bool:
        """Check if position is empty"""
        return self.get_piece(position) is None
    
    def is_enemy_piece(self, position: Position, color: Color) -> bool:
        """Check if position contains an enemy piece"""
        piece = self.get_piece(position)
        return piece is not None and piece.color != color
    
    def is_friendly_piece(self, position: Position, color: Color) -> bool:
        """Check if position contains a friendly piece"""
        piece = self.get_piece(position)
        return piece is not None and piece.color == color
    
    def get_all_pieces(self, color: Color) -> List[Piece]:
        """Get all pieces of given color"""
        pieces = []
        for row in range(8):
            for col in range(8):
                piece = self.board[row][col]
                if piece and piece.color == color:
                    pieces.append(piece)
        return pieces
    
    def is_in_check(self, color: Color) -> bool:
        """Check if the king of given color is in check"""
        king_pos = self.king_positions[color]
        enemy_color = Color.BLACK if color == Color.WHITE else Color.WHITE
        
        # Check if any enemy piece can attack the king
        for piece in self.get_all_pieces(enemy_color):
            if king_pos in piece.get_possible_moves(self):
                return True
        return False
    
    def would_be_in_check(self, move_from: Position, move_to: Position, color: Color) -> bool:
        """Check if making a move would put the king in check"""
        # Create a copy of the board state
        original_piece = self.get_piece(move_from)
        captured_piece = self.get_piece(move_to)
        
        # Make the move temporarily
        self.set_piece(move_to, original_piece)
        self.set_piece(move_from, None)
        
        # Update king position if king moved
        if original_piece.piece_type == PieceType.KING:
            old_king_pos = self.king_positions[color]
            self.king_positions[color] = move_to
        
        # Check if in check
        in_check = self.is_in_check(color)
        
        # Restore the board state
        self.set_piece(move_from, original_piece)
        self.set_piece(move_to, captured_piece)
        
        # Restore king position if king moved
        if original_piece.piece_type == PieceType.KING:
            self.king_positions[color] = move_from
        
        return in_check
    
    def get_valid_moves(self, piece: Piece) -> List[Position]:
        """Get all valid moves for a piece (excluding moves that would put king in check)"""
        from chess_pieces import King
        
        # Get possible moves
        if isinstance(piece, King):
            # For kings, get moves including castling
            possible_moves = piece.get_possible_moves_with_castling(self)
        else:
            possible_moves = piece.get_possible_moves(self)
        
        valid_moves = []
        
        for move in possible_moves:
            if not self.would_be_in_check(piece.position, move, piece.color):
                valid_moves.append(move)
        
        return valid_moves
    
    def make_move(self, from_pos: Position, to_pos: Position) -> bool:
        """Make a move on the board"""
        piece = self.get_piece(from_pos)
        if not piece or piece.color != self.current_player:
            return False
        
        valid_moves = self.get_valid_moves(piece)
        if to_pos not in valid_moves:
            return False
        
        # Record the move
        captured_piece = self.get_piece(to_pos)
        move_record = {
            'from': from_pos,
            'to': to_pos,
            'piece': piece,
            'captured': captured_piece,
            'en_passant_target': self.en_passant_target
        }
        
        # Handle captures
        if captured_piece:
            self.captured_pieces[self.current_player].append(captured_piece)
        
        # Handle en passant
        if piece.piece_type == PieceType.PAWN and to_pos == self.en_passant_target:
            # Remove the captured pawn
            capture_row = to_pos.row + (1 if piece.color == Color.WHITE else -1)
            captured_pawn = self.remove_piece(Position(capture_row, to_pos.col))
            if captured_pawn:
                self.captured_pieces[self.current_player].append(captured_pawn)
        
        # Make the move
        self.set_piece(to_pos, piece)
        self.set_piece(from_pos, None)
        piece.move_to(to_pos)
        
        # Update king position
        if piece.piece_type == PieceType.KING:
            self.king_positions[piece.color] = to_pos
        
        # Handle pawn double move for en passant
        self.en_passant_target = None
        if (piece.piece_type == PieceType.PAWN and 
            abs(to_pos.row - from_pos.row) == 2):
            self.en_passant_target = Position(
                (from_pos.row + to_pos.row) // 2, 
                to_pos.col
            )
        
        # Record move and switch players
        self.move_history.append(move_record)
        self.current_player = Color.BLACK if self.current_player == Color.WHITE else Color.WHITE
        
        return True
    
    def setup_initial_position(self):
        """Set up the initial chess position"""
        # Clear the board
        self.board = [[None for _ in range(8)] for _ in range(8)]
        
        # We'll implement piece classes next and then set up the initial position
        pass

    def __str__(self):
        """String representation of the board"""
        result = "  a b c d e f g h\n"
        for row in range(8):
            result += f"{8-row} "
            for col in range(8):
                piece = self.board[row][col]
                if piece:
                    symbol = self.get_piece_symbol(piece)
                    result += f"{symbol} "
                else:
                    result += ". "
            result += f"{8-row}\n"
        result += "  a b c d e f g h"
        return result
    
    def get_piece_symbol(self, piece: Piece) -> str:
        """Get symbol for piece display"""
        symbols = {
            PieceType.PAWN: 'P',
            PieceType.ROOK: 'R',
            PieceType.KNIGHT: 'N',
            PieceType.BISHOP: 'B',
            PieceType.QUEEN: 'Q',
            PieceType.KING: 'K'
        }
        symbol = symbols.get(piece.piece_type, '?')
        return symbol if piece.color == Color.WHITE else symbol.lower()