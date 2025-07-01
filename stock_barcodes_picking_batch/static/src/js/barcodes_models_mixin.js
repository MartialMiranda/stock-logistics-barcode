/* Copyright 2024 Tecnativa - Sergio Teruel
 * License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl). */

odoo.define("stock_barcodes_picking_batch.BarcodesModelsMixin", [
    "stock_barcodes.utils.barcodes_models_utils"
], function (require) {
    "use strict";

    const {barcodeModels} = require("stock_barcodes.utils.barcodes_models_utils");

    barcodeModels.push("stock.picking.batch", "wiz.candidate.picking.batch");
});