# -*- coding: utf-8 -*-

from odoo import api, fields, models, _


class ResPartner(models.Model):
    """
    Extension Partenaire pour Comptabilite
    """
    _inherit = 'res.partner'

    # Comptes comptables par defaut
    property_account_receivable_id = fields.Many2one(
        'account.account.custom',
        string='Compte client',
        domain="[('account_type', '=', 'asset_receivable'), ('deprecated', '=', False)]",
        help="Compte utilise pour les creances clients",
        company_dependent=True,
    )
    property_account_payable_id = fields.Many2one(
        'account.account.custom',
        string='Compte fournisseur',
        domain="[('account_type', '=', 'liability_payable'), ('deprecated', '=', False)]",
        help="Compte utilise pour les dettes fournisseurs",
        company_dependent=True,
    )

    # Position fiscale
    property_account_position_id = fields.Many2one(
        'account.fiscal.position.custom',
        string='Position fiscale',
        company_dependent=True,
    )

    # Conditions de paiement
    property_payment_term_id = fields.Many2one(
        'account.payment.term.custom',
        string='Conditions paiement client',
        company_dependent=True,
    )
    property_supplier_payment_term_id = fields.Many2one(
        'account.payment.term.custom',
        string='Conditions paiement fournisseur',
        company_dependent=True,
    )

    # Statistiques comptables
    debit = fields.Monetary(
        string='Total Debiteur',
        compute='_compute_accounting_stats',
        currency_field='currency_id',
    )
    credit = fields.Monetary(
        string='Total Crediteur',
        compute='_compute_accounting_stats',
        currency_field='currency_id',
    )
    debit_limit = fields.Monetary(
        string='Plafond de credit',
        currency_field='currency_id',
    )

    # Compteur factures
    invoice_count = fields.Integer(
        string='Nombre de factures',
        compute='_compute_invoice_count',
    )
    total_invoiced = fields.Monetary(
        string='Total facture',
        compute='_compute_accounting_stats',
        currency_field='currency_id',
    )
    total_due = fields.Monetary(
        string='Total du',
        compute='_compute_accounting_stats',
        currency_field='currency_id',
    )

    # Numero de compte auxiliaire
    ref_supplier = fields.Char(string='Reference fournisseur')

    # Blocage comptable
    invoice_warn = fields.Selection([
        ('no-message', 'Pas de message'),
        ('warning', 'Avertissement'),
        ('block', 'Bloquer'),
    ], string='Avertissement facture', default='no-message')
    invoice_warn_msg = fields.Text(string='Message avertissement')

    def _compute_accounting_stats(self):
        for partner in self:
            # Calculer debit/credit depuis les lignes d'ecriture
            domain = [
                ('partner_id', '=', partner.id),
                ('move_id.state', '=', 'posted'),
                ('account_id.account_type', 'in', ['asset_receivable', 'liability_payable']),
            ]
            lines = self.env['account.move.line.custom'].search(domain)

            partner.debit = sum(lines.mapped('debit'))
            partner.credit = sum(lines.mapped('credit'))
            partner.total_due = sum(lines.mapped('amount_residual'))

            # Total facture
            invoices = self.env['account.move.custom'].search([
                ('partner_id', '=', partner.id),
                ('state', '=', 'posted'),
                ('move_type', 'in', ['out_invoice', 'out_refund']),
            ])
            partner.total_invoiced = sum(invoices.mapped('amount_total'))

    def _compute_invoice_count(self):
        for partner in self:
            partner.invoice_count = self.env['account.move.custom'].search_count([
                ('partner_id', '=', partner.id),
                ('move_type', 'in', ['out_invoice', 'out_refund', 'in_invoice', 'in_refund']),
            ])

    def action_view_partner_invoices(self):
        """Voir les factures du partenaire"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Factures'),
            'res_model': 'account.move.custom',
            'view_mode': 'list,form',
            'domain': [
                ('partner_id', '=', self.id),
                ('move_type', 'in', ['out_invoice', 'out_refund', 'in_invoice', 'in_refund']),
            ],
            'context': {'default_partner_id': self.id},
        }

    def action_view_partner_ledger(self):
        """Voir le grand livre du partenaire"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Grand livre - %s') % self.name,
            'res_model': 'account.move.line.custom',
            'view_mode': 'list,form',
            'domain': [
                ('partner_id', '=', self.id),
                ('move_id.state', '=', 'posted'),
            ],
        }


class AccountPaymentTerm(models.Model):
    """
    Conditions de Paiement
    """
    _name = 'account.payment.term.custom'
    _description = 'Conditions de paiement'
    _order = 'sequence, id'

    name = fields.Char(string='Nom', required=True, translate=True)
    active = fields.Boolean(default=True)
    sequence = fields.Integer(default=10)

    note = fields.Html(string='Description')

    line_ids = fields.One2many(
        'account.payment.term.line.custom',
        'payment_id',
        string='Lignes',
        copy=True,
    )

    company_id = fields.Many2one(
        'res.company',
        string='Societe',
        default=lambda self: self.env.company,
    )

    def compute(self, value, date_ref=False):
        """
        Calculer les echeances de paiement
        Retourne une liste de tuples (date, montant)
        """
        self.ensure_one()
        date_ref = date_ref or fields.Date.today()
        amount = value
        result = []

        for line in self.line_ids:
            if line.value == 'fixed':
                amt = min(line.value_amount, amount)
            elif line.value == 'percent':
                amt = value * (line.value_amount / 100.0)
            else:  # balance
                amt = amount

            if amt:
                # Calculer la date
                if line.delay_type == 'days_after':
                    next_date = fields.Date.add(date_ref, days=line.nb_days)
                elif line.delay_type == 'days_end_of_month':
                    from dateutil.relativedelta import relativedelta
                    next_date = fields.Date.add(date_ref, days=line.nb_days)
                    next_date = next_date + relativedelta(day=31)
                elif line.delay_type == 'days_end_of_month_on':
                    from dateutil.relativedelta import relativedelta
                    next_date = date_ref + relativedelta(day=31)
                    next_date = fields.Date.add(next_date, days=line.nb_days)
                else:
                    next_date = date_ref

                result.append((next_date, amt))
                amount -= amt

        return result


class AccountPaymentTermLine(models.Model):
    """
    Ligne de Conditions de Paiement
    """
    _name = 'account.payment.term.line.custom'
    _description = 'Ligne condition paiement'
    _order = 'sequence, id'

    payment_id = fields.Many2one(
        'account.payment.term.custom',
        string='Condition de paiement',
        required=True,
        ondelete='cascade',
    )
    sequence = fields.Integer(default=10)

    value = fields.Selection([
        ('balance', 'Solde'),
        ('percent', 'Pourcentage'),
        ('fixed', 'Montant fixe'),
    ], string='Type', required=True, default='balance')

    value_amount = fields.Float(
        string='Valeur',
        help="Pour pourcentage: valeur entre 0 et 100. Pour fixe: montant.",
    )

    delay_type = fields.Selection([
        ('days_after', 'Jours apres la date de facture'),
        ('days_end_of_month', 'Jours apres fin de mois'),
        ('days_end_of_month_on', 'Jour du mois suivant'),
    ], string='Type delai', required=True, default='days_after')

    nb_days = fields.Integer(
        string='Nombre de jours',
        default=0,
    )
