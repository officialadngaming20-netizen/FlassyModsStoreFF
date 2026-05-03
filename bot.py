import json
import os
from telegram import *
from telegram.ext import *

TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID"))

DATA_FILE = "data.json"

# --------- DATABASE ----------
def load_data():
    with open(DATA_FILE) as f:
        return json.load(f)

def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=4)

# --------- START ----------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = load_data()
    uid = str(update.effective_user.id)

    if uid not in data["users"]:
        data["users"][uid] = {"balance": 0}
        save_data(data)

    keyboard = [
        [InlineKeyboardButton("🛍 Shop", callback_data="shop")],
        [InlineKeyboardButton("💰 Wallet", callback_data="wallet")],
        [InlineKeyboardButton("➕ Add Money", callback_data="addmoney")],
        [InlineKeyboardButton("📦 Orders", callback_data="orders")]
    ]

    await update.message.reply_text(
        "🔥 ULTRA PRO SHOP BOT (NO MONGO)",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# --------- BUTTON ----------
async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    data = load_data()
    uid = str(query.from_user.id)

    if query.data == "shop":
        msg = "🛍 Products:\n\n"
        keyboard = []

        for pid, p in data["products"].items():
            msg += f"{pid}. {p['name']} - {p['price']} BDT\n"
            keyboard.append([InlineKeyboardButton(f"Buy {p['name']}", callback_data=f"buy_{pid}")])

        await query.edit_message_text(msg, reply_markup=InlineKeyboardMarkup(keyboard))

    elif query.data.startswith("buy_"):
        pid = query.data.split("_")[1]
        product = data["products"].get(pid)

        if not product:
            await query.edit_message_text("❌ Product not found")
            return

        balance = data["users"][uid]["balance"]

        if balance < product["price"]:
            await query.edit_message_text("❌ Not enough balance")
            return

        if not product["stock"]:
            await query.edit_message_text("❌ Out of stock")
            return

        # Deduct balance
        data["users"][uid]["balance"] -= product["price"]

        # Deliver item
        item = product["stock"].pop(0)

        data["orders"].append({
            "user": uid,
            "product": product["name"],
            "item": item
        })

        save_data(data)

        await query.edit_message_text(f"✅ Purchased!\n\n📦 {item}")

    elif query.data == "wallet":
        balance = data["users"][uid]["balance"]

        await query.edit_message_text(
            f"💰 Balance: {balance} BDT\n\n"
            "Bkash: 01XXXXXXXXX\n"
            "Nagad: 01XXXXXXXXX\n"
            "Rocket: 01XXXXXXXXX\n\n"
            "Then click ➕ Add Money"
        )

    elif query.data == "addmoney":
        await query.edit_message_text("📸 Send payment screenshot")

    elif query.data == "orders":
        user_orders = [o for o in data["orders"] if o["user"] == uid]

        if not user_orders:
            await query.edit_message_text("No orders yet")
        else:
            msg = "\n".join([o["product"] for o in user_orders])
            await query.edit_message_text(msg)

# --------- SCREENSHOT ----------
async def screenshot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.photo:
        uid = str(update.effective_user.id)

        await context.bot.send_message(
            ADMIN_ID,
            f"💰 Payment request from {uid}\nUse:\n/approve {uid} amount"
        )

        await update.message.reply_text("✅ Sent for approval")

# --------- ADMIN ----------
async def approve(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return

    data = load_data()

    uid = context.args[0]
    amount = int(context.args[1])

    if uid not in data["users"]:
        data["users"][uid] = {"balance": 0}

    data["users"][uid]["balance"] += amount

    save_data(data)

    await context.bot.send_message(int(uid), f"✅ {amount} BDT added")
    await update.message.reply_text("Approved")

async def addproduct(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return

    data = load_data()

    pid = str(len(data["products"]) + 1)
    name = context.args[0]
    price = int(context.args[1])

    data["products"][pid] = {
        "name": name,
        "price": price,
        "stock": []
    }

    save_data(data)

    await update.message.reply_text("✅ Product added")

async def addstock(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return

    data = load_data()

    pid = context.args[0]
    item = " ".join(context.args[1:])

    data["products"][pid]["stock"].append(item)

    save_data(data)

    await update.message.reply_text("✅ Stock added")

# --------- MAIN ----------
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
