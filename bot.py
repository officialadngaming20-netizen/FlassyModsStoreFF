import os
from dotenv import load_dotenv
from pymongo import MongoClient
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

load_dotenv()

TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID"))
MONGO_URI = os.getenv("MONGO_URI")

client = MongoClient(MONGO_URI)
db = client["shopbot"]

users = db["users"]
products = db["products"]
orders = db["orders"]

# ---------- START ----------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id

    if not users.find_one({"_id": uid}):
        users.insert_one({"_id": uid, "balance": 0})

    keyboard = [
        [InlineKeyboardButton("🛍 Shop", callback_data="shop")],
        [InlineKeyboardButton("💰 Wallet", callback_data="wallet")],
        [InlineKeyboardButton("➕ Add Money", callback_data="addmoney")],
        [InlineKeyboardButton("📦 Orders", callback_data="orders")]
    ]

    await update.message.reply_text(
        "🔥 ULTRA PRO SHOP BOT",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# ---------- BUTTON ----------
async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    uid = query.from_user.id

    if query.data == "shop":
        text = "🛍 Products:\n\n"
        keyboard = []

        for p in products.find():
            text += f"{p['_id']}. {p['name']} - {p['price']} BDT\n"
            keyboard.append([InlineKeyboardButton(f"Buy {p['name']}", callback_data=f"buy_{p['_id']}")])

        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

    elif query.data.startswith("buy_"):
        pid = int(query.data.split("_")[1])
        product = products.find_one({"_id": pid})
        user = users.find_one({"_id": uid})

        if not product:
            await query.edit_message_text("❌ Product not found")
            return

        if user["balance"] < product["price"]:
            await query.edit_message_text("❌ Not enough balance")
            return

        if not product.get("stock"):
            await query.edit_message_text("❌ Out of stock")
            return

        # Deduct balance
        users.update_one({"_id": uid}, {"$inc": {"balance": -product["price"]}})

        # Deliver item
        item = product["stock"].pop(0)
        products.update_one({"_id": pid}, {"$set": {"stock": product["stock"]}})

        orders.insert_one({
            "user": uid,
            "product": product["name"],
            "item": item
        })

        await query.edit_message_text(f"✅ Purchased!\n\n📦 {item}")

    elif query.data == "wallet":
        user = users.find_one({"_id": uid})
        await query.edit_message_text(
            f"💰 Balance: {user['balance']} BDT\n\n"
            "Send money to:\n"
            "Bkash: 01XXXXXXXXX\n"
            "Nagad: 01XXXXXXXXX\n"
            "Rocket: 01XXXXXXXXX\n\n"
            "Then click ➕ Add Money"
        )

    elif query.data == "addmoney":
        await query.edit_message_text("📸 Send payment screenshot")

    elif query.data == "orders":
        user_orders = orders.find({"user": uid})
        msg = "\n".join([o["product"] for o in user_orders]) or "No orders yet"
        await query.edit_message_text(msg)

# ---------- SCREENSHOT ----------
async def screenshot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.photo:
        uid = update.effective_user.id

        await context.bot.send_message(
            chat_id=ADMIN_ID,
            text=f"💰 Payment request from {uid}\nUse:\n/approve {uid} amount"
        )

        await update.message.reply_text("✅ Sent for approval")

# ---------- ADMIN ----------
async def approve(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return

    uid = int(context.args[0])
    amount = int(context.args[1])

    users.update_one({"_id": uid}, {"$inc": {"balance": amount}})

    await context.bot.send_message(uid, f"✅ {amount} BDT added")
    await update.message.reply_text("Approved")

async def addproduct(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return

    name = context.args[0]
    price = int(context.args[1])

    pid = products.count_documents({}) + 1

    products.insert_one({
        "_id": pid,
        "name": name,
        "price": price,
        "stock": []
    })

    await update.message.reply_text("✅ Product added")

async def addstock(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return

    pid = int(context.args[0])
    item = " ".join(context.args[1:])

    products.update_one({"_id": pid}, {"$push": {"stock": item}})

    await update.message.reply_text("✅ Stock added")

# ---------- MAIN ----------
def main():
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("approve", approve))
    app.add_handler(CommandHandler("addproduct", addproduct))
    app.add_handler(CommandHandler("addstock", addstock))

    app.add_handler(CallbackQueryHandler(button))
    app.add_handler(MessageHandler(filters.PHOTO, screenshot))

    print("Bot running...")
    app.run_polling()

if __name__ == "__main__":
    main()
