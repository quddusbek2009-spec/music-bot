import os
import asyncio
import static_ffmpeg
from aiogram import Bot, Dispatcher, types, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
import yt_dlp

static_ffmpeg.add_paths()

BOT_TOKEN = "8907903522:AAFzCrsoCRoEjT3zFlo-udXPKvjczPfWiIw"

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())


class MusicSearch(StatesGroup):
    waiting_for_query = State()


@dp.message(F.text == "/start")
async def start_cmd(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer(
        "🎵 Salom! \n\n"
        "• Faqat **qo'shiqchi nomini** yozsangiz, 10 ta qo'shig'i chiqadi.\n"
        "• **Qo'shiqchi va qo'shig'ini** birga yozsangiz, 5 ta variant chiqadi."
    )
    await state.set_state(MusicSearch.waiting_for_query)


@dp.message(MusicSearch.waiting_for_query)
@dp.message(F.text & ~F.text.startswith("/"))
async def search_music_options(message: types.Message, state: FSMContext):
    query = message.text
    status_msg = await message.answer(f"🔍 '{query}' tezkor qidirilmoqda...")

    limit = 10 if len(query.split()) == 1 else 5

    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
        'extract_flat': True,
    }

    try:
        def fetch_results():
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                return ydl.extract_info(f"ytsearch{limit}:{query}", download=False)

        info = await asyncio.to_thread(fetch_results)
        entries = info.get('entries', [])

        if not entries:
            await status_msg.edit_text("❌ Hech qanday qo'shiq topilmadi.")
            return

        keyboard = []
        for index, entry in enumerate(entries):
            title = entry.get('title', 'Nomaʼlum qoʻshiq')
            url = entry.get('url') or f"https://www.youtube.com/watch?v={entry.get('id')}"

            await state.update_data({f"url_{index}": url, f"title_{index}": title})

            if len(title) > 40:
                title = title[:37] + "..."

            keyboard.append([types.InlineKeyboardButton(text=f"{index + 1}. {title}", callback_data=f"dl_{index}")])

        markup = types.InlineKeyboardMarkup(inline_keyboard=keyboard)
        await status_msg.edit_text(f"🎵 Qidiruv natijalari (Keraklisini tanlang):", reply_markup=markup)

    except Exception as e:
        await status_msg.edit_text(f"❌ Xatolik yuz berdi: {e}")


@dp.callback_query(F.data.startswith("dl_"))
async def download_selected_music(call: types.CallbackQuery, state: FSMContext):
    index = call.data.split("_")[1]
    data = await state.get_data()
    url = data.get(f"url_{index}")
    song_title = data.get(f"title_{index}", "Musiqa")

    if not url:
        await call.answer("❌ Havola eskirgan, qaytadan qidiring!", show_alert=True)
        return

    await call.message.edit_text("⚡ Tezkor yuklab olinmoqda, biroz kuting...")

    output_template = f"song_{call.from_user.id}.%(ext)s"
    mp3_file = f"song_{call.from_user.id}.mp3"

    # Eng tez yuklash va konratsiya qilish uchun optimallashtirilgan sozlamalar
    ydl_opts = {
        'format': 'worstaudio/worst',  # Eng tez yuklanadigan yengil audio formatini olish
        'outtmpl': output_template,
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '96',  # Sifat yetarli darajada yaxshi, lekin hajmi kichik va tez ishlaydi
        }],
        'quiet': True,
        'no_warnings': True,
        'concurrent_fragment_downloads': 5,  # Yuklash tezligini oshirish uchun
    }

    try:
        def download_audio():
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])

        await asyncio.to_thread(download_audio)

        actual_file = mp3_file
        if not os.path.exists(actual_file):
            for f in os.listdir('.'):
                if f.startswith(f"song_{call.from_user.id}") and f.endswith('.mp3'):
                    actual_file = f
                    break

        if os.path.exists(actual_file):
            audio = types.FSInputFile(actual_file)

            parts = song_title.split("-")
            performer = parts[0].strip() if len(parts) > 1 else "YouTube"
            title = parts[1].strip() if len(parts) > 1 else song_title

            await call.message.answer_audio(
                audio=audio,
                title=title,
                performer=performer,
                caption=f"🎵 {song_title}"
            )
            await call.message.delete()
        else:
            await call.message.edit_text("❌ Yuklab olishda xatolik yuz berdi.")

    except Exception as e:
        await call.message.edit_text(f"❌ Xatolik: {e}")
    finally:
        for f in os.listdir('.'):
            if f.startswith(f"song_{call.from_user.id}"):
                try:
                    os.remove(f)
                except:
                    pass
        await state.set_state(MusicSearch.waiting_for_query)


async def main():
    print("Musiqa tanlash boti (tezkor) ishga tushdi...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())