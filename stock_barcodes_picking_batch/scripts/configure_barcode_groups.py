#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para configurar grupos de opciones de código de barras usando Odoo shell
Ejecutar con: python3 /path/to/odoo-bin shell -d odoo17 --shell-interface python3 < configure_barcode_groups.py
"""

# Configuración de grupos de opciones por tipo de operación
operation_mappings = {
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

print("=== CONFIGURANDO GRUPOS DE OPCIONES DE CÓDIGO DE BARRAS ===")

try:
    # Obtener tipos de operación sin grupos de opciones
    OperationType = env['stock.picking.type']
    BarcodeOptionGroup = env['wiz.stock.barcodes.read.picking.option.group']
    
    operation_types = OperationType.search([
        ('barcode_option_group_id', '=', False)
    ])
    
    print(f"Encontrados {len(operation_types)} tipos de operación sin grupos de opciones")
    
    configured_count = 0
    
    for op_type in operation_types:
        try:
            print(f"Configurando: {op_type.name} (Código: {op_type.code})")
            
            # Determinar configuración según el código del tipo de operación
            config = operation_mappings.get(op_type.code, operation_mappings['internal'])
            
            # Buscar grupo existente o crear uno nuevo
            group_name = f"{op_type.name} - {config['name']}"
            existing_group = BarcodeOptionGroup.search([
                ('name', '=', group_name)
            ], limit=1)
            
            if existing_group:
                print(f"Usando grupo existente: {group_name}")
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
                print(f"Creado nuevo grupo: {group_name}")
            
            # Asignar grupo al tipo de operación
            op_type.write({
                'barcode_option_group_id': option_group.id
            })
            
            configured_count += 1
            print(f"✓ Configurado exitosamente: {op_type.name}")
            
        except Exception as e:
            print(f"✗ Error configurando {op_type.name}: {e}")
            continue
    
    # Confirmar cambios
    env.cr.commit()
    
    print(f"\n=== CONFIGURACIÓN COMPLETADA ===")
    print(f"Tipos de operación configurados: {configured_count}/{len(operation_types)}")
    
    # Verificar configuración
    print("\n=== VERIFICANDO CONFIGURACIÓN ===")
    
    configured_types = OperationType.search([
        ('barcode_option_group_id', '!=', False)
    ])
    
    unconfigured_types = OperationType.search([
        ('barcode_option_group_id', '=', False)
    ])
    
    print(f"Tipos de operación configurados: {len(configured_types)}")
    for op_type in configured_types:
        print(f"  ✓ {op_type.name}: {op_type.barcode_option_group_id.name}")
    
    if unconfigured_types:
        print(f"\nTipos de operación sin configurar: {len(unconfigured_types)}")
        for op_type in unconfigured_types:
            print(f"  ⚠ {op_type.name} (Código: {op_type.code})")
    else:
        print("\n✓ Todos los tipos de operación están configurados")
        
except Exception as e:
    print(f"Error en el proceso: {e}")
    import traceback
    traceback.print_exc()

print("\n=== PROCESO COMPLETADO ===")