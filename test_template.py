from chess_mechanics import ChessGame
import json

# Test what data is being passed to the template
dummy = ChessGame()
board_str = dummy.board.board_to_string()
print("Board string:")
print(repr(board_str[:100]))
print("\n")

# Convert to array
board_array = []
for line in board_str.split('\n'):
    board_array.append(list(line))

print("Board array:")
print(json.dumps(board_array))
print("\n")

print("Current player:")
print(repr(dummy.current_player))
print("\n")

print("Game status:")
print(repr(dummy.get_game_status()))
