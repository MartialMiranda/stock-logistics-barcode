odoo.define('stock_barcodes.utils.barcodes_models_utils', [], function (require) {
    'use strict';
    
    // Models allowed to have extra keybinding features
    const barcodeModels = [
        "stock.barcodes.action",
        "stock.picking",
        "stock.picking.type",
        "wiz.candidate.picking",
        "wiz.stock.barcodes.new.lot",
        "wiz.stock.barcodes.read",
        "wiz.stock.barcodes.read.inventory",
        "wiz.stock.barcodes.read.picking",
        "wiz.stock.barcodes.read.todo",
    ];

    /**
     * Helper to know if the given model is allowed
     *
     * @returns {Boolean}
     */
    function isAllowedBarcodeModel(modelName) {
        return barcodeModels.includes(modelName);
    }

    return {
        barcodeModels: barcodeModels,
        isAllowedBarcodeModel: isAllowedBarcodeModel,
    };
});
