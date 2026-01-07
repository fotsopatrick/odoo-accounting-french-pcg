# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
from dateutil.relativedelta import relativedelta


class AccountFiscalYear(models.Model):
    """
    Exercice Fiscal
    """
    _name = 'account.fiscal.year.custom'
    _description = 'Exercice fiscal'
    _order = 'date_from desc'

    name = fields.Char(
        string='Nom',
        required=True,
    )
    code = fields.Char(
        string='Code',
        size=6,
    )

    date_from = fields.Date(
        string='Date debut',
        required=True,
    )
    date_to = fields.Date(
        string='Date fin',
        required=True,
    )

    company_id = fields.Many2one(
        'res.company',
        string='Societe',
        required=True,
        default=lambda self: self.env.company,
    )

    state = fields.Selection([
        ('draft', 'Ouvert'),
        ('done', 'Cloture'),
    ], string='Etat', default='draft')

    # Periodes
    period_ids = fields.One2many(
        'account.period.custom',
        'fiscal_year_id',
        string='Periodes',
    )

    _sql_constraints = [
        ('date_check', 'CHECK(date_from < date_to)',
         'La date de debut doit etre anterieure a la date de fin!'),
    ]

    @api.constrains('date_from', 'date_to', 'company_id')
    def _check_dates_overlap(self):
        for fy in self:
            overlapping = self.search([
                ('id', '!=', fy.id),
                ('company_id', '=', fy.company_id.id),
                '|',
                '&', ('date_from', '<=', fy.date_from), ('date_to', '>=', fy.date_from),
                '&', ('date_from', '<=', fy.date_to), ('date_to', '>=', fy.date_to),
            ])
            if overlapping:
                raise ValidationError(_(
                    "L'exercice fiscal chevauche un exercice existant: %s"
                ) % overlapping[0].name)

    def action_create_periods(self):
        """Creer les 12 periodes mensuelles"""
        self.ensure_one()

        if self.period_ids:
            raise UserError(_("Des periodes existent deja pour cet exercice."))

        Period = self.env['account.period.custom']
        current_date = self.date_from
        period_num = 1

        while current_date < self.date_to:
            # Calculer la fin de la periode (fin du mois)
            next_month = current_date + relativedelta(months=1)
            period_end = min(next_month - relativedelta(days=1), self.date_to)

            Period.create({
                'name': '%s/%02d' % (self.code or self.name, period_num),
                'code': '%02d/%s' % (period_num, self.code or ''),
                'date_start': current_date,
                'date_stop': period_end,
                'fiscal_year_id': self.id,
                'number': period_num,
            })

            current_date = next_month
            period_num += 1

        return True

    def action_close(self):
        """Cloturer l'exercice fiscal"""
        for fy in self:
            # Verifier que toutes les periodes sont cloturees
            open_periods = fy.period_ids.filtered(lambda p: p.state == 'draft')
            if open_periods:
                raise UserError(_(
                    "Toutes les periodes doivent etre cloturees avant de cloturer l'exercice.\n"
                    "Periodes ouvertes: %s"
                ) % ', '.join(open_periods.mapped('name')))

            fy.state = 'done'
        return True

    def action_reopen(self):
        """Reouvrir l'exercice fiscal"""
        for fy in self:
            fy.state = 'draft'
        return True


class AccountPeriod(models.Model):
    """
    Periode Comptable
    """
    _name = 'account.period.custom'
    _description = 'Periode comptable'
    _order = 'date_start'

    name = fields.Char(
        string='Nom',
        required=True,
    )
    code = fields.Char(
        string='Code',
        size=12,
    )

    date_start = fields.Date(
        string='Date debut',
        required=True,
    )
    date_stop = fields.Date(
        string='Date fin',
        required=True,
    )

    fiscal_year_id = fields.Many2one(
        'account.fiscal.year.custom',
        string='Exercice fiscal',
        required=True,
        ondelete='cascade',
    )

    company_id = fields.Many2one(
        related='fiscal_year_id.company_id',
        store=True,
    )

    number = fields.Integer(string='Numero')

    state = fields.Selection([
        ('draft', 'Ouverte'),
        ('done', 'Cloturee'),
    ], string='Etat', default='draft')

    special = fields.Boolean(
        string='Periode speciale',
        default=False,
        help="Periode d'ouverture ou de cloture",
    )

    _sql_constraints = [
        ('date_check', 'CHECK(date_start < date_stop)',
         'La date de debut doit etre anterieure a la date de fin!'),
    ]

    def action_close(self):
        """Cloturer la periode"""
        for period in self:
            # Verifier qu'il n'y a pas d'ecritures en brouillon
            draft_moves = self.env['account.move.custom'].search_count([
                ('date', '>=', period.date_start),
                ('date', '<=', period.date_stop),
                ('company_id', '=', period.company_id.id),
                ('state', '=', 'draft'),
            ])
            if draft_moves:
                raise UserError(_(
                    "Il reste %d ecritures en brouillon dans cette periode. "
                    "Veuillez les valider ou les supprimer avant de cloturer."
                ) % draft_moves)

            period.state = 'done'
        return True

    def action_reopen(self):
        """Reouvrir la periode"""
        for period in self:
            if period.fiscal_year_id.state == 'done':
                raise UserError(_("Impossible de reouvrir une periode d'un exercice cloture."))
            period.state = 'draft'
        return True

    @api.model
    def find(self, dt=None, company_id=None):
        """Trouver la periode pour une date donnee"""
        if not dt:
            dt = fields.Date.today()
        if not company_id:
            company_id = self.env.company.id

        period = self.search([
            ('date_start', '<=', dt),
            ('date_stop', '>=', dt),
            ('company_id', '=', company_id),
            ('special', '=', False),
        ], limit=1)

        return period


class AccountFiscalPosition(models.Model):
    """
    Position Fiscale
    Permet de mapper les taxes et comptes selon le partenaire
    """
    _name = 'account.fiscal.position.custom'
    _description = 'Position fiscale'
    _order = 'sequence'

    name = fields.Char(string='Nom', required=True)
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)

    company_id = fields.Many2one(
        'res.company',
        string='Societe',
        default=lambda self: self.env.company,
    )

    # Conditions d'application automatique
    auto_apply = fields.Boolean(
        string='Application automatique',
        default=False,
    )
    country_id = fields.Many2one(
        'res.country',
        string='Pays',
    )
    country_group_id = fields.Many2one(
        'res.country.group',
        string='Groupe de pays',
    )
    state_ids = fields.Many2many(
        'res.country.state',
        'fiscal_position_state_custom_rel',
        'position_id',
        'state_id',
        string='Regions',
    )
    zip_from = fields.Char(string='Code postal de')
    zip_to = fields.Char(string='Code postal a')

    vat_required = fields.Boolean(
        string='TVA intra requise',
        default=False,
    )

    # Mapping taxes
    tax_ids = fields.One2many(
        'account.fiscal.position.tax.custom',
        'position_id',
        string='Correspondance taxes',
    )

    # Mapping comptes
    account_ids = fields.One2many(
        'account.fiscal.position.account.custom',
        'position_id',
        string='Correspondance comptes',
    )

    note = fields.Html(string='Notes')

    def map_tax(self, taxes):
        """Mapper les taxes selon la position fiscale"""
        result = self.env['account.tax.custom']
        for tax in taxes:
            mapping = self.tax_ids.filtered(lambda m: m.tax_src_id == tax)
            if mapping:
                if mapping.tax_dest_id:
                    result |= mapping.tax_dest_id
            else:
                result |= tax
        return result

    def map_account(self, account):
        """Mapper un compte selon la position fiscale"""
        mapping = self.account_ids.filtered(lambda m: m.account_src_id == account)
        if mapping:
            return mapping.account_dest_id
        return account


class AccountFiscalPositionTax(models.Model):
    """
    Correspondance Taxes Position Fiscale
    """
    _name = 'account.fiscal.position.tax.custom'
    _description = 'Correspondance taxe position fiscale'

    position_id = fields.Many2one(
        'account.fiscal.position.custom',
        string='Position fiscale',
        required=True,
        ondelete='cascade',
    )
    tax_src_id = fields.Many2one(
        'account.tax.custom',
        string='Taxe origine',
        required=True,
    )
    tax_dest_id = fields.Many2one(
        'account.tax.custom',
        string='Taxe destination',
    )


class AccountFiscalPositionAccount(models.Model):
    """
    Correspondance Comptes Position Fiscale
    """
    _name = 'account.fiscal.position.account.custom'
    _description = 'Correspondance compte position fiscale'

    position_id = fields.Many2one(
        'account.fiscal.position.custom',
        string='Position fiscale',
        required=True,
        ondelete='cascade',
    )
    account_src_id = fields.Many2one(
        'account.account.custom',
        string='Compte origine',
        required=True,
    )
    account_dest_id = fields.Many2one(
        'account.account.custom',
        string='Compte destination',
        required=True,
    )
