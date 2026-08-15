import app


sent_audio = []
sent_text = []


async def fake_female_voice(spoken_text):
    assert "أهلاً" in spoken_text
    return b"ID3" + b"x" * 1024


app._generate_female_voice_audio = fake_female_voice
app.whatsapp.send_audio = lambda recipient, audio, mime, filename: sent_audio.append(
    (recipient, audio, mime, filename)
) or True
app.whatsapp.send_message = lambda recipient, text: sent_text.append((recipient, text)) or True
app._record_outbound_event = lambda *args, **kwargs: None

mode_token = app.voice_reply_mode.set(True)
sent_token = app.voice_reply_sent.set(False)
try:
    assert app.send_message("967700000222", "أهلاً بكِ يا غالية، كيف أقدر أساعدك؟") is True
    assert len(sent_audio) == 1
    assert sent_audio[0][2] == "audio/mpeg"
    assert sent_audio[0][1][:1] == b"\xff" or sent_audio[0][1][:3] == b"ID3"
    assert sent_text == []
    assert app.send_message("967700000222", "هذه رسالة ثانية") is True
    assert sent_text == [("967700000222", "هذه رسالة ثانية")]
finally:
    app.voice_reply_sent.reset(sent_token)
    app.voice_reply_mode.reset(mode_token)

print("voice_reply_test: OK")
