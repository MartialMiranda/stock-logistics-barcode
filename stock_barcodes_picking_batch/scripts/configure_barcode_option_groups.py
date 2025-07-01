#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para configurar automáticamente los grupos de opciones de código de barras
para los tipos de operación que no los tienen configurados.

Este script:
1. Identifica tipos de operación sin grupos de opciones de código de barras
2. Crea o asigna grupos de opciones apropiados según el tipo de operación
3. Configura las opciones de código de barras por defecto
"""

import os
import sys
import logging
from datetime import datetime

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('barcode_configuration.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def setup_odoo_environment():
    """Configurar el entorno de Odoo"""
    try:
        # Agregar el directorio de Odoo al path
        odoo_path = '/home/administrator/Projects/Odoo/v17'
        if odoo_path not in sys.path:
            sys.path.insert(0, odoo_path)
        
        # Configurar variables de entorno
        os.environ['ODOO_RC'] = '/etc/odoo/odoo.conf'
        
        # Importar Odoo
        import odoo
        from odoo import api, registry
        
        # Configurar la base de datos
        odoo.tools.config.parse_config()
        odoo.tools.config['db_name'] = 'odoo17'
        
        logger.info("Entorno de Odoo configurado correctamente")
        return True
    except Exception as e:
        logger.error(f"Error configurando entorno de Odoo: {e}")
        return False

def get_operation_type_mappings():
    """Definir mapeos de tipos de operación a configuraciones de código de barras"""
    return {
        'incoming': {
            'name': 'Recepción - Opciones de Código de Barras',
            'manual_entry': True,
            'display_read_quant': True,
            'create_lot': True,
            'confirm_done': True,
        },
        'outgoing': {
            'name': 'Entrega - Opciones de Código de Barras',
            'manual_entry': True,
            'display_read_quant': True,
            'create_lot': False,
            'confirm_done': True,
        },
        'internal': {
            'name': 'Transferencia Interna - Opciones de Código de Barras',
            'manual_entry': True,
            'display_read_quant': True,
            'create_lot': False,
            'confirm_done': False,
        },
        'mrp_operation': {
            'name': 'Fabricación - Opciones de Código de Barras',
            'manual_entry': True,
            'display_read_quant': True,
            'create_lot': True,
            'confirm_done': False,
        }
    }

def configure_barcode_option_groups():
    """Configurar grupos de opciones de código de barras para tipos de operación"""
    try:
        import odoo
        from odoo import api, registry
        
        # Obtener registro de la base de datos
        db_registry = registry(odoo.tools.config['db_name'])
        
        with db_registry.cursor() as cr:
            env = api.Environment(cr, 1, {})
            
            # Obtener modelos
            OperationType = env['stock.picking.type']
            BarcodeOptionGroup = env['wiz.stock.barcodes.read.picking.option.group']
            
            # Obtener mapeos de configuración
            mappings = get_operation_type_mappings()
            
            logger.info("=== CONFIGURANDO GRUPOS DE OPCIONES DE CÓDIGO DE BARRAS ===")
            
            # Buscar tipos de operación sin grupos de opciones
            operation_types = OperationType.search([
                ('barcode_option_group_id', '=', False)
            ])
            
            logger.info(f"Encontrados {len(operation_types)} tipos de operación sin grupos de opciones")
            
            configured_count = 0
            
            for op_type in operation_types:
                try:
                    logger.info(f"Configurando tipo de operación: {op_type.name} (Código: {op_type.code})")
                    
                    # Determinar configuración según el código del tipo de operación
                    config = mappings.get(op_type.code, mappings['internal'])
                    
                    # Buscar grupo existente o crear uno nuevo
                    group_name = f"{op_type.name} - {config['name']}"
                    existing_group = BarcodeOptionGroup.search([
                        ('name', '=', group_name)
                    ], limit=1)
                    
                    if existing_group:
                        logger.info(f"Usando grupo existente: {group_name}")
                        option_group = existing_group
                    else:
                        # Crear nuevo grupo de opciones
                        group_vals = {
                            'name': group_name,
                            'manual_entry': config['manual_entry'],
                            'display_read_quant': config['display_read_quant'],
                            'create_lot': config['create_lot'],
                            'confirm_done': config['confirm_done'],
                        }
                        
                        option_group = BarcodeOptionGroup.create(group_vals)
                        logger.info(f"Creado nuevo grupo: {group_name}")
                    
                    # Asignar grupo al tipo de operación
                    op_type.write({
                        'barcode_option_group_id': option_group.id
                    })
                    
                    configured_count += 1
                    logger.info(f"Configurado exitosamente: {op_type.name}")
                    
                except Exception as e:
                    logger.error(f"Error configurando {op_type.name}: {e}")
                    continue
            
            # Confirmar cambios
            cr.commit()
            
            logger.info(f"=== CONFIGURACIÓN COMPLETADA ===")
            logger.info(f"Tipos de operación configurados: {configured_count}/{len(operation_types)}")
            
            return configured_count
            
    except Exception as e:
        logger.error(f"Error en configuración de grupos de opciones: {e}")
        return 0

def verify_configuration():
    """Verificar la configuración de grupos de opciones"""
    try:
        import odoo
        from odoo import api, registry
        
        db_registry = registry(odoo.tools.config['db_name'])
        
        with db_registry.cursor() as cr:
            env = api.Environment(cr, 1, {})
            
            OperationType = env['stock.picking.type']
            
            logger.info("=== VERIFICANDO CONFIGURACIÓN ===")
            
            # Verificar tipos de operación configurados
            configured_types = OperationType.search([
                ('barcode_option_group_id', '!=', False)
            ])
            
            unconfigured_types = OperationType.search([
                ('barcode_option_group_id', '=', False)
            ])
            
            logger.info(f"Tipos de operación configurados: {len(configured_types)}")
            for op_type in configured_types:
                logger.info(f"  - {op_type.name}: {op_type.barcode_option_group_id.name}")
            
            if unconfigured_types:
                logger.warning(f"Tipos de operación sin configurar: {len(unconfigured_types)}")
                for op_type in unconfigured_types:
                    logger.warning(f"  - {op_type.name} (Código: {op_type.code})")
            else:
                logger.info("✓ Todos los tipos de operación están configurados")
            
            return len(unconfigured_types) == 0
            
    except Exception as e:
        logger.error(f"Error verificando configuración: {e}")
        return False

def main():
    """Función principal"""
    logger.info("=== INICIANDO CONFIGURACIÓN DE GRUPOS DE OPCIONES DE CÓDIGO DE BARRAS ===")
    logger.info(f"Fecha y hora: {datetime.now()}")
    
    # Configurar entorno
    if not setup_odoo_environment():
        logger.error("No se pudo configurar el entorno de Odoo")
        return False
    
    try:
        # Configurar grupos de opciones
        configured_count = configure_barcode_option_groups()
        
        if configured_count > 0:
            logger.info(f"Se configuraron {configured_count} tipos de operación")
        else:
            logger.info("No se encontraron tipos de operación para configurar")
        
        # Verificar configuración
        if verify_configuration():
            logger.info("✓ Configuración completada exitosamente")
            return True
        else:
            logger.warning("⚠ Configuración completada con advertencias")
            return True
            
    except Exception as e:
        logger.error(f"Error en el proceso principal: {e}")
        return False

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)