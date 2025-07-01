# Copyright 2023 Tecnativa - Sergio Teruel
# Enhanced validation and error handling for barcode actions
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).
import logging
import traceback
from odoo import api, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo.tools.safe_eval import safe_eval

_logger = logging.getLogger(__name__)


class StockBarcodesActionEnhanced(models.Model):
    _inherit = "stock.barcodes.action"

    def validate_general_prerequisites(self):
        """Validar prerrequisitos generales del sistema de códigos de barras"""
        try:
            _logger.info("Iniciando validación de prerrequisitos generales")
            
            # Verificar que el usuario tenga permisos
            if not self.env.user.has_group('stock.group_stock_user'):
                _logger.warning("Usuario sin permisos de stock")
                return False
            
            # Verificar configuración básica
            company = self.env.company
            if not company:
                _logger.error("No se encontró compañía")
                return False
            
            # Verificar módulos requeridos
            required_modules = ['stock_barcodes', 'stock']
            for module in required_modules:
                if not self.env['ir.module.module'].search([('name', '=', module), ('state', '=', 'installed')]):
                    _logger.error(f"Módulo requerido no instalado: {module}")
                    return False
            
            # Verificar configuración de almacenes
            warehouses = self.env['stock.warehouse'].search([])
            if not warehouses:
                _logger.error("No se encontraron almacenes configurados")
                return False
            
            _logger.info("Prerrequisitos generales validados correctamente")
            return True
            
        except Exception as e:
            _logger.error(f"Error validando prerrequisitos generales: {e}")
            return False

    def _validate_action_prerequisites(self):
        """Validate prerequisites before opening any barcode action"""
        _logger.info("=== VALIDATING BARCODE ACTION PREREQUISITES ===")
        
        # Check if action window exists
        if not self.action_window_id:
            error_msg = f"No action window defined for barcode action '{self.name}'"
            _logger.error(error_msg)
            raise ValidationError(error_msg)
        
        # Check if action window is accessible
        try:
            action_data = self.action_window_id.sudo().read(['name', 'res_model', 'context'])
            _logger.info(f"Action window data: {action_data}")
        except Exception as e:
            error_msg = f"Error reading action window for '{self.name}': {str(e)}"
            _logger.error(error_msg)
            raise ValidationError(error_msg)
        
        # Check user permissions
        if not self.env.user.has_group('stock.group_stock_user'):
            error_msg = "User does not have stock user permissions"
            _logger.error(error_msg)
            raise UserError(error_msg)
        
        _logger.info("Prerequisites validation passed")
        return True

    def validate_inventory_prerequisites(self):
        """Validar prerrequisitos específicos para acciones de inventario"""
        try:
            _logger.info("Validando prerrequisitos de inventario")
            
            # Verificar permisos específicos de inventario
            if not self.env.user.has_group('stock.group_stock_manager'):
                _logger.warning("Usuario sin permisos de gestión de inventario")
            
            # Verificar grupo de opciones de inventario
            option_group = self.env['stock.barcodes.option.group'].search([('name', '=', 'Inventory options')], limit=1)
            if not option_group:
                _logger.error("No se encontró grupo de opciones de inventario")
                return False, None
            
            # Verificar que el grupo tenga configuración válida
            if not hasattr(option_group, 'name') or not option_group.name:
                _logger.error("Grupo de opciones de inventario sin nombre válido")
                return False, None
            
            # Verificar almacén por defecto
            warehouse = self.env['stock.warehouse'].search([], limit=1)
            if not warehouse:
                _logger.error("No se encontró almacén")
                return False, None
            
            # Verificar ubicaciones de stock
            stock_locations = warehouse.lot_stock_id
            if not stock_locations:
                _logger.error(f"Almacén {warehouse.name} sin ubicaciones de stock")
                return False, None
            
            # Verificar modelo de wizard (opcional)
            try:
                # Intentar acceder al modelo de wizard si existe
                if 'wiz.stock.barcodes.read.inventory' in self.env:
                    wizard_model = self.env['wiz.stock.barcodes.read.inventory']
                    _logger.info("Modelo de wizard de inventario disponible")
                else:
                    _logger.info("Modelo de wizard de inventario no disponible, continuando sin él")
            except Exception as model_error:
                _logger.warning(f"Advertencia accediendo al modelo de wizard: {model_error}")
                # No retornar False aquí, ya que el wizard puede ser opcional
            
            _logger.info(f"Prerrequisitos de inventario validados. Grupo: {option_group.name}, Almacén: {warehouse.name}")
            return True, option_group
            
        except Exception as e:
            _logger.error(f"Error validando prerrequisitos de inventario: {e}")
            return False, None

    def open_action(self):
        """Enhanced open_action with detailed validation and error handling"""
        _logger.info(f"=== OPENING BARCODE ACTION: {self.name} ===")
        
        try:
            # Validate general prerequisites
            self._validate_action_prerequisites()
            
            # Get action data with enhanced error handling
            try:
                action = self.action_window_id.sudo().read()[0]
                _logger.info(f"Action data retrieved: {action.get('name', 'Unknown')}")
            except Exception as e:
                error_msg = f"Failed to read action window data: {str(e)}"
                _logger.error(error_msg)
                raise ValidationError(error_msg)
            
            # Process action context with validation
            try:
                action_context = safe_eval(action.get("context", "{}"))
                _logger.info(f"Action context: {action_context}")
            except Exception as e:
                error_msg = f"Invalid action context format: {str(e)}"
                _logger.error(error_msg)
                raise ValidationError(error_msg)
            
            # Build final context
            ctx = self.env.context.copy()
            if action_context:
                ctx.update(action_context)
            if self.context:
                try:
                    custom_context = safe_eval(self.context)
                    ctx.update(custom_context)
                    _logger.info(f"Custom context applied: {custom_context}")
                except Exception as e:
                    error_msg = f"Invalid custom context format: {str(e)}"
                    _logger.error(error_msg)
                    raise ValidationError(error_msg)
            
            # Check if this is an inventory action
            if action_context.get("inventory_mode", False):
                _logger.info("Detected inventory mode - routing to inventory action")
                return self.open_inventory_action_enhanced(ctx)
            
            # Return standard action
            action["context"] = ctx
            _logger.info(f"Standard action opened successfully: {action.get('name')}")
            return action
            
        except (UserError, ValidationError):
            # Re-raise user/validation errors as-is
            raise
        except Exception as e:
            # Log unexpected errors with full traceback
            error_msg = f"Unexpected error opening barcode action '{self.name}': {str(e)}"
            _logger.error(f"{error_msg}\n{traceback.format_exc()}")
            raise UserError(f"Error opening barcode interface: {str(e)}")

    def open_inventory_action_enhanced(self, ctx):
        """Enhanced inventory action with detailed validation"""
        _logger.info("=== OPENING ENHANCED INVENTORY ACTION ===")
        
        try:
            # Validate inventory-specific prerequisites
            is_valid, option_group = self.validate_inventory_prerequisites()
            if not is_valid or not option_group:
                error_msg = "Failed inventory prerequisites validation"
                _logger.error(error_msg)
                raise ValidationError(error_msg)
            
            _logger.info(f"Using option group: {option_group.name}")
            
            # Prepare wizard values with validation
            vals = {
                "option_group_id": option_group.id,
                "manual_entry": False,
                "display_read_quant": False,
            }
            _logger.info(f"Base wizard values: {vals}")
            
            # Set default location if configured
            try:
                warehouse = self.env["stock.warehouse"].search([], limit=1)
                if warehouse and warehouse.lot_stock_id:
                    vals["location_id"] = warehouse.lot_stock_id.id
                    _logger.info(f"Default location set: {warehouse.lot_stock_id.name}")
                else:
                    _logger.warning("No warehouse or stock location found for default location")
            except Exception as e:
                _logger.error(f"Error setting default location: {str(e)}")
                # Continue without default location
            
            # Create wizard with error handling
            try:
                wiz = self.env["wiz.stock.barcodes.read.inventory"].create(vals)
                _logger.info(f"Inventory wizard created successfully: ID {wiz.id}")
            except Exception as e:
                error_msg = f"Failed to create inventory wizard: {str(e)}"
                _logger.error(error_msg)
                raise ValidationError(error_msg)
            
            # Get action with validation
            try:
                action = self.env["ir.actions.actions"]._for_xml_id(
                    "stock_barcodes.action_stock_barcodes_read_inventory"
                )
                _logger.info("Inventory action template retrieved")
            except Exception as e:
                error_msg = f"Failed to get inventory action template: {str(e)}"
                _logger.error(error_msg)
                raise ValidationError(error_msg)
            
            # Configure final action
            action["res_id"] = wiz.id
            action["context"] = ctx
            
            _logger.info(f"Inventory action opened successfully - Wizard ID: {wiz.id}")
            return action
            
        except (UserError, ValidationError):
            # Re-raise user/validation errors as-is
            raise
        except Exception as e:
            # Log unexpected errors with full traceback
            error_msg = f"Unexpected error opening inventory action: {str(e)}"
            _logger.error(f"{error_msg}\n{traceback.format_exc()}")
            raise UserError(f"Error opening inventory interface: {str(e)}")

    @api.model
    def validate_barcode_system_health(self):
        """Comprehensive system health check for barcode functionality"""
        _logger.info("=== BARCODE SYSTEM HEALTH CHECK ===")
        
        issues = []
        
        # Check barcode actions
        try:
            actions = self.search([])
            _logger.info(f"Found {len(actions)} barcode actions")
            for action in actions:
                if not action.action_window_id:
                    issues.append(f"Action '{action.name}' has no action window")
        except Exception as e:
            issues.append(f"Error checking barcode actions: {str(e)}")
        
        # Check inventory option group
        try:
            option_group = self.env.ref(
                "stock_barcodes.stock_barcodes_option_group_inventory", 
                raise_if_not_found=False
            )
            if not option_group:
                issues.append("Inventory option group not found")
        except Exception as e:
            issues.append(f"Error checking inventory option group: {str(e)}")
        
        # Check warehouse configuration
        try:
            warehouses = self.env["stock.warehouse"].search([])
            if not warehouses:
                issues.append("No warehouses configured")
            else:
                for warehouse in warehouses:
                    if not warehouse.lot_stock_id:
                        issues.append(f"Warehouse '{warehouse.name}' has no stock location")
        except Exception as e:
            issues.append(f"Error checking warehouses: {str(e)}")
        
        # Check wizard models
        try:
            self.env["wiz.stock.barcodes.read.inventory"]
        except Exception as e:
            issues.append(f"Inventory wizard model not accessible: {str(e)}")
        
        if issues:
            _logger.error(f"Barcode system health check found {len(issues)} issues:")
            for issue in issues:
                _logger.error(f"  - {issue}")
            return False, issues
        else:
            _logger.info("Barcode system health check passed")
            return True, []