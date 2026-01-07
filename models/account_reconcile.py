# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class AccountFullReconcile(models.Model):
    """
    Lettrage Complet
    Represente un groupe de lignes d'ecriture totalement lettrees
    """
    _name = 'account.full.reconcile.custom'
    _description = 'Lettrage complet'

    name = fields.Char(
        string='Numero',
        required=True,
        copy=False,
        default=lambda self: self.env['ir.sequence'].next_by_code('account.reconcile.custom') or 'NEW',
    )

    partial_reconcile_ids = fields.One2many(
        'account.partial.reconcile.custom',
        'full_reconcile_id',
        string='Lettrages partiels',
    )

    reconciled_line_ids = fields.Many2many(
        'account.move.line.custom',
        'full_reconcile_line_custom_rel',
        'full_reconcile_id',
        'line_id',
        string='Lignes lettrees',
    )

    exchange_move_id = fields.Many2one(
        'account.move.custom',
        string='Ecriture d ecart de change',
    )


class AccountPartialReconcile(models.Model):
    """
    Lettrage Partiel
    Represente un lien entre deux lignes d'ecriture
    """
    _name = 'account.partial.reconcile.custom'
    _description = 'Lettrage partiel'

    debit_move_id = fields.Many2one(
        'account.move.line.custom',
        string='Ligne debit',
        required=True,
        index=True,
    )
    credit_move_id = fields.Many2one(
        'account.move.line.custom',
        string='Ligne credit',
        required=True,
        index=True,
    )

    amount = fields.Monetary(
        string='Montant',
        required=True,
        currency_field='company_currency_id',
    )
    amount_currency = fields.Monetary(
        string='Montant en devise',
        currency_field='currency_id',
    )

    currency_id = fields.Many2one(
        'res.currency',
        string='Devise',
    )
    company_currency_id = fields.Many2one(
        'res.currency',
        string='Devise societe',
        default=lambda self: self.env.company.currency_id,
    )
    company_id = fields.Many2one(
        'res.company',
        string='Societe',
        default=lambda self: self.env.company,
    )

    full_reconcile_id = fields.Many2one(
        'account.full.reconcile.custom',
        string='Lettrage complet',
    )

    max_date = fields.Date(
        string='Date max',
        compute='_compute_max_date',
        store=True,
    )

    @api.depends('debit_move_id.date', 'credit_move_id.date')
    def _compute_max_date(self):
        for partial in self:
            partial.max_date = max(
                partial.debit_move_id.date or fields.Date.today(),
                partial.credit_move_id.date or fields.Date.today()
            )

    def unlink(self):
        """Supprimer le lettrage"""
        full_reconciles = self.mapped('full_reconcile_id')
        res = super().unlink()
        # Supprimer les lettrages complets vides
        for full in full_reconciles:
            if not full.partial_reconcile_ids:
                full.unlink()
        return res


class AccountReconcileModel(models.Model):
    """
    Modele de Lettrage Automatique
    Pour automatiser le rapprochement bancaire
    """
    _name = 'account.reconcile.model.custom'
    _description = 'Modele de lettrage'
    _order = 'sequence, id'

    name = fields.Char(string='Nom', required=True)
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)

    rule_type = fields.Selection([
        ('writeoff_button', 'Bouton ecart'),
        ('writeoff_suggestion', 'Suggestion ecart'),
        ('invoice_matching', 'Correspondance facture'),
    ], string='Type', required=True, default='writeoff_button')

    # Conditions de correspondance
    match_nature = fields.Selection([
        ('amount_received', 'Montant recu'),
        ('amount_paid', 'Montant paye'),
        ('both', 'Les deux'),
    ], string='Nature', default='both')

    match_amount = fields.Selection([
        ('lower', 'Inferieur a'),
        ('greater', 'Superieur a'),
        ('between', 'Entre'),
    ], string='Condition montant')

    match_amount_min = fields.Float(string='Montant min')
    match_amount_max = fields.Float(string='Montant max')

    match_label = fields.Selection([
        ('contains', 'Contient'),
        ('not_contains', 'Ne contient pas'),
        ('match_regex', 'Regex'),
    ], string='Condition libelle')
    match_label_param = fields.Char(string='Parametre libelle')

    match_partner = fields.Boolean(string='Meme partenaire')
    match_partner_ids = fields.Many2many(
        'res.partner',
        'reconcile_model_partner_custom_rel',
        'model_id',
        'partner_id',
        string='Partenaires specifiques',
    )

    # Actions
    account_id = fields.Many2one(
        'account.account.custom',
        string='Compte',
    )
    journal_id = fields.Many2one(
        'account.journal.custom',
        string='Journal',
    )
    label = fields.Char(string='Libelle ecriture')

    amount_type = fields.Selection([
        ('fixed', 'Montant fixe'),
        ('percentage', 'Pourcentage'),
        ('regex', 'Expression reguliere'),
    ], string='Type montant', default='percentage')

    amount = fields.Float(string='Montant/Pourcentage', default=100.0)

    tax_ids = fields.Many2many(
        'account.tax.custom',
        'reconcile_model_tax_custom_rel',
        'model_id',
        'tax_id',
        string='Taxes',
    )
    analytic_account_id = fields.Many2one(
        'account.analytic.account.custom',
        string='Compte analytique',
    )

    company_id = fields.Many2one(
        'res.company',
        string='Societe',
        default=lambda self: self.env.company,
    )


class AccountBankStatementLine(models.Model):
    """
    Ligne de Releve Bancaire
    """
    _name = 'account.bank.statement.line.custom'
    _description = 'Ligne de releve bancaire'
    _order = 'date desc, id desc'

    statement_id = fields.Many2one(
        'account.bank.statement.custom',
        string='Releve',
        required=True,
        ondelete='cascade',
    )

    date = fields.Date(
        string='Date',
        required=True,
        default=fields.Date.context_today,
    )
    name = fields.Char(string='Libelle', required=True)
    ref = fields.Char(string='Reference')

    partner_id = fields.Many2one(
        'res.partner',
        string='Partenaire',
    )

    amount = fields.Monetary(
        string='Montant',
        required=True,
        currency_field='currency_id',
    )
    currency_id = fields.Many2one(
        related='statement_id.currency_id',
    )

    # Rapprochement
    is_reconciled = fields.Boolean(
        string='Rapproche',
        default=False,
    )
    move_id = fields.Many2one(
        'account.move.custom',
        string='Ecriture comptable',
    )

    # Sequence interne
    sequence = fields.Integer(default=10)


class AccountBankStatement(models.Model):
    """
    Releve Bancaire
    """
    _name = 'account.bank.statement.custom'
    _description = 'Releve bancaire'
    _order = 'date desc, id desc'
    _inherit = ['mail.thread']

    name = fields.Char(
        string='Reference',
        required=True,
        copy=False,
    )
    date = fields.Date(
        string='Date',
        required=True,
        default=fields.Date.context_today,
        tracking=True,
    )

    journal_id = fields.Many2one(
        'account.journal.custom',
        string='Journal',
        required=True,
        domain="[('type', 'in', ['bank', 'cash'])]",
    )

    company_id = fields.Many2one(
        'res.company',
        string='Societe',
        related='journal_id.company_id',
        store=True,
    )
    currency_id = fields.Many2one(
        'res.currency',
        string='Devise',
        default=lambda self: self.env.company.currency_id,
    )

    # Soldes
    balance_start = fields.Monetary(
        string='Solde initial',
        currency_field='currency_id',
    )
    balance_end_real = fields.Monetary(
        string='Solde final (releve)',
        currency_field='currency_id',
    )
    balance_end = fields.Monetary(
        string='Solde final calcule',
        compute='_compute_balance_end',
        currency_field='currency_id',
    )

    # Lignes
    line_ids = fields.One2many(
        'account.bank.statement.line.custom',
        'statement_id',
        string='Lignes',
    )

    # Totaux
    total_entry_encoding = fields.Monetary(
        string='Total mouvements',
        compute='_compute_totals',
        currency_field='currency_id',
    )

    state = fields.Selection([
        ('open', 'Ouvert'),
        ('confirm', 'Valide'),
    ], string='Etat', default='open', tracking=True)

    @api.depends('balance_start', 'line_ids.amount')
    def _compute_balance_end(self):
        for statement in self:
            statement.balance_end = statement.balance_start + sum(statement.line_ids.mapped('amount'))

    @api.depends('line_ids.amount')
    def _compute_totals(self):
        for statement in self:
            statement.total_entry_encoding = sum(statement.line_ids.mapped('amount'))

    def action_confirm(self):
        for statement in self:
            # Verifier que toutes les lignes sont rapprochees
            unreconciled = statement.line_ids.filtered(lambda l: not l.is_reconciled)
            if unreconciled:
                raise UserError(_(
                    "Toutes les lignes doivent etre rapprochees avant validation.\n"
                    "Lignes non rapprochees: %s"
                ) % ', '.join(unreconciled.mapped('name')))

            # Verifier l'equilibre
            if abs(statement.balance_end - statement.balance_end_real) > 0.01:
                raise UserError(_(
                    "Le solde calcule (%.2f) ne correspond pas au solde du releve (%.2f)."
                ) % (statement.balance_end, statement.balance_end_real))

            statement.state = 'confirm'
        return True

    def action_reopen(self):
        for statement in self:
            statement.state = 'open'
        return True
