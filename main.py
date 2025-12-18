from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from vosk import Model, KaldiRecognizer
import json, time
from names import NAMES

app = FastAPI()

print("🔄 Loading Vosk model...")
model = Model("models/vosk-model-small-hi-0.22")
print("✅ Vosk model loaded")


@app.websocket("/ws/audio")
async def websocket_audio(ws: WebSocket):
    await ws.accept()

    rec = KaldiRecognizer(model, 16000)
    rec.SetWords(False)

    selected_god = None
    last_emit_time = 0
    last_partial = ""

    COOLDOWN = 0.35   # 🔥 fast + safe

    try:
        while True:
            msg = await ws.receive()

            # 🔌 disconnect
            if msg["type"] == "websocket.disconnect":
                break

            # 🟡 config message
            if msg.get("text"):
                data = json.loads(msg["text"])
                if data.get("type") == "config":
                    selected_god = data.get("selectedGod")
                    last_partial = ""
                    last_emit_time = 0
                    print("🎯 Selected God:", selected_god)
                continue

            # 🟢 audio bytes
            if msg.get("bytes") and selected_god:
                rec.AcceptWaveform(msg["bytes"])

                partial = json.loads(rec.PartialResult()).get("partial", "").lower()

                # ignore empty / same text
                if not partial or partial == last_partial:
                    continue

                last_partial = partial
                now = time.time()

                if now - last_emit_time < COOLDOWN:
                    continue

                # 🔥 check last spoken words only
                words = partial.split()[-2:]

                for w in words:
                    if w in NAMES[selected_god]:
                        last_emit_time = now
                        await ws.send_text(json.dumps({"count": 1}))
                        break

    except WebSocketDisconnect:
        print("🔌 WebSocket disconnected")

    except Exception as e:
        print("❌ WebSocket error:", e)
