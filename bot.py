import logging
import os
import requests
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
from apscheduler.schedulers.background import BackgroundScheduler

# --- Configuration ---
# Note: Keep your API token secure!
API_TOKEN = '8685424257:AAEfATzkF1jC0w1BJFE6n8bKnZlqxM-_fXQ'
links = {}  # Format: {"Label": "URL"}

# Logging setup
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', 
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# --- Dummy Port / Health Check (For Render) ---
class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/plain")
        self.end_headers()
        self.wfile.write(b"Bot is active and polling.")

    def log_message(self, format, *args):
        return  # Keep logs clean

def run_health_server():
    port = int(os.environ.get("PORT", 10000))
    server = HTTPServer(('0.0.0.0', port), HealthCheckHandler)
    logger.info(f"Starting Health Check Server on port {port}")
    server.serve_forever()

# --- Background Task (5-Minute Pings) ---
def ping_links():
    if not links:
        return
    for label, url in links.items():
        try:
            # Set timeout to prevent the bot from hanging
            response = requests.get(url, timeout=10)
            logger.info(f"Pinged {label}: {response.status_code}")
        except Exception as e:
            logger.error(f"Ping failed for {label}: {e}")

scheduler = BackgroundScheduler()
scheduler.add_job(ping_links, 'interval', minutes=5)
scheduler.start()

# --- Telegram UI Helpers ---
def get_main_menu():
    keyboard = [
        [InlineKeyboardButton("➕ Add Link", callback_data='menu_add')],
        [InlineKeyboardButton("📡 Check Live Status", callback_data='menu_status')],
        [InlineKeyboardButton("📋 List & Manage", callback_data='menu_list')],
    ]
    return InlineKeyboardMarkup(keyboard)

# --- Handlers ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🌐 **Web Monitor Pro**\nI'll ping your links every 5 minutes to keep them alive.",
        reply_markup=get_main_menu(),
        parse_mode='Markdown'
    )

async def add_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        # Check if enough arguments are provided
        if len(context.args) < 2:
            raise ValueError("Missing arguments")
            
        label, url = context.args[0], context.args[1]
        if not url.startswith("http"): 
            url = f"https://{url}"
            
        links[label] = url
        await update.message.reply_text(f"✅ Added **{label}** to the monitor list.", parse_mode='Markdown')
    except:
        await update.message.reply_text("❌ **Invalid Format**\nUse: `/add Name URL`", parse_mode='Markdown')

async def handle_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    try: 
        await query.answer()
    except: 
        pass

    # FIXED: Changed get_main_mode() to get_main_menu()
    if query.data == 'menu_add':
        await query.edit_message_text(
            "📝 **To add a link:**\nSend a message in this format:\n\n`/add Google google.com`", 
            reply_markup=get_main_menu(),
            parse_mode='Markdown'
        )
    
    elif query.data == 'menu_status':
        if not links:
            await query.edit_message_text("No links monitored yet.", reply_markup=get_main_menu())
            return
            
        report = "📡 **Live Status Check:**\n\n"
        for label, url in links.items():
            try:
                res = requests.get(url, timeout=5)
                status_icon = '✅' if res.status_code == 200 else '⚠️'
                report += f"{status_icon} **{label}**: {res.status_code}\n"
            except: 
                report += f"❌ **{label}**: Down\n"
        await query.edit_message_text(report, reply_markup=get_main_menu(), parse_mode='Markdown')

    elif query.data == 'menu_list':
        if not links:
            await query.edit_message_text("The list is currently empty.", reply_markup=get_main_menu())
            return
            
        kb = [[InlineKeyboardButton(f"🗑 Remove {n}", callback_data=f"del_{n}")] for n in links.keys()]
        kb.append([InlineKeyboardButton("⬅️ Back", callback_data='back_main')])
        await query.edit_message_text("Select a link to remove:", reply_markup=InlineKeyboardMarkup(kb))

    elif query.data.startswith('del_'):
        key = query.data.replace('del_', '')
        if key in links: 
            del links[key]
        await query.edit_message_text(f"✅ Removed **{key}** from monitoring.", reply_markup=get_main_menu())

    elif query.data == 'back_main':
        await query.edit_message_text("Select an option:", reply_markup=get_main_menu())

# --- Main Entry ---
def main():
    # 1. Start Health Check thread (Required for Render to stay awake)
    threading.Thread(target=run_health_server, daemon=True).start()

    # 2. Start Bot Application
    app = Application.builder().token(API_TOKEN).build()
    
    # Registering Handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("add", add_command))
    app.add_handler(CallbackQueryHandler(handle_buttons))
    
    logger.info("Bot started and monitoring.")
    app.run_polling()

if __name__ == '__main__':
    main()

