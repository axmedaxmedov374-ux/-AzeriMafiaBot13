import os
import random
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
)

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
OWNER_IDS = {
    int(x.strip())
    for x in os.getenv("OWNER_IDS", "").split(",")
    if x.strip().isdigit()
}

games = {}


def is_owner(user_id):
    return user_id in OWNER_IDS


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "🎭 AZƏRİ MAFİA\n\n"
        "🇦🇿 Azərbaycan dilində Mafia oyunu!\n\n"
        "👥 /game — Yeni oyun\n"
        "➕ /join — Oyuna qoşul\n"
        "➖ /leave — Oyundan çıx\n"
        "👥 /players — Oyunçular\n"
        "🎭 /role — Rolunu göstər\n"
        "🗳️ /vote @istifadəçi — Səs ver\n"
        "📜 /help — Qaydalar\n"
        "🏆 /results — Nəticələr"
    )

    if is_owner(update.effective_user.id):
        text += "\n\n👑 Sən sahibisən: /panel"

    await update.message.reply_text(text)


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📜 OYUN QAYDALARI\n\n"
        "1️⃣ /game ilə oyun yaradılır.\n"
        "2️⃣ /join ilə oyunçular qoşulur.\n"
        "3️⃣ Sahib /startgame ilə oyunu başladır.\n"
        "4️⃣ Rollar avtomatik bölüşdürülür.\n"
        "5️⃣ Gündüz səsvermə edilir.\n"
        "6️⃣ Oyunun sonunda nəticə göstərilir.\n\n"
        "🎭 Rollar: Mafia, Polis, Həkim, Sakin"
    )


async def game(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id

    games[chat_id] = {
        "players": {},
        "roles": {},
        "votes": {},
        "started": False,
        "phase": "lobby",
    }

    await update.message.reply_text(
        "🎭 Yeni AZƏRİ MAFİA oyunu yaradıldı!\n\n"
        "Qoşulmaq üçün: /join\n"
        "Oyunçuları görmək üçün: /players"
    )


async def join(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    user = update.effective_user

    if chat_id not in games:
        await update.message.reply_text("❌ Əvvəlcə /game yaz.")
        return

    if games[chat_id]["started"]:
        await update.message.reply_text("❌ Oyun artıq başlayıb.")
        return

    games[chat_id]["players"][user.id] = {
        "name": user.full_name,
        "username": user.username,
    }

    await update.message.reply_text(
        f"✅ {user.full_name} oyuna qoşuldu!"
    )


async def leave(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id

    if chat_id in games:
        games[chat_id]["players"].pop(user_id, None)
        await update.message.reply_text("✅ Oyundan çıxdın.")


async def players(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id

    if chat_id not in games:
        await update.message.reply_text("❌ Aktiv oyun yoxdur.")
        return

    player_list = games[chat_id]["players"]

    if not player_list:
        await update.message.reply_text("👥 Hələ heç kim qoşulmayıb.")
        return

    text = "👥 OYUNÇULAR\n\n"

    for i, player in enumerate(player_list.values(), 1):
        username = (
            f"@{player['username']}"
            if player["username"]
            else "username yoxdur"
        )
        text += f"{i}. {player['name']} — {username}\n"

    await update.message.reply_text(text)


async def startgame(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id

    if not is_owner(user_id):
        await update.message.reply_text("⛔ Bu əmri yalnız bot sahibi istifadə edə bilər.")
        return

    if chat_id not in games:
        await update.message.reply_text("❌ Əvvəlcə /game yaz.")
        return

    player_ids = list(games[chat_id]["players"].keys())

    if len(player_ids) < 4:
        await update.message.reply_text(
            "❌ Oyunu başlatmaq üçün ən azı 4 oyunçu lazımdır."
        )
        return

    roles = []

    mafia_count = max(1, len(player_ids) // 4)

    roles += ["Mafia"] * mafia_count

    if len(player_ids) >= 5:
        roles.append("Polis")

    if len(player_ids) >= 6:
        roles.append("Həkim")

    while len(roles) < len(player_ids):
        roles.append("Sakin")

    random.shuffle(roles)

    games[chat_id]["roles"] = dict(zip(player_ids, roles))
    games[chat_id]["started"] = True
    games[chat_id]["phase"] = "day"

    for player_id, role in games[chat_id]["roles"].items():
        try:
            await context.bot.send_message(
                player_id,
                f"🎭 Sənin rolun: {role}\n\n"
                "Oyunu izləmək üçün qrupa qayıt."
            )
        except Exception:
            pass

    await update.message.reply_text(
        "🎭 OYUN BAŞLADI!\n\n"
        "Rollar oyunçulara göndərildi.\n"
        "☀️ Mərhələ: GÜNDÜZ\n\n"
        "🗳️ Səs vermək üçün:\n"
        "/vote @istifadəçi"
    )


async def role(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id

    if chat_id not in games or user_id not in games[chat_id]["roles"]:
        await update.message.reply_text("❌ Sənin aktiv oyunda rolun yoxdur.")
        return

    await update.message.reply_text(
        f"🎭 Sənin rolun: {games[chat_id]['roles'][user_id]}"
    )


async def vote(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    voter = update.effective_user

    if chat_id not in games or not games[chat_id]["started"]:
        await update.message.reply_text("❌ Aktiv oyun yoxdur.")
        return

    if not context.args:
        await update.message.reply_text(
            "🗳️ İstifadə: /vote @istifadəçi"
        )
        return

    target_username = context.args[0].lstrip("@").lower()

    target_id = None

    for player_id, player in games[chat_id]["players"].items():
        if player["username"] and player["username"].lower() == target_username:
            target_id = player_id
            break

    if target_id is None:
        await update.message.reply_text("❌ Bu oyunçu tapılmadı.")
        return

    games[chat_id]["votes"][voter.id] = target_id

    await update.message.reply_text(
        f"🗳️ Səsin {target_username} üçün qeydə alındı."
    )


async def results(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id

    if chat_id not in games:
        await update.message.reply_text("❌ Aktiv oyun yoxdur.")
        return

    votes = games[chat_id]["votes"]

    if not votes:
        await update.message.reply_text("🗳️ Hələ səs yoxdur.")
        return

    counts = {}

    for target in votes.values():
        counts[target] = counts.get(target, 0) + 1

    text = "🏆 SƏSVERMƏ NƏTİCƏLƏRİ\n\n"

    for player_id, count in counts.items():
        name = games[chat_id]["players"].get(
            player_id, {}
        ).get("name", "Naməlum")

        text += f"👤 {name}: {count} səs\n"

    await update.message.reply_text(text)


async def panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_owner(update.effective_user.id):
        await update.message.reply_text("⛔ Owner Panel yalnız bot sahibinə açıqdır.")
        return

    keyboard = [
        [
            InlineKeyboardButton("▶️ Oyunu başlat", callback_data="start"),
            InlineKeyboardButton("⏹️ Oyunu dayandır", callback_data="stop"),
        ],
        [
            InlineKeyboardButton("☀️ Gündüz", callback_data="day"),
            InlineKeyboardButton("🌙 Gecə", callback_data="night"),
        ],
        [
            InlineKeyboardButton("🗳️ Səsvermə", callback_data="vote"),
            InlineKeyboardButton("👥 Oyunçular", callback_data="players"),
        ],
        [
            InlineKeyboardButton("🔄 Sıfırla", callback_data="reset"),
        ],
    ]

    await update.message.reply_text(
        "👑 OWNER PANEL\n\nİdarə etmək istədiyin bölməni seç:",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )


async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if not is_owner(query.from_user.id):
        await query.edit_message_text("⛔ İcazən yoxdur.")
        return

    chat_id = query.message.chat.id

    if query.data == "start":
        await query.message.reply_text(
            "▶️ Oyunu başlatmaq üçün /startgame istifadə et."
        )

    elif query.data == "stop":
        if chat_id in games:
            games[chat_id]["started"] = False
        await query.message.reply_text("⏹️ Oyun dayandırıldı.")

    elif query.data == "day":
        if chat_id in games:
            games[chat_id]["phase"] = "day"
        await query.message.reply_text("☀️ Gündüz mərhələsi açıldı.")

    elif query.data == "night":
        if chat_id in games:
            games[chat_id]["phase"] = "night"
        await query.message.reply_text("🌙 Gecə mərhələsi açıldı.")

    elif query.data == "vote":
        await query.message.reply_text(
            "🗳️ Səsvermə açıldı!\n/vote @istifadəçi"
        )

    elif query.data == "players":
        await players(update, context)

    elif query.data == "reset":
        games.pop(chat_id, None)
        await query.message.reply_text("🔄 Oyun sıfırlandı.")


def main():
    if not TOKEN:
        raise RuntimeError(
            "TELEGRAM_BOT_TOKEN dəyişəni təyin edilməyib."
        )

    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("game", game))
    app.add_handler(CommandHandler("newgame", game))
    app.add_handler(CommandHandler("join", join))
    app.add_handler(CommandHandler("leave", leave))
    app.add_handler(CommandHandler("players", players))
    app.add_handler(CommandHandler("startgame", startgame))
    app.add_handler(CommandHandler("role", role))
    app.add_handler(CommandHandler("vote", vote))
    app.add_handler(CommandHandler("results", results))
    app.add_handler(CommandHandler("panel", panel))

    app.add_handler(CallbackQueryHandler(button))

    print("🇦🇿 Azeri Mafia Bot başladı!")

    app.run_polling()


if __name__ == "__main__":
    main()
