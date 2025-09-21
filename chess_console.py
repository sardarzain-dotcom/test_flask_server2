"""
Console Chess Game
A text-based version of the chess game for testing and playing without GUI
"""

from chess_mechanics import ChessGame, GameState
from chess_game import Position, Color
import sys

class ConsoleChess:
    """Console interface for the chess game"""
    
    def __init__(self):
        self.game = ChessGame()
    
    def display_board(self):
        """Display the current board state"""
        print("\n" + "="*50)
        print(self.game.board)
        print("="*50)
        print(f"Status: {self.game.get_game_status()}")
        print("="*50)
    
    def get_position_input(self, prompt: str) -> Position:
        """Get a position input from the user"""
        while True:
            try:
                user_input = input(prompt).strip().lower()
                if len(user_input) == 2:
                    col = ord(user_input[0]) - ord('a')
                    row = 8 - int(user_input[1])
                    position = Position(row, col)
                    if position.is_valid():
                        return position
                print("Invalid input. Please enter a position like 'e4' or 'a1'.")
            except (ValueError, IndexError):
                print("Invalid input. Please enter a position like 'e4' or 'a1'.")
    
    def display_help(self):
        """Display help information"""
        print("\nChess Game Commands:")
        print("- Enter moves like 'e2 e4' (from square to square)")
        print("- Type 'help' for this help message")
        print("- Type 'quit' to exit the game")
        print("- Type 'new' to start a new game")
        print("- Type 'undo' to undo the last move")
        print("- Type 'history' to see move history")
        print("- Type 'status' to see current game status")
        print("\nPosition format: column (a-h) + row (1-8), e.g., 'e4', 'a1'")
    
    def display_move_history(self):
        """Display the move history"""
        history = self.game.get_move_history_algebraic()
        if not history:
            print("No moves have been made yet.")
            return
        
        print("\nMove History:")
        for move in history:
            print(f"  {move}")
    
    def play(self):
        """Main game loop for console chess"""
        print("Welcome to Console Chess!")
        print("Type 'help' for commands.")
        
        self.display_board()
        
        while not self.game.is_game_over():
            try:
                user_input = input(f"\n{self.game.board.current_player.value.capitalize()}'s turn. Enter move or command: ").strip().lower()
                
                if user_input == 'quit':
                    print("Thanks for playing!")
                    break
                elif user_input == 'help':
                    self.display_help()
                    continue
                elif user_input == 'new':
                    self.game.reset_game()
                    print("New game started!")
                    self.display_board()
                    continue
                elif user_input == 'undo':
                    if self.game.undo_last_move():
                        print("Move undone!")
                        self.display_board()
                    else:
                        print("No moves to undo.")
                    continue
                elif user_input == 'history':
                    self.display_move_history()
                    continue
                elif user_input == 'status':
                    print(f"Game Status: {self.game.get_game_status()}")
                    continue
                
                # Parse move input
                parts = user_input.split()
                if len(parts) != 2:
                    print("Invalid input. Enter move as 'from to', e.g., 'e2 e4'")
                    continue
                
                from_str, to_str = parts
                
                # Validate input format
                if (len(from_str) != 2 or len(to_str) != 2 or
                    not from_str[0].isalpha() or not from_str[1].isdigit() or
                    not to_str[0].isalpha() or not to_str[1].isdigit()):
                    print("Invalid position format. Use format like 'e2 e4'")
                    continue
                
                # Convert to positions
                from_col = ord(from_str[0]) - ord('a')
                from_row = 8 - int(from_str[1])
                to_col = ord(to_str[0]) - ord('a')
                to_row = 8 - int(to_str[1])
                
                from_pos = Position(from_row, from_col)
                to_pos = Position(to_row, to_col)
                
                if not from_pos.is_valid() or not to_pos.is_valid():
                    print("Invalid positions. Positions must be within the board (a1-h8).")
                    continue
                
                # Check if there's a piece to move
                piece = self.game.board.get_piece(from_pos)
                if not piece:
                    print("No piece at the starting position.")
                    continue
                
                if piece.color != self.game.board.current_player:
                    print("You can only move your own pieces.")
                    continue
                
                # Try to make the move
                if self.game.make_move(from_pos, to_pos):
                    print(f"Move made: {from_str} to {to_str}")
                    self.display_board()
                    
                    # Check for game end
                    if self.game.is_game_over():
                        print(f"\nGame Over! {self.game.get_game_status()}")
                        break
                else:
                    print("Invalid move. Try again.")
                    # Show valid moves for the selected piece
                    valid_moves = self.game.board.get_valid_moves(piece)
                    if valid_moves:
                        print("Valid moves for this piece:")
                        for move in valid_moves[:5]:  # Show first 5 moves
                            print(f"  {move.to_algebraic()}")
                        if len(valid_moves) > 5:
                            print(f"  ... and {len(valid_moves) - 5} more")
            
            except KeyboardInterrupt:
                print("\nGame interrupted. Thanks for playing!")
                break
            except Exception as e:
                print(f"An error occurred: {e}")
                print("Please try again.")
        
        if self.game.is_game_over():
            print(f"\nFinal Result: {self.game.get_game_status()}")

def main():
    """Main function to start the console chess game"""
    game = ConsoleChess()
    game.play()

if __name__ == "__main__":
    main()