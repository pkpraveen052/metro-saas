# Copyright (C) 2019 Open Source Integrators
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
import re
from odoo import fields, models
from odoo.exceptions import UserError,ValidationError

class FSMLocationBuilderWizard(models.TransientModel):
    _name = "fsm.location.builder.wizard"
    _description = "FSM Location Builder Wizard"
    
    level_ids = fields.One2many("fsm.location.level", "wizard_id", string="Level ID's")

    def create_sub_locations(self):
        levels = len(self.level_ids) - 1
        location = self.env["block.location"].browse(self.env.context.get("active_id"))

        def build_location(parent, num):
            spacer = " " + self.level_ids[num].spacer + " " if self.level_ids[num].spacer else " "
            
            # Fetch and sanitize the custom suffixes for the current level
            custom_suffixes = str(self.level_ids[num].custom_suffixes or '').strip()
            # Split the suffix string by commas and spaces, removing any extraneous characters
            suffix_list = [suffix.strip() for suffix in re.split(r'[,\s]+', custom_suffixes) if suffix.strip()]

            # Calculate the total number of buildings to create
            total_buildings = self.level_ids[num].end_number - self.level_ids[num].start_number + 1

            # Ensure there are enough suffixes for the number of buildings
            if len(suffix_list) < total_buildings:
                raise ValidationError(f"Not enough custom suffixes provided. Expected {total_buildings}, but got {len(suffix_list)}. Please provide enough suffixes.")

            # If there are extra suffixes, truncate them to match the number of buildings
            suffix_list = suffix_list[:total_buildings]

            # Create the buildings using the provided suffixes
            for i, lev_id in enumerate(range(self.level_ids[num].start_number, self.level_ids[num].end_number + 1)):
                suffix = suffix_list[i]  # Get the corresponding suffix
                vals = self.prepare_fsm_location_values(location, parent, spacer, suffix, num)
                new_location = self.env["block.location"].create(vals)

                # Recursively create sub-locations if more levels exist
                if num < levels:
                    build_location(new_location, num + 1)

        # Start the recursive creation process
        build_location(location, 0)


    def prepare_fsm_location_values(self, location, parent, spacer, suffix, num):
        # Construct the location name, including the suffix and level information
        location_name = f"{self.level_ids[num].name} {spacer} {suffix}"
        
        vals = {
            "name": location_name,
            "fsm_parent_id": parent.id,
            "security_location_id": location.security_location_id.id,
            # Additional location details can be added here
        }
        # Debugging: Output the values prepared for each location
        print(f"Prepared location values: {vals}")

        return vals