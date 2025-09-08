from typing import Final
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters

TOKEN: Final = '8020756971:AAGSzEXLXH4IvzKzNHD-6YjtvCDs3ikBPZA'
BOT_USERNAME: Final = '@Emfirst_bot'

#Commands
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text('Hello! I am your bot. How can I assist you today?')
    
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text('Hello! I am your bot. How can I help you?')
    
async def custom_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text('Thanks for chatting with me!')
    
    
#Responses
def handle_response(text: str) -> str:
    text = text.lower()
    
    if 'hello' in text:
        return 'Hello there!'
    
    if 'how are you' in text:
        return 'I am doing well, thank you!'
    if 'do you know ananna' in text:
        return 'Yes, she is the wife of my boss'
    
    if 'what is your name' in text:
        return f'My name is {BOT_USERNAME}'
    
    return 'I am sorry, I do not understand.' 


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message_type: str = update.message.chat.type
    text: str = update.message.text
    
    print(f'User ({update.message.chat.id}) in {message_type} sent: {text}')
    
    
    if message_type == 'group':
        if BOT_USERNAME in text:
            new_text: str = text.replace(BOT_USERNAME, '').strip()
            response: str = handle_response(new_text)
        else:
            return
    else:
        response: str = handle_response(text)
        
    print('Bot response:', response)
    await update.message.reply_text(response)
    
    
async def error(update: Update, context: ContextTypes.DEFAULT_TYPE):
    print(f'Update {update} caused error {context.error}')
    
if __name__ == '__main__':
    print('Starting bot...')
    app = Application.builder().token(TOKEN).build()
    
    #commands
    app.add_handler(CommandHandler('start', start_command))
    app.add_handler(CommandHandler('help', help_command))
    app.add_handler(CommandHandler('custom', custom_command))
    
    #messages
    app.add_handler(MessageHandler(filters.TEXT, handle_message))
    
    #errors
    app.add_error_handler(error)
    
    print('Polling...')
    app.run_polling(poll_interval=3)