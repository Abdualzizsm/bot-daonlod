#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
اختبار سريع للتأكد من أن البوت يعمل بشكل صحيح
"""

import sys
import os
import importlib.util

def test_imports():
    """اختبار استيراد المكتبات المطلوبة"""
    print("🔍 اختبار استيراد المكتبات...")
    
    required_modules = [
        'telegram',
        'yt_dlp', 
        'flask',
        'requests',
        'dotenv'
    ]
    
    missing_modules = []
    
    for module in required_modules:
        try:
            __import__(module)
            print(f"✅ {module}")
        except ImportError:
            print(f"❌ {module}")
            missing_modules.append(module)
    
    if missing_modules:
        print(f"\n❌ مكتبات مفقودة: {', '.join(missing_modules)}")
        print("قم بتشغيل: pip install -r requirements.txt")
        return False
    else:
        print("\n✅ جميع المكتبات متوفرة!")
        return True

def test_bot_file():
    """اختبار ملف البوت"""
    print("\n🔍 اختبار ملف البوت...")
    
    bot_file = "bot.py"
    if not os.path.exists(bot_file):
        print(f"❌ ملف {bot_file} غير موجود")
        return False
    
    try:
        # محاولة استيراد البوت
        spec = importlib.util.spec_from_file_location("bot", bot_file)
        bot_module = importlib.util.module_from_spec(spec)
        
        # التحقق من وجود الدوال المهمة
        required_functions = [
            'update_stats',
            'load_stats', 
            'save_stats',
            'run_bot',
            'error_handler'
        ]
        
        print("🔍 فحص الدوال المطلوبة...")
        with open(bot_file, 'r', encoding='utf-8') as f:
            content = f.read()
            
        missing_functions = []
        for func in required_functions:
            if f"def {func}" in content:
                print(f"✅ {func}")
            else:
                print(f"❌ {func}")
                missing_functions.append(func)
        
        if missing_functions:
            print(f"\n❌ دوال مفقودة: {', '.join(missing_functions)}")
            return False
        else:
            print("\n✅ جميع الدوال موجودة!")
            return True
            
    except Exception as e:
        print(f"❌ خطأ في فحص ملف البوت: {e}")
        return False

def test_env_file():
    """اختبار ملف البيئة"""
    print("\n🔍 اختبار ملف البيئة...")
    
    env_file = ".env"
    if not os.path.exists(env_file):
        print(f"⚠️ ملف {env_file} غير موجود")
        print("قم بإنشائه مع: echo 'TELEGRAM_BOT_TOKEN=your_token' > .env")
        return False
    
    try:
        with open(env_file, 'r') as f:
            content = f.read()
            
        if 'TELEGRAM_BOT_TOKEN' in content:
            print("✅ TELEGRAM_BOT_TOKEN موجود في .env")
            return True
        else:
            print("❌ TELEGRAM_BOT_TOKEN غير موجود في .env")
            return False
            
    except Exception as e:
        print(f"❌ خطأ في قراءة ملف .env: {e}")
        return False

def test_python_version():
    """اختبار إصدار Python"""
    print("\n🔍 اختبار إصدار Python...")
    
    version = sys.version_info
    print(f"📍 إصدار Python الحالي: {version.major}.{version.minor}.{version.micro}")
    
    if version.major == 3 and version.minor >= 8:
        print("✅ إصدار Python مناسب")
        return True
    else:
        print("❌ يتطلب Python 3.8 أو أحدث")
        return False

def main():
    """تشغيل جميع الاختبارات"""
    print("🧪 بدء اختبار البوت...\n")
    
    tests = [
        ("إصدار Python", test_python_version),
        ("المكتبات المطلوبة", test_imports),
        ("ملف البوت", test_bot_file),
        ("ملف البيئة", test_env_file)
    ]
    
    results = []
    
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ خطأ في اختبار {test_name}: {e}")
            results.append((test_name, False))
    
    # عرض النتائج النهائية
    print("\n" + "="*50)
    print("📊 نتائج الاختبار:")
    print("="*50)
    
    passed = 0
    total = len(results)
    
    for test_name, result in results:
        status = "✅ نجح" if result else "❌ فشل"
        print(f"{test_name}: {status}")
        if result:
            passed += 1
    
    print(f"\n📈 النتيجة النهائية: {passed}/{total} اختبارات نجحت")
    
    if passed == total:
        print("\n🎉 البوت جاهز للتشغيل!")
        print("قم بتشغيله مع: python3 bot.py")
    else:
        print(f"\n⚠️ يرجى إصلاح {total - passed} مشكلة قبل التشغيل")
    
    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
