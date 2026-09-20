
import sys
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

import os
import time
import socket
import threading
import base64
from datetime import datetime
from flask import Flask, render_template_string, jsonify
import pyautogui
import keyboard
import pygetwindow as gw
from PIL import Image
from google import genai
import qrcode

# ==========================================
# 🔑 APIキー設定
# ==========================================
GEMINI_API_KEY = "ここに取得したAPIキーを入れる"

app = Flask(__name__)
gemini_client = genai.Client(api_key=GEMINI_API_KEY)

IMAGE_SAVE_DIR = "saved_captures"
if not os.path.exists(IMAGE_SAVE_DIR):
    os.makedirs(IMAGE_SAVE_DIR)

latest_result = {
    "title": "HVOS Web Earth Edition - スタンバイ完了",
    "gemini_content": "【HVOS Web Earth版 スタンバイOK！】\nPCで Google Earth（全画面）を開いた状態で【1】を押すと、景色をGeminiが即座に解析します！",
    "timestamp": ""
}

is_processing = False
processing_lock = threading.Lock()

def get_local_ip():
    hostname = socket.gethostname()
    try:
        return socket.gethostbyname(hostname)
    except Exception:
        return "127.0.0.1"

LOCAL_IP = get_local_ip()
MOBILE_URL = f"http://{LOCAL_IP}:5000"

def generate_qr_base64(url):
    qr = qrcode.QRCode(border=2)
    qr.add_data(url)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buffered = io.BytesIO()
    img.save(buffered, format="PNG")
    return base64.b64encode(buffered.getvalue()).decode("utf-8")

QR_BASE64 = generate_qr_base64(MOBILE_URL)

def bring_earth_window_to_front():
    try:
        all_wins = gw.getAllWindows()
        target_win = None
        for win in all_wins:
            title_lower = win.title.lower()
            if any(k in title_lower for k in ["google earth", "earth", "map", "マップ"]):
                target_win = win
                break

        if target_win:
            if target_win.isMinimized:
                target_win.restore()
                time.sleep(0.05)
            pyautogui.press('alt')
            target_win.activate()
            time.sleep(0.1)
            return target_win
    except Exception:
        pass
    return None

def execute_analysis():
    global latest_result, is_processing

    with processing_lock:
        if is_processing:
            return
        is_processing = True

    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    latest_result["title"] = "解析中..."
    latest_result["gemini_content"] = "画像を最適化して送信中...最新のAIガイド解説を生成しています。"
    latest_result["timestamp"] = now_str

    saved_img_path = os.path.join(IMAGE_SAVE_DIR, f"cap_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg")

    try:
        earth_win = bring_earth_window_to_front()
        screenshot = pyautogui.screenshot()

        if earth_win and earth_win.width > 0 and earth_win.height > 0:
            left, top = max(0, earth_win.left), max(0, earth_win.top)
            right = min(screenshot.width, earth_win.right)
            bottom = min(screenshot.height, earth_win.bottom)
            w, h = right - left, bottom - top
            
            cropped_img = screenshot.crop((
                left + int(w * 0.02),
                top + int(h * 0.08),
                left + int(w * 0.98),
                bottom - int(h * 0.02)
            ))
        else:
            w, h = screenshot.size
            cropped_img = screenshot.crop((int(w * 0.02), int(h * 0.08), int(w * 0.98), int(h * 0.98)))

        cropped_img = cropped_img.convert("RGB")
        cropped_img.thumbnail((1024, 1024))
        cropped_img.save(saved_img_path, "JPEG", quality=85)

        prompt = (
            "あなたは最高のバーチャルツアーガイドです。この画面（Google Earthの3D景観またはストリートビュー）に写っている場所について、以下の構成で400〜500文字で魅力的に解説してください。\n\n"
            "1. 【場所の特定と概要】：ここがどこか、何という施設・自然・街並みか\n"
            "2. 【歴史と背景】：この場所にまつわる歴史やストーリー、地理的な特徴など\n"
            "3. 【ここだけの魅力・おすすめポイント】：訪れた人がワクワクする豆知識や見どころ\n"
            "4. 【周囲のおすすめ・楽しみ方】：周辺の立ち寄りスポットや体験のポイント\n\n"
            "語り口は親しみやすく、聞いているだけで旅に出たくなるようなワクワクする文章でまとめてください。文末には必ず『（文字数：〇〇文字）』と実際に生成した文字数を記載してください。"
        )
        img = Image.open(saved_img_path)
        
        response = gemini_client.models.generate_content(
            model='gemini-3.6-flash',
            contents=[prompt, img]
        )

        latest_result["title"] = "HVOS Web Earth ガイド解説"
        latest_result["gemini_content"] = response.text

    except Exception as e:
        latest_result["title"] = "エラー発生"
        latest_result["gemini_content"] = f"処理エラー: {e}"

    finally:
        with processing_lock:
            is_processing = False

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no, viewport-fit=cover">
    <meta name="apple-mobile-web-app-capable" content="yes">
    <meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
    <title>HVOS Web Earth Dashboard</title>
    <style>
        * { box-sizing: border-box; }
        html, body {
            height: 100%;
            margin: 0;
            padding: 0;
            background-color: #0f172a;
            color: #f8fafc;
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            overflow-x: hidden;
        }
        .container {
            display: flex;
            flex-direction: column;
            min-height: 100vh;
            padding: 12px;
        }
        .header { 
            font-size: 1.0rem; 
            font-weight: bold; 
            color: #818cf8; 
            border-bottom: 1px solid #334155; 
            padding-bottom: 6px; 
            display: flex; 
            justify-content: space-between; 
            align-items: center;
            flex-shrink: 0;
        }
        .connect-box {
            background: #0284c7;
            color: #ffffff;
            border-radius: 8px;
            padding: 12px 16px;
            margin-top: 10px;
            display: flex;
            align-items: center;
            justify-content: space-between;
        }
        .connect-info {
            font-size: 0.9rem;
            line-height: 1.5;
        }
        .connect-url {
            font-family: monospace;
            font-size: 1.1rem;
            font-weight: bold;
            background: #0369a1;
            padding: 4px 8px;
            border-radius: 4px;
            display: inline-block;
            margin-top: 4px;
            color: #ffffff;
            text-decoration: none;
        }
        .qr-img {
            width: 90px;
            height: 90px;
            border-radius: 6px;
            background: #ffffff;
            padding: 4px;
        }
        .card { 
            flex-grow: 1;
            background: #1e293b; 
            border-radius: 12px; 
            padding: 14px; 
            margin-top: 10px; 
            border-top: 4px solid #38bdf8; 
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.3);
            overflow-y: auto;
            -webkit-overflow-scrolling: touch;
        }
        .content { 
            font-size: 0.95rem; 
            line-height: 1.7; 
            white-space: pre-wrap; 
            word-wrap: break-word;
        }
    </style>
    <script>
        setInterval(async () => {
            try {
                const res = await fetch('/api/data');
                const data = await res.json();
                document.getElementById('ui-title').innerText = data.title;
                document.getElementById('ui-timestamp').innerText = data.timestamp;
                document.getElementById('ui-gemini').innerText = data.gemini_content;
            } catch (e) {}
        }, 1000);
    </script>
</head>
<body>
    <div class="container">
        <div class="header">
            <span id="ui-title">{{ title }}</span>
            <span id="ui-timestamp" style="font-size:0.75rem; color:#94a3b8;">{{ timestamp }}</span>
        </div>
        
        <div class="connect-box">
            <div class="connect-info">
                📱 <strong>スマホ接続用URL（カメラで読み取り）</strong><br>
                <a href="{{ mobile_url }}" target="_blank" class="connect-url">{{ mobile_url }}</a>
            </div>
            <img class="qr-img" src="data:image/png;base64,{{ qr_code }}" alt="QR Code">
        </div>

        <div class="card">
            <div id="ui-gemini" class="content">{{ gemini_content }}</div>
        </div>
    </div>
</body>
</html>
"""

@app.route('/')
def home():
    return render_template_string(
        HTML_TEMPLATE, 
        title=latest_result["title"], 
        timestamp=latest_result["timestamp"], 
        gemini_content=latest_result["gemini_content"],
        mobile_url=MOBILE_URL,
        qr_code=QR_BASE64
    )

@app.route('/api/data')
def get_data():
    return jsonify(latest_result)

def start_keyboard_listener():
    last_execution_time = 0
    cooldown_seconds = 3.0

    while True:
        if keyboard.is_pressed("1") or keyboard.is_pressed("num 1"):
            current_time = time.time()
            if current_time - last_execution_time > cooldown_seconds:
                last_execution_time = current_time
                if not is_processing:
                    threading.Thread(target=execute_analysis).start()
            
            while keyboard.is_pressed("1") or keyboard.is_pressed("num 1"):
                time.sleep(0.05)

        time.sleep(0.05)

if __name__ == '__main__':
    threading.Thread(target=start_keyboard_listener, daemon=True).start()

    print(f"\n==========================================")
    print(f"=== HVOS (PC Base Edition) 稼働中 ===")
    print(f"・PC用URL: http://localhost:5000")
    print(f"・スマホ用URL: {MOBILE_URL}")
    print(f"==========================================\n")

    app.run(host='0.0.0.0', port=5000, debug=False, use_reloader=False)

app = Flask(__name__)
gemini_client = genai.Client(api_key=GEMINI_API_KEY)

IMAGE_SAVE_DIR = "saved_captures"
if not os.path.exists(IMAGE_SAVE_DIR):
    os.makedirs(IMAGE_SAVE_DIR)

# スタンバイ完了時のメッセージ
latest_result = {
    "title": "HVOS Web Earth Edition - スタンバイ完了",
    "gemini_content": "【HVOS Web Earth版 スタンバイOK！】\nPCで Google Earth（ブラウザ）を開いた状態で、キーボードの【1】を押すと、画面の景色をGeminiが撮影＆解析します！",
    "timestamp": ""
}

is_processing = False
processing_lock = threading.Lock()

def bring_earth_window_to_front():
    """ブラウザで開いている Google Earth のウィンドウを探して最前面にする"""
    try:
        all_wins = gw.getAllWindows()
        target_win = None
        
        # Google Earth を開いているブラウザウィンドウを検索
        for win in all_wins:
            title_lower = win.title.lower()
            if any(k in title_lower for k in ["google earth", "earth"]):
                target_win = win
                break

        if target_win:
            if target_win.isMinimized:
                target_win.restore()
                time.sleep(0.1)
            pyautogui.press('alt')
            target_win.activate()
            time.sleep(0.3)
            return target_win
    except Exception as e:
        print(f"⚠️ ウィンドウ制御エラー: {e}")
    return None

def execute_analysis():
    global latest_result, is_processing

    with processing_lock:
        if is_processing:
            print("⚠️ 解析処理中のためスキップします。")
            return
        is_processing = True

    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    latest_result["title"] = "解析中..."
    latest_result["gemini_content"] = "Google Earth の画面を分析しています...数秒お待ちください。"
    latest_result["timestamp"] = now_str

    saved_img_path = os.path.join(IMAGE_SAVE_DIR, f"cap_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png")

    try:
        earth_win = bring_earth_window_to_front()
        screenshot = pyautogui.screenshot()

        if earth_win and earth_win.width > 0 and earth_win.height > 0:
            left, top = max(0, earth_win.left), max(0, earth_win.top)
            right = min(screenshot.width, earth_win.right)
            bottom = min(screenshot.height, earth_win.bottom)
            w, h = right - left, bottom - top
            
            # ブラウザの上部（タブやアドレスバー）、左ツールバーをカットして3D表示領域のみトリミング
            cropped_img = screenshot.crop((
                left + int(w * 0.05),
                top + int(h * 0.12),
                left + int(w * 0.98),
                bottom - int(h * 0.03)
            ))
        else:
            w, h = screenshot.size
            cropped_img = screenshot.crop((int(w * 0.05), int(h * 0.10), int(w * 0.95), int(h * 0.95)))

        # API費用＆通信量削減のための軽量化（アスペクト比を維持して最大1024pxにリサイズ）
        cropped_img.thumbnail((1024, 1024))
        cropped_img.save(saved_img_path)

        # バーチャルツアー用ガイドプロンプト
        prompt = (
            "あなたは最高のバーチャルツアーガイドです。この画面（Google Earthの3D景観またはストリートビュー）に写っている場所について、以下の構成で400〜500文字で魅力的に解説してください。\n\n"
            "1. 【場所の特定と概要】：ここがどこか、何という施設・自然・街並みか\n"
            "2. 【歴史と背景】：この場所にまつわる歴史やストーリー、地理的な特徴など\n"
            "3. 【ここだけの魅力・おすすめポイント】：訪れた人がワクワクする豆知識や見どころ\n"
            "4. 【周囲のおすすめ・楽しみ方】：周辺の立ち寄りスポットや体験のポイント\n\n"
            "語り口は親しみやすく、聞いているだけで旅に出たくなるようなワクワクする文章でまとめてください。文末には必ず『（文字数：〇〇文字）』と実際に生成した文字数を記載してください。"
        )
        img = Image.open(saved_img_path)
        
        # 最新推奨モデルで生成
        response = gemini_client.models.generate_content(
            model='gemini-3.6-flash',
            contents=[prompt, img]
        )

        latest_result["title"] = "HVOS Web Earth ガイド解説"
        latest_result["gemini_content"] = response.text

    except Exception as e:
        print(f"❌ エラー発生: {e}")
        latest_result["title"] = "エラー発生"
        latest_result["gemini_content"] = f"処理エラー: {e}"

    finally:
        with processing_lock:
            is_processing = False

HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>HVOS Web Earth Dashboard</title>
    <style>
        body { background-color: #0f172a; color: #f8fafc; font-family: sans-serif; padding: 15px; margin: 0; }
        .header { font-size: 1rem; font-weight: bold; color: #818cf8; border-bottom: 1px solid #334155; padding-bottom: 6px; display: flex; justify-content: space-between; }
        .card { background: #1e293b; border-radius: 8px; padding: 15px; margin-top: 12px; border-top: 4px solid #38bdf8; }
        .content { font-size: 0.9rem; line-height: 1.6; white-space: pre-wrap; }
    </style>
    <script>
        setInterval(async () => {
            try {
                const res = await fetch('/api/data');
                const data = await res.json();
                document.getElementById('ui-title').innerText = data.title;
                document.getElementById('ui-timestamp').innerText = data.timestamp;
                document.getElementById('ui-gemini').innerText = data.gemini_content;
            } catch (e) {}
        }, 1000);
    </script>
</head>
<body>
    <div class="header">
        <span id="ui-title">{{ title }}</span>
        <span id="ui-timestamp" style="font-size:0.75rem; color:#64748b;">{{ timestamp }}</span>
    </div>
    <div class="card">
        <div id="ui-gemini" class="content">{{ gemini_content }}</div>
    </div>
</body>
</html>
"""

@app.route('/')
def home():
    return render_template_string(HTML_TEMPLATE, title=latest_result["title"], timestamp=latest_result["timestamp"], gemini_content=latest_result["gemini_content"])

@app.route('/api/data')
def get_data():
    return jsonify(latest_result)

def start_keyboard_listener():
    print("▶ 【1】キーの監視を開始しました。（Google Earthを画面に出して【1】を押してください）")
    last_execution_time = 0
    cooldown_seconds = 5.0  # 強制クールダウン（5秒間は連打を無効化）

    while True:
        if keyboard.is_pressed("1") or keyboard.is_pressed("num 1"):
            current_time = time.time()
            
            # クールダウン＆重複処理ブロック
            if current_time - last_execution_time > cooldown_seconds:
                last_execution_time = current_time
                if not is_processing:
                    threading.Thread(target=execute_analysis).start()
            
            # 指が離れるまでループ待機（長押し事故防止）
            while keyboard.is_pressed("1") or keyboard.is_pressed("num 1"):
                time.sleep(0.05)

        time.sleep(0.05)

if __name__ == '__main__':
    threading.Thread(target=start_keyboard_listener, daemon=True).start()

    hostname = socket.gethostname()
    try:
        local_ip = socket.gethostbyname(hostname)
    except Exception:
        local_ip = "127.0.0.1"

    print(f"\n==========================================")
    print(f"=== HVOS (Google Earth Web Edition) 稼働中 ===")
    print(f"・ダッシュボード表示用URL: http://localhost:5000")
    print(f"・サブモニター/スマホ用URL: http://{local_ip}:5000")
    print(f"==========================================\n")

    app.run(host='0.0.0.0', port=5000, debug=False, use_reloader=False)