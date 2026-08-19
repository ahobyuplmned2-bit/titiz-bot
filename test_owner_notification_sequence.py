"""اختبار عداد إشعارات الإدارة في قاعدة مستقلة من دون لمس بيانات البوت."""

import os
import tempfile

import database


with tempfile.TemporaryDirectory() as temp_dir:
    database.DB_PATH = os.path.join(temp_dir, "sequence-test.db")
    database.init_db()
    assert database.reserve_owner_notification_sequence("9677712282204", 101) == 1
    assert database.reserve_owner_notification_sequence("9677712282204", 102) == 2
    assert database.reserve_owner_notification_sequence("967774405284", 103) == 3
    assert database.reserve_owner_notification_sequence("9677712282204", 102) == 2

print("اختبار تسلسل إشعارات الإدارة: ناجح")
