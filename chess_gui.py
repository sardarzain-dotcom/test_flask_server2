"""
Chess GUI using Pygame
Provides a graphical interface for the chess game
"""

import pygame
import sys
import os
from chess_mechanics import ChessGame, GameState
from chess_game import Position, Color, PieceType
from typing import Tuple, Optional

# Initialize Pygame
pygame.init()

# Constants
BOARD_SIZE = 640
SQUARE_SIZE = BOARD_SIZE // 8
SIDEBAR_WIDTH = 250
WINDOW_WIDTH = BOARD_SIZE + SIDEBAR_WIDTH
WINDOW_HEIGHT = BOARD_SIZE + 100

# Colors
WHITE = (240, 217, 181)
BLACK = (181, 136, 99)
HIGHLIGHT = (255, 255, 0, 128)
VALID_MOVE = (0, 255, 0, 128)
CHECK = (255, 0, 0, 128)
SELECTED = (0, 0, 255, 128)

# UI Colors
UI_BG = (50, 50, 50)
UI_TEXT = (255, 255, 255)
BUTTON_COLOR = (70, 70, 70)
BUTTON_HOVER = (90, 90, 90)

class ChessGUI:
    """Chess game GUI using Pygame"""
    
    def __init__(self):
        self.screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
        pygame.display.set_caption("Python Chess Game")
        self.clock = pygame.time.Clock()
        self.font = pygame.font.Font(None, 24)
        self.title_font = pygame.font.Font(None, 32)
        
        self.game = ChessGame()
        self.piece_images = self._load_piece_images()
        self.dragging = False
        self.drag_piece = None
        self.drag_pos = (0, 0)
        
        # UI Elements
        self.buttons = self._create_buttons()
        
    def _load_piece_images(self) -> dict:
        """Load piece images (using text representations for now)"""
        # For simplicity, we'll use text representations
        # In a full implementation, you would load actual piece images
        piece_symbols = {
            (Color.WHITE, PieceType.KING): "♔",
            (Color.WHITE, PieceType.QUEEN): "♕",
            (Color.WHITE, PieceType.ROOK): "♖",
            (Color.WHITE, PieceType.BISHOP): "♗",
            (Color.WHITE, PieceType.KNIGHT): "♘",
            (Color.WHITE, PieceType.PAWN): "♙",
            (Color.BLACK, PieceType.KING): "♚",
            (Color.BLACK, PieceType.QUEEN): "♛",
            (Color.BLACK, PieceType.ROOK): "♜",
            (Color.BLACK, PieceType.BISHOP): "♝",
            (Color.BLACK, PieceType.KNIGHT): "♞",
            (Color.BLACK, PieceType.PAWN): "♟",
        }
        
        images = {}
        piece_font = pygame.font.Font(None, 48)
        
        for (color, piece_type), symbol in piece_symbols.items():
            # Create text surface for each piece
            text_surface = piece_font.render(symbol, True, (0, 0, 0))
            images[(color, piece_type)] = text_surface
        
        return images
    
    def _create_buttons(self) -> list:
        """Create UI buttons"""
        buttons = []
        
        # New Game button
        new_game_rect = pygame.Rect(BOARD_SIZE + 20, 50, 200, 40)
        buttons.append({"rect": new_game_rect, "text": "New Game", "action": "new_game"})
        
        # Undo Move button
        undo_rect = pygame.Rect(BOARD_SIZE + 20, 100, 200, 40)
        buttons.append({"rect": undo_rect, "text": "Undo Move", "action": "undo"})
        
        return buttons
    
    def get_square_from_pos(self, pos: Tuple[int, int]) -> Optional[Position]:
        """Convert screen position to board square"""
        x, y = pos
        if 0 <= x < BOARD_SIZE and 0 <= y < BOARD_SIZE:
            col = x // SQUARE_SIZE
            row = y // SQUARE_SIZE
            return Position(row, col)
        return None
    
    def get_screen_pos(self, position: Position) -> Tuple[int, int]:
        """Convert board position to screen coordinates"""
        x = position.col * SQUARE_SIZE
        y = position.row * SQUARE_SIZE
        return (x, y)
    
    def draw_board(self):
        """Draw the chess board"""
        for row in range(8):
            for col in range(8):
                color = WHITE if (row + col) % 2 == 0 else BLACK
                rect = pygame.Rect(col * SQUARE_SIZE, row * SQUARE_SIZE, SQUARE_SIZE, SQUARE_SIZE)
                pygame.draw.rect(self.screen, color, rect)
                
                # Draw coordinates
                if col == 0:  # Row numbers
                    text = self.font.render(str(8 - row), True, (0, 0, 0))
                    self.screen.blit(text, (5, row * SQUARE_SIZE + 5))
                if row == 7:  # Column letters
                    text = self.font.render(chr(ord('a') + col), True, (0, 0, 0))
                    self.screen.blit(text, (col * SQUARE_SIZE + SQUARE_SIZE - 15, BOARD_SIZE - 20))
    
    def draw_highlights(self):
        """Draw square highlights"""
        # Highlight selected square
        if self.game.selected_position:
            x, y = self.get_screen_pos(self.game.selected_position)
            highlight_surface = pygame.Surface((SQUARE_SIZE, SQUARE_SIZE), pygame.SRCALPHA)
            highlight_surface.fill(SELECTED)
            self.screen.blit(highlight_surface, (x, y))
        
        # Highlight valid moves
        for move in self.game.valid_moves:
            x, y = self.get_screen_pos(move)
            highlight_surface = pygame.Surface((SQUARE_SIZE, SQUARE_SIZE), pygame.SRCALPHA)
            highlight_surface.fill(VALID_MOVE)
            self.screen.blit(highlight_surface, (x, y))
            
            # Draw a circle for empty squares, border for captures
            center_x = x + SQUARE_SIZE // 2
            center_y = y + SQUARE_SIZE // 2
            if self.game.board.is_empty(move):
                pygame.draw.circle(self.screen, (0, 150, 0), (center_x, center_y), 10)
            else:
                pygame.draw.circle(self.screen, (150, 0, 0), (center_x, center_y), SQUARE_SIZE // 2 - 5, 3)
        
        # Highlight king if in check
        if self.game.game_state == GameState.CHECK:
            king_pos = self.game.board.king_positions[self.game.board.current_player]
            x, y = self.get_screen_pos(king_pos)
            highlight_surface = pygame.Surface((SQUARE_SIZE, SQUARE_SIZE), pygame.SRCALPHA)
            highlight_surface.fill(CHECK)
            self.screen.blit(highlight_surface, (x, y))
    
    def draw_pieces(self):
        """Draw all pieces on the board"""
        for row in range(8):
            for col in range(8):
                piece = self.game.board.get_piece(Position(row, col))
                if piece and (not self.dragging or piece != self.drag_piece):
                    image = self.piece_images.get((piece.color, piece.piece_type))
                    if image:
                        x, y = self.get_screen_pos(Position(row, col))
                        # Center the piece in the square
                        piece_x = x + (SQUARE_SIZE - image.get_width()) // 2
                        piece_y = y + (SQUARE_SIZE - image.get_height()) // 2
                        self.screen.blit(image, (piece_x, piece_y))
    
    def draw_dragging_piece(self):
        """Draw piece being dragged"""
        if self.dragging and self.drag_piece:
            image = self.piece_images.get((self.drag_piece.color, self.drag_piece.piece_type))
            if image:
                x, y = self.drag_pos
                piece_x = x - image.get_width() // 2
                piece_y = y - image.get_height() // 2
                self.screen.blit(image, (piece_x, piece_y))
    
    def draw_sidebar(self):
        """Draw the sidebar with game information"""
        # Background
        sidebar_rect = pygame.Rect(BOARD_SIZE, 0, SIDEBAR_WIDTH, WINDOW_HEIGHT)
        pygame.draw.rect(self.screen, UI_BG, sidebar_rect)
        
        # Title
        title_text = self.title_font.render("Chess Game", True, UI_TEXT)
        self.screen.blit(title_text, (BOARD_SIZE + 20, 20))
        
        # Game status
        status_text = self.font.render(self.game.get_game_status(), True, UI_TEXT)
        self.screen.blit(status_text, (BOARD_SIZE + 20, 160))
        
        # Current player
        player_text = f"Current: {self.game.board.current_player.value.capitalize()}"
        player_surface = self.font.render(player_text, True, UI_TEXT)
        self.screen.blit(player_surface, (BOARD_SIZE + 20, 190))
        
        # Move history (last 10 moves)
        history = self.game.get_move_history_algebraic()
        history_title = self.font.render("Move History:", True, UI_TEXT)
        self.screen.blit(history_title, (BOARD_SIZE + 20, 230))
        
        for i, move in enumerate(history[-10:]):
            move_text = self.font.render(move, True, UI_TEXT)
            self.screen.blit(move_text, (BOARD_SIZE + 20, 250 + i * 20))
        
        # Captured pieces
        white_captured = len(self.game.board.captured_pieces[Color.WHITE])
        black_captured = len(self.game.board.captured_pieces[Color.BLACK])
        
        captured_text = f"Captured - W: {white_captured}, B: {black_captured}"
        captured_surface = self.font.render(captured_text, True, UI_TEXT)
        self.screen.blit(captured_surface, (BOARD_SIZE + 20, 450))
    
    def draw_buttons(self):
        """Draw UI buttons"""
        mouse_pos = pygame.mouse.get_pos()
        
        for button in self.buttons:
            # Determine button color
            color = BUTTON_HOVER if button["rect"].collidepoint(mouse_pos) else BUTTON_COLOR
            
            # Draw button
            pygame.draw.rect(self.screen, color, button["rect"])
            pygame.draw.rect(self.screen, UI_TEXT, button["rect"], 2)
            
            # Draw button text
            text_surface = self.font.render(button["text"], True, UI_TEXT)
            text_rect = text_surface.get_rect(center=button["rect"].center)
            self.screen.blit(text_surface, text_rect)
    
    def handle_button_click(self, pos: Tuple[int, int]):
        """Handle button clicks"""
        for button in self.buttons:
            if button["rect"].collidepoint(pos):
                if button["action"] == "new_game":
                    self.game.reset_game()
                elif button["action"] == "undo":
                    self.game.undo_last_move()
    
    def handle_mouse_down(self, pos: Tuple[int, int], button: int):
        """Handle mouse button down events"""
        if button == 1:  # Left click
            # Check if clicking on sidebar buttons
            if pos[0] >= BOARD_SIZE:
                self.handle_button_click(pos)
                return
            
            # Handle board clicks
            square = self.get_square_from_pos(pos)
            if square:
                piece = self.game.board.get_piece(square)
                if piece and piece.color == self.game.board.current_player:
                    self.dragging = True
                    self.drag_piece = piece
                    self.drag_pos = pos
                else:
                    self.game.select_square(square)
    
    def handle_mouse_up(self, pos: Tuple[int, int], button: int):
        """Handle mouse button up events"""
        if button == 1 and self.dragging:  # Left click release
            square = self.get_square_from_pos(pos)
            if square and self.drag_piece:
                # Try to move the piece
                self.game.select_square(self.drag_piece.position)
                self.game.select_square(square)
            
            self.dragging = False
            self.drag_piece = None
    
    def handle_mouse_motion(self, pos: Tuple[int, int]):
        """Handle mouse motion events"""
        if self.dragging:
            self.drag_pos = pos
    
    def run(self):
        """Main game loop"""
        running = True
        
        while running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.MOUSEBUTTONDOWN:
                    self.handle_mouse_down(event.pos, event.button)
                elif event.type == pygame.MOUSEBUTTONUP:
                    self.handle_mouse_up(event.pos, event.button)
                elif event.type == pygame.MOUSEMOTION:
                    self.handle_mouse_motion(event.pos)
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_r:  # R key to reset
                        self.game.reset_game()
                    elif event.key == pygame.K_u:  # U key to undo
                        self.game.undo_last_move()
            
            # Clear screen
            self.screen.fill((255, 255, 255))
            
            # Draw everything
            self.draw_board()
            self.draw_highlights()
            self.draw_pieces()
            self.draw_dragging_piece()
            self.draw_sidebar()
            self.draw_buttons()
            
            # Update display
            pygame.display.flip()
            self.clock.tick(60)
        
        pygame.quit()
        sys.exit()

def main():
    """Main function to start the chess game"""
    try:
        game = ChessGUI()
        game.run()
    except Exception as e:
        print(f"Error running chess game: {e}")
        print("Make sure pygame is installed: pip install pygame")

if __name__ == "__main__":
    main()