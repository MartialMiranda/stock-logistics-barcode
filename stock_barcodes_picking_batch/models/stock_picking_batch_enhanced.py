# Copyright 2019 Sergio Teruel <sergio.teruel@tecnativa.com>
# Enhanced validation and error handling for picking batch barcode operations
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
import logging
import traceback
from odoo import models, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class StockPickingBatchEnhanced(models.Model):
    _inherit = "stock.picking.batch"

    def _validate_barcode_scan_prerequisites(self):
        """Validate prerequisites before starting barcode scan for picking batch"""
        _logger.info(f"=== VALIDATING PICKING BATCH BARCODE SCAN: {self.name} ===")
        
        # Check if batch has pickings
        if not self.picking_ids:
            error_msg = f"Picking batch '{self.name}' has no pickings assigned"
            _logger.error(error_msg)
            raise ValidationError(error_msg)
        
        _logger.info(f"Batch has {len(self.picking_ids)} pickings")
        
        # Check if pickings are in valid state
        invalid_pickings = self.picking_ids.filtered(lambda p: p.state not in ['confirmed', 'assigned'])
        if invalid_pickings:
            error_msg = f"Some pickings in batch '{self.name}' are not in valid state: {', '.join(invalid_pickings.mapped('name'))}"
            _logger.error(error_msg)
            raise ValidationError(error_msg)
        
        # Get first picking for validation
        first_picking = self.picking_ids[:1]
        _logger.info(f"First picking: {first_picking.name}, Type: {first_picking.picking_type_code}")
        
        # Check if picking type has barcode option group
        if not first_picking.picking_type_id:
            error_msg = f"First picking '{first_picking.name}' has no picking type defined"
            _logger.error(error_msg)
            raise ValidationError(error_msg)
        
        if not first_picking.picking_type_id.barcode_option_group_id:
            error_msg = f"Picking type '{first_picking.picking_type_id.name}' has no barcode option group configured"
            _logger.error(error_msg)
            raise ValidationError(error_msg)
        
        _logger.info(f"Barcode option group: {first_picking.picking_type_id.barcode_option_group_id.name}")
        
        # Validate locations based on picking type
        if first_picking.picking_type_id.code == "outgoing":
            if not first_picking.location_dest_id:
                error_msg = f"Outgoing picking '{first_picking.name}' has no destination location"
                _logger.error(error_msg)
                raise ValidationError(error_msg)
            _logger.info(f"Destination location: {first_picking.location_dest_id.name}")
        
        if first_picking.picking_type_id.code == "incoming":
            if not first_picking.location_id:
                error_msg = f"Incoming picking '{first_picking.name}' has no source location"
                _logger.error(error_msg)
                raise ValidationError(error_msg)
            _logger.info(f"Source location: {first_picking.location_id.name}")
        
        # Check if wizard model exists
        try:
            self.env["wiz.stock.barcodes.read.picking"]
            _logger.info("Picking barcode wizard model accessible")
        except Exception as e:
            error_msg = f"Picking barcode wizard model not accessible: {str(e)}"
            _logger.error(error_msg)
            raise ValidationError(error_msg)
        
        # Check if action exists
        try:
            action_ref = self.env.ref(
                "stock_barcodes_picking_batch.action_stock_barcodes_read_picking_batch",
                raise_if_not_found=False
            )
            if not action_ref:
                error_msg = "Picking batch barcode action not found. Module may not be properly installed."
                _logger.error(error_msg)
                raise ValidationError(error_msg)
            _logger.info(f"Barcode action found: {action_ref.name}")
        except Exception as e:
            error_msg = f"Error accessing picking batch barcode action: {str(e)}"
            _logger.error(error_msg)
            raise ValidationError(error_msg)
        
        _logger.info("Picking batch barcode scan prerequisites validation passed")
        return True

    def action_barcode_scan(self):
        """Enhanced action_barcode_scan with detailed validation and error handling"""
        _logger.info(f"=== STARTING BARCODE SCAN FOR BATCH: {self.name} ===")
        
        try:
            # Validate prerequisites
            self._validate_barcode_scan_prerequisites()
            
            # Get first picking with validation
            first_picking = self.picking_ids[:1]
            picking_type_code = first_picking.picking_type_code
            option_group = first_picking.picking_type_id.barcode_option_group_id
            
            _logger.info(f"Processing batch with picking type: {picking_type_code}")
            
            # Prepare wizard values with enhanced validation
            vals = {
                "picking_batch_id": self.id,
                "res_model_id": self.env.ref(
                    "stock_picking_batch.model_stock_picking_batch"
                ).id,
                "res_id": self.id,
                "picking_type_code": picking_type_code,
                "option_group_id": option_group.id,
                "picking_mode": "picking_batch",
            }
            
            # Set location values based on picking type
            try:
                if first_picking.picking_type_id.code == "outgoing":
                    if first_picking.location_dest_id:
                        vals["location_dest_id"] = first_picking.location_dest_id.id
                        _logger.info(f"Set destination location: {first_picking.location_dest_id.name}")
                
                if first_picking.picking_type_id.code == "incoming":
                    if first_picking.location_id:
                        vals["location_id"] = first_picking.location_id.id
                        _logger.info(f"Set source location: {first_picking.location_id.name}")
                
                # Apply option group defaults
                if option_group.get_option_value("location_id", "filled_default"):
                    if first_picking.location_id:
                        vals["location_id"] = first_picking.location_id.id
                        _logger.info(f"Applied default source location: {first_picking.location_id.name}")
                
                if option_group.get_option_value("location_dest_id", "filled_default"):
                    if first_picking.location_dest_id:
                        vals["location_dest_id"] = first_picking.location_dest_id.id
                        _logger.info(f"Applied default destination location: {first_picking.location_dest_id.name}")
            
            except Exception as e:
                _logger.error(f"Error setting location values: {str(e)}")
                # Continue without location defaults
            
            _logger.info(f"Wizard values prepared: {vals}")
            
            # Create wizard with error handling
            try:
                wiz = self.env["wiz.stock.barcodes.read.picking"].create(vals)
                _logger.info(f"Picking batch wizard created successfully: ID {wiz.id}")
            except Exception as e:
                error_msg = f"Failed to create picking batch wizard: {str(e)}"
                _logger.error(error_msg)
                raise ValidationError(error_msg)
            
            # Initialize wizard with error handling
            try:
                wiz.determine_todo_action()
                _logger.info("Wizard todo action determined")
                
                wiz.fill_pending_moves()
                _logger.info("Wizard pending moves filled")
            except Exception as e:
                error_msg = f"Error initializing wizard: {str(e)}"
                _logger.error(error_msg)
                raise ValidationError(error_msg)
            
            # Get action with validation
            try:
                action = self.env["ir.actions.act_window"]._for_xml_id(
                    "stock_barcodes_picking_batch.action_stock_barcodes_read_picking_batch"
                )
                action["res_id"] = wiz.id
                _logger.info(f"Barcode scan action prepared successfully - Wizard ID: {wiz.id}")
                return action
            except Exception as e:
                error_msg = f"Failed to get picking batch barcode action: {str(e)}"
                _logger.error(error_msg)
                raise ValidationError(error_msg)
            
        except (UserError, ValidationError):
            # Re-raise user/validation errors as-is
            raise
        except Exception as e:
            # Log unexpected errors with full traceback
            error_msg = f"Unexpected error starting barcode scan for batch '{self.name}': {str(e)}"
            _logger.error(f"{error_msg}\n{traceback.format_exc()}")
            raise UserError(f"Error starting barcode scan: {str(e)}")

    def validate_batch_barcode_system_health(self):
        """Comprehensive health check for picking batch barcode functionality"""
        _logger.info(f"=== BATCH BARCODE SYSTEM HEALTH CHECK: {self.name} ===")
        
        issues = []
        
        # Check batch state
        if self.state not in ['in_progress', 'assigned']:
            issues.append(f"Batch '{self.name}' is in invalid state: {self.state}")
        
        # Check pickings
        if not self.picking_ids:
            issues.append(f"Batch '{self.name}' has no pickings")
        else:
            for picking in self.picking_ids:
                if picking.state not in ['confirmed', 'assigned']:
                    issues.append(f"Picking '{picking.name}' is in invalid state: {picking.state}")
                
                if not picking.picking_type_id:
                    issues.append(f"Picking '{picking.name}' has no picking type")
                elif not picking.picking_type_id.barcode_option_group_id:
                    issues.append(f"Picking type '{picking.picking_type_id.name}' has no barcode option group")
        
        # Check wizard model
        try:
            self.env["wiz.stock.barcodes.read.picking"]
        except Exception as e:
            issues.append(f"Picking wizard model not accessible: {str(e)}")
        
        # Check action
        try:
            self.env.ref(
                "stock_barcodes_picking_batch.action_stock_barcodes_read_picking_batch",
                raise_if_not_found=True
            )
        except Exception as e:
            issues.append(f"Picking batch barcode action not found: {str(e)}")
        
        if issues:
            _logger.error(f"Batch barcode health check found {len(issues)} issues:")
            for issue in issues:
                _logger.error(f"  - {issue}")
            return False, issues
        else:
            _logger.info("Batch barcode health check passed")
            return True, []