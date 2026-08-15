import asyncio

import app


sent_audio = []
sent_text = []


async def fake_female_voice(spoken_text):
    assert "أبشري" in spoken_text
    return b"ID3" + b"v" * 1024


app.APP_SECRET = ""
app.processed_messages.clear()
app.claim_processed_webhook_message = lambda message_id, timestamp: True
app.record_contact = lambda sender: None
app.record_message_event = lambda **kwargs: 1
app.persist_customer_session = lambda sender: None
app.whatsapp.mark_as_read = lambda message_id: True
app.whatsapp.send_typing_indicator = lambda message_id: True
app.whatsapp.send_audio = lambda recipient, audio, mime, filename: sent_audio.append(
    (recipient, audio, mime, filename)
) or True
app.whatsapp.send_message = lambda recipient, text: sent_text.append((recipient, text)) or True
app._record_outbound_event = lambda *args, **kwargs: None
app._generate_female_voice_audio = fake_female_voice
app.transcribe_voice_message = lambda message: "ابغى قدور"
app.notify_owner = lambda sender, text: None
app.deliver_pending_replies = lambda sender: None
app.time.sleep = lambda seconds: None
app.handle_customer_message = lambda sender, body, normalized, message: app.send_message(
    sender, "أبشري يا غالية، هذه قدورنا المتوفرة."
)

client = app.app.test_client()
payload = {
    "entry": [{"changes": [{"value": {"messages": [{
        "id": "voice-reply-test-1",
        "from": "967700000333",
        "type": "audio",
        "audio": {"id": "voice-media-1", "mime_type": "audio/ogg"},
    }]}}]}]
}
response = client.post("/webhook", json=payload)

assert response.status_code == 200
assert len(sent_audio) == 1
assert sent_audio[0][0] == "967700000333"
assert sent_audio[0][2] == "audio/mpeg"
assert sent_text == []
assert app.voice_reply_mode.get() is False
assert app.voice_reply_sent.get() is False

print("voice_webhook_reply_test: OK")
