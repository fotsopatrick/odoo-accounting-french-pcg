# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError


class AccountAccount(models.Model):
    """
    Plan Comptable - Comptes comptables
    Inspire d'Odoo 8, adapte pour Odoo 18
    """
    _name = 'account.account.custom'
    _description = 'Compte Comptable'
    _order = 'code'
    _parent_store = True

    name = fields.Char(
        string='Nom du compte',
        required=True,
        index=True,
    )
    code = fields.Char(
        string='Code',
        required=True,
        index=True,
    )
    active = fields.Boolean(
        default=True,
    )

    # Type de compte (classification PCG)
    account_type = fields.Selection([
        ('asset_receivable', 'Creances clients'),
        ('asset_cash', 'Banque et Caisse'),
        ('asset_current', 'Actif circulant'),
        ('asset_non_current', 'Immobilisations'),
        ('asset_prepayments', 'Charges constatees d avance'),
        ('asset_fixed', 'Immobilisations corporelles'),
        ('liability_payable', 'Dettes fournisseurs'),
        ('liability_credit_card', 'Carte de credit'),
        ('liability_current', 'Passif circulant'),
        ('liability_non_current', 'Dettes long terme'),
        ('equity', 'Capitaux propres'),
        ('equity_unaffected', 'Resultat non affecte'),
        ('income', 'Produits'),
        ('income_other', 'Autres produits'),
        ('expense', 'Charges'),
        ('expense_depreciation', 'Amortissements'),
        ('expense_direct_cost', 'Cout direct'),
        ('off_balance', 'Hors bilan'),
    ], string='Type de compte', required=True, default='asset_current')

    # Classification PCG francais
    account_class = fields.Selection([
        ('1', 'Classe 1 - Capitaux'),
        ('2', 'Classe 2 - Immobilisations'),
        ('3', 'Classe 3 - Stocks'),
        ('4', 'Classe 4 - Tiers'),
        ('5', 'Classe 5 - Financiers'),
        ('6', 'Classe 6 - Charges'),
        ('7', 'Classe 7 - Produits'),
        ('8', 'Classe 8 - Speciaux'),
    ], string='Classe PCG', compute='_compute_account_class', store=True)

    # Hierarchie
    parent_id = fields.Many2one(
        'account.account.custom',
        string='Compte parent',
        ondelete='cascade',
    )
    parent_path = fields.Char(index=True, unaccent=False)
    child_ids = fields.One2many(
        'account.account.custom',
        'parent_id',
        string='Sous-comptes',
    )

    # Configuration
    reconcile = fields.Boolean(
        string='Lettrable',
        default=False,
        help="Cochez si ce compte permet le lettrage (clients, fournisseurs)",
    )
    deprecated = fields.Boolean(
        string='Obsolete',
        default=False,
    )
    company_id = fields.Many2one(
        'res.company',
        string='Societe',
        default=lambda self: self.env.company,
        required=True,
    )
    currency_id = fields.Many2one(
        'res.currency',
        string='Devise du compte',
        help="Devise specifique pour ce compte",
    )

    # Taxes par defaut
    tax_ids = fields.Many2many(
        'account.tax.custom',
        'account_account_tax_custom_rel',
        'account_id',
        'tax_id',
        string='Taxes par defaut',
    )

    # Tags pour classification
    tag_ids = fields.Many2many(
        'account.account.tag.custom',
        'account_account_tag_custom_rel',
        'account_id',
        'tag_id',
        string='Tags',
    )

    # Groupe interne (pour compatibilite)
    internal_group = fields.Selection([
        ('asset', 'Actif'),
        ('liability', 'Passif'),
        ('equity', 'Capitaux'),
        ('income', 'Produits'),
        ('expense', 'Charges'),
        ('off_balance', 'Hors bilan'),
    ], string='Groupe interne', compute='_compute_internal_group', store=True)

    # Notes
    note = fields.Text(string='Notes')

    # Soldes
    balance = fields.Monetary(
        string='Solde',
        compute='_compute_balance',
        currency_field='company_currency_id',
    )
    debit = fields.Monetary(
        string='Total Debit',
        compute='_compute_balance',
        currency_field='company_currency_id',
    )
    credit = fields.Monetary(
        string='Total Credit',
        compute='_compute_balance',
        currency_field='company_currency_id',
    )
    company_currency_id = fields.Many2one(
        related='company_id.currency_id',
        string='Devise societe',
    )

    # Compteur d'ecritures
    move_line_count = fields.Integer(
        string='Nombre d ecritures',
        compute='_compute_move_line_count',
    )

    _sql_constraints = [
        ('code_company_uniq', 'unique(code, company_id)',
         'Le code du compte doit etre unique par societe!'),
    ]

    @api.depends('code')
    def _compute_account_class(self):
        for account in self:
            if account.code:
                account.account_class = account.code[0] if account.code[0].isdigit() else False
            else:
                account.account_class = False

    @api.depends('account_type')
    def _compute_internal_group(self):
        type_to_group = {
            'asset_receivable': 'asset',
            'asset_cash': 'asset',
            'asset_current': 'asset',
            'asset_non_current': 'asset',
            'asset_prepayments': 'asset',
            'asset_fixed': 'asset',
            'liability_payable': 'liability',
            'liability_credit_card': 'liability',
            'liability_current': 'liability',
            'liability_non_current': 'liability',
            'equity': 'equity',
            'equity_unaffected': 'equity',
            'income': 'income',
            'income_other': 'income',
            'expense': 'expense',
            'expense_depreciation': 'expense',
            'expense_direct_cost': 'expense',
            'off_balance': 'off_balance',
        }
        for account in self:
            account.internal_group = type_to_group.get(account.account_type, 'asset')

    def _compute_balance(self):
        for account in self:
            lines = self.env['account.move.line.custom'].search([
                ('account_id', '=', account.id),
                ('move_id.state', '=', 'posted'),
            ])
            account.debit = sum(lines.mapped('debit'))
            account.credit = sum(lines.mapped('credit'))
            account.balance = account.debit - account.credit

    def _compute_move_line_count(self):
        for account in self:
            account.move_line_count = self.env['account.move.line.custom'].search_count([
                ('account_id', '=', account.id),
            ])

    @api.constrains('code')
    def _check_code(self):
        for account in self:
            if account.code and len(account.code) < 3:
                raise ValidationError(_("Le code du compte doit avoir au moins 3 caracteres."))

    def action_view_move_lines(self):
        """Voir les ecritures du compte"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Ecritures - %s') % self.name,
            'res_model': 'account.move.line.custom',
            'view_mode': 'list,form',
            'domain': [('account_id', '=', self.id)],
            'context': {'default_account_id': self.id},
        }

    @api.model
    def _get_opening_balance_account(self):
        """Retourne le compte de bilan d'ouverture"""
        return self.search([('code', '=', '890')], limit=1)


class AccountAccountTag(models.Model):
    """
    Tags de compte pour classification et rapports
    """
    _name = 'account.account.tag.custom'
    _description = 'Tag de compte'
    _order = 'name'

    name = fields.Char(string='Nom', required=True)
    applicability = fields.Selection([
        ('accounts', 'Comptes'),
        ('taxes', 'Taxes'),
        ('products', 'Produits'),
    ], string='Applicabilite', required=True, default='accounts')
    active = fields.Boolean(default=True)
    color = fields.Integer(string='Couleur')
    company_id = fields.Many2one(
        'res.company',
        string='Societe',
        default=lambda self: self.env.company,
    )


class AccountGroup(models.Model):
    """
    Groupes de comptes pour les rapports
    """
    _name = 'account.group.custom'
    _description = 'Groupe de comptes'
    _order = 'code_prefix_start'

    name = fields.Char(string='Nom', required=True)
    code_prefix_start = fields.Char(string='Prefixe debut', required=True)
    code_prefix_end = fields.Char(string='Prefixe fin')
    parent_id = fields.Many2one('account.group.custom', string='Groupe parent')
    company_id = fields.Many2one(
        'res.company',
        string='Societe',
        default=lambda self: self.env.company,
    )
