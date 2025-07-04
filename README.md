# 🤖 بوت التحميل الاحترافي - إصدار Render

[![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com/deploy?repo=https://github.com/Abdualzizsm/bot-daonlod)

## 📋 نظرة عامة

بوت تلقرام احترافي لتحميل الفيديوهات والصوتيات من منصات متعددة مع لوحة تحكم ويب مدمجة لمراقبة الإحصائيات في الوقت الفعلي.

## ✨ المميزات الرئيسية

### 🎥 تحميل الوسائط
- **منصات مدعومة**: YouTube, TikTok, Instagram, Facebook, Twitter, SoundCloud, Vimeo
- **خيارين بسيطين**: فيديو بأعلى جودة متوفرة أو صوت فقط
- **جودة عالية**: فيديو بأفضل جودة متاحة، صوت MP3 192kbps
- **شريط تقدم**: متابعة حالة التحميل في الوقت الفعلي
- **معلومات تفصيلية**: عنوان، مدة، منشئ المحتوى، عدد المشاهدات

### 📊 نظام الإحصائيات المدمج
- **إحصائيات شاملة**: عدد المستخدمين، التحميلات، نوع المحتوى
- **إحصائيات يومية**: تتبع التحميلات اليومية
- **وقت التشغيل**: مراقبة مدة تشغيل البوت
- **حفظ تلقائي**: الإحصائيات محفوظة في `bot_stats.json`

### 🌐 لوحة تحكم ويب
- **واجهة عصرية**: تصميم متجاوب وجميل
- **تحديث تلقائي**: كل 30 ثانية
- **إحصائيات مباشرة**: مراقبة في الوقت الفعلي
- **سهولة الوصول**: متاحة على `http://localhost:5002`

## 🚀 النشر على Render

### الطريقة السهلة (النقر على الزر)

[![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com/deploy?repo=https://github.com/Abdualzizsm/bot-daonlod)

### الطريقة اليدوية:

1. قم بإنشاء حساب جديد على [Render](https://render.com/) إذا لم يكن لديك حساب
2. انقر على "New +" ثم اختر "Web Service"
3. قم بربط حساب GitHub الخاص بك
4. اختر مستودع `Abdualzizsm/bot-daonlod`
5. قم بتعيين الإعدادات التالية:
   - **Name**: أي اسم تفضله (مثل: my-telegram-bot)
   - **Region**: اختر الأقرب إليك
   - **Branch**: main
   - **Runtime**: Python 3
   - **Build Command**: pip install -r requirements.txt
   - **Start Command**: python bot.py
6. أضف متغير البيئة:
   - **Key**: `TELEGRAM_BOT_TOKEN`
   - **Value**: توكن البوت الخاص بك
7. انقر على "Create Web Service"

## 💻 التثبيت والتشغيل محلياً

### 1. متطلبات النظام
```bash
# Python 3.8+ مطلوب
python --version

# FFmpeg مطلوب لمعالجة الوسائط
# macOS:
brew install ffmpeg

# Ubuntu/Debian:
sudo apt update && sudo apt install ffmpeg

# Windows: تحميل من https://ffmpeg.org/
```

### 2. إعداد المشروع
```bash
# استنساخ أو تحميل المشروع
cd bot

# إنشاء البيئة الافتراضية
python -m venv venv

# تفعيل البيئة الافتراضية
# macOS/Linux:
source venv/bin/activate
# Windows:
venv\Scripts\activate

# تثبيت المتطلبات
pip install -r requirements.txt
```

### 3. إعداد متغيرات البيئة
```bash
# إنشاء ملف .env
echo "TELEGRAM_BOT_TOKEN=YOUR_BOT_TOKEN_HERE" > .env

# أو تحرير الملف يدوياً
nano .env
```

### 4. تشغيل البوت المدمج
```bash
# تشغيل البوت مع لوحة التحكم
python bot_complete.py
```

## 📱 استخدام البوت

### أوامر البوت
- `/start` - بدء استخدام البوت
- إرسال رابط فيديو من أي منصة مدعومة

### خيارات التحميل
1. **🎥 فيديو** - تحميل بأعلى جودة متوفرة
2. **🎵 صوت** - استخراج الصوت بجودة MP3 192kbps

### لوحة التحكم
- **الوصول**: `http://localhost:5002`
- **المميزات**:
  - 👥 إجمالي المستخدمين
  - 📥 إجمالي التحميلات
  - 🎥 تحميلات الفيديو
  - 🎵 تحميلات الصوت
  - ⏰ وقت التشغيل
  - 📅 تحميلات اليوم

## 📁 هيكل الملفات

```
bot/
├── bot_complete.py      # الملف الرئيسي المدمج
├── requirements.txt     # المتطلبات
├── .env                # متغيرات البيئة
├── bot_stats.json      # ملف الإحصائيات (يُنشأ تلقائياً)
├── temp/               # مجلد التحميل المؤقت
└── venv/               # البيئة الافتراضية
```

## 🔧 المتطلبات التقنية

### Python Packages
```
python-telegram-bot==20.7
yt-dlp
requests
python-dotenv==1.0.0
ffmpeg-python
Flask==3.0.0
```

### متغيرات البيئة
- `TELEGRAM_BOT_TOKEN` - توكن البوت من @BotFather

## 🛡️ الأمان والحماية

### حماية التوكن
- التوكن محفوظ في ملف `.env` منفصل
- عدم تضمين التوكن في الكود المصدري
- إضافة `.env` إلى `.gitignore`

### تنظيف الملفات
- حذف تلقائي للملفات المؤقتة
- تنظيف عند إغلاق البوت
- حد أقصى لحجم الملف (50 MB)

### لوحة التحكم
- **محلية فقط**: متاحة على localhost
- **بدون مصادقة**: مناسبة للاستخدام المحلي
- **للاستخدام العام**: يُنصح بإضافة مصادقة

## 🔍 استكشاف الأخطاء

### مشاكل شائعة

#### 1. خطأ في التوكن
```
❌ لم يتم العثور على TELEGRAM_BOT_TOKEN في ملف .env
```
**الحل**: تأكد من وجود ملف `.env` مع التوكن الصحيح

#### 2. تعارض البوت
```
❌ تعارض في getUpdates - يرجى إيقاف النسخ الأخرى من البوت
```
**الحل**: أوقف جميع نسخ البوت الأخرى

#### 3. خطأ في FFmpeg
```
❌ خطأ في التحميل: ffmpeg not found
```
**الحل**: تثبيت FFmpeg على النظام

#### 4. تعارض المنفذ
```
Address already in use - Port 5002 is in use
```
**الحل**: غيّر المنفذ في الكود أو أوقف العملية المستخدمة للمنفذ

### سجلات الأخطاء
- السجلات تظهر في وحدة التحكم
- تفاصيل الأخطاء مع أرقام الأسطر
- رسائل خطأ باللغة العربية

## 📈 مراقبة الأداء

### الإحصائيات المتاحة
- عدد المستخدمين الفريدين
- إجمالي التحميلات
- تقسيم التحميلات (فيديو/صوت)
- الإحصائيات اليومية
- وقت تشغيل البوت

### ملف الإحصائيات
```json
{
  "total_users": 150,
  "total_downloads": 500,
  "video_downloads": 300,
  "audio_downloads": 200,
  "start_time": 1640995200.0,
  "daily_stats": {
    "2024-01-01": 25,
    "2024-01-02": 30
  },
  "users": [123456789, 987654321]
}
```

## 🚀 النشر والتشغيل المستمر

### تشغيل في الخلفية
```bash
# استخدام nohup
nohup python bot_complete.py > bot.log 2>&1 &

# استخدام screen
screen -S telegram_bot
python bot_complete.py
# Ctrl+A, D للخروج

# العودة إلى الجلسة
screen -r telegram_bot
```

### خدمة systemd (Linux)
```ini
[Unit]
Description=Telegram Download Bot
After=network.target

[Service]
Type=simple
User=your_username
WorkingDirectory=/path/to/bot
ExecStart=/path/to/bot/venv/bin/python bot_complete.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

## 🔄 التحديثات والصيانة

### تحديث المتطلبات
```bash
pip install --upgrade -r requirements.txt
```

### نسخ احتياطي للإحصائيات
```bash
cp bot_stats.json bot_stats_backup_$(date +%Y%m%d).json
```

### مراقبة السجلات
```bash
tail -f bot.log
```

## 📞 الدعم والمساعدة

### الإبلاغ عن المشاكل
- تحقق من السجلات أولاً
- تأكد من تحديث المتطلبات
- قدم تفاصيل كاملة عن الخطأ

### تحسين الأداء
- مراقبة استخدام الذاكرة
- تنظيف الملفات المؤقتة دورياً
- مراقبة مساحة القرص الصلب

---

## 📝 ملاحظات مهمة

1. **الاستخدام القانوني**: تأكد من احترام حقوق الطبع والنشر
2. **حدود التحميل**: 50 MB حد أقصى للملف الواحد
3. **الأداء**: قد يتأثر بسرعة الإنترنت وحجم الملف
4. **التحديثات**: تحقق من تحديثات yt-dlp دورياً

**استمتع باستخدام البوت! 🎉**
