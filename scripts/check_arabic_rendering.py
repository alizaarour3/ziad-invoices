from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from PIL import Image, ImageDraw, features

from app.services.pdf_service import _find_font

status = {
    "raqm": bool(features.check("raqm")),
    "harfbuzz": bool(features.check("harfbuzz")),
    "fribidi": bool(features.check("fribidi")),
}
print(status)
if not all(status.values()):
    raise SystemExit("Arabic shaping engine is incomplete")

image = Image.new("RGB", (1200, 250), "white")
draw = ImageDraw.Draw(image)
font = _find_font(64, bold=False, direction="rtl")
draw.text((1150, 125), "محمد علي حسن - مبلغ 135000 دينار", font=font, fill="black", direction="rtl", language="ar", anchor="rm")
print("Arabic RTL rendering check passed")
