# -*- coding: utf-8 -*-

from odoo import api, fields, models, _


class AccountAnalyticAccount(models.Model):
    """
    Compte Analytique
    """
    _name = 'account.analytic.account.custom'
    _description = 'Compte Analytique'
    _order = 'code, name'

    name = fields.Char(string='Nom', required=True, index=True)
    code = fields.Char(string='Reference', index=True)
    active = fields.Boolean(default=True)

    # Plan analytique (multi-axes)
    plan_id = fields.Many2one(
        'account.analytic.plan.custom',
        string='Plan analytique',
    )

    # Partenaire lie
    partner_id = fields.Many2one(
        'res.partner',
        string='Partenaire',
    )

    # Societe
    company_id = fields.Many2one(
        'res.company',
        string='Societe',
        default=lambda self: self.env.company,
    )

    # Soldes
    balance = fields.Monetary(
        string='Solde',
        compute='_compute_balance',
        currency_field='currency_id',
    )
    debit = fields.Monetary(
        string='Debit',
        compute='_compute_balance',
        currency_field='currency_id',
    )
    credit = fields.Monetary(
        string='Credit',
        compute='_compute_balance',
        currency_field='currency_id',
    )
    currency_id = fields.Many2one(
        related='company_id.currency_id',
    )

    # Lignes analytiques
    line_ids = fields.One2many(
        'account.analytic.line.custom',
        'account_id',
        string='Lignes analytiques',
    )

    def _compute_balance(self):
        for account in self:
            account.debit = sum(account.line_ids.filtered(lambda l: l.amount > 0).mapped('amount'))
            account.credit = abs(sum(account.line_ids.filtered(lambda l: l.amount < 0).mapped('amount')))
            account.balance = account.debit - account.credit

    def action_view_lines(self):
        """Voir les lignes analytiques"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Lignes analytiques - %s') % self.name,
            'res_model': 'account.analytic.line.custom',
            'view_mode': 'list,form',
            'domain': [('account_id', '=', self.id)],
            'context': {'default_account_id': self.id},
        }


class AccountAnalyticPlan(models.Model):
    """
    Plan Analytique (Multi-axes)
    """
    _name = 'account.analytic.plan.custom'
    _description = 'Plan Analytique'
    _order = 'sequence, id'

    name = fields.Char(string='Nom', required=True)
    sequence = fields.Integer(default=10)
    description = fields.Text(string='Description')
    color = fields.Integer(string='Couleur')

    company_id = fields.Many2one(
        'res.company',
        string='Societe',
        default=lambda self: self.env.company,
    )

    # Comptes de ce plan
    account_ids = fields.One2many(
        'account.analytic.account.custom',
        'plan_id',
        string='Comptes analytiques',
    )

    account_count = fields.Integer(
        string='Nombre de comptes',
        compute='_compute_account_count',
    )

    def _compute_account_count(self):
        for plan in self:
            plan.account_count = len(plan.account_ids)


class AccountAnalyticLine(models.Model):
    """
    Ligne Analytique
    """
    _name = 'account.analytic.line.custom'
    _description = 'Ligne Analytique'
    _order = 'date desc, id desc'

    name = fields.Char(string='Description', required=True)
    date = fields.Date(string='Date', required=True, default=fields.Date.context_today, index=True)

    account_id = fields.Many2one(
        'account.analytic.account.custom',
        string='Compte analytique',
        required=True,
        ondelete='restrict',
        index=True,
    )
    partner_id = fields.Many2one('res.partner', string='Partenaire')

    # Montant (positif = debit, negatif = credit)
    amount = fields.Monetary(
        string='Montant',
        required=True,
        currency_field='currency_id',
    )
    currency_id = fields.Many2one(
        'res.currency',
        string='Devise',
        default=lambda self: self.env.company.currency_id,
    )
    unit_amount = fields.Float(string='Quantite', default=0.0)

    # Lien avec comptabilite generale
    move_line_id = fields.Many2one(
        'account.move.line.custom',
        string='Ligne comptable',
    )
    general_account_id = fields.Many2one(
        'account.account.custom',
        string='Compte general',
    )

    company_id = fields.Many2one(
        'res.company',
        string='Societe',
        default=lambda self: self.env.company,
    )

    # Categorie/Projet
    category = fields.Selection([
        ('project', 'Projet'),
        ('department', 'Departement'),
        ('product', 'Produit'),
        ('other', 'Autre'),
    ], string='Categorie', default='other')


class AccountAnalyticTag(models.Model):
    """
    Tags Analytiques
    """
    _name = 'account.analytic.tag.custom'
    _description = 'Tag Analytique'
    _order = 'name'

    name = fields.Char(string='Nom', required=True)
    color = fields.Integer(string='Couleur')
    active = fields.Boolean(default=True)

    company_id = fields.Many2one(
        'res.company',
        string='Societe',
        default=lambda self: self.env.company,
    )
