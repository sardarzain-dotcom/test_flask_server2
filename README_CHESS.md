# Python Chess Game

A complete chess implementation in Python with both GUI (pygame) and console interfaces.

## Features

### ✅ Complete Chess Implementation
- **All piece movements**: Pawn, Rook, Knight, Bishop, Queen, King
- **Special moves**: Castling, En passant, Pawn promotion
- **Game rules**: Check, Checkmate, Stalemate detection
- **Move validation**: Prevents illegal moves and moves that put king in check
- **Turn management**: Alternating white and black moves

### 🎮 Dual Interface Options
1. **GUI Version** (pygame): Beautiful graphical interface with drag-and-drop
2. **Console Version**: Text-based for terminal play

### 🎯 Game Features
- Move history tracking
- Undo functionality
- Game state management
- Position notation (algebraic)
- Captured pieces tracking

## Installation

### Prerequisites
```bash
# Python 3.7 or higher required
python --version
```

### Install Dependencies
```bash
# For console version only
pip install -r requirements_minimal.txt

# For GUI version (includes pygame)
pip install -r requirements.txt
```

### Alternative Installation
```bash
# Install pygame separately for GUI
pip install pygame

# Or install all dependencies
pip install Flask Werkzeug gunicorn python-dotenv pygame
```

## How to Play

### Starting the Game
```bash
# Run main launcher (choose GUI or console)
python main_chess.py

# Or run directly:
python chess_gui.py      # GUI version
python chess_console.py  # Console version
```

### Game Controls

#### GUI Version
- **Click** to select a piece
- **Click** destination to move
- **Drag and drop** pieces
- **Buttons**: New Game, Undo Move
- **Keyboard shortcuts**:
  - `R` - Reset game
  - `U` - Undo move

#### Console Version
- **Move format**: `e2 e4` (from square to square)
- **Commands**:
  - `help` - Show help
  - `new` - New game
  - `undo` - Undo last move
  - `history` - Show move history
  - `status` - Game status
  - `quit` - Exit game

### Chess Notation
- **Squares**: `a1` to `h8` (column + row)
- **Files**: a, b, c, d, e, f, g, h (columns)
- **Ranks**: 1, 2, 3, 4, 5, 6, 7, 8 (rows)

## File Structure

```
chess_game/
├── main_chess.py          # Main entry point
├── chess_game.py          # Core game classes (Board, Position, Piece)
├── chess_pieces.py        # Individual piece implementations
├── chess_mechanics.py     # Game mechanics and rules
├── chess_gui.py          # Pygame GUI interface
├── chess_console.py      # Console/text interface
├── requirements.txt      # All dependencies
└── README_CHESS.md       # This file
```

## Architecture

### Core Classes
- **`ChessBoard`**: Manages the 8x8 board and piece positions
- **`Position`**: Represents board coordinates with validation
- **`Piece`**: Base class for all chess pieces
- **`ChessGame`**: Main game controller with rules and state

### Piece Classes
- **`Pawn`**: Implements pawn movement, en passant, promotion
- **`Rook`**: Straight-line movement, castling support
- **`Knight`**: L-shaped movement pattern
- **`Bishop`**: Diagonal movement
- **`Queen`**: Combined rook and bishop movement
- **`King`**: One-square movement, castling, check detection

### Game Mechanics
- **Move validation**: Ensures legal moves only
- **Check detection**: Identifies when kings are in check
- **Checkmate/Stalemate**: Game-ending conditions
- **Special moves**: Castling, en passant, pawn promotion

## Game Rules Implemented

### Standard Chess Rules
✅ **Piece Movement**: All pieces move according to chess rules  
✅ **Captures**: Pieces can capture opponent pieces  
✅ **Turn-based**: Players alternate turns  
✅ **Check**: King under attack must move to safety  
✅ **Checkmate**: Game ends when king cannot escape check  
✅ **Stalemate**: Game ends in draw when no legal moves available  

### Special Moves
✅ **Castling**: King and rook special move (both kingside and queenside)  
✅ **En Passant**: Pawn capture of opponent pawn that moved two squares  
✅ **Pawn Promotion**: Pawns reaching end rank become queens (auto-promotion)  

### Advanced Features
✅ **Move History**: Track all moves made in the game  
✅ **Undo Moves**: Reverse the last move made  
✅ **Position Validation**: Prevent illegal moves  
✅ **Game State Management**: Track current game status  

## Usage Examples

### Quick Start - Console
```python
from chess_console import ConsoleChess

game = ConsoleChess()
game.play()
```

### Quick Start - GUI
```python
from chess_gui import ChessGUI

game = ChessGUI()
game.run()
```

### Programmatic Game Control
```python
from chess_mechanics import ChessGame
from chess_game import Position

# Create a new game
game = ChessGame()

# Make moves
game.make_move(Position(6, 4), Position(4, 4))  # e2 to e4
game.make_move(Position(1, 4), Position(3, 4))  # e7 to e5

# Check game status
print(game.get_game_status())
print(f"Current player: {game.board.current_player}")
```

## Troubleshooting

### Common Issues

1. **"pygame not installed"**
   ```bash
   pip install pygame
   ```

2. **"Module not found" errors**
   ```bash
   # Make sure all files are in the same directory
   # Check Python path
   ```

3. **GUI window not opening**
   - Check if display is available
   - Try console version instead
   - Verify pygame installation

### Performance Notes
- The game runs at 60 FPS in GUI mode
- Console version has no performance constraints
- Move validation is optimized for quick response

## Features for Future Enhancement

### Potential Additions
- [ ] AI opponent (minimax algorithm)
- [ ] Online multiplayer
- [ ] Game saving/loading
- [ ] Time controls
- [ ] Move sound effects
- [ ] Board themes
- [ ] Piece animations
- [ ] Tournament mode
- [ ] Chess puzzles
- [ ] Analysis mode

### Code Improvements
- [ ] Type hints completion
- [ ] Unit tests
- [ ] Documentation
- [ ] Code optimization
- [ ] Error handling improvements

## Contributing

Feel free to contribute improvements:
1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## License

This project is open source and available under the MIT License.

## Credits

Created as a demonstration of object-oriented programming and game development in Python. Uses pygame for the GUI interface and implements full chess rules and mechanics.

---

**Enjoy playing chess!** 🏁♟️