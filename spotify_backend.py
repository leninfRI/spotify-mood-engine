#V0.2
import os
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import io
from fastapi.responses import StreamingResponse
import barcode
from barcode.writer import ImageWriter

# --- FastAPI App & CORS ---
app = FastAPI()

origins = ["*"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Spotify API Setup ---
client_id = os.environ.get('SPOTIPY_CLIENT_ID')
client_secret = os.environ.get('SPOTIPY_CLIENT_SECRET')

if not client_id or not client_secret:
    print("[重大錯誤] 找不到 Spotify API 金鑰。")
    sp = None
else:
    auth_manager = SpotifyClientCredentials(client_id=client_id, client_secret=client_secret)
    sp = spotipy.Spotify(auth_manager=auth_manager)

# --- Pydantic Models ---
class PlaylistRequest(BaseModel):
    playlist_url: str

class BarcodeRequest(BaseModel):
    discount_code: str

# --- Mood & Discount Engine ---
def analyze_mood(avg_valence, avg_energy):
    """根據平均 valence 和 energy 判斷情緒象限"""
    if avg_valence >= 0.5 and avg_energy >= 0.5:
        return "快樂 / 充滿活力"
    elif avg_valence >= 0.5 and avg_energy < 0.5:
        return "平靜 / 療癒"
    elif avg_valence < 0.5 and avg_energy >= 0.5:
        return "憤怒 / 激昂"
    else:
        return "悲傷 / 憂鬱"

def convert_mood_to_discount(avg_valence, avg_energy):
    """將心情指數轉換為折扣百分比"""
    base_discount = (1 - avg_valence) * 15
    energy_bonus = avg_energy * 5
    total_discount = base_discount + energy_bonus
    final_discount = max(5.0, min(total_discount, 20.0))
    return round(final_discount, 2)

# --- API Endpoints ---
@app.get("/")
def read_root():
    return {"status": "Spotify Mood Analyzer is alive"}

@app.post("/api/analyze-playlist")
def analyze_playlist(request: PlaylistRequest):
    if not sp:
        raise HTTPException(status_code=500, detail="Spotify 服務未正確初始化。")

    try:
        playlist_id = request.playlist_url.split("/")[-1].split("?")[0]
        
        # [FIX] 加入 market="TW" 參數，確保能讀取台灣地區的歌單
        results = sp.playlist_tracks(playlist_id, market="TW")
        tracks = results['items']
        
        while results['next']:
            results = sp.next(results)
            tracks.extend(results['items'])

        track_ids = [item['track']['id'] for item in tracks if item['track'] and item['track']['id']]
        
        if not track_ids:
            raise HTTPException(status_code=404, detail="歌單中找不到有效歌曲。")

        audio_features = []
        for i in range(0, len(track_ids), 100):
            batch = track_ids[i:i+100]
            # [FIX] 獲取音訊特徵時也加入 market="TW"
            audio_features.extend(sp.audio_features(batch))

        valid_features = [f for f in audio_features if f]

        if not valid_features:
            raise HTTPException(status_code=404, detail="無法獲取歌曲的音訊特徵。")

        total_valence = sum(f['valence'] for f in valid_features)
        total_energy = sum(f['energy'] for f in valid_features)
        avg_valence = total_valence / len(valid_features)
        avg_energy = total_energy / len(valid_features)

        mood = analyze_mood(avg_valence, avg_energy)
        discount = convert_mood_to_discount(avg_valence, avg_energy)

        playlist_info = sp.playlist(playlist_id, market="TW")

        return {
            "playlist_name": playlist_info['name'],
            "total_tracks": len(valid_features),
            "mood": mood,
            "avg_valence": round(avg_valence, 3),
            "avg_energy": round(avg_energy, 3),
            "discount_percentage": discount,
            "tracks_details": [
                {
                    "name": item['track']['name'],
                    "artist": ", ".join([artist['name'] for artist in item['track']['artists']]),
                    "valence": next((f['valence'] for f in valid_features if f['id'] == item['track']['id']), None),
                    "energy": next((f['energy'] for f in valid_features if f['id'] == item['track']['id']), None)
                } for item in tracks[:5] if item['track']
            ]
        }

    except spotipy.exceptions.SpotifyException as e:
        # 提供更詳細的錯誤訊息
        if e.http_status == 404:
            raise HTTPException(status_code=404, detail="找不到這個歌單，請確認網址是否正確，或該歌單是否為公開。")
        raise HTTPException(status_code=400, detail=f"Spotify API 錯誤: {e.msg}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"伺服器內部錯誤: {e}")

@app.post("/api/generate-barcode")
def generate_barcode(request: BarcodeRequest):
    """根據提供的折扣碼文字，產生 Barcode 圖片"""
    try:
        EAN = barcode.get_barcode_class('code128')
        image_buffer = io.BytesIO()
        EAN(request.discount_code, writer=ImageWriter()).write(image_buffer)
        image_buffer.seek(0)
        return StreamingResponse(image_buffer, media_type="image/png")
    except Exception as e:
        print(f"產生 Barcode 時發生錯誤: {e}")
        raise HTTPException(status_code=500, detail="無法產生 Barcode。")
