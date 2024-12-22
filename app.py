import autogen
import streamlit as st
from IPython.display import display
import time
import base64

config_list = autogen.config_list_openai_aoai()
llm_config = {"model": "gpt-4-turbo"}

# Initialize the chess board
import chess
import chess.svg
#import cairosvg
from typing_extensions import Annotated
board = chess.Board()
made_move = False

# Helper function to stream chat results
def stream_data(content: str):
    for word in content.split(" "):
        yield word + " "
        time.sleep(0.05)

## Define the tools

def get_legal_moves(
# Tool for getting legal moves
    
) -> Annotated[str, "A list of legal moves in UCI format"]:
    return "Possible moves are: " + ",".join(
        [str(move) for move in board.legal_moves]
    )

def make_move(
# Tool for making a move on the board.
    move: Annotated[str, "A move in UCI format."]
) -> Annotated[str, "Result of the move."]:
    move = chess.Move.from_uci(move)
    board.push_uci(str(move))
    global made_move
    made_move = True
    
    st.image(chess.svg.board(
            board,
            arrows=[(move.from_square, move.to_square)],
            fill={move.from_square: "gray"},
            size=200
        ))

    # Get the piece name.
    piece = board.piece_at(move.to_square)
    piece_symbol = piece.unicode_symbol()
    piece_name = (
        chess.piece_name(piece.piece_type).capitalize()
        if piece_symbol.isupper()
        else chess.piece_name(piece.piece_type)
    )

    return f"Moved {piece_name} ({piece_symbol}) from "\
    f"{chess.SQUARE_NAMES[move.from_square]} to "\
    f"{chess.SQUARE_NAMES[move.to_square]}."

# Create agents
from autogen import ConversableAgent
player_white = ConversableAgent(
    name="Player White",
    system_message="You are a chess player and you play as white. "
    "First call get_legal_moves(), to get a list of legal moves. "
    "Then call make_move(move) to make a move. "
    "After a move is made, chitchat to make the game fun."
    "Then call write_to_streamlit(chat_result) to write the chat summary to streamlit.",
    llm_config=llm_config,
)

player_black = ConversableAgent(
    name="Player Black",
    system_message="You are a chess player and you play as black. "
    "First call get_legal_moves(), to get a list of legal moves. "
    "Then call make_move(move) to make a move. "
    "After a move is made, chitchat to make the game fun."
    "Then call write_to_streamlit(chat_result) to write the chat summary to streamlit.",
    llm_config=llm_config,
)

def check_made_move(msg):
    global made_move
    if made_move:
        made_move = False
        return True
    else:
        return False

board_proxy = ConversableAgent(
    name="Board Proxy",
    llm_config=False,
    is_termination_msg=check_made_move,
    default_auto_reply="Please make a move.",
    human_input_mode="NEVER",
)

# Register the tools
from autogen import register_function

for caller in [player_white, player_black]:
    register_function(
        get_legal_moves,
        caller=caller,
        executor=board_proxy,
        name="get_legal_moves",
        description="Get legal moves.",
    )
    
    register_function(
        make_move,
        caller=caller,
        executor=board_proxy,
        name="make_move",
        description="Call this tool to make a move.",
    )


check_tools = player_black.llm_config["tools"]
if check_tools:
    st.title("Chess AI")
    st.markdown("Welcome to the Chess AI!")
    st.markdown("Enjoy the game!")

# Register nested chats
player_white.register_nested_chats(
    trigger=player_black,
    chat_queue=[
        {
            "sender": board_proxy,
            "recipient": player_white,
            "summary_method": "last_msg",
            "silent": False,
        }
    ],
)

player_black.register_nested_chats(
    trigger=player_white,
    chat_queue=[
        {
            "sender": board_proxy,
            "recipient": player_black,
            "summary_method": "last_msg",
            "silent": False,
        }
    ],
)


# Start the game
if __name__ == "__main__":
    start_game = st.button("Start Game")
    if start_game:
        chat_result = player_black.initiate_chat(
            player_white,
            message="Let's play chess! Your move.",
            max_turns=2,
        )
        
        for item in chat_result.chat_history:
            st.write_stream(stream_data(item['content']))
        
        st.write(chat_result)
        st.write("Game Over!")
    else: 
        st.write("We're waiting...")
