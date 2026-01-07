# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class AccountJournal(models.Model):
    """
    Journaux Comptables
    """
    _name = 'account.journal.custom'
    _description = 'Journal Comptable'
    _order = 'sequence, type, code'

    name = fields.Char(
        string='Nom du journal',
        required=True,
    )
    code = fields.Char(
        string='Code',
        required=True,
        size=5,
        help="Code court du journal (max 5 caracteres)",
    )
    active = fields.Boolean(default=True)
    sequence = fields.Integer(default=10)

    type = fields.Selection([
        ('sale', 'Ventes'),
        ('purchase', 'Achats'),
        ('cash', 'Caisse'),
        ('bank', 'Banque'),
        ('general', 'Operations diverses'),
        ('situation', 'Situation (ouverture/cloture)'),
    ], string='Type', required=True, default='general')

    # Comptes par defaut
    default_account_id = fields.Many2one(
        'account.account.custom',
        string='Compte par defaut',
        help="Compte utilise par defaut pour les ecritures",
    )
    suspense_account_id = fields.Many2one(
        'account.account.custom',
        string='Compte d attente',
        help="Compte pour les ecritures en attente de rapprochement",
    )
    profit_account_id = fields.Many2one(
        'account.account.custom',
        string='Compte de profit',
        help="Compte pour les ecarts positifs de rapprochement",
    )
    loss_account_id = fields.Many2one(
        'account.account.custom',
        string='Compte de perte',
        help="Compte pour les ecarts negatifs de rapprochement",
    )

    # Configuration banque
    bank_account_id = fields.Many2one(
        'res.partner.bank',
        string='Compte bancaire',
    )
    bank_id = fields.Many2one(
        related='bank_account_id.bank_id',
        string='Banque',
    )

    # Sequences
    sequence_id = fields.Many2one(
        'ir.sequence',
        string='Sequence des ecritures',
        copy=False,
    )
    refund_sequence = fields.Boolean(
        string='Sequence dediee aux avoirs',
        default=False,
    )
    refund_sequence_id = fields.Many2one(
        'ir.sequence',
        string='Sequence des avoirs',
        copy=False,
    )

    # Configuration
    company_id = fields.Many2one(
        'res.company',
        string='Societe',
        required=True,
        default=lambda self: self.env.company,
    )
    currency_id = fields.Many2one(
        'res.currency',
        string='Devise',
        help="Devise du journal (laisser vide pour devise societe)",
    )

    # Restrictions
    account_control_ids = fields.Many2many(
        'account.account.custom',
        'journal_custom_account_control_rel',
        'journal_id',
        'account_id',
        string='Comptes autorises',
        help="Si rempli, seuls ces comptes peuvent etre utilises",
    )

    # Couleur pour kanban
    color = fields.Integer(string='Couleur')

    # Statistiques
    move_count = fields.Integer(
        string='Nombre d ecritures',
        compute='_compute_move_count',
    )

    _sql_constraints = [
        ('code_company_uniq', 'unique(code, company_id)',
         'Le code du journal doit etre unique par societe!'),
    ]

    def _compute_move_count(self):
        for journal in self:
            journal.move_count = self.env['account.move.custom'].search_count([
                ('journal_id', '=', journal.id),
            ])

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('sequence_id'):
                # Creer une sequence automatiquement
                seq_vals = {
                    'name': 'Journal %s' % vals.get('name', 'New'),
                    'code': 'account.journal.%s' % vals.get('code', 'new'),
                    'padding': 4,
                    'prefix': '%s/%%(year)s/' % vals.get('code', 'NEW'),
                }
                vals['sequence_id'] = self.env['ir.sequence'].create(seq_vals).id
        return super().create(vals_list)

    def action_view_moves(self):
        """Voir les ecritures du journal"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Ecritures - %s') % self.name,
            'res_model': 'account.move.custom',
            'view_mode': 'list,form',
            'domain': [('journal_id', '=', self.id)],
            'context': {'default_journal_id': self.id},
        }

    def action_create_new_move(self):
        """Creer une nouvelle ecriture"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Nouvelle ecriture'),
            'res_model': 'account.move.custom',
            'view_mode': 'form',
            'context': {
                'default_journal_id': self.id,
                'default_move_type': 'entry' if self.type == 'general' else self.type,
            },
        }
