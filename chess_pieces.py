"""
Chess Pieces Implementation
Contains all individual piece classes with their movement logic
"""

from chess_game import Piece, Position, Color, PieceType
from typing import List

class Pawn(Piece):
    """Pawn piece implementation"""
    def __init__(self, color: Color, position: Position):
        super().__init__(color, position)
        self.piece_type = PieceType.PAWN
    
    def get_possible_moves(self, board) -> List[Position]:
        moves = []
        direction = -1 if self.color == Color.WHITE else 1
        start_row = 6 if self.color == Color.WHITE else 1
        
        # Forward move
        forward_pos = Position(self.position.row + direction, self.position.col)
        if forward_pos.is_valid() and board.is_empty(forward_pos):
            moves.append(forward_pos)
            
            # Double move from starting position
            if self.position.row == start_row:
                double_move = Position(self.position.row + 2 * direction, self.position.col)
                if double_move.is_valid() and board.is_empty(double_move):
                    moves.append(double_move)
        
        # Diagonal captures
        for col_offset in [-1, 1]:
            capture_pos = Position(self.position.row + direction, self.position.col + col_offset)
            if capture_pos.is_valid() and board.is_enemy_piece(capture_pos, self.color):
                moves.append(capture_pos)
        
        # En passant capture
        if board.en_passant_target:
            en_passant_pos = board.en_passant_target
            if (abs(en_passant_pos.col - self.position.col) == 1 and 
                en_passant_pos.row == self.position.row + direction):
                moves.append(en_passant_pos)
        
        return moves

class Rook(Piece):
    """Rook piece implementation"""
    def __init__(self, color: Color, position: Position):
        super().__init__(color, position)
        self.piece_type = PieceType.ROOK
    
    def get_possible_moves(self, board) -> List[Position]:
        moves = []
        directions = [(0, 1), (0, -1), (1, 0), (-1, 0)]  # Right, Left, Down, Up
        
        for dr, dc in directions:
            for i in range(1, 8):
                new_pos = Position(self.position.row + i * dr, self.position.col + i * dc)
                if not new_pos.is_valid():
                    break
                
                if board.is_empty(new_pos):
                    moves.append(new_pos)
                elif board.is_enemy_piece(new_pos, self.color):
                    moves.append(new_pos)
                    break
                else:  # Friendly piece
                    break
        
        return moves

class Knight(Piece):
    """Knight piece implementation"""
    def __init__(self, color: Color, position: Position):
        super().__init__(color, position)
        self.piece_type = PieceType.KNIGHT
    
    def get_possible_moves(self, board) -> List[Position]:
        moves = []
        knight_moves = [
            (-2, -1), (-2, 1), (-1, -2), (-1, 2),
            (1, -2), (1, 2), (2, -1), (2, 1)
        ]
        
        for dr, dc in knight_moves:
            new_pos = Position(self.position.row + dr, self.position.col + dc)
            if (new_pos.is_valid() and 
                (board.is_empty(new_pos) or board.is_enemy_piece(new_pos, self.color))):
                moves.append(new_pos)
        
        return moves

class Bishop(Piece):
    """Bishop piece implementation"""
    def __init__(self, color: Color, position: Position):
        super().__init__(color, position)
        self.piece_type = PieceType.BISHOP
    
    def get_possible_moves(self, board) -> List[Position]:
        moves = []
        directions = [(1, 1), (1, -1), (-1, 1), (-1, -1)]  # Diagonals
        
        for dr, dc in directions:
            for i in range(1, 8):
                new_pos = Position(self.position.row + i * dr, self.position.col + i * dc)
                if not new_pos.is_valid():
                    break
                
                if board.is_empty(new_pos):
                    moves.append(new_pos)
                elif board.is_enemy_piece(new_pos, self.color):
                    moves.append(new_pos)
                    break
                else:  # Friendly piece
                    break
        
        return moves

class Queen(Piece):
    """Queen piece implementation"""
    def __init__(self, color: Color, position: Position):
        super().__init__(color, position)
        self.piece_type = PieceType.QUEEN
    
    def get_possible_moves(self, board) -> List[Position]:
        moves = []
        # Queen moves like both rook and bishop
        directions = [
            (0, 1), (0, -1), (1, 0), (-1, 0),      # Rook moves
            (1, 1), (1, -1), (-1, 1), (-1, -1)     # Bishop moves
        ]
        
        for dr, dc in directions:
            for i in range(1, 8):
                new_pos = Position(self.position.row + i * dr, self.position.col + i * dc)
                if not new_pos.is_valid():
                    break
                
                if board.is_empty(new_pos):
                    moves.append(new_pos)
                elif board.is_enemy_piece(new_pos, self.color):
                    moves.append(new_pos)
                    break
                else:  # Friendly piece
                    break
        
        return moves

class King(Piece):
    """King piece implementation"""
    def __init__(self, color: Color, position: Position):
        super().__init__(color, position)
        self.piece_type = PieceType.KING
    
    def get_possible_moves(self, board) -> List[Position]:
        moves = []
        directions = [
            (0, 1), (0, -1), (1, 0), (-1, 0),      # Orthogonal
            (1, 1), (1, -1), (-1, 1), (-1, -1)     # Diagonal
        ]
        
        for dr, dc in directions:
            new_pos = Position(self.position.row + dr, self.position.col + dc)
            if (new_pos.is_valid() and 
                (board.is_empty(new_pos) or board.is_enemy_piece(new_pos, self.color))):
                moves.append(new_pos)
        
        return moves
    
    def get_possible_moves_with_castling(self, board) -> List[Position]:
        """Get moves including castling - used separately to avoid recursion"""
        moves = self.get_possible_moves(board)
        
        # Castling - check separately to avoid recursion
        if not self.has_moved:
            # Simple check for castling without calling is_in_check
            # Kingside castling
            if self._can_castle_kingside(board):
                moves.append(Position(self.position.row, self.position.col + 2))
            
            # Queenside castling
            if self._can_castle_queenside(board):
                moves.append(Position(self.position.row, self.position.col - 2))
        
        return moves
    
    def _can_castle_kingside(self, board) -> bool:
        """Check if kingside castling is possible"""
        row = self.position.row
        
        # Check if rook is in place and hasn't moved
        rook_pos = Position(row, 7)
        rook = board.get_piece(rook_pos)
        if not rook or rook.piece_type != PieceType.ROOK or rook.has_moved:
            return False
        
        # Check if squares between king and rook are empty
        for col in range(self.position.col + 1, 7):
            if not board.is_empty(Position(row, col)):
                return False
        
        return True
    
    def _can_castle_queenside(self, board) -> bool:
        """Check if queenside castling is possible"""
        row = self.position.row
        
        # Check if rook is in place and hasn't moved
        rook_pos = Position(row, 0)
        rook = board.get_piece(rook_pos)
        if not rook or rook.piece_type != PieceType.ROOK or rook.has_moved:
            return False
        
        # Check if squares between king and rook are empty
        for col in range(1, self.position.col):
            if not board.is_empty(Position(row, col)):
                return False
        
        return True