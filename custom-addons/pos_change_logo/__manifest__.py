# -*- coding: utf-8 -*-
#################################################################################
# Author      : Webkul Software Pvt. Ltd. (<https://webkul.com/>)
# Copyright(c): 2015-Present Webkul Software Pvt. Ltd.
# All Rights Reserved.
#
#
#
# This program is copyright property of the author mentioned above.
# You can`t redistribute it and/or modify it.
#
#
# You should have received a copy of the License along with this program.
# If not, see <https://store.webkul.com/license.html/>
#################################################################################
{
  "name"                 :  "POS Change Logo",
  "summary"              :  """Add your company logo to the POS with the module. The logo will appear in the POS session and on the order receipt.""",
  "category"             :  "Point of Sale",
  "version"              :  "1.0",
  "sequence"             :  1,
  "author"               :  "Webkul Software Pvt. Ltd.",
  "license"              :  "Other proprietary",
  "website"              :  "https://store.webkul.com/Odoo-POS-Change-Logo.html",
  "description"          :  """Odoo POS Change Logo
Add logo in POS
Logo on POS receipts
Pos receipts LOGO
Company logo POS
Print company logo
Use Company logo in POS
POS Session logo""",
  "live_test_url"        :  "http://odoodemo.webkul.com/?module=pos_change_logo&custom_url=/web#action=point_of_sale.action_client_pos_menu",
  "depends"              :  ['point_of_sale'],
  "data"                 :  [
                             'views/pos_config_view.xml',
                             'views/template.xml',
                             'security/ir.model.access.csv',
                            ],
  "demo"                 :  ['data/pos_change_logo_demo.xml'],
  "qweb"                 :  ['static/src/xml/*.xml'],
  "images"               :  ['static/description/Banner.png'],
  "application"          :  True,
  "installable"          :  True,
  "auto_install"         :  False,
  "price"                :  20,
  "currency"             :  "USD",
  "pre_init_hook"        :  "pre_init_check",
}