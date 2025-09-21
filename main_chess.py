"""
Main Chess Game Entry Point
Choose between GUI and console versions
"""

import sys
import os

def main():
    """Main function to choose game interface"""
    print("Python Chess Game")
    print("=================")
    print("Choose your interface:")
    print("1. GUI (requires pygame)")
    print("2. Console/Text")
    print("3. Exit")
    
    while True:
        try:
            choice = input("\nEnter your choice (1-3): ").strip()
            
            if choice == '1':
                try:
                    from chess_gui import ChessGUI
                    print("Starting GUI chess game...")
                    game = ChessGUI()
                    game.run()
                    break
                except ImportError:
                    print("pygame is not installed. Install it with: pip install pygame")
                    print("Falling back to console version...")
                    choice = '2'
                except Exception as e:
                    print(f"Error starting GUI: {e}")
                    print("Falling back to console version...")
                    choice = '2'
            
            if choice == '2':
                from chess_console import ConsoleChess
                print("Starting console chess game...")
                game = ConsoleChess()
                game.play()
                break
            
            elif choice == '3':
                print("Thanks for using Python Chess!")
                break
            
            else:
                print("Invalid choice. Please enter 1, 2, or 3.")
        
        except KeyboardInterrupt:
            print("\nExiting...")
            break
        except Exception as e:
            print(f"An error occurred: {e}")

if __name__ == "__main__":
    main()