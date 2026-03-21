# -*- coding: utf-8 -*-
import logging
from odoo import models, api, _, fields
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class AccountMove(models.Model):
    _inherit = 'account.move'

    cogs_move_id = fields.Many2one('account.move', 'COGS Move')

    def write(self, vals):
        res = super(AccountMove, self).write(vals)

        if vals.get('state') == 'cancel':
            for move in self:
                if move.cogs_move_id:
                    cogs_move = move.cogs_move_id

                    if cogs_move.state == 'posted':
                        cogs_move.button_draft()

                    if cogs_move.state != 'cancel':
                        cogs_move.button_cancel()

        return res

    def action_post(self):
        res = super(AccountMove, self).action_post()
        for move in self:
            # Only apply on customer invoices
            if move.move_type == 'out_invoice' and move.company_id.anglo_saxon_accounting:
                move._create_cogs_journal_entry()
        return res

    def _create_cogs_journal_entry(self):
        """
        Create NEW accounting entry in 'Inventory Valuation' journal:
        Dr COGS
        Cr Output Stock
        in one shot using line_ids.
        """
        Journal = self.env['account.journal']
        Move = self.env['account.move']

        # Find Inventory Valuation Journal
        inv_journal = Journal.search(
            [('type', '=', 'general'), ('name', 'ilike', 'Inventory Valuation')],
            limit=1
        )
        if not inv_journal:
            raise UserError(_("Please configure an 'Inventory Valuation' journal."))

        if self.cogs_move_id:
            cogs_move_obj = Move.search([('id','=',self.cogs_move_id.id),('journal_id','=',inv_journal.id)], limit=1)
        else:
            cogs_move_obj = Move.search([('ref','=','COGS Entry for Invoice ' + str(self.name)),('journal_id','=',inv_journal.id)], limit=1)
        _logger.info(cogs_move_obj)

        move_lines = []  # collect all COGS + Output Stock lines

        for line in self.invoice_line_ids:
            product = line.product_id
            if not product or product.type != 'product':
                continue
            if product.categ_id.property_valuation != 'real_time':
                continue
            # Fetch accounts from product category
            cogs_account = product.categ_id.cogs_account_id
            output_account = product.categ_id.property_stock_account_output_categ_id

            if product.categ_id.property_valuation == 'real_time' and (not cogs_account or not output_account):
                raise UserError(
                    _("Please configure COGS & Output Stock accounts on product category: %s for Invoice %s") 
                    % (product.display_name, self.name)
                )

            # Get related stock moves from Delivery Order
            stock_moves = self.env['stock.move'].search([
                ('sale_line_id', 'in', line.sale_line_ids.ids),
                ('state', '=', 'done')
            ])
            valuation_layers = stock_moves.mapped('stock_valuation_layer_ids')
            value = sum(valuation_layers.mapped('value'))

            if not value:
                continue

            # Prepare journal lines
            move_lines.append((0, 0, {
                'name': _('COGS for %s') % product.display_name,
                'account_id': cogs_account.id,
                'debit': abs(value),
                'credit': 0.0,
            }))
            move_lines.append((0, 0, {
                'name': _('Output Stock for %s') % product.display_name,
                'account_id': output_account.id,
                'debit': 0.0,
                'credit': abs(value),
            }))

        if cogs_move_obj and move_lines:
            if cogs_move_obj.state in ['posted','cancel']:
                cogs_move_obj.button_draft()
            cogs_move_obj.line_ids.unlink()
            cogs_move_obj.write({
                'journal_id': inv_journal.id,
                'date': self.date,
                'ref': _('COGS Entry for Invoice %s') % self.name,
                'line_ids': move_lines,
                })
            cogs_move_obj.action_post()
            self.write({'cogs_move_id': cogs_move_obj.id})

        # Only create if we have lines
        elif move_lines:
            cogs_move_obj = Move.create({
                'journal_id': inv_journal.id,
                'date': self.date,
                'ref': _('COGS Entry for Invoice %s') % self.name,
                'line_ids': move_lines,
                'move_type': 'entry'
            })
            cogs_move_obj.action_post()
            self.write({'cogs_move_id': cogs_move_obj.id})


        _logger.info(self.cogs_move_id)