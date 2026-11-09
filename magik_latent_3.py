import random
import torch
from comfy_api.latest import io

# Megapixel presets. Only narrow_side / wide_side / square are used for this node
# (mirrors the "_A" values from the 5-outcome node's preset table).
PRESETS_3 = {
    "1MP": {"narrow_side": 832, "wide_side": 1216, "square": 1024},
    "1.5MP": {"narrow_side": 1024, "wide_side": 1472, "square": 1280},
    "2MP": {"narrow_side": 1216, "wide_side": 1664, "square": 1408},
    "4MP": {"narrow_side": 1664, "wide_side": 2432, "square": 2048},
}


class MagikRandomLatent3(io.ComfyNode):
    @classmethod
    def define_schema(cls):
        return io.Schema(
            node_id="Magik.RandomLatent3",
            display_name="Magik Random Latent 3",
            category="Magik/Image/Latent",
            description=(
                "Randomly selects between square, portrait, and landscape orientations "
                "with equiprobability (1/3) and outputs the corresponding target dimensions."
            ),
            inputs=[
                io.Int.Input(
                    "seed",
                    default=0,
                    min=0,
                    max=0xffffffffffffffff,
                    control_after_generate=True,
                    tooltip="Random seed. Set this to 'randomize' in the UI to change the output each generation.",
                ),
                io.Combo.Input(
                    "presets",
                    options=["custom", "1MP", "1.5MP", "2MP", "4MP"],
                    default="custom",
                    tooltip=(
                        "Quickly apply a target megapixel preset for narrow_side/wide_side/square. "
                        "Select 'custom' to set the dimensions below manually."
                    ),
                ),
                io.Int.Input(
                    "narrow_side",
                    default=512,
                    min=0,
                    max=0xffffffffffffffff,
                    tooltip="Output value for the short side when the outcome is landscape or portrait.",
                ),
                io.Int.Input(
                    "square",
                    default=512,
                    min=0,
                    max=0xffffffffffffffff,
                    tooltip="Output value for both width and height when the outcome is square.",
                ),
                io.Int.Input(
                    "wide_side",
                    default=768,
                    min=0,
                    max=0xffffffffffffffff,
                    tooltip="Output value for the long side when the outcome is landscape or portrait.",
                ),
                io.Int.Input(
                    "batch_size",
                    default=1,
                    min=1,
                    max=99,
                    tooltip="Number of latent images to generate in the batch.",
                ),
            ],
            outputs=[
                io.Int.Output("WIDTH", display_name="Width"),
                io.Int.Output("HEIGHT", display_name="Height"),
                io.String.Output("ORIENTATION", display_name="Orientation"),
                io.Latent.Output("LATENT", display_name="Latent"),
            ],
        )

    @classmethod
    def execute(cls, seed, presets, narrow_side, square, wide_side, batch_size):
        # A non-custom preset overrides the manual dimension widgets, so behavior
        # stays correct even if this is called directly (e.g. via the API) without
        # the frontend having synced/greyed-out the widget values.
        if presets != "custom":
            preset = PRESETS_3[presets]
            narrow_side = preset["narrow_side"]
            wide_side = preset["wide_side"]
            square = preset["square"]

        # Seed the random number generator to ensure the result is tied to the current seed
        random.seed(seed)
        outcome = random.randint(1, 3)

        if outcome == 1:
            width = square
            height = square
            orientation = "Square"
        elif outcome == 2:
            width = narrow_side
            height = wide_side
            orientation = "Portrait"
        else:
            width = wide_side
            height = narrow_side
            orientation = "Landscape"

        # Anima is a Cosmos-Predict2-2B derivative: 16-channel latent, 8x spatial downscale.
        latent = torch.zeros([batch_size, 16, height // 8, width // 8])

        return io.NodeOutput(width, height, orientation, {"samples": latent})