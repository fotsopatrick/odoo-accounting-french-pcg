# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError


class AccountPayment(models.Model):
    """
    Paiements
    """
    _name = 'account.payment.custom'
    _description = 'Paiement'
    _inherit = ['mail.thread']
    _order = 'date desc, name desc, id desc'

    name = fields.Char(
        string='Numero',
        readonly=True,
        copy=False,
        default='/',
    )
    state = fields.Selection([
        ('draft', 'Brouillon'),
        ('posted', 'Valide'),
        ('cancel', 'Annule'),
    ], string='Etat', default='draft', tracking=True)

    payment_type = fields.Selection([
        ('outbound', 'Envoyer de l argent'),
        ('inbound', 'Recevoir de l argent'),
    ], string='Type de paiement', required=True, default='inbound')

    partner_type = fields.Selection([
        ('customer', 'Client'),
        ('supplier', 'Fournisseur'),
    ], string='Type de partenaire', default='customer')

    partner_id = fields.Many2one(
        'res.partner',
        string='Partenaire',
        required=True,
        tracking=True,
    )

    # Montant
    amount = fields.Monetary(
        string='Montant',
        required=True,
        currency_field='currency_id',
        tracking=True,
    )
    currency_id = fields.Many2one(
        'res.currency',
        string='Devise',
        default=lambda self: self.env.company.currency_id,
        required=True,
    )

    # Dates
    date = fields.Date(
        string='Date',
        required=True,
        default=fields.Date.context_today,
        tracking=True,
    )

    # Journal
    journal_id = fields.Many2one(
        'account.journal.custom',
        string='Journal',
        required=True,
        domain="[('type', 'in', ['bank', 'cash'])]",
    )

    # Mode de paiement
    payment_method = fields.Selection([
        ('manual', 'Manuel'),
        ('check', 'Cheque'),
        ('transfer', 'Virement'),
        ('card', 'Carte bancaire'),
        ('cash', 'Especes'),
    ], string='Methode de paiement', default='manual')

    # Reference
    ref = fields.Char(string='Reference/Memo')
    communication = fields.Char(string='Communication')

    # Lien avec factures
    move_ids = fields.Many2many(
        'account.move.custom',
        'account_move_payment_custom_rel',
        'payment_id',
        'move_id',
        string='Factures',
    )

    # Ecriture comptable generee
    move_id = fields.Many2one(
        'account.move.custom',
        string='Ecriture comptable',
        readonly=True,
        copy=False,
    )

    # Societe
    company_id = fields.Many2one(
        'res.company',
        string='Societe',
        required=True,
        default=lambda self: self.env.company,
    )

    # Compte de destination
    destination_account_id = fields.Many2one(
        'account.account.custom',
        string='Compte de destination',
        compute='_compute_destination_account',
    )

    @api.depends('partner_id', 'payment_type', 'partner_type')
    def _compute_destination_account(self):
        for payment in self:
            if payment.partner_type == 'customer':
                # Compte client
                payment.destination_account_id = self.env['account.account.custom'].search([
                    ('account_type', '=', 'asset_receivable'),
                    ('company_id', '=', payment.company_id.id),
                ], limit=1)
            else:
                # Compte fournisseur
                payment.destination_account_id = self.env['account.account.custom'].search([
                    ('account_type', '=', 'liability_payable'),
                    ('company_id', '=', payment.company_id.id),
                ], limit=1)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', '/') == '/':
                vals['name'] = self.env['ir.sequence'].next_by_code('account.payment.custom') or '/'
        return super().create(vals_list)

    def action_post(self):
        """Valider le paiement"""
        for payment in self:
            if payment.state != 'draft':
                raise UserError(_("Seuls les paiements en brouillon peuvent etre valides."))
            if payment.amount <= 0:
                raise UserError(_("Le montant doit etre positif."))

            # Creer l'ecriture comptable
            move_vals = payment._prepare_move_vals()
            move = self.env['account.move.custom'].create(move_vals)
            move.action_post()

            payment.write({
                'state': 'posted',
                'move_id': move.id,
            })

            # Lettrer avec les factures si applicable
            if payment.move_ids:
                payment._reconcile_invoices()

        return True

    def _prepare_move_vals(self):
        """Preparer les valeurs de l'ecriture comptable"""
        self.ensure_one()

        # Compte banque/caisse
        liquidity_account = self.journal_id.default_account_id
        if not liquidity_account:
            raise UserError(_("Veuillez configurer un compte par defaut sur le journal %s") % self.journal_id.name)

        # Sens de l'ecriture
        if self.payment_type == 'inbound':
            debit_account = liquidity_account
            credit_account = self.destination_account_id
            debit_amount = self.amount
            credit_amount = self.amount
        else:
            debit_account = self.destination_account_id
            credit_account = liquidity_account
            debit_amount = self.amount
            credit_amount = self.amount

        return {
            'date': self.date,
            'journal_id': self.journal_id.id,
            'ref': self.ref or self.name,
            'partner_id': self.partner_id.id,
            'move_type': 'entry',
            'line_ids': [
                (0, 0, {
                    'name': self.communication or self.name,
                    'account_id': debit_account.id,
                    'partner_id': self.partner_id.id,
                    'debit': debit_amount,
                    'credit': 0,
                }),
                (0, 0, {
                    'name': self.communication or self.name,
                    'account_id': credit_account.id,
                    'partner_id': self.partner_id.id,
                    'debit': 0,
                    'credit': credit_amount,
                }),
            ],
        }

    def _reconcile_invoices(self):
        """Lettrer le paiement avec les factures"""
        self.ensure_one()
        # Implementation simplifiee du lettrage
        # A completer selon les besoins
        pass

    def action_cancel(self):
        """Annuler le paiement"""
        for payment in self:
            if payment.move_id:
                payment.move_id.action_cancel()
            payment.state = 'cancel'
        return True

    def action_draft(self):
        """Remettre en brouillon"""
        for payment in self:
            payment.state = 'draft'
        return True


class AccountPaymentMethod(models.Model):
    """
    Methodes de paiement
    """
    _name = 'account.payment.method.custom'
    _description = 'Methode de paiement'

    name = fields.Char(string='Nom', required=True)
    code = fields.Char(string='Code', required=True)
    payment_type = fields.Selection([
        ('inbound', 'Entrant'),
        ('outbound', 'Sortant'),
    ], string='Type', required=True)
