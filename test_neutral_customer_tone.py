from pathlib import Path

import app


PROHIBITED_CUSTOMER_PHRASES = (
    "أرسلي",
    "اختاري",
    "اكتبي",
    "تريدين",
    "تبغين",
    "تبحثين",
    "تحبين",
    "انتظري",
    "يا غالية",
    "منورة",
    "بكِ",
    "لكِ",
    "منكِ",
    "معكِ",
    "عليكِ",
    "أضيفي",
    "تقدرين",
    "تثقين",
    "تتابعن",
)

source = Path(app.__file__).read_text(encoding="utf-8")
for phrase in PROHIBITED_CUSTOMER_PHRASES:
    assert phrase not in source, f"يجب ألا تعود صياغة مؤنثة للعميل: {phrase}"

assert "هلا فيك" in app.WELCOME_MESSAGE
assert "اكتب اسم المنتج" in app.GUIDED_HELP_MESSAGE
assert "اختر من القائمة" in app.GUIDED_HELP_MESSAGE

print("test_neutral_customer_tone: OK")
