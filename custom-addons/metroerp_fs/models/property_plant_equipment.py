# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
import datetime
from datetime import datetime
from odoo.exceptions import ValidationError, UserError
import random
import string

class PlantEquipmentCost(models.Model):
    _name = 'plant.equipment.cost'
    _description = 'Plant Equipment Cost'

    @api.depends(
        'computer_cost',
        'furniture_fittings_cost',
        'office_equipment_cost',
        'renovation_cost',
        'motor_vehicle_cost',
        'software_cost',
        'property_cost',
        'leasehold_building_cost',
        'machinery_cost',
        'it_equipment_cost')
    def _compute_cost_balances(self):
        print('\n\n\n\n\n\n_compute_cost_balances', self)
        def format_float_custom(value):
            if value == 0:
                return '-'
            elif value < 0:
                formatted_value = f"({abs(value):,})"
            else:
                formatted_value = f"{value:,}"
            return formatted_value

        for obj in self:
            obj.computer_vl = format_float_custom(obj.computer_cost)
            obj.furniture_fittings_vl = format_float_custom(obj.furniture_fittings_cost)
            obj.office_equipment_vl = format_float_custom(obj.office_equipment_cost)
            obj.renovation_vl = format_float_custom(obj.renovation_cost)
            obj.motor_vehicle_vl = format_float_custom(obj.motor_vehicle_cost)
            obj.software_vl = format_float_custom(obj.software_cost)
            obj.property_vl = format_float_custom(obj.property_cost)
            obj.leasehold_building_vl = format_float_custom(obj.leasehold_building_cost)
            obj.machinery_vl = format_float_custom(obj.machinery_cost)
            obj.it_equipment_vl = format_float_custom(obj.it_equipment_cost)

    statement_id = fields.Many2one('director.statement')
    name = fields.Char('Name')
    computer_cost = fields.Integer(string='Computer (S$)')
    furniture_fittings_cost = fields.Integer(string='Furniture & Fittings Cost (S$)')
    office_equipment_cost = fields.Integer(string='Office Equipment (S$)')
    renovation_cost = fields.Integer(string='Renovation (S$)')
    motor_vehicle_cost = fields.Integer(string='Motor Vehicle (S$)')
    software_cost = fields.Integer(string='Software (S$)')
    property_cost = fields.Integer(string='Property (S$)')
    leasehold_building_cost = fields.Integer(string='Leaseh Old Building (S$)')
    machinery_cost = fields.Integer(string='Machinery (S$)')
    it_equipment_cost = fields.Integer(string='It Equipment (S$)')
    total_cost = fields.Integer(string='Total (S$)')

    computer_vl = fields.Char(compute=_compute_cost_balances, string='Computer')
    furniture_fittings_vl = fields.Char(compute=_compute_cost_balances, string='Furniture & Fittings Cost')
    office_equipment_vl = fields.Char(compute=_compute_cost_balances, string='Office Equipment')
    renovation_vl = fields.Char(compute=_compute_cost_balances, string='Renovation')
    motor_vehicle_vl = fields.Char(compute=_compute_cost_balances, string='Motor Vehicle')
    software_vl = fields.Char(compute=_compute_cost_balances, string='Software')
    property_vl = fields.Char(compute=_compute_cost_balances, string='Property')
    leasehold_building_vl = fields.Char(compute=_compute_cost_balances, string='Leaseh Old Building')
    machinery_vl = fields.Char(compute=_compute_cost_balances, string='Machinery')
    it_equipment_vl = fields.Char(compute=_compute_cost_balances, string='It Equipment')

class PlantEquipmentDepreciation(models.Model):
    _name = 'plant.equipment.depreciation'
    _description = 'Plant Equipment Depreciation'

    @api.depends(
        'computer_depreciation',
        'furniture_fittings_depreciation',
        'office_equipment_depreciation',
        'renovation_depreciation',
        'motor_vehicle_depreciation',
        'software_depreciation',
        'property_depreciation',
        'leasehold_building_depreciation',
        'machinery_depreciation',
        'it_equipment_depreciation')
    def _compute_depreciation_balances(self):
        def format_float_custom(value):
            if value == 0:
                return '-'
            elif value < 0:
                formatted_value = f"({abs(value):,})"
            else:
                formatted_value = f"{value:,}"
            return formatted_value

        for obj in self:
            obj.computer_vl = format_float_custom(obj.computer_depreciation)
            obj.furniture_fittings_vl = format_float_custom(obj.furniture_fittings_depreciation)
            obj.office_equipment_vl = format_float_custom(obj.office_equipment_depreciation)
            obj.renovation_vl = format_float_custom(obj.renovation_depreciation)
            obj.motor_vehicle_vl = format_float_custom(obj.motor_vehicle_depreciation)
            obj.software_vl = format_float_custom(obj.software_depreciation)
            obj.property_vl = format_float_custom(obj.property_depreciation)
            obj.leasehold_building_vl = format_float_custom(obj.leasehold_building_depreciation)
            obj.machinery_vl = format_float_custom(obj.machinery_depreciation)
            obj.it_equipment_vl = format_float_custom(obj.it_equipment_depreciation)

    statement_id = fields.Many2one('director.statement')
    name = fields.Char('Name')
    computer_depreciation = fields.Integer(string='Computer (S$)')
    furniture_fittings_depreciation = fields.Integer(string='Furniture & Fittings Cost (S$)')
    office_equipment_depreciation = fields.Integer(string='Office Equipment (S$)')
    renovation_depreciation = fields.Integer(string='Renovation (S$)')
    motor_vehicle_depreciation = fields.Integer(string='Motor Vehicle (S$)')
    software_depreciation = fields.Integer(string='Software (S$)')
    property_depreciation = fields.Integer(string='Property (S$)')
    leasehold_building_depreciation = fields.Integer(string='Leaseh Old Building (S$)')
    machinery_depreciation = fields.Integer(string='Machinery (S$)')
    it_equipment_depreciation = fields.Integer(string='It Equipment (S$)')
    total_depreciation = fields.Integer(string='Total (S$)')


    computer_vl = fields.Char(compute=_compute_depreciation_balances, string='Computer')
    furniture_fittings_vl = fields.Char(compute=_compute_depreciation_balances, string='Furniture & Fittings Cost')
    office_equipment_vl = fields.Char(compute=_compute_depreciation_balances, string='Office Equipment')
    renovation_vl = fields.Char(compute=_compute_depreciation_balances, string='Renovation')
    motor_vehicle_vl = fields.Char(compute=_compute_depreciation_balances, string='Motor Vehicle')
    software_vl = fields.Char(compute=_compute_depreciation_balances, string='Software')
    property_vl = fields.Char(compute=_compute_depreciation_balances, string='Property')
    leasehold_building_vl = fields.Char(compute=_compute_depreciation_balances, string='Leaseh Old Building')
    machinery_vl = fields.Char(compute=_compute_depreciation_balances, string='Machinery')
    it_equipment_vl = fields.Char(compute=_compute_depreciation_balances, string='It Equipment')

class PlantEquipmentCarryingAmount(models.Model):
    _name = 'plant.equipment.carrying.amount'
    _description = 'Plant Equipment Carrying Amount'

    @api.depends(
        'computer_carryamount',
        'furniture_fittings_carryamount',
        'office_equipment_carryamount',
        'renovation_carryamount',
        'motor_vehicle_carryamount',
        'software_carryamount',
        'property_carryamount',
        'leasehold_building_carryamount',
        'machinery_carryamount',
        'it_equipment_carryamount')
    def _compute_carryingamount_balances(self):
        def format_float_custom(value):
            if value == 0:
                return '-'
            elif value < 0:
                formatted_value = f"({abs(value):,})"
            else:
                formatted_value = f"{value:,}"
            return formatted_value

        for obj in self:
            obj.computer_vl = format_float_custom(obj.computer_carryamount)
            obj.furniture_fittings_vl = format_float_custom(obj.furniture_fittings_carryamount)
            obj.office_equipment_vl = format_float_custom(obj.office_equipment_carryamount)
            obj.renovation_vl = format_float_custom(obj.renovation_carryamount)
            obj.motor_vehicle_vl = format_float_custom(obj.motor_vehicle_carryamount)
            obj.software_vl = format_float_custom(obj.software_carryamount)
            obj.property_vl = format_float_custom(obj.property_carryamount)
            obj.leasehold_building_vl = format_float_custom(obj.leasehold_building_carryamount)
            obj.machinery_vl = format_float_custom(obj.machinery_carryamount)
            obj.it_equipment_vl = format_float_custom(obj.it_equipment_carryamount)

    statement_id = fields.Many2one('director.statement')
    name = fields.Char('Name')
    computer_carryamount = fields.Integer(string='Computer (S$)')
    furniture_fittings_carryamount = fields.Integer(string='Furniture & Fittings Cost (S$)')
    office_equipment_carryamount = fields.Integer(string='Office Equipment (S$)')
    renovation_carryamount = fields.Integer(string='Renovation (S$)')
    motor_vehicle_carryamount = fields.Integer(string='Motor Vehicle (S$)')
    software_carryamount = fields.Integer(string='Software (S$)')
    property_carryamount = fields.Integer(string='Property (S$)')
    leasehold_building_carryamount = fields.Integer(string='Leaseh Old Building (S$)')
    machinery_carryamount = fields.Integer(string='Machinery (S$)')
    it_equipment_carryamount = fields.Integer(string='It Equipment (S$)')
    total_carryamount = fields.Integer(string='Total (S$)')


    computer_vl = fields.Char(compute=_compute_carryingamount_balances, string='Computer')
    furniture_fittings_vl = fields.Char(compute=_compute_carryingamount_balances, string='Furniture & Fittings Cost')
    office_equipment_vl = fields.Char(compute=_compute_carryingamount_balances, string='Office Equipment')
    renovation_vl = fields.Char(compute=_compute_carryingamount_balances, string='Renovation')
    motor_vehicle_vl = fields.Char(compute=_compute_carryingamount_balances, string='Motor Vehicle')
    software_vl = fields.Char(compute=_compute_carryingamount_balances, string='Software')
    property_vl = fields.Char(compute=_compute_carryingamount_balances, string='Property')
    leasehold_building_vl = fields.Char(compute=_compute_carryingamount_balances, string='Leaseh Old Building')
    machinery_vl = fields.Char(compute=_compute_carryingamount_balances, string='Machinery')
    it_equipment_vl = fields.Char(compute=_compute_carryingamount_balances, string='It Equipment')

