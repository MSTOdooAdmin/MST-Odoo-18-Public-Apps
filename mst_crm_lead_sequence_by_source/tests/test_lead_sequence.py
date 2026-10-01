from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestLeadSequenceBySource(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.source_fb = cls.env["utm.source"].create({
            "name": "Facebook Sequence Test",
            "lead_prefix": "FB-",
        })
        cls.source_gg = cls.env["utm.source"].create({
            "name": "Google Sequence Test",
            "lead_prefix": "GG-",
        })
        cls.source_plain = cls.env["utm.source"].create({
            "name": "Referral Sequence Test",
        })
        cls.sales_user = cls.env["res.users"].create({
            "name": "Sequence Sales",
            "login": "sequence_sales_user",
            "group_ids": [(4, cls.env.ref("sales_team.group_sale_salesman").id)],
        })

    def test_sequence_is_unique_per_source(self):
        lead_a = self.env["crm.lead"].create({
            "name": "Facebook Lead A",
            "source_id": self.source_fb.id,
        })
        lead_b = self.env["crm.lead"].create({
            "name": "Facebook Lead B",
            "source_id": self.source_fb.id,
        })
        lead_c = self.env["crm.lead"].create({
            "name": "Google Lead",
            "source_id": self.source_gg.id,
        })
        self.assertEqual(lead_a.lead_sequence, "FB-00001")
        self.assertEqual(lead_b.lead_sequence, "FB-00002")
        self.assertEqual(lead_c.lead_sequence, "GG-00001")

    def test_missing_source_or_prefix_does_not_assign_sequence(self):
        bare = self.env["crm.lead"].create({"name": "Bare Lead"})
        plain = self.env["crm.lead"].create({
            "name": "Plain Source Lead",
            "source_id": self.source_plain.id,
        })
        self.assertFalse(bare.lead_sequence)
        self.assertFalse(plain.lead_sequence)
        self.assertFalse(self.env["ir.sequence"].search([
            ("code", "=", f"crm.lead.source.{self.source_plain.id}"),
        ]))

    def test_explicit_sequence_is_preserved(self):
        lead = self.env["crm.lead"].create({
            "name": "Preset Sequence",
            "source_id": self.source_fb.id,
            "lead_sequence": "KEEP-1",
        })
        self.assertEqual(lead.lead_sequence, "KEEP-1")

    def test_prefix_is_stripped_and_later_changes_apply(self):
        spaced = self.env["utm.source"].create({
            "name": "Spaced Prefix Source",
            "lead_prefix": "  IN-  ",
        })
        first = self.env["crm.lead"].create({
            "name": "LinkedIn First",
            "source_id": spaced.id,
        })
        self.assertEqual(first.lead_sequence, "IN-00001")
        spaced.lead_prefix = "LI-"
        second = self.env["crm.lead"].create({
            "name": "LinkedIn Second",
            "source_id": spaced.id,
        })
        self.assertEqual(second.lead_sequence, "LI-00002")
        sequence = self.env["ir.sequence"].search([
            ("code", "=", f"crm.lead.source.{spaced.id}"),
        ])
        self.assertEqual(sequence.prefix, "LI-")
        self.assertFalse(sequence.company_id)

    def test_sales_user_can_create_a_numbered_lead(self):
        lead = self.env["crm.lead"].with_user(self.sales_user).create({
            "name": "Sales User Lead",
            "source_id": self.source_fb.id,
        })
        self.assertTrue(lead.lead_sequence.startswith("FB-"))

    def test_views_expose_sequence_and_prefix(self):
        lead_form = self.env["crm.lead"].get_view(
            view_id=self.env.ref("crm.crm_lead_view_form").id,
            view_type="form",
        )["arch"]
        self.assertIn("lead_sequence", lead_form)
        self.assertIn('name="source_id" required="1"', lead_form)
        self.assertIn('name="source_id" invisible="1"', lead_form)

        lead_list = self.env["crm.lead"].get_view(
            view_id=self.env.ref("crm.crm_case_tree_view_leads").id,
            view_type="list",
        )["arch"]
        self.assertIn("lead_sequence", lead_list)

        lead_search = self.env["crm.lead"].get_view(
            view_id=self.env.ref("crm.view_crm_case_leads_filter").id,
            view_type="search",
        )["arch"]
        self.assertIn("lead_sequence", lead_search)

        source_form = self.env["utm.source"].get_view(
            view_id=self.env.ref("utm.utm_source_view_form").id,
            view_type="form",
        )["arch"]
        self.assertIn("lead_prefix", source_form)

        source_list = self.env["utm.source"].get_view(
            view_id=self.env.ref("utm.utm_source_view_tree").id,
            view_type="list",
        )["arch"]
        self.assertIn("lead_prefix", source_list)
