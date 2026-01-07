# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class AccountTax(models.Model):
    """
    Taxes (TVA)
    """
    _name = 'account.tax.custom'
    _description = 'Taxe'
    _order = 'sequence, id'

    name = fields.Char(string='Nom de la taxe', required=True)
    active = fields.Boolean(default=True)
    sequence = fields.Integer(default=1)

    type_tax_use = fields.Selection([
        ('sale', 'Ventes'),
        ('purchase', 'Achats'),
        ('none', 'Aucun'),
    ], string='Application', required=True, default='sale')

    amount_type = fields.Selection([
        ('percent', 'Pourcentage du prix'),
        ('fixed', 'Montant fixe'),
        ('group', 'Groupe de taxes'),
    ], string='Type de calcul', required=True, default='percent')

    amount = fields.Float(
        string='Montant',
        required=True,
        default=0.0,
        help="Pour pourcentage: 20 = 20%. Pour fixe: montant par unite.",
    )

    description = fields.Char(
        string='Code affiche',
        help="Code court affiche sur les factures",
    )

    # Comptes comptables
    account_id = fields.Many2one(
        'account.account.custom',
        string='Compte de taxe',
        help="Compte pour collecter cette taxe",
    )
    refund_account_id = fields.Many2one(
        'account.account.custom',
        string='Compte de taxe (avoir)',
        help="Compte pour les avoirs",
    )

    # Configuration
    company_id = fields.Many2one(
        'res.company',
        string='Societe',
        required=True,
        default=lambda self: self.env.company,
    )
    price_include = fields.Boolean(
        string='Inclus dans le prix',
        default=False,
        help="Si coche, le prix affiché inclut cette taxe",
    )
    include_base_amount = fields.Boolean(
        string='Inclure dans la base des taxes suivantes',
        default=False,
    )

    # Groupe de taxes
    children_tax_ids = fields.Many2many(
        'account.tax.custom',
        'account_tax_children_custom_rel',
        'parent_tax_id',
        'child_tax_id',
        string='Taxes enfants',
    )

    # Tags pour rapports
    tag_ids = fields.Many2many(
        'account.tax.tag.custom',
        'account_tax_tag_custom_rel',
        'tax_id',
        'tag_id',
        string='Tags',
    )

    def compute_all(self, price_unit, quantity=1.0, product=None, partner=None):
        """
        Calcule le montant de taxe
        Retourne un dictionnaire avec:
        - total_excluded: prix HT
        - total_included: prix TTC
        - taxes: liste des taxes calculees
        """
        self.ensure_one()

        if self.amount_type == 'percent':
            tax_amount = price_unit * quantity * (self.amount / 100.0)
        elif self.amount_type == 'fixed':
            tax_amount = self.amount * quantity
        else:
            tax_amount = 0.0

        if self.price_include:
            total_excluded = price_unit * quantity - tax_amount
            total_included = price_unit * quantity
        else:
            total_excluded = price_unit * quantity
            total_included = price_unit * quantity + tax_amount

        return {
            'total_excluded': total_excluded,
            'total_included': total_included,
            'taxes': [{
                'id': self.id,
                'name': self.name,
                'amount': tax_amount,
                'account_id': self.account_id.id if self.account_id else False,
            }],
        }


class AccountTaxTag(models.Model):
    """
    Tags de taxes pour les declarations fiscales
    """
    _name = 'account.tax.tag.custom'
    _description = 'Tag de taxe'
    _order = 'name'

    name = fields.Char(string='Nom', required=True)
    applicability = fields.Selection([
        ('taxes', 'Taxes'),
        ('products', 'Produits'),
    ], string='Applicabilite', required=True, default='taxes')
    active = fields.Boolean(default=True)
    company_id = fields.Many2one(
        'res.company',
        string='Societe',
        default=lambda self: self.env.company,
    )
    country_id = fields.Many2one(
        'res.country',
        string='Pays',
    )

    # Pour les rapports de TVA
    tax_negate = fields.Boolean(
        string='Inverser le signe',
        default=False,
    )
