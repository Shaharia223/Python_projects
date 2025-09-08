import pandas as pd
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, MessageHandler, filters, ConversationHandler



#connected database
import sqlite3
# Initialize the database connection
def init_db():
    conn = sqlite3.connect('bot_users.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY
        )
    ''')
    conn.commit()
    return conn
# Establish the connection to be used globally
db_conn = init_db()



# States for the conversation
SELECTING_POST, ASKING_FOR_MORE = range(2)
SELECTING_HALL = 2 # New state for hall selection

BOT_TOKEN = "8272051668:AAG0assj9F6wYprYV5OujL4WOjsTLfnm7xE"
EXCEL_FILE_PATH = 'ducsu_candidates.xlsx'

df = None

WELCOME_MESSAGE = """
Welcome to the DUCSU Bot!

I can help you find information about the candidates and their contesting posts. You can interact with me using the following commands:

/start - Get a welcome message and a brief introduction to the bot.
/posts - See a list of all contesting posts. Once you see the list, you can reply with the name of a post to see the candidates.
/halls - See a list of all halls. Once you see the list, you can reply with the name of a hall to see the candidates.
/cancel - End an ongoing conversation with me.

You can also search for a candidate by simply typing their name or a part of their name. For example, try typing "Ahad Bin Islam Shoeb" to see the profile.

Limitations: This bot can only give you information in English. I'm really sorry if you ask me something in Bangla. I won't be able to understand it. If you are a candidate and your name has been spelled wrong, please accept my apologies. You can knock my boss Sheikh Shaharia Emon (Facebook: https://www.facebook.com/sheikh.shahria.75) to correct it.
"""

async def start_and_help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handles the /start command, sends a welcome message, and logs the user's ID.
    """
    user_id = update.message.from_user.id
    
    try:
        cursor = db_conn.cursor()
        cursor.execute("INSERT INTO users (user_id) VALUES (?)", (user_id,))
        db_conn.commit()
        print(f"New user ID logged: {user_id}")
    except sqlite3.IntegrityError:
        print(f"Returning user ID: {user_id}")
        pass

    await update.message.reply_text(WELCOME_MESSAGE, parse_mode="Markdown")

# -----------------
# Conversation Handlers
# -----------------

async def list_posts_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Starts the conversation by listing all unique posts."""
    unique_posts = df['contesting post'].dropna().unique()
    response_text = "Here is the list of all contesting posts:\n\n"
    response_text += "\n".join(unique_posts)
    await update.message.reply_text(response_text)
    await update.message.reply_text("Please reply with the name of the post you are interested in.")
    return SELECTING_POST
#count users command
async def count_users_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Replies with the total number of unique users.
    """
    cursor = db_conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM users")
    count = cursor.fetchone()[0]
    await update.message.reply_text(f"Total unique users: {count}")

async def select_post(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles the user's reply with a post name."""
    user_reply = update.message.text.strip().title()
    candidates = df[df['contesting post'].str.contains(user_reply, case=False, na=False)]
    
    if candidates.empty:
        await update.message.reply_text("I couldn't find any candidates for that post. Please try with a different post name from the list.")
        return SELECTING_POST # Stay in this state
        
    candidate_names = candidates['candidate\'s name'].tolist()
    context.user_data['candidate_list'] = candidate_names
    context.user_data['post_index'] = 0
    
    await send_next_20_candidates(update, context)
    return ASKING_FOR_MORE

# New function for Hall conversation
async def list_halls_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Starts the conversation by listing all unique halls."""
    unique_halls = df['hall'].dropna().unique()
    response_text = "Here is the list of all halls:\n\n"
    response_text += "\n".join(unique_halls)
    await update.message.reply_text(response_text)
    await update.message.reply_text("Please reply with the name of the hall you are interested in.")
    return SELECTING_HALL

# New function for Hall conversation
async def select_hall(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles the user's reply with a hall name."""
    user_reply = update.message.text.strip()
    candidates = df[df['hall'].str.contains(user_reply, case=False, na=False)]

    if candidates.empty:
        await update.message.reply_text("I couldn't find any candidates for that hall. Please try with a different hall name from the list.")
        return SELECTING_HALL # Stay in this state
    
    candidate_names = candidates['candidate\'s name'].tolist()
    context.user_data['candidate_list'] = candidate_names
    context.user_data['post_index'] = 0

    await send_next_20_candidates(update, context)
    return ASKING_FOR_MORE

async def ask_for_more(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles the user's 'yes' or 'no' reply, or a candidate search."""
    user_reply = update.message.text.strip()
    # Check if the user reply matches any candidate's name for a search
    search_results = df[df["candidate's name"].str.contains(user_reply, case=False, na=False)]
    if not search_results.empty:
        # If a candidate is found, handle the search and end the conversation
        await search_candidate_and_end_conv(update, context)
        return ConversationHandler.END

    # If not a search query, then proceed with the 'yes'/'no' logic
    user_reply_lower = user_reply.lower()

    if user_reply_lower == 'yes':
        await send_next_20_candidates(update, context)
        # Stay in this state if more candidates are available
        if context.user_data.get('post_index', 0) < len(context.user_data.get('candidate_list', [])):
            return ASKING_FOR_MORE
        else:
            return ConversationHandler.END
            
    elif user_reply_lower == 'no':
        await update.message.reply_text("Thanks for reducing my workload.")
        return ConversationHandler.END

    else:
        await update.message.reply_text("I'm sorry, I didn't understand that. Please reply 'yes', 'no', or a candidate's name.")
        return ASKING_FOR_MORE

async def end_conversation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """A general handler to end the conversation if the user cancels."""
    await update.message.reply_text("Conversation ended.")
    return ConversationHandler.END

# -----------------
# Helper Functions
# -----------------

async def send_next_20_candidates(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Sends the next 20 candidates in the list."""
    candidate_list = context.user_data['candidate_list']
    current_index = context.user_data['post_index']

    if current_index >= len(candidate_list):
        await update.message.reply_text("That's all the candidates for this post!")
        return

    end_index = current_index + 25
    next_candidates = candidate_list[current_index:end_index]
    
    response_text = "\n".join(next_candidates)
    
    context.user_data['post_index'] = end_index
    
    if end_index < len(candidate_list):
        response_text += "\n\nDo you want more candidate's name? Please reply 'yes' if you want."

    await update.message.reply_text(response_text)
    
async def search_candidate_and_end_conv(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles a general search and ends the conversation."""
    await search_candidate(update, context)
    return ConversationHandler.END

async def search_candidate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles general search queries that are not part of the conversation flow."""
    user_query = update.message.text.strip().lower()
    results = df[df["candidate's name"].str.contains(user_query, case=False, na=False)]
    if not results.empty:
        if len(results) > 1:
            response_text = "I found multiple candidates matching your query:\n\n"
            for index, row in results.iterrows():
                response_text += (
                    f"Ballot No.: {row.get('ballot no.', 'N/A')}\n"
                    f"Name: {row.get('candidate\'s name', 'N/A')}\n"
                    f"Session: {row.get('session number', 'N/A')}\n"
                    f"Department: {row.get('department', 'N/A')}\n"
                    f"Contesting Post: {row.get('contesting post', 'N/A')}\n"
                    f"Tier: {row.get('tier', 'N/A')}\n"
                    f"Facebook: {row.get('facebook id link', 'N/A')}\n\n"
                )

            await update.message.reply_text(response_text)
        else:
            first_match = results.iloc[0]
            response_text = (
                f"Candidate found!\n\n"
                f"Ballot No.: {first_match.get('ballot no.', 'N/A')}\n"
                f"Name: {first_match.get('candidate\'s name', 'N/A')}\n"
                f"Session: {first_match.get('session number', 'N/A')}\n"
                f"Department: {first_match.get('department', 'N/A')}\n"
                f"Hall: {first_match.get('hall', 'N/A')}\n"
                f"Contesting Post: {first_match.get('contesting post', 'N/A')}\n"
                f"Tier: {first_match.get('tier', 'N/A')}\n"
                f"Facebook: {first_match.get('facebook id link', 'N/A')}\n"
            )
            await update.message.reply_text(response_text)
    else:
        await update.message.reply_text(f"Sorry, I couldn't find a candidate matching '{user_query}'. Please check the name and try again.")


def main():
    global df
    try:
        df = pd.read_excel(EXCEL_FILE_PATH)
        print("Excel file loaded successfully!")
    except FileNotFoundError:
        print(f"Error: The file '{EXCEL_FILE_PATH}' was not found. Please make sure it's in the same folder as this script.")
        return
    except Exception as e:
        print(f"An error occurred while loading the file: {e}")
        return
    
    application = ApplicationBuilder().token(BOT_TOKEN).build()
    application.add_handler(CommandHandler(["start", "help"], start_and_help_command))
    application.add_handler(CommandHandler("count_users", count_users_command))

    # Conversation handler for posts
    post_conv_handler = ConversationHandler(
        entry_points=[CommandHandler("posts", list_posts_start)],
        states={
            SELECTING_POST: [MessageHandler(filters.TEXT & ~filters.COMMAND, select_post)],
            ASKING_FOR_MORE: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_for_more)],
        },
        fallbacks=[
            CommandHandler("cancel", end_conversation),
            # Removed the search_candidate_and_end_conv fallback
        ],
    )

    # Conversation handler for halls
    hall_conv_handler = ConversationHandler(
        entry_points=[CommandHandler("halls", list_halls_start)],
        states={
            SELECTING_HALL: [MessageHandler(filters.TEXT & ~filters.COMMAND, select_hall)],
            ASKING_FOR_MORE: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_for_more)],
        },
        fallbacks=[
            CommandHandler("cancel", end_conversation),
            # Removed the search_candidate_and_end_conv fallback
        ],
    )

    # Add both conversation handlers
    application.add_handler(post_conv_handler)
    application.add_handler(hall_conv_handler)
    
    # This general handler must be added after the ConversationHandler to avoid conflicts
    # It will only trigger if the message doesn't match a conversation's entry point or current state.
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, search_candidate_and_end_conv))

    print("Bot is ready! Listening for messages...")
    application.run_polling()

if __name__ == '__main__':
    main()