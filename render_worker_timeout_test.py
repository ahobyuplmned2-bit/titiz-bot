import pathlib

root = pathlib.Path(__file__).resolve().parent
render_config = (root / "render.yaml").read_text(encoding="utf-8")
procfile = (root / "Procfile").read_text(encoding="utf-8")
app_source = (root / "app.py").read_text(encoding="utf-8")

for command in (render_config, procfile):
    assert "--timeout 120" in command
    assert "--threads 2" in command

assert "def process_customer_image_in_background" in app_source
assert "target=process_customer_image_in_background" in app_source
assert 'return jsonify({"status": "ok"}), 200' in app_source

print("render_worker_timeout_test: OK")

