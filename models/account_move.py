# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
from datetime import date


class AccountMove(models.Model):
    """
    Piece Comptable (Ecriture)
    """
    _name = 'account.move.custom'
    _description = 'Piece Comptable'
    _inherit = ['mail.thread']
    _order = 'date desc, name desc, id desc'

    name = fields.Char(
        string='Numero',
        readonly=True,
        copy=False,
        default='/',
        index=True,
    )
    ref = fields.Char(
        string='Reference',
        copy=False,
    )
    date = fields.Date(
        string='Date',
        required=True,
        default=fields.Date.context_today,
        index=True,
        tracking=True,
    )
    state = fields.Selection([
        ('draft', 'Brouillon'),
        ('posted', 'Comptabilise'),
        ('cancel', 'Annule'),
    ], string='Etat', default='draft', tracking=True, index=True)

    move_type = fields.Selection([
        ('entry', 'Ecriture diverse'),
        ('out_invoice', 'Facture client'),
        ('out_refund', 'Avoir client'),
        ('in_invoice', 'Facture fournisseur'),
        ('in_refund', 'Avoir fournisseur'),
        ('out_receipt', 'Recu de vente'),
        ('in_receipt', 'Recu d achat'),
    ], string='Type', required=True, default='entry', index=True)

    # Relations
    journal_id = fields.Many2one(
        'account.journal.custom',
        string='Journal',
        required=True,
        tracking=True,
    )
    company_id = fields.Many2one(
        'res.company',
        string='Societe',
        required=True,
        default=lambda self: self.env.company,
    )
    currency_id = fields.Many2one(
        'res.currency',
        string='Devise',
        default=lambda self: self.env.company.currency_id,
        required=True,
    )
    partner_id = fields.Many2one(
        'res.partner',
        string='Partenaire',
        tracking=True,
    )

    # Lignes d'ecriture
    line_ids = fields.One2many(
        'account.move.line.custom',
        'move_id',
        string='Lignes d ecriture',
        copy=True,
    )

    # Montants
    amount_untaxed = fields.Monetary(
        string='Total HT',
        compute='_compute_amounts',
        store=True,
        currency_field='currency_id',
    )
    amount_tax = fields.Monetary(
        string='Total TVA',
        compute='_compute_amounts',
        store=True,
        currency_field='currency_id',
    )
    amount_total = fields.Monetary(
        string='Total TTC',
        compute='_compute_amounts',
        store=True,
        currency_field='currency_id',
    )
    amount_residual = fields.Monetary(
        string='Reste a payer',
        compute='_compute_amounts',
        store=True,
        currency_field='currency_id',
    )

    # Verification equilibre
    is_balanced = fields.Boolean(
        string='Equilibre',
        compute='_compute_is_balanced',
    )

    # Dates factures
    invoice_date = fields.Date(string='Date facture')
    invoice_date_due = fields.Date(string='Date echeance')

    # Origine
    invoice_origin = fields.Char(string='Document origine')
    narration = fields.Html(string='Notes internes')

    # Paiements lies
    payment_ids = fields.Many2many(
        'account.payment.custom',
        'account_move_payment_custom_rel',
        'move_id',
        'payment_id',
        string='Paiements',
    )
    payment_state = fields.Selection([
        ('not_paid', 'Non paye'),
        ('partial', 'Partiellement paye'),
        ('paid', 'Paye'),
        ('reversed', 'Extourne'),
    ], string='Statut paiement', compute='_compute_payment_state', store=True)

    # Exercice fiscal
    fiscal_year_id = fields.Many2one(
        'account.fiscal.year.custom',
        string='Exercice fiscal',
        compute='_compute_fiscal_year',
        store=True,
    )

    @api.depends('line_ids.debit', 'line_ids.credit', 'line_ids.amount_currency')
    def _compute_amounts(self):
        for move in self:
            if move.move_type in ('out_invoice', 'out_refund', 'in_invoice', 'in_refund'):
                # Pour les factures
                lines = move.line_ids.filtered(lambda l: l.account_id.account_type not in ('asset_receivable', 'liability_payable'))
                move.amount_untaxed = sum(lines.filtered(lambda l: not l.tax_line_id).mapped('balance'))
                move.amount_tax = sum(lines.filtered(lambda l: l.tax_line_id).mapped('balance'))
                move.amount_total = move.amount_untaxed + move.amount_tax

                receivable_lines = move.line_ids.filtered(lambda l: l.account_id.account_type in ('asset_receivable', 'liability_payable'))
                move.amount_residual = sum(receivable_lines.mapped('amount_residual'))
            else:
                move.amount_untaxed = 0
                move.amount_tax = 0
                move.amount_total = sum(move.line_ids.mapped('debit'))
                move.amount_residual = 0

    @api.depends('line_ids.debit', 'line_ids.credit')
    def _compute_is_balanced(self):
        for move in self:
            total_debit = sum(move.line_ids.mapped('debit'))
            total_credit = sum(move.line_ids.mapped('credit'))
            move.is_balanced = abs(total_debit - total_credit) < 0.01

    @api.depends('amount_residual', 'amount_total', 'state')
    def _compute_payment_state(self):
        for move in self:
            if move.state != 'posted' or move.move_type == 'entry':
                move.payment_state = 'not_paid'
            elif move.amount_residual == 0:
                move.payment_state = 'paid'
            elif move.amount_residual < move.amount_total:
                move.payment_state = 'partial'
            else:
                move.payment_state = 'not_paid'

    @api.depends('date', 'company_id')
    def _compute_fiscal_year(self):
        for move in self:
            fiscal_year = self.env['account.fiscal.year.custom'].search([
                ('company_id', '=', move.company_id.id),
                ('date_from', '<=', move.date),
                ('date_to', '>=', move.date),
            ], limit=1)
            move.fiscal_year_id = fiscal_year

    @api.constrains('line_ids')
    def _check_balanced(self):
        for move in self:
            if move.line_ids and not move.is_balanced:
                raise ValidationError(_(
                    "L'ecriture %s n'est pas equilibree. "
                    "Debit: %s, Credit: %s"
                ) % (move.name, sum(move.line_ids.mapped('debit')), sum(move.line_ids.mapped('credit'))))

    def action_post(self):
        """Valider l'ecriture"""
        for move in self:
            if move.state != 'draft':
                raise UserError(_("Seules les ecritures en brouillon peuvent etre validees."))
            if not move.line_ids:
                raise UserError(_("L'ecriture doit avoir au moins une ligne."))
            if not move.is_balanced:
                raise UserError(_("L'ecriture n'est pas equilibree."))

            # Generer le numero
            if move.name == '/':
                move.name = move.journal_id.sequence_id.next_by_id()

            move.state = 'posted'
        return True

    def action_cancel(self):
        """Annuler l'ecriture"""
        for move in self:
            if move.state == 'posted':
                # Verifier si des lignes sont lettrees
                if any(line.reconciled for line in move.line_ids):
                    raise UserError(_("Impossible d'annuler une ecriture avec des lignes lettrees."))
            move.state = 'cancel'
        return True

    def action_draft(self):
        """Remettre en brouillon"""
        for move in self:
            if move.state == 'cancel':
                move.state = 'draft'
        return True

    def action_reverse(self):
        """Extourner l'ecriture"""
        self.ensure_one()
        reverse_move = self.copy({
            'ref': _('Extourne de %s') % self.name,
            'date': fields.Date.today(),
        })
        # Inverser debit/credit
        for line in reverse_move.line_ids:
            line.debit, line.credit = line.credit, line.debit
        return {
            'type': 'ir.actions.act_window',
            'name': _('Extourne'),
            'res_model': 'account.move.custom',
            'view_mode': 'form',
            'res_id': reverse_move.id,
        }

    def action_register_payment(self):
        """Ouvrir wizard de paiement"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Enregistrer un paiement'),
            'res_model': 'account.payment.custom',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_partner_id': self.partner_id.id,
                'default_amount': self.amount_residual,
                'default_move_ids': [(6, 0, [self.id])],
                'default_payment_type': 'inbound' if self.move_type in ('out_invoice', 'in_refund') else 'outbound',
            },
        }


class AccountMoveLine(models.Model):
    """
    Ligne d'ecriture comptable
    """
    _name = 'account.move.line.custom'
    _description = 'Ligne d ecriture'
    _order = 'date desc, move_name desc, id'

    move_id = fields.Many2one(
        'account.move.custom',
        string='Piece',
        required=True,
        ondelete='cascade',
        index=True,
    )
    move_name = fields.Char(related='move_id.name', store=True)
    date = fields.Date(related='move_id.date', store=True, index=True)

    name = fields.Char(string='Libelle')
    ref = fields.Char(string='Reference')

    account_id = fields.Many2one(
        'account.account.custom',
        string='Compte',
        required=True,
        index=True,
    )
    partner_id = fields.Many2one(
        'res.partner',
        string='Partenaire',
    )
    journal_id = fields.Many2one(
        related='move_id.journal_id',
        store=True,
    )
    company_id = fields.Many2one(
        related='move_id.company_id',
        store=True,
    )
    currency_id = fields.Many2one(
        'res.currency',
        string='Devise',
        default=lambda self: self.env.company.currency_id,
    )

    # Montants
    debit = fields.Monetary(
        string='Debit',
        default=0.0,
        currency_field='company_currency_id',
    )
    credit = fields.Monetary(
        string='Credit',
        default=0.0,
        currency_field='company_currency_id',
    )
    balance = fields.Monetary(
        string='Solde',
        compute='_compute_balance',
        store=True,
        currency_field='company_currency_id',
    )
    amount_currency = fields.Monetary(
        string='Montant devise',
        currency_field='currency_id',
    )
    company_currency_id = fields.Many2one(
        related='company_id.currency_id',
    )

    # Quantite (pour analytique)
    quantity = fields.Float(string='Quantite', default=1.0)
    product_id = fields.Many2one('product.product', string='Article')

    # TVA
    tax_ids = fields.Many2many(
        'account.tax.custom',
        'account_move_line_tax_custom_rel',
        'line_id',
        'tax_id',
        string='Taxes',
    )
    tax_line_id = fields.Many2one(
        'account.tax.custom',
        string='Ligne de taxe',
        help="Si cette ligne represente une taxe",
    )

    # Analytique
    analytic_account_id = fields.Many2one(
        'account.analytic.account.custom',
        string='Compte analytique',
    )
    analytic_tag_ids = fields.Many2many(
        'account.analytic.tag.custom',
        'account_move_line_analytic_tag_custom_rel',
        'line_id',
        'tag_id',
        string='Tags analytiques',
    )

    # Lettrage
    reconciled = fields.Boolean(
        string='Lettre',
        compute='_compute_reconciled',
        store=True,
    )
    full_reconcile_id = fields.Many2one(
        'account.full.reconcile.custom',
        string='Lettrage complet',
    )
    matched_debit_ids = fields.One2many(
        'account.partial.reconcile.custom',
        'credit_move_id',
        string='Lignes debit lettrees',
    )
    matched_credit_ids = fields.One2many(
        'account.partial.reconcile.custom',
        'debit_move_id',
        string='Lignes credit lettrees',
    )
    amount_residual = fields.Monetary(
        string='Montant residuel',
        compute='_compute_amount_residual',
        store=True,
        currency_field='company_currency_id',
    )

    # Echeance
    date_maturity = fields.Date(string='Date echeance')

    @api.depends('debit', 'credit')
    def _compute_balance(self):
        for line in self:
            line.balance = line.debit - line.credit

    @api.depends('full_reconcile_id')
    def _compute_reconciled(self):
        for line in self:
            line.reconciled = bool(line.full_reconcile_id)

    @api.depends('debit', 'credit', 'matched_debit_ids', 'matched_credit_ids')
    def _compute_amount_residual(self):
        for line in self:
            matched_amount = sum(line.matched_debit_ids.mapped('amount')) + sum(line.matched_credit_ids.mapped('amount'))
            line.amount_residual = abs(line.balance) - matched_amount

    @api.onchange('account_id')
    def _onchange_account_id(self):
        if self.account_id:
            self.tax_ids = self.account_id.tax_ids

    @api.onchange('debit')
    def _onchange_debit(self):
        if self.debit:
            self.credit = 0.0

    @api.onchange('credit')
    def _onchange_credit(self):
        if self.credit:
            self.debit = 0.0
