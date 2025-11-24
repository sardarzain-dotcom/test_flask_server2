"""
Simple AI player for the chess game using minimax with alpha-beta pruning.

Public API:
- choose_ai_move(game: ChessGame, depth: int = 2) -> tuple[Position, Position]
  Returns (from_pos, to_pos) for the current player to move.

Notes:
- Works directly with the provided ChessGame API.
- Uses game.make_move(...) and game.undo_last_move() to simulate moves.
- Evaluation is material-based with a slight mobility term.
"""

from __future__ import annotations

from typing import List, Tuple, Optional
import copy

from chess_game import Position, Color, PieceType
from chess_mechanics import ChessGame


# Piece values for evaluation (centipawns)
PIECE_VALUES = {
    PieceType.PAWN: 100,
    PieceType.KNIGHT: 320,
    PieceType.BISHOP: 330,
    PieceType.ROOK: 500,
    PieceType.QUEEN: 900,
    PieceType.KING: 20000,
}


def list_legal_moves(game: ChessGame) -> List[Tuple[Position, Position]]:
    """List legal moves for the current player in the given game."""
    moves: List[Tuple[Position, Position]] = []
    board = game.board
    color = board.current_player
    for piece in board.get_all_pieces(color):
        for to_pos in board.get_valid_moves(piece):
            moves.append((piece.position, to_pos))
    return moves


def evaluate(game: ChessGame) -> int:
    """Evaluate the board from the perspective of White (positive is good for White)."""
    board = game.board
    score = 0

    # Material evaluation
    for row in range(8):
        for col in range(8):
            piece = board.board[row][col]
            if not piece:
                continue
            val = PIECE_VALUES.get(piece.piece_type, 0)
            score += val if piece.color == Color.WHITE else -val

    # Simple mobility bonus for side to move
    try:
        mobility = 0
        for p in board.get_all_pieces(board.current_player):
            mobility += len(board.get_valid_moves(p))
        score += 5 * (mobility if board.current_player == Color.WHITE else -mobility)
    except Exception:
        # Be robust; if anything goes wrong, ignore mobility
        pass

    # Terminal states: big bonuses/penalties
    if game.is_game_over():
        winner = game.get_winner()
        if winner is None:
            return 0
        return 100000 if winner == Color.WHITE else -100000

    return score


def minimax(game: ChessGame, depth: int, alpha: int, beta: int, maximizing: bool) -> Tuple[int, Optional[Tuple[Position, Position]]]:
    """Minimax with alpha-beta pruning operating on the stateful ChessGame.

    Returns (score, best_move).
    """
    if depth == 0 or game.is_game_over():
        return evaluate(game), None

    legal_moves = list_legal_moves(game)
    if not legal_moves:
        # No legal moves; game._update_game_state would reflect stalemate/checkmate
        return evaluate(game), None

    best_move: Optional[Tuple[Position, Position]] = None

    if maximizing:
        value = -10**9
        for move in legal_moves:
            from_pos, to_pos = move
            # Work on a deep copy to avoid relying on undo correctness
            sim = copy.deepcopy(game)
            res = sim.make_move(from_pos, to_pos)
            if not (isinstance(res, dict) and res.get('success')):
                continue
            score, _ = minimax(sim, depth - 1, alpha, beta, False)
            if score > value:
                value = score
                best_move = move
            alpha = max(alpha, value)
            if alpha >= beta:
                break
        return value, best_move
    else:
        value = 10**9
        for move in legal_moves:
            from_pos, to_pos = move
            sim = copy.deepcopy(game)
            res = sim.make_move(from_pos, to_pos)
            if not (isinstance(res, dict) and res.get('success')):
                continue
            score, _ = minimax(sim, depth - 1, alpha, beta, True)
            if score < value:
                value = score
                best_move = move
            beta = min(beta, value)
            if alpha >= beta:
                break
        return value, best_move


def choose_ai_move(game: ChessGame, depth: int = 2) -> Optional[Tuple[Position, Position]]:
    """Choose the best move for the current player using minimax.

    - depth: search depth (2 is fast; 3 a bit stronger; >3 may be slow)
    """
    maximizing = game.board.current_player == Color.WHITE
    _, move = minimax(game, depth, -10**9, 10**9, maximizing)
    return move
