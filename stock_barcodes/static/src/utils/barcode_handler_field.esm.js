/** @odoo-module **/
import {BarcodeHandlerField} from "@barcodes/barcode_handler_field";
import {patch} from "@web/core/utils/patch";
import {useService} from "@web/core/utils/hooks";
import {useEffect} from "@odoo/owl";
import { standardFieldProps } from "@web/views/fields/standard_field_props";
import { registry } from "@web/core/registry";

// CRITICAL FIX: Store original props internally per instance and provide safe access
// This prevents template rendering errors in Odoo 17 while allowing OWL to set props
// Using WeakMap to avoid conflicts between multiple component instances
const _instanceProps = new WeakMap();

patch(BarcodeHandlerField.prototype, {
    // Override props getter/setter to ensure props are always valid
    setup(){
        // Call the original setup method to ensure proper initialization
        super.setup();
        console.log(this);
        
    },
    get props() {
        try {
            // Return internal props if available for this instance, otherwise create safe defaults
            const internalProps = _instanceProps.get(this);
            if (internalProps) {
                return internalProps;
            }
            
            // If no internal props, try to get from parent or create minimal structure
            let parentProps;
            try {
                parentProps = super.props;
            } catch (error) {
                console.warn("BarcodeHandlerField: Error accessing super.props:", error);
                parentProps = null;
            }
            
            if (!parentProps) {
                console.warn("BarcodeHandlerField: props is undefined, creating minimal structure");
                const defaultProps = {
                    name: '_barcode_scanned',
                    type: 'char',
                    readonly: false,
                    record: { resModel: '' },
                    value: '',
                    id: '_barcode_scanned'
                };
                // Store the default props for this instance
                _instanceProps.set(this, defaultProps);
                return defaultProps;
            }
            
            // Ensure all required props exist with safe defaults
            const safeProps = {
                name: parentProps.name || '_barcode_scanned',
                type: parentProps.type || 'char',
                readonly: parentProps.readonly !== undefined ? parentProps.readonly : false,
                record: parentProps.record || { resModel: '' },
                value: parentProps.value !== undefined ? parentProps.value : '',
                id: parentProps.id || parentProps.name || '_barcode_scanned',
                ...parentProps  // Preserve any other existing props
            };
            
            // Ensure record has required properties
            if (!safeProps.record || !safeProps.record.resModel) {
                safeProps.record = { ...safeProps.record, resModel: '' };
            }
            
            // Store the safe props for this instance
            _instanceProps.set(this, safeProps);
            return safeProps;
        } catch (error) {
            console.error("BarcodeHandlerField: Critical error in props getter:", error);
            // Return absolute minimal props to prevent complete failure
            const emergencyProps = {
                name: '_barcode_scanned',
                type: 'char',
                readonly: false,
                record: { resModel: '' },
                value: '',
                id: '_barcode_scanned'
            };
            _instanceProps.set(this, emergencyProps);
            return emergencyProps;
        }
    },
    
    set props(value) {
        // Store props internally per instance and allow OWL to set them
        _instanceProps.set(this, value);
        // Also call parent setter if it exists
        if (super.props !== undefined) {
            try {
                super.props = value;
            } catch (error) {
                // If parent setter fails, just store internally
                console.warn("Could not set parent props, storing internally:", error);
            }
        }
    },
    
    /* eslint-disable no-unused-vars */
    setup() {
        // Now it's safe to call super.setup() because props getter ensures valid props
        super.setup();
        
        // Initialize services with proper error handling to prevent FormController conflicts
        // The 'methods is not iterable' error can occur when useService is called incorrectly
        this.busService = null;
        this.orm = null;
        
        try {
            // Only initialize services if we're in a proper component context
            if (this.env && this.env.services) {
                this.busService = useService("bus_service");
                this.orm = useService("orm");
            } else {
                console.warn("BarcodeHandlerField: Services not available in current context");
                return;
            }
        } catch (error) {
            console.error("Error initializing services in BarcodeHandlerField:", error);
            // Don't return here, continue with setup but without services
        }
        // Only set up bus service listeners if service is available
        if (this.busService) {
            const notifyChanges = async ({detail: notifications}) => {
                for (const {payload, type} of notifications) {
                    if (type === "stock_barcodes_refresh_data") {
                        // Add validation to prevent 'Cannot read properties of undefined' errors
                        if (this.env && this.env.model && this.env.model.root) {
                            await this.env.model.root.load();
                            this.env.model.notify();
                        }
                    }
                }
            };
            useEffect(() => {
                this.busService.addChannel("barcode_reload");
                this.busService.addEventListener("notification", notifyChanges);
                return () => {
                    this.busService.deleteChannel("barcode_reload");
                    this.busService.removeEventListener("notification", notifyChanges);
                };
            });
        }
    },
    onBarcodeScanned(event) {
        try {
            super.onBarcodeScanned(event);
        } catch (error) {
            console.error("Error in super.onBarcodeScanned:", error);
        }
        
        // Comprehensive validation to prevent 'Cannot read properties of undefined' errors
        if (!this.props) {
            console.error("onBarcodeScanned: props is undefined");
            return;
        }
        
        if (!this.props.record) {
            console.error("onBarcodeScanned: record is undefined");
            return;
        }
        
        if (!this.props.record.resModel) {
            console.warn("onBarcodeScanned: resModel is undefined");
            return;
        }
        
        if (typeof this.props.record.resModel === 'string' && 
            this.props.record.resModel.includes("wiz.stock.barcodes.read")) {
            try {
                $("#dummy_on_barcode_scanned").click();
            } catch (error) {
                console.error("Error clicking dummy_on_barcode_scanned:", error);
            }
        }
    },
});

// Re-register the patched widget to ensure it uses the safe props implementation
registry.category("fields").add("barcode_handler", BarcodeHandlerField, { force: true });
