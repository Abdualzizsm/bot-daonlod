#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
بوت Telegram لتحميل الفيديوهات من منصات متعددة
نسخة مبسطة بدون لوحة تحكم
"""

import os
import sys
import json
import time
import random
import asyncio
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Set, Optional

import yt_dlp
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from telegram.error import TelegramError, Conflict
from dotenv import load_dotenv

# تحميل متغيرات البيئة
load_dotenv()

# إعداد التسجيل
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# إعدادات البوت
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
if not TELEGRAM_BOT_TOKEN:
    logger.error("❌ TELEGRAM_BOT_TOKEN غير موجود في متغيرات البيئة")
    sys.exit(1)

# إعدادات Rate Limiting
RATE_LIMIT_REQUESTS = 5
RATE_LIMIT_WINDOW = 300  # 5 دقائق
user_requests: Dict[int, list] = {}

# إحصائيات البوت
stats = {
    'total_downloads': 0,
    'video_downloads': 0,
    'audio_downloads': 0,
    'unique_users': set(),
    'start_time': datetime.now().isoformat()
}

# User-Agents عشوائية
USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
]

def load_stats():
    """تحميل الإحصائيات من الملف"""
    global stats
    try:
        if os.path.exists('stats.json'):
            with open('stats.json', 'r', encoding='utf-8') as f:
                loaded_stats = json.load(f)
                # تحويل list إلى set للمستخدمين الفريدين
                if 'unique_users' in loaded_stats:
                    loaded_stats['unique_users'] = set(loaded_stats['unique_users'])
                stats.update(loaded_stats)
                logger.info(f"✅ تم تحميل الإحصائيات: {len(stats['unique_users'])} مستخدم فريد")
    except Exception as e:
        logger.error(f"❌ خطأ في تحميل الإحصائيات: {e}")

def save_stats():
    """حفظ الإحصائيات في الملف"""
    try:
        # تحويل set إلى list للحفظ في JSON
        stats_to_save = stats.copy()
        stats_to_save['unique_users'] = list(stats['unique_users'])
        
        with open('stats.json', 'w', encoding='utf-8') as f:
            json.dump(stats_to_save, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error(f"❌ خطأ في حفظ الإحصائيات: {e}")

def update_stats(user_id: int, download_type: str = 'total'):
    """تحديث الإحصائيات"""
    try:
        stats['unique_users'].add(user_id)
        stats['total_downloads'] += 1
        
        if download_type == 'video':
            stats['video_downloads'] += 1
        elif download_type == 'audio':
            stats['audio_downloads'] += 1
            
        save_stats()
    except Exception as e:
        logger.error(f"❌ خطأ في تحديث الإحصائيات: {e}")

def check_rate_limit(user_id: int) -> bool:
    """فحص حد المعدل للمستخدم"""
    now = time.time()
    
    if user_id not in user_requests:
        user_requests[user_id] = []
    
    # إزالة الطلبات القديمة
    user_requests[user_id] = [req_time for req_time in user_requests[user_id] 
                             if now - req_time < RATE_LIMIT_WINDOW]
    
    # فحص عدد الطلبات
    if len(user_requests[user_id]) >= RATE_LIMIT_REQUESTS:
        return False
    
    # إضافة الطلب الحالي
    user_requests[user_id].append(now)
    return True

def get_random_user_agent():
    """الحصول على User-Agent عشوائي"""
    return random.choice(USER_AGENTS)

def get_ydl_opts(format_type='best'):
    """إعدادات yt-dlp"""
    return {
        'format': format_type,
        'outtmpl': 'downloads/%(title)s.%(ext)s',
        'restrictfilenames': True,
        'noplaylist': True,
        'extractaudio': format_type == 'bestaudio',
        'audioformat': 'mp3' if format_type == 'bestaudio' else None,
        'embed_subs': True,
        'writesubtitles': False,
        'writeautomaticsub': False,
        'ignoreerrors': True,
        'no_warnings': False,
        'retries': 3,
        'fragment_retries': 3,
        'http_headers': {
            'User-Agent': get_random_user_agent()
        }
    }

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالج أمر /start"""
    user_id = update.effective_user.id
    username = update.effective_user.first_name or "صديق"
    
    update_stats(user_id)
    
    welcome_message = f"""
🎬 مرحباً {username}! 

أنا بوت تحميل الفيديوهات من منصات متعددة

📱 المنصات المدعومة:
• YouTube
• TikTok  
• Instagram
• Facebook
• Twitter/X
• SoundCloud
• Vimeo

📝 كيفية الاستخدام:
1. أرسل رابط الفيديو
2. اختر جودة التحميل
3. انتظر التحميل

⚡ ابدأ بإرسال رابط الفيديو الآن!
"""
    
    await update.message.reply_text(welcome_message)

async def get_video_info(url: str) -> Optional[dict]:
    """الحصول على معلومات الفيديو"""
    try:
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'extract_flat': False,
            'http_headers': {
                'User-Agent': get_random_user_agent()
            }
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            return {
                'title': info.get('title', 'غير معروف'),
                'duration': info.get('duration', 0),
                'uploader': info.get('uploader', 'غير معروف'),
                'view_count': info.get('view_count', 0),
                'formats': info.get('formats', [])
            }
    except Exception as e:
        logger.error(f"❌ خطأ في الحصول على معلومات الفيديو: {e}")
        return None

def format_duration(seconds):
    """تنسيق مدة الفيديو"""
    if not seconds:
        return "غير معروف"
    
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    seconds = seconds % 60
    
    if hours > 0:
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
    else:
        return f"{minutes:02d}:{seconds:02d}"

def format_number(num):
    """تنسيق الأرقام"""
    if not num:
        return "0"
    
    if num >= 1000000:
        return f"{num/1000000:.1f}M"
    elif num >= 1000:
        return f"{num/1000:.1f}K"
    else:
        return str(num)

async def handle_url(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالج الروابط"""
    user_id = update.effective_user.id
    url = update.message.text.strip()
    
    # فحص Rate Limiting
    if not check_rate_limit(user_id):
        remaining_time = RATE_LIMIT_WINDOW - (time.time() - min(user_requests[user_id]))
        await update.message.reply_text(
            f"⏳ لقد تجاوزت الحد المسموح ({RATE_LIMIT_REQUESTS} طلبات كل 5 دقائق)\n"
            f"⏰ حاول مرة أخرى بعد {int(remaining_time/60)} دقيقة"
        )
        return
    
    # التحقق من صحة الرابط
    if not any(domain in url for domain in ['youtube.com', 'youtu.be', 'tiktok.com', 'instagram.com', 
                                           'facebook.com', 'twitter.com', 'x.com', 'soundcloud.com', 'vimeo.com']):
        await update.message.reply_text("❌ رابط غير مدعوم. يرجى إرسال رابط من المنصات المدعومة.")
        return
    
    # رسالة انتظار
    loading_msg = await update.message.reply_text("🔍 جاري الحصول على معلومات الفيديو...")
    
    try:
        # الحصول على معلومات الفيديو
        video_info = await get_video_info(url)
        
        if not video_info:
            await loading_msg.edit_text("❌ لا يمكن الحصول على معلومات الفيديو. تأكد من صحة الرابط.")
            return
        
        # عرض معلومات الفيديو
        info_text = f"""
📹 **{video_info['title'][:50]}{'...' if len(video_info['title']) > 50 else ''}**

👤 القناة: {video_info['uploader']}
⏱️ المدة: {format_duration(video_info['duration'])}
👁️ المشاهدات: {format_number(video_info['view_count'])}

اختر جودة التحميل:
"""
        
        # أزرار اختيار الجودة
        keyboard = [
            [
                InlineKeyboardButton("🎬 فيديو عالي الجودة", callback_data=f"download_video_best_{user_id}"),
                InlineKeyboardButton("🎬 فيديو متوسط", callback_data=f"download_video_medium_{user_id}")
            ],
            [
                InlineKeyboardButton("🎵 صوت فقط", callback_data=f"download_audio_{user_id}"),
                InlineKeyboardButton("📱 جودة منخفضة", callback_data=f"download_video_low_{user_id}")
            ]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        # حفظ الرابط مؤقتاً
        context.user_data['current_url'] = url
        
        await loading_msg.edit_text(info_text, reply_markup=reply_markup, parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"❌ خطأ في معالجة الرابط: {e}")
        await loading_msg.edit_text("❌ حدث خطأ في معالجة الرابط. حاول مرة أخرى.")

async def download_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالج أزرار التحميل"""
    query = update.callback_query
    await query.answer()
    
    data_parts = query.data.split('_')
    if len(data_parts) < 3:
        await query.edit_message_text("❌ خطأ في البيانات")
        return
    
    download_type = data_parts[1]  # video أو audio
    quality = data_parts[2] if len(data_parts) > 3 else 'best'
    user_id = int(data_parts[-1])
    
    # التحقق من المستخدم
    if query.from_user.id != user_id:
        await query.answer("❌ لا يمكنك استخدام هذا الزر", show_alert=True)
        return
    
    url = context.user_data.get('current_url')
    if not url:
        await query.edit_message_text("❌ انتهت صلاحية الرابط. أرسل الرابط مرة أخرى.")
        return
    
    # رسالة التحميل
    await query.edit_message_text("⬇️ جاري التحميل... قد يستغرق بعض الوقت")
    
    try:
        # إعداد مجلد التحميل
        download_dir = Path("downloads")
        download_dir.mkdir(exist_ok=True)
        
        # تحديد نوع التحميل
        if download_type == 'audio':
            format_selector = 'bestaudio/best'
            file_ext = 'mp3'
            stats_type = 'audio'
        else:
            if quality == 'best':
                format_selector = 'best[height<=1080]'
            elif quality == 'medium':
                format_selector = 'best[height<=720]'
            else:  # low
                format_selector = 'worst'
            file_ext = 'mp4'
            stats_type = 'video'
        
        # إعدادات التحميل
        ydl_opts = get_ydl_opts(format_selector)
        
        # التحميل
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info)
            
            # البحث عن الملف المحمل
            downloaded_file = None
            for file_path in download_dir.glob("*"):
                if file_path.is_file() and info['title'] in file_path.name:
                    downloaded_file = file_path
                    break
            
            if not downloaded_file or not downloaded_file.exists():
                await query.edit_message_text("❌ فشل في العثور على الملف المحمل")
                return
            
            # فحص حجم الملف
            file_size = downloaded_file.stat().st_size
            max_size = 50 * 1024 * 1024  # 50 MB
            
            if file_size > max_size:
                await query.edit_message_text(
                    f"❌ الملف كبير جداً ({file_size/1024/1024:.1f} MB)\n"
                    f"الحد الأقصى: 50 MB"
                )
                downloaded_file.unlink()  # حذف الملف
                return
            
            # إرسال الملف
            await query.edit_message_text("📤 جاري رفع الملف...")
            
            with open(downloaded_file, 'rb') as file:
                if download_type == 'audio':
                    await context.bot.send_audio(
                        chat_id=query.message.chat_id,
                        audio=file,
                        title=info.get('title', 'صوت'),
                        performer=info.get('uploader', 'غير معروف')
                    )
                else:
                    await context.bot.send_video(
                        chat_id=query.message.chat_id,
                        video=file,
                        caption=f"🎬 {info.get('title', 'فيديو')}"
                    )
            
            # تحديث الإحصائيات
            update_stats(user_id, stats_type)
            
            # حذف الملف المؤقت
            downloaded_file.unlink()
            
            await query.edit_message_text("✅ تم التحميل بنجاح!")
            
    except Exception as e:
        logger.error(f"❌ خطأ في التحميل: {e}")
        await query.edit_message_text(f"❌ فشل التحميل: {str(e)[:100]}")
        
        # تنظيف الملفات المؤقتة
        try:
            for file_path in Path("downloads").glob("*"):
                if file_path.is_file():
                    file_path.unlink()
        except:
            pass

async def handle_other_messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالج الرسائل الأخرى"""
    await update.message.reply_text(
        "❌ يرجى إرسال رابط فيديو صحيح من المنصات المدعومة:\n"
        "• YouTube\n• TikTok\n• Instagram\n• Facebook\n• Twitter/X\n• SoundCloud\n• Vimeo"
    )

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    """معالج الأخطاء العام"""
    logger.error(f"❌ خطأ في البوت: {context.error}")
    
    if isinstance(update, Update) and update.effective_message:
        try:
            await update.effective_message.reply_text("❌ حدث خطأ غير متوقع. حاول مرة أخرى.")
        except:
            pass

async def run_bot():
    """تشغيل البوت مع إعادة المحاولة في حالة الأخطاء"""
    max_retries = 5
    retry_delay = 5
    
    for attempt in range(max_retries):
        application = None
        try:
            logger.info(f"🚀 محاولة تشغيل البوت #{attempt + 1}")
            
            # إنشاء التطبيق
            application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
            
            # إضافة المعالجات
            application.add_handler(CommandHandler("start", start))
            application.add_handler(CommandHandler("help", help_command))
            application.add_handler(CommandHandler("stats", stats))
            application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
            application.add_error_handler(error_handler)
            
            # حذف webhook إذا كان موجوداً
            try:
                await application.bot.delete_webhook(drop_pending_updates=True)
                await asyncio.sleep(1)
            except Exception as e:
                logger.warning(f"⚠️ تحذير عند حذف webhook: {e}")
            
            # تهيئة التطبيق
            await application.initialize()
            logger.info("✅ البوت يعمل الآن...")
            
            # تشغيل البوت
            await application.run_polling(
                drop_pending_updates=True,
                allowed_updates=['message', 'callback_query']
            )
            
            # إذا وصلنا هنا، فالبوت توقف بشكل طبيعي
            break
            
        except Conflict as e:
            logger.warning(f"⚠️ تعارض Telegram: {e}")
            if application:
                try:
                    await application.shutdown()
                except:
                    pass
            
            if attempt < max_retries - 1:
                wait_time = retry_delay * (2 ** attempt) + random.uniform(1, 5)
                logger.info(f"⏳ إعادة المحاولة بعد {wait_time:.1f} ثانية...")
                await asyncio.sleep(wait_time)
            else:
                logger.error("❌ فشل في حل تعارض Telegram بعد عدة محاولات")
                break
                
        except Exception as e:
            logger.error(f"❌ خطأ في تشغيل البوت: {e}")
            if application:
                try:
                    await application.shutdown()
                except:
                    pass
            
            if attempt < max_retries - 1:
                wait_time = retry_delay * (2 ** attempt)
                logger.info(f"⏳ إعادة المحاولة بعد {wait_time} ثانية...")
                await asyncio.sleep(wait_time)
            else:
                logger.error("❌ فشل في تشغيل البوت بعد عدة محاولات")
                break
        
        finally:
            # تنظيف التطبيق
            if application:
                try:
                    await application.shutdown()
                except:
                    pass

def main():
    """الدالة الرئيسية"""
    try:
        # تحميل الإحصائيات
        load_stats()
        
        # تشغيل البوت
        asyncio.run(run_bot())
    except KeyboardInterrupt:
        logger.info("🛑 تم إيقاف البوت بواسطة المستخدم")
    except Exception as e:
        logger.error(f"❌ خطأ في الدالة الرئيسية: {e}")

if __name__ == "__main__":
    main()
