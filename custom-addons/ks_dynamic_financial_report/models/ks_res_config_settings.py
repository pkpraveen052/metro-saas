from odoo import models, fields, api, _


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    ks_enable_ledger_in_bal = fields.Boolean('Enable Ledger Initial Balance',
                                             config_parameter='ks_enable_ledger_in_bal')
    ks_disable_trial_en_bal = fields.Boolean('Disable Trial Initial Balance',
                                             config_parameter='ks_disable_trial_en_bal')

    ks_disable_bs_sign = fields.Boolean('Disable Balance Sheet Sign',
                                        config_parameter='ks_disable_bs_sign')
    ks_enable_net_tax = fields.Boolean('Enable Net Tax',
                                             config_parameter='ks_enable_net_tax')

    ks_enable_total_sale_net_tax = fields.Boolean('Enable Total Sales Tax', config_parameter='ks_dynamic_financial_report.ks_true_enable_total_sale_net_tax')

    def set_values(self):
        super(ResConfigSettings, self).set_values()
        res = self.env['ir.config_parameter'].set_param('ks_dynamic_financial_report.ks_true_enable_total_sale_net_tax', self.ks_enable_total_sale_net_tax)
        return res

    @api.model
    def get_values(self):
        res = super(ResConfigSettings, self).get_values()
        params = self.env['ir.config_parameter'].sudo()
        res.update(
            ks_enable_total_sale_net_tax=params.get_param('ks_dynamic_financial_report.ks_true_enable_total_sale_net_tax'),
        )
        return res

