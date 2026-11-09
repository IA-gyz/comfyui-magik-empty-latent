import { app } from "../../scripts/app.js";

// Mirrors the PRESETS_3 / PRESETS_5 tables in the Python nodes so the UI can
// preview the effective values immediately, without waiting on an execution
// round-trip.
const PRESETS_3 = {
    "1MP": { narrow_side: 832, wide_side: 1216, square: 1024 },
    "1.5MP": { narrow_side: 1024, wide_side: 1472, square: 1280 },
    "2MP": { narrow_side: 1216, wide_side: 1664, square: 1408 },
    "4MP": { narrow_side: 1664, wide_side: 2432, square: 2048 },
};

const PRESETS_5 = {
    "1MP": { narrow_side_A: 832, wide_side_A: 1216, narrow_side_B: 896, wide_side_B: 1152, square: 1024 },
    "1.5MP": { narrow_side_A: 1024, wide_side_A: 1472, narrow_side_B: 1152, wide_side_B: 1344, square: 1280 },
    "2MP": { narrow_side_A: 1216, wide_side_A: 1664, narrow_side_B: 1280, wide_side_B: 1536, square: 1408 },
    "4MP": { narrow_side_A: 1664, wide_side_A: 2432, narrow_side_B: 1728, wide_side_B: 2304, square: 2048 },
};

// node class name -> { table, fields } (fields are the widget names to grey out / overlay)
const NODE_PRESET_CONFIG = {
    "Magik.RandomLatent3": { table: PRESETS_3, fields: ["narrow_side", "wide_side", "square"] },
    "Magik.RandomLatent5": {
        table: PRESETS_5,
        fields: ["narrow_side_A", "wide_side_A", "narrow_side_B", "wide_side_B", "square"],
    },
};

// Returns the active preset's value map, or null when "custom" is selected.
// NOTE: this never touches widget.value — the user's manually-entered numbers
// stay intact underneath so switching back to "custom" restores them exactly.
// The Python node independently re-applies the preset from this same table at
// execution time, so the overlay is purely visual/informational.
function getActivePresetValues(node, config) {
    const presetWidget = node.widgets?.find((w) => w.name === "presets");
    if (!presetWidget || presetWidget.value === "custom") return null;
    return config.table[presetWidget.value] || null;
}

// A widget's native draw() can render more than a plain label/value (e.g. the
// underline LiteGraph adds to hint a widget is convertible to an input), and
// nothing guarantees it runs strictly before onDrawForeground. Painting an
// opaque box over it is therefore order-dependent and can let that native
// render show through/ghost behind our overlay text. Silencing draw() itself
// removes the native render at the source instead of trying to hide it.
function silenceWidgetDraw(node, config) {
    for (const fieldName of config.fields) {
        const widget = node.widgets?.find((w) => w.name === fieldName);
        if (!widget) continue;
        if (widget.__origDraw === undefined) {
            widget.__origDraw = widget.draw ?? null;
        }
    }
}

function syncWidgetDisabled(node, config) {
    const presetValues = getActivePresetValues(node, config);
    for (const fieldName of config.fields) {
        const widget = node.widgets?.find((w) => w.name === fieldName);
        if (!widget) continue;
        widget.disabled = !!presetValues;
        // While a preset is active, our overlay is the sole renderer for this
        // row — no-op the widget's own draw so nothing from it can show
        // through underneath (or on top of) our box.
        widget.draw = presetValues ? function () {} : widget.__origDraw;
    }
}

function drawPresetOverlay(node, ctx, config) {
    const presetValues = getActivePresetValues(node, config);
    if (!presetValues) return;

    const H = (typeof LiteGraph !== "undefined" && LiteGraph.NODE_WIDGET_HEIGHT) || 20;
    const margin = 15;
    const boxWidth = Math.max(0, node.size[0] - margin * 2);

    for (const fieldName of config.fields) {
        const widget = node.widgets?.find((w) => w.name === fieldName);
        if (!widget || widget.last_y == null || !(fieldName in presetValues)) continue;

        const y = widget.last_y;

        ctx.save();
        // Guard against any reduced alpha the widget's own (disabled-state) drawing
        // left active — without this, its label can bleed through our overlay.
        ctx.globalAlpha = 1;

        // Fully opaque (no alpha channel) backing so none of the underlying
        // greyed-out widget's own label/value text can show through.
        ctx.fillStyle = "#242424";
        ctx.beginPath();
        if (ctx.roundRect) {
            ctx.roundRect(margin, y, boxWidth, H, 4);
        } else {
            ctx.rect(margin, y, boxWidth, H);
        }
        ctx.fill();

        ctx.font = "12px Arial";
        ctx.textBaseline = "middle";

        ctx.fillStyle = "#9a9a9a";
        ctx.textAlign = "left";
        ctx.fillText(widget.label ?? widget.name, margin + 10, y + H / 2);

        ctx.fillStyle = "#ffffff";
        ctx.textAlign = "right";
        ctx.fillText(String(presetValues[fieldName]), margin + boxWidth - 10, y + H / 2);

        ctx.restore();
    }
}

app.registerExtension({
    name: "magik.latent_presets",

    async beforeRegisterNodeDef(nodeType, nodeData) {
        const config = NODE_PRESET_CONFIG[nodeData.name];
        if (!config) return;

        const onNodeCreated = nodeType.prototype.onNodeCreated;
        nodeType.prototype.onNodeCreated = function () {
            onNodeCreated?.apply(this, arguments);

            const presetWidget = this.widgets?.find((w) => w.name === "presets");
            if (!presetWidget) return;

            silenceWidgetDraw(this, config);

            const origCallback = presetWidget.callback;
            presetWidget.callback = (value, ...rest) => {
                const result = origCallback?.call(presetWidget, value, ...rest);
                syncWidgetDisabled(this, config);
                this.setDirtyCanvas(true, true);
                return result;
            };

            // Sync state right away (covers the default "custom" state on a fresh node).
            syncWidgetDisabled(this, config);
        };

        // Re-apply after a saved workflow is loaded so a restored preset selection
        // still greys out the correct widgets.
        const onConfigure = nodeType.prototype.onConfigure;
        nodeType.prototype.onConfigure = function () {
            onConfigure?.apply(this, arguments);
            silenceWidgetDraw(this, config);
            syncWidgetDisabled(this, config);
        };

        // Draw the preset value overlay on top of the (greyed-out) widgets.
        const onDrawForeground = nodeType.prototype.onDrawForeground;
        nodeType.prototype.onDrawForeground = function (ctx) {
            onDrawForeground?.apply(this, arguments);
            if (this.flags?.collapsed) return;
            drawPresetOverlay(this, ctx, config);
        };
    },
});
