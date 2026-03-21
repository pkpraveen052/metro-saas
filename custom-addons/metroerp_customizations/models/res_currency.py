from odoo import models, fields, _, api
import logging
import requests
import json
from datetime import datetime
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import pytz




_logger = logging.getLogger(__name__)

class ResCurrency(models.Model):
    _inherit = 'res.currency'

    @api.model
    def update_mas_currency_rates(self):
        api_url = "https://eservices.mas.gov.sg/apimg-gw/server/monthly_statistical_bulletin_non610ora/exchange_rates_end_of_period_daily/views/exchange_rates_end_of_period_daily"
        sg_tz = pytz.timezone('Asia/Singapore')
        today = datetime.now(sg_tz).date()
        params = {"end_of_day": today.strftime('%Y-%m-%d')}
        headers = {
            "accept": "application/json; charset=UTF-8",
            "KeyId": "7378f0f7-2637-48ff-9511-961545887475"
        }

        companies = self.env['res.company'].sudo().search([])
        status_messages = {
            204: "No results were returned.",
            400: "Bad request.",
            401: "Authentication failed.",
            403: "Insufficient permissions.",
            500: "Runtime error.",
        }

        # ---- requests retry + timeout setup ----
        session = requests.Session()


        retry_strategy = Retry(
            total=3,
            backoff_factor=2,
            status_forcelist=[500, 502, 503, 504],
            method_whitelist=["GET"],
            raise_on_status=False,
        )

        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("https://", adapter)
        session.mount("http://", adapter)


        try:
            response = session.get(
                                api_url,
                                headers=headers,
                                params=params,
                                timeout=30  # timeout in seconds
                            )

            status_code = response.status_code
            raw_json = response.text

            if status_code != 200:
                error_msg = status_messages.get(status_code, "Unexpected response code.")
                try:
                    formatted_json = json.dumps(json.loads(raw_json), indent=4)
                except Exception:
                    formatted_json = raw_json

                for company in companies:
                    self.env['currency.log'].sudo().create({
                        'name': f'MAS API Sync - {today}',
                        'status': 'fail',
                        'status_code': status_code,
                        'json_data': formatted_json,
                        'message': f"MAS API request failed ({status_code}): {error_msg}",
                        'company_id': company.id,
                    })
                return

            data = response.json()
            elements = data.get('elements', [])
            if not elements:
                for company in companies:
                    self.env['currency.log'].sudo().create({
                        'name': f'MAS API Sync - {today}',
                        'status': 'fail',
                        'status_code': status_code,
                        'json_data': raw_json,
                        'message': "MAS API response contained no 'elements' data.",
                        'company_id': company.id,
                    })
                return

            rates = elements[0]

            currency_map = {
                "usd_sgd": "USD", "eur_sgd": "EUR", "gbp_sgd": "GBP", "aud_sgd": "AUD",
                "cad_sgd": "CAD", "chf_sgd": "CHF", "nzd_sgd": "NZD",
                "cny_sgd_100": "CNY", "inr_sgd_100": "INR", "hkd_sgd_100": "HKD",
                "jpy_sgd_100": "JPY", "krw_sgd_100": "KRW", "myr_sgd_100": "MYR",
                "twd_sgd_100": "TWD", "php_sgd_100": "PHP", "qar_sgd_100": "QAR",
                "sar_sgd_100": "SAR", "thb_sgd_100": "THB", "aed_sgd_100": "AED",
                "vnd_sgd_100": "VND", "khr_sgd_100": "KHR", "idr_sgd_100": "IDR",
            }

            base_currency_map = {
                "USD": "usd_sgd", "EUR": "eur_sgd", "GBP": "gbp_sgd",
                "AUD": "aud_sgd", "CAD": "cad_sgd", "CHF": "chf_sgd",
                "NZD": "nzd_sgd", "CNY": "cny_sgd_100", "INR": "inr_sgd_100",
                "HKD": "hkd_sgd_100", "JPY": "jpy_sgd_100", "KRW": "krw_sgd_100",
                "MYR": "myr_sgd_100", "TWD": "twd_sgd_100", "PHP": "php_sgd_100",
                "QAR": "qar_sgd_100", "SAR": "sar_sgd_100", "THB": "thb_sgd_100",
                "AED": "aed_sgd_100", "VND": "vnd_sgd_100",
                "KHR": "khr_sgd_100", "IDR": "idr_sgd_100",
            }

            def _get_rate_to_sgd(field_key, rates):
                if not field_key:
                    return None
                value = rates.get(field_key)
                if not value:
                    return None
                value = float(value)
                if "_100" in field_key:
                    value /= 100
                return value

            for company in companies:
                # Respect auto update setting
                if not company.auto_currency_rate:
                    continue

                error_msgs = []
                base_currency = company.currency_id.name

                # Get base → SGD rate
                if base_currency == 'SGD':
                    base_to_sgd = 1.0
                else:
                    base_field_key = base_currency_map.get(base_currency)
                    if not base_field_key:
                        error_msgs.append(f"Base currency {base_currency} not supported by MAS")
                        continue

                    base_to_sgd = _get_rate_to_sgd(base_field_key, rates)
                    if not base_to_sgd:
                        error_msgs.append(f"Base currency {base_currency}: rate not found in MAS")
                        continue

                    # CREATE SGD RATE WHEN BASE IS NOT SGD (SAFE PLACE)
                    sgd_currency = self.env['res.currency'].sudo().search(
                        [('name', '=', 'SGD')], limit=1
                    )
                    if sgd_currency:
                        sgd_rate_exists = self.env['res.currency.rate'].sudo().search([
                            ('currency_id', '=', sgd_currency.id),
                            ('name', '=', today),
                            ('company_id', '=', company.id),
                        ], limit=1)

                        if not sgd_rate_exists:
                            self.env['res.currency.rate'].sudo().create({
                                'currency_id': sgd_currency.id,
                                'rate': base_to_sgd,
                                'name': today,
                                'company_id': company.id,
                            })


                    if not base_to_sgd:
                        error_msgs.append(f"Base currency {base_currency}: rate not found in MAS")
                        continue

                # Ensure base currency rate exists (ONCE)
                base_currency_rec = company.currency_id
                base_rate_exists = self.env['res.currency.rate'].sudo().search([
                    ('currency_id', '=', base_currency_rec.id),
                    ('name', '=', today),
                    ('company_id', '=', company.id),
                ], limit=1)

                if not base_rate_exists:
                    self.env['res.currency.rate'].sudo().create({
                        'currency_id': base_currency_rec.id,
                        'rate': 1.0,
                        'name': today,
                        'company_id': company.id,
                    })

                # Foreign currencies
                for field_key, currency_code in currency_map.items():
                    if currency_code == base_currency:
                        continue

                    foreign_to_sgd = _get_rate_to_sgd(field_key, rates)
                    if not foreign_to_sgd:
                        continue

                    try:
                        rate = base_to_sgd / foreign_to_sgd

                        currency = self.env['res.currency'].sudo().search(
                            [('name', '=', currency_code)], limit=1
                        )
                        if not currency:
                            continue

                        exists = self.env['res.currency.rate'].sudo().search([
                            ('currency_id', '=', currency.id),
                            ('name', '=', today),
                            ('company_id', '=', company.id),
                        ], limit=1)

                        if not exists:
                            self.env['res.currency.rate'].sudo().create({
                                'currency_id': currency.id,
                                'rate': rate,
                                'name': today,
                                'company_id': company.id,
                            })

                    except Exception as err:
                        error_msgs.append(f"{currency_code}: {str(err)}")

                if error_msgs:
                    self.env['currency.log'].sudo().create({
                        'name': f'MAS API Sync - {today}',
                        'status': 'fail',
                        'status_code': status_code,
                        'json_data': json.dumps(rates, indent=4),
                        'message': "\n".join(error_msgs),
                        'company_id': company.id,
                    })

        except Exception as e:
            _logger.exception("MAS currency update failed with exception: %s", str(e))
            for company in companies:
                self.env['currency.log'].sudo().create({
                    'name': f'MAS API Sync - {today}',
                    'status': 'fail',
                    'status_code': None,
                    'json_data': '',
                    'message': f"Exception occurred: {str(e)}",
                    'company_id': company.id,
                })

