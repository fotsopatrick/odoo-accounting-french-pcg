# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError


class AccountBudget(models.Model):
    """
    Budget Comptable
    """
    _name = 'account.budget.custom'
    _description = 'Budget'
    _inherit = ['mail.thread']
    _order = 'date_from desc'

    name = fields.Char(
        string='Nom du budget',
        required=True,
        tracking=True,
    )
    state = fields.Selection([
        ('draft', 'Brouillon'),
        ('confirm', 'Confirme'),
        ('validate', 'Valide'),
        ('done', 'Termine'),
        ('cancel', 'Annule'),
    ], string='Etat', default='draft', tracking=True)

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

    # Lignes de budget
    line_ids = fields.One2many(
        'account.budget.line.custom',
        'budget_id',
        string='Lignes de budget',
        copy=True,
    )

    # Responsable
    user_id = fields.Many2one(
        'res.users',
        string='Responsable',
        default=lambda self: self.env.user,
    )

    # Totaux
    total_planned = fields.Monetary(
        string='Total prevu',
        compute='_compute_totals',
        currency_field='currency_id',
    )
    total_practical = fields.Monetary(
        string='Total realise',
        compute='_compute_totals',
        currency_field='currency_id',
    )
    total_variance = fields.Monetary(
        string='Ecart',
        compute='_compute_totals',
        currency_field='currency_id',
    )
    currency_id = fields.Many2one(
        related='company_id.currency_id',
    )

    @api.constrains('date_from', 'date_to')
    def _check_dates(self):
        for budget in self:
            if budget.date_from > budget.date_to:
                raise ValidationError(_("La date de debut doit etre anterieure a la date de fin."))

    @api.depends('line_ids.planned_amount', 'line_ids.practical_amount')
    def _compute_totals(self):
        for budget in self:
            budget.total_planned = sum(budget.line_ids.mapped('planned_amount'))
            budget.total_practical = sum(budget.line_ids.mapped('practical_amount'))
            budget.total_variance = budget.total_planned - budget.total_practical

    def action_confirm(self):
        for budget in self:
            budget.state = 'confirm'
        return True

    def action_validate(self):
        for budget in self:
            budget.state = 'validate'
        return True

    def action_done(self):
        for budget in self:
            budget.state = 'done'
        return True

    def action_cancel(self):
        for budget in self:
            budget.state = 'cancel'
        return True

    def action_draft(self):
        for budget in self:
            budget.state = 'draft'
        return True


class AccountBudgetLine(models.Model):
    """
    Ligne de Budget
    """
    _name = 'account.budget.line.custom'
    _description = 'Ligne de budget'
    _order = 'sequence, id'

    budget_id = fields.Many2one(
        'account.budget.custom',
        string='Budget',
        required=True,
        ondelete='cascade',
    )
    sequence = fields.Integer(default=10)

    # Compte ou analytique
    account_id = fields.Many2one(
        'account.account.custom',
        string='Compte general',
    )
    analytic_account_id = fields.Many2one(
        'account.analytic.account.custom',
        string='Compte analytique',
    )

    name = fields.Char(string='Description')

    # Dates (heritees ou personnalisees)
    date_from = fields.Date(
        string='Date debut',
        related='budget_id.date_from',
        store=True,
    )
    date_to = fields.Date(
        string='Date fin',
        related='budget_id.date_to',
        store=True,
    )

    # Montants
    planned_amount = fields.Monetary(
        string='Montant prevu',
        required=True,
        default=0.0,
        currency_field='currency_id',
    )
    practical_amount = fields.Monetary(
        string='Montant realise',
        compute='_compute_practical_amount',
        currency_field='currency_id',
    )
    variance = fields.Monetary(
        string='Ecart',
        compute='_compute_variance',
        currency_field='currency_id',
    )
    variance_percent = fields.Float(
        string='Ecart %',
        compute='_compute_variance',
    )

    currency_id = fields.Many2one(
        related='budget_id.currency_id',
    )
    company_id = fields.Many2one(
        related='budget_id.company_id',
    )

    def _compute_practical_amount(self):
        for line in self:
            practical = 0.0
            if line.analytic_account_id:
                # Somme des lignes analytiques
                analytic_lines = self.env['account.analytic.line.custom'].search([
                    ('account_id', '=', line.analytic_account_id.id),
                    ('date', '>=', line.date_from),
                    ('date', '<=', line.date_to),
                ])
                practical = sum(analytic_lines.mapped('amount'))
            elif line.account_id:
                # Somme des ecritures comptables
                move_lines = self.env['account.move.line.custom'].search([
                    ('account_id', '=', line.account_id.id),
                    ('date', '>=', line.date_from),
                    ('date', '<=', line.date_to),
                    ('move_id.state', '=', 'posted'),
                ])
                practical = sum(move_lines.mapped('balance'))
            line.practical_amount = abs(practical)

    @api.depends('planned_amount', 'practical_amount')
    def _compute_variance(self):
        for line in self:
            line.variance = line.planned_amount - line.practical_amount
            if line.planned_amount:
                line.variance_percent = (line.variance / line.planned_amount) * 100
            else:
                line.variance_percent = 0.0


class AccountBudgetPost(models.Model):
    """
    Postes Budgetaires (regroupement de comptes)
    """
    _name = 'account.budget.post.custom'
    _description = 'Poste budgetaire'
    _order = 'name'

    name = fields.Char(string='Nom', required=True)
    code = fields.Char(string='Code')

    account_ids = fields.Many2many(
        'account.account.custom',
        'budget_post_account_custom_rel',
        'post_id',
        'account_id',
        string='Comptes',
    )

    company_id = fields.Many2one(
        'res.company',
        string='Societe',
        default=lambda self: self.env.company,
    )
