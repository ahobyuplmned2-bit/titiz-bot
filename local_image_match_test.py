import io

from PIL import Image, ImageDraw

import app


def make_product_image(color, accent):
    image = Image.new("RGB", (120, 120), color)
    draw = ImageDraw.Draw(image)
    draw.rectangle((25, 20, 95, 100), fill=accent)
    draw.ellipse((42, 35, 78, 70), fill=color)
    stream = io.BytesIO()
    image.save(stream, format="PNG")
    return stream.getvalue()


catalog_bytes = make_product_image((210, 210, 210), (35, 120, 180))
other_bytes = make_product_image((245, 245, 245), (180, 60, 50))
product = {
    "id": 77,
    "name": "ثلاجة شاي المائدة",
    "image_urls": '["https://catalog.test/tea.jpg"]',
}

original_download = app._download_catalog_image
app._download_catalog_image = lambda url: app._catalog_image_fingerprint(catalog_bytes)
matched = app.match_image_against_catalog(catalog_bytes, [product])
assert matched and matched["product"]["id"] == 77
assert matched["match_type"] == "exact"
family_match = app.match_image_against_catalog(other_bytes, [product])
assert family_match and family_match["product"]["id"] == 77
assert family_match["match_type"] in {"exact", "family"}
app._download_catalog_image = original_download
print("local_image_match_test: OK")
