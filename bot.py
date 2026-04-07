import logging
import requests
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
from apscheduler.schedulers.background import BackgroundScheduler

# --- Configuration ---
# Replace with your actual Bot Token
API_TOKEN = '8685424257:AAEfATzkF1jC0w1BJFE6n8bKnZlqxM-_fXQ'
links = {}  # Format: {"Label": "URL"}

# Logging setup
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', 
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# --- Background Task (The "Keep-Alive" Engine) ---
def ping_links():
    """Pings all stored URLs every 5 minutes."""
    if not links:
        logger.info("No links to ping.")
        return
    
    for label, url in links.items():
        try:
            # Use a short timeout to prevent the bot from hanging
            response = requests.get(url, timeout=15)
            logger.info(f"Pinged {label} ({url}) - Status: {response.status_code}")
        except Exception as e:
            logger.error(f"Ping failed for {label}: {e}")

# Start the scheduler
scheduler = BackgroundScheduler()
scheduler.add_job(ping_links, 'interval', minutes=5)
scheduler.start()

# --- Menu Builders ---
def get_main_menu():
    keyboard = [
        [InlineKeyboardButton("➕ Add Link", callback_data='menu_add')],
        [InlineKeyboardButton("📡 Check Live Status", callback_data='menu_status')],
        [InlineKeyboardButton("📋 List & Manage", callback_data='menu_list')],
    ]
    return InlineKeyboardMarkup(keyboard)

# --- Command Handlers ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Sends the main menu."""
    await update.message.reply_text(
        "🌐 **Web Monitor Pro**\n\nI will ping your links every 5 minutes to keep them alive on Render.",
        reply_markup=get_main_menu(),
        parse_mode='Markdown'
    )

async def add_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Usage: /add Name https://url.com"""
    try:
        label = context.args[0]
        url = context.args[1]
        if not url.startswith("http"):
            url = f"https://{url}"
        
        links[label] = url
        await update.message.reply_text(f"✅ **Success!**\nMonitoring **{label}** every 5 minutes.", parse_mode='Markdown')
    except (IndexError, ValueError):
        await update.message.reply_text("❌ **Format Error**\nUse: `/add Name URL`", parse_mode='Markdown')

# --- Callback Query Handler (Menu Logic) ---
async def handle_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    
    # 1. Handle the "Query is too old" timeout gracefully
    try:
        await query.answer()
    except Exception as e:
        logger.warning(f"Callback answer failed: {e}")

    # 2. Add Link Info
    if query.data == 'menu_add':
        await query.edit_message_text(
            "To add a new link, type:\n`/add Name YourURL`", 
            reply_markup=get_main_menu(),
            parse_mode='Markdown'
        )
    
    # 3. Status Check
    elif query.data == 'menu_status':
        if not links:
            await query.edit_message_text("No links found.", reply_markup=get_main_menu())
            return
        
        status_report = "📡 **Live Connectivity Check:**\n\n"
        for label, url in links.items():
            try:
                res = requests.get(url, timeout=10)
                icon = "✅" if res.status_code == 200 else "⚠️"
                status_report += f"{icon} **{label}**: {res.status_code}\n"
            except:
                status_report += f"❌ **{label}**: Unreachable\n"
        
        await query.edit_message_text(status_report, reply_markup=get_main_menu(), parse_mode='Markdown')

    # 4. List & Remove Menu
    elif query.data == 'menu_list':
        if not links:
            await query.edit_message_text("Your list is empty.", reply_markup=get_main_menu())
            return
        
        # Build a list of buttons for each link to allow deletion
        keyboard = [[InlineKeyboardButton(f"🗑 Remove {name}", callback_data=f"del_{name}")] for name in links.keys()]
        keyboard.append([InlineKeyboardButton("⬅️ Back", callback_data='back_main')])
        
        await query.edit_message_text("Select a link to **Remove**:", 
                                     reply_markup=InlineKeyboardMarkup(keyboard),
                                     parse_mode='Markdown')

    # 5. Delete Action
    elif query.data.startswith('del_'):
        key = query.data.replace('del_', '')
        if key in links:
            del links[key]
            await query.edit_message_text(f"✅ Removed **{key}**.", reply_markup=get_main_menu(), parse_mode='Markdown')

    # 6. Back Button
    elif query.data == 'back_main':
        await query.edit_message_text("Select an option:", reply_markup=get_main_menu())

# --- Main Entry Point ---
def main():
    # Build the Application
    application = Application.builder().token(API_TOKEN).build()
    
    # Add Handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("add", add_command))
    application.add_handler(CallbackQueryHandler(handle_buttons))
    
    # Run
    print("--- Bot is live and Monitoring ---")
    application.run_polling()

if __name__ == '__main__':
    main()
