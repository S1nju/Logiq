"""
Unit tests for internationalization (i18n) system
"""

import unittest
from utils.i18n import I18nManager, t, SUPPORTED_LANGUAGES


class TestI18n(unittest.TestCase):

    def test_i18n_loading(self):
        """Test loading translations from internationalization directory"""
        manager = I18nManager()
        self.assertIn("en", manager.translations)
        self.assertIn("ar", manager.translations)
        self.assertEqual(manager.translations["en"]["common"]["success"], "Success")
        self.assertEqual(manager.translations["ar"]["common"]["success"], "نجاح")

    def test_translation_lookup(self):
        """Test translating keys with parameter interpolation"""
        manager = I18nManager(default_lang="en")
        
        # English lookup
        self.assertEqual(manager.get("common.success", lang="en"), "Success")
        self.assertEqual(
            manager.get("admin.reload_success", lang="en", cog="moderation"),
            "Successfully reloaded **moderation**"
        )
        
        # Arabic lookup
        self.assertEqual(manager.get("common.success", lang="ar"), "نجاح")
        self.assertEqual(
            manager.get("admin.reload_success", lang="ar", cog="moderation"),
            "تم إعادة تحميل الإضافة **moderation** بنجاح"
        )

    def test_fallback_lookup(self):
        """Test fallback when key is missing or language invalid"""
        manager = I18nManager(default_lang="en")
        
        # Missing key returns key path
        self.assertEqual(manager.get("non_existent.key", lang="en"), "non_existent.key")
        
        # Invalid lang falls back to default_lang
        self.assertEqual(manager.get("common.success", lang="fr"), "Success")

    def test_language_switch(self):
        """Test changing language state"""
        manager = I18nManager(default_lang="en")
        
        self.assertEqual(manager.current_language, "en")
        
        # Switch to Arabic
        self.assertTrue(manager.set_language("ar"))
        self.assertEqual(manager.current_language, "ar")
        self.assertEqual(manager.get("common.error"), "خطأ")
        
        # Invalid language switch fails
        self.assertFalse(manager.set_language("invalid"))
        self.assertEqual(manager.current_language, "ar")

    def test_shorthand_t(self):
        """Test global shorthand helper function t()"""
        self.assertEqual(t("common.success", lang="en"), "Success")
        self.assertEqual(t("common.success", lang="ar"), "نجاح")

    def test_embed_factory_translation(self):
        """Test EmbedFactory translation keys for verification and tickets"""
        from utils.i18n import i18n
        i18n.set_language("en")
        self.assertEqual(t("verification.prompt_title"), "🔐 Verification Required")

        i18n.set_language("ar")
        self.assertEqual(t("verification.prompt_title"), "🔐 التحقق مطلوب")

    def test_phrase_auto_translation(self):
        """Test phrase auto translation fallback for English literals"""
        from utils.i18n import i18n
        i18n.set_language("ar")
        self.assertEqual(t("Commands Synced"), "تمت مزامنة الأوامر")
        self.assertEqual(t("Cog Reloaded"), "تم إعادة تحميل الإضافة")
        self.assertEqual(t("⚠️ No Warnings"), "⚠️ لا توجد تحذيرات")

    def test_ticket_translations(self):
        """Test ticket button and panel translations"""
        from utils.i18n import i18n
        i18n.set_language("ar")
        self.assertEqual(t("tickets.create_button"), "إنشاء تذكرة")
        self.assertEqual(t("tickets.close_button"), "إغلاق التذكرة")
        self.assertEqual(t("tickets.panel_title"), "🎫 تذاكر الدعم")
        self.assertIn("هل تحتاج إلى مساعدة؟", t("tickets.panel_desc"))

        i18n.set_language("en")
        self.assertEqual(t("tickets.create_button"), "Create Ticket")
        self.assertEqual(t("tickets.close_button"), "Close Ticket")
        self.assertEqual(t("tickets.panel_title"), "🎫 Support Tickets")








if __name__ == '__main__':
    unittest.main()

