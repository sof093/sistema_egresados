from telegram.ext import Application, CommandHandler, MessageHandler, filters
from telegram import KeyboardButton, ReplyKeyboardMarkup
import mysql.connector

def normalizar_telefono(telefono):
    telefono = telefono.strip()

    if telefono.startswith("+52"):
        telefono = telefono[3:]
    elif telefono.startswith("52"):
        telefono = telefono[2:]

    return telefono.replace(" ", "").replace("-", "")
from datetime import datetime

def calcular_temporalidad(estatus, generacion):
    anio_actual = datetime.now().year

    if estatus.lower() == "titulado":
        return "🎓 *Estatus:* Titulado\n⏳ *Temporalidad:* No aplica"

    if not generacion or "-" not in generacion:
        return "⚠️ No se pudo calcular la temporalidad (generación inválida)."

    partes = generacion.split("-")
    anio_egreso = int(partes[1])
    anio_limite = anio_egreso + 10
    anios_restantes = anio_limite - anio_actual

    if anios_restantes > 1:
        return (
            "🟢 *En tiempo*\n"
            f"⏳ Te restan *{anios_restantes} años* para concluir tu titulación."
        )
    elif anios_restantes == 1:
        return (
            "🟡 *En límite de tiempo*\n"
            "⚠️ Te resta *1 año* para concluir tu titulación."
        )
    else:
        return (
            "🔴 *Fuera de tiempo*\n"
            f"❌ El límite fue en el año *{anio_limite}*."
        )


TELEGRAM_TOKEN = "8228079798:AAGQdTst1MuV3V1sV_4ApPphgEg7dzEHYac"

# CONEXIÓN BD
db = mysql.connector.connect(
    host="localhost",
    user="root",
    password="",
    database="seguimiento_egresados_umb"
)
cursor = db.cursor()

async def start(update, context):
    await update.message.reply_text(
        "👋 Hola\n\n"
        "Para vincular tu cuenta con el sistema:\n"
        " 1 Presiona el botón de abajo\n"
        "2 Comparte tu número telefónico\n\n"
        "📱 El número debe ser el mismo que está en la base de datos."
    )

    keyboard = [[KeyboardButton("📱 Compartir mi número", request_contact=True)]]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

    await update.message.reply_text(
        "Presiona el botón 👇",
        reply_markup=reply_markup
    )


async def recibir_telefono(update, context):
    contact = update.message.contact
    chat_id = update.effective_chat.id

    telefono = normalizar_telefono(contact.phone_number)

    print("📞 Teléfono recibido:", telefono)
    print("💬 Chat ID:", chat_id)

    cursor.execute("""
        SELECT nombre_egresado, telefono
        FROM egresados
        WHERE REPLACE(REPLACE(REPLACE(REPLACE(telefono,'+',''),'52',''),' ',''),'-','') = %s
    """, (telefono,))

    egresado = cursor.fetchone()

    if egresado:
        cursor.execute("""
            UPDATE egresados
            SET chat_id = %s
            WHERE REPLACE(REPLACE(REPLACE(REPLACE(telefono,'+',''),'52',''),' ',''),'-','') = %s
        """, (str(chat_id), telefono))

        db.commit()

        await update.message.reply_text(
            f"🟢 Hola {egresado[0]}\n"
            "Tu cuenta fue vinculada correctamente.\n"
            "A partir de ahora recibirás notificaciones."
        )
    else:
        await update.message.reply_text(
            "❌ Tu número no está registrado en el sistema."
        )
async def texto_no_valido(update, context):
    await update.message.reply_text(
        "⚠️ Usa el comando /start y comparte tu número desde el botón."
    )
async def ver_temporalidad(update, context):
    chat_id = update.effective_chat.id

    cursor.execute("""
        SELECT nombre_egresado, estatus_titulacion, generacion
        FROM egresados
        WHERE chat_id = %s
    """, (str(chat_id),))

    egresado = cursor.fetchone()

    if not egresado:
        await update.message.reply_text(
            "⚠️ Tu cuenta no está vinculada.\nUsa /start para registrarte."
        )
        return

    nombre, estatus, generacion = egresado
    mensaje = calcular_temporalidad(estatus, generacion)

    await update.message.reply_text(
        f"📌 *Estado de tu titulación*\n\n"
        f"👤 *{nombre}*\n\n"
        f"{mensaje}",
        parse_mode="Markdown"
    )


def main():
    app = Application.builder().token(TELEGRAM_TOKEN).build()

    # Handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("temporalidad", ver_temporalidad))

    app.add_handler(MessageHandler(filters.CONTACT, recibir_telefono))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, texto_no_valido))

    print("🤖 Bot listo y esperando mensajes...")
    app.run_polling()


if __name__ == "__main__":
    main()
