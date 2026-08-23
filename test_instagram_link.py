import os
import sys
import tempfile


with tempfile.TemporaryDirectory() as temporary_directory:
    os.environ["DATABASE_PATH"] = os.path.join(temporary_directory, "instagram-link-test.db")
    os.environ["FOLLOWUP_WORKER_ENABLED"] = "false"
    sys.modules.pop("database", None)
    sys.modules.pop("app", None)
    import app

    captured_menu = {}
    app.send_list = lambda to, text, button_text, sections: captured_menu.update(
        {"to": to, "sections": sections}
    ) or True
    app.send_contact_menu("967700000001")
    rows = captured_menu["sections"][0]["rows"]
    assert any(row["id"] == "contact_instagram" for row in rows)

    calls = []
    app.whatsapp.send_url_button = lambda to, text, title, url: calls.append(
        (to, text, title, url)
    ) or True
    assert app.send_instagram_link("967700000001") is True
    assert calls == [
        (
            "967700000001",
            "📷 تابعي أحدث منتجات وعروض Titiz على Instagram 😊",
            "📷 Instagram",
            "https://www.instagram.com/lsdh3241/",
        )
    ]

print("test_instagram_link: OK")
