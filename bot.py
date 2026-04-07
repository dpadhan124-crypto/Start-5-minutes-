import logging
import requests
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters
from apscheduler.schedulers.background import BackgroundScheduler

# --- Configuration ---
API_TOKEN = '8685424257:AAEfATzkF1jC0w1BJFE6n8bKnZlqxM-_fXQ'
links = {}  # In-memory storage: {"Name": "URL"}

logging.basicConfig(format='%(asctime)s - %(message)s', level=logging.INFO)

# --- Background Task ---
def ping_links():
    """Pings all links every 5 minutes to keep services (like Render) alive."""
    if not links:
        logging.info("No links to ping.")
        return
    for label, url in links.items():
        try:
            response = requests.get(url, timeout=10)
            logging.info(f"Auto-Ping {label} ({url}): {response.status_code}")
        except Exception as e:
            logging.error(f"Auto-Ping Failed for {label}: {e}")

scheduler = BackgroundScheduler()
scheduler.add_job(ping_links, 'interval', minutes=5)
scheduler.start()

# --- Menu Helpers ---
def get_main_menu():
    keyboard = [
        [InlineKeyboardButton("➕ Add Link", callback_data='menu_add')],
        [InlineKeyboardButton("📡 Check Live Status", callback_data='menu_status')],
        [InlineKeyboardButton("📋 List & Manage", callback_data='menu_list')],
    ]
    return InlineKeyboardMarkup(keyboard)

# --- Handlers ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🌐 **Web Monitor Pro**\nSelect an option:", 
                                   reply_markup=get_main_menu(), parse_mode='Markdown')

async def handle_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == 'menu_add':
        await query.edit_message_text("To add a link, use the command:\n`/add Name URL`", parse_mode='Markdown')
    
    elif query.data == 'menu_status':
        if not links:
            await query.edit_message_text("No links found.", reply_markup=get_main_menu())
            return
        
        status_msg = "⏳ *Checking connectivity...*\n\n"
        for label, url in links.items():
            try:
                res = requests.get(url, timeout=5)
                icon = "✅" if res.status_code == 200 else "⚠️"
                status_msg += f"{icon} *{label}*: {res.status_code}\n"
            except:
                status_msg += f"❌ *{label}*: Unreachable\n"
        
        await query.edit_message_text(status_msg, reply_markup=get_main_menu(), parse_mode='Markdown')

    elif query.data == 'menu_list':
        if not links:
            await query.edit_message_text("Your list is empty.", reply_markup=get_main_menu())
            return
        
        # Create a removal menu: one button per link
        keyboard = [[InlineKeyboardButton(f"🗑 Remove {name}", callback_data=f"del_{name}")] for name in links.keys()]
        keyboard.append([InlineKeyboardButton("⬅️ Back", callback_data='back_main')])
        
        await query.edit_message_text("Current Links (Click to remove):", reply_markup=InlineKeyboardMarkup(keyboard))

    elif query.data.startswith('del_'):
        label_to_del = query.data.replace('del_', '')
        if label_to_del in links:
            del links[label_to_del]
            await query.edit_message_text(f"✅ Removed: {label_to_del}", reply_markup=get_main_menu())

    elif query.data == 'back_main':
        await query.edit_message_text("Select an option:", reply_markup=get_main_menu())

async def add_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        label = context.args[0]
        url = context.args[1]
        # Simple URL validation
        if not url.startswith("http"):
            url = "http://" + url
        links[label] = url
        await update.message.reply_text(f"✅ *Added:* {label}\n🔗 {url}", parse_mode='Markdown', reply_markup=get_main_menu())
    except (IndexError, ValueError):
        await update.message.reply_text("❌ Usage: `/add Name URL`", parse_mode='Markdown')

# --- Execution ---
def main():
    app = Application.builder().token(API_TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("add", add_command))
    app.add_handler(CallbackQueryHandler(handle_buttons))
    
    print("Bot is running...")
    app.run_polling()

if __name__ == '__main__':
    main()

