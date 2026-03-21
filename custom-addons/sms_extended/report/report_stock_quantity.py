# -*- coding: utf-8 -*-
from odoo import fields, models, tools, api

class ReportStockQuantity(models.Model):
    _inherit = 'report.stock.quantity'

    product_cost = fields.Float('Cost')

    def init(self):
        tools.drop_view_if_exists(self._cr, 'report_stock_quantity')
        query = """
CREATE or REPLACE VIEW report_stock_quantity AS (
SELECT
    MIN(forecast_qty.id) as id,
    product_id,
    state,
    date,
    sum(product_qty) as product_qty,
    forecast_qty.company_id,
    warehouse_id,
    sum(product_qty) * ir.value_float as product_cost
FROM (
    SELECT
        m.id,
        m.product_id,
        CASE
            WHEN whs.id IS NOT NULL AND whd.id IS NULL THEN 'out'
            WHEN whd.id IS NOT NULL AND whs.id IS NULL THEN 'in'
        END AS state,
        m.date::date AS date,
        CASE
            WHEN whs.id IS NOT NULL AND whd.id IS NULL THEN -m.product_qty
            WHEN whd.id IS NOT NULL AND whs.id IS NULL THEN m.product_qty
        END AS product_qty,
        m.company_id,
        CASE
            WHEN whs.id IS NOT NULL AND whd.id IS NULL THEN whs.id
            WHEN whd.id IS NOT NULL AND whs.id IS NULL THEN whd.id
        END AS warehouse_id
    FROM
        stock_move m
    LEFT JOIN stock_location ls on (ls.id=m.location_id)
    LEFT JOIN stock_location ld on (ld.id=m.location_dest_id)
    LEFT JOIN stock_warehouse whs ON ls.parent_path like concat('%/', whs.view_location_id, '/%')
    LEFT JOIN stock_warehouse whd ON ld.parent_path like concat('%/', whd.view_location_id, '/%')
    LEFT JOIN product_product pp on pp.id=m.product_id
    LEFT JOIN product_template pt on pt.id=pp.product_tmpl_id
    WHERE
        pt.type = 'product' AND
        m.product_qty != 0 AND
        (whs.id IS NOT NULL OR whd.id IS NOT NULL) AND
        (whs.id IS NULL OR whd.id IS NULL OR whs.id != whd.id) AND
        m.state NOT IN ('cancel', 'draft', 'done')

    UNION ALL

    SELECT
        -q.id as id,
        q.product_id,
        'forecast' as state,
        date.*::date,
        q.quantity as product_qty,
        q.company_id,
        wh.id as warehouse_id
    FROM
        GENERATE_SERIES((now() at time zone 'utc')::date - interval '3month',
        (now() at time zone 'utc')::date + interval '3 month', '1 day'::interval) date,
        stock_quant q
    LEFT JOIN stock_location l on (l.id=q.location_id)
    LEFT JOIN stock_warehouse wh ON l.parent_path like concat('%/', wh.view_location_id, '/%')
    WHERE
        (l.usage = 'internal' AND wh.id IS NOT NULL) OR
        l.usage = 'transit'

    UNION ALL

    SELECT
        m.id,
        m.product_id,
        'forecast' as state,
        GENERATE_SERIES(
        CASE
            WHEN m.state = 'done' THEN (now() at time zone 'utc')::date - interval '3month'
            ELSE m.date::date
        END,
        CASE
            WHEN m.state != 'done' THEN (now() at time zone 'utc')::date + interval '3 month'
            ELSE m.date::date - interval '1 day'
        END, '1 day'::interval)::date date,
        CASE
            WHEN whs.id IS NOT NULL AND whd.id IS NULL AND m.state = 'done' THEN m.product_qty
            WHEN whd.id IS NOT NULL AND whs.id IS NULL AND m.state = 'done' THEN -m.product_qty
            WHEN whs.id IS NOT NULL AND whd.id IS NULL THEN -m.product_qty
            WHEN whd.id IS NOT NULL AND whs.id IS NULL THEN m.product_qty
        END AS product_qty,
        m.company_id,
        CASE
            WHEN whs.id IS NOT NULL AND whd.id IS NULL THEN whs.id
            WHEN whd.id IS NOT NULL AND whs.id IS NULL THEN whd.id
        END AS warehouse_id
    FROM
        stock_move m
    LEFT JOIN stock_location ls on (ls.id=m.location_id)
    LEFT JOIN stock_location ld on (ld.id=m.location_dest_id)
    LEFT JOIN stock_warehouse whs ON ls.parent_path like concat('%/', whs.view_location_id, '/%')
    LEFT JOIN stock_warehouse whd ON ld.parent_path like concat('%/', whd.view_location_id, '/%')
    LEFT JOIN product_product pp on pp.id=m.product_id
    LEFT JOIN product_template pt on pt.id=pp.product_tmpl_id
    WHERE
        pt.type = 'product' AND
        m.product_qty != 0 AND
        (whs.id IS NOT NULL OR whd.id IS NOT NULL) AND
        (whs.id IS NULL or whd.id IS NULL OR whs.id != whd.id) AND
        m.state NOT IN ('cancel', 'draft')) AS forecast_qty
    LEFT JOIN ir_property ir on ir.res_id = 'product.product,' || forecast_qty.product_id AND name = 'standard_price'  
GROUP BY product_id, state, date, forecast_qty.company_id, warehouse_id, ir.value_float
);
"""
        self.env.cr.execute(query)