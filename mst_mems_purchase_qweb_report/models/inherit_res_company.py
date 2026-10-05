from odoo import models, fields

class ResCompany(models.Model):
    _inherit = 'res.company'

    po_seal = fields.Binary("Purchase order Seal")
    managing_director = fields.Char("Managing Director")
    store_keeper = fields.Char("Store Keeper")
    po_manager = fields.Char("Manager")
    bank_acc_no = fields.Char("Bank Account Number")
    bank_ifsc = fields.Char("Bank Branch IFSC")