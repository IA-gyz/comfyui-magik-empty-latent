import random
import torch
from comfy_api.latest import io

# Megapixel presets for all five dimension widgets.
PRESETS_5 = {
    "1MP": {
        "narrow_side_A": 832, "wide_side_A": 1216,
        "narrow_side_B": 896, "wide_side_B": 1152,
        "square": 1024,
    },
    "1.5MP": {
        "narrow_side_A": 1024, "wide_side_A": 1472,
        "narrow_side_B": 1152, "wide_side_B": 1344,
        "square": 1280,
    },
    "2MP": {
        "narrow_side_A": 1216, "wide_side_A": 1664,
        "narrow_side_B": 1280, "wide_side_B": 1536,
        "square": 1408,
    },
    "4MP": {
        "narrow_side_A": 1664, "wide_side_A": 2432,
        "narrow_side_B": 1728, "wide_side_B": 2304,
        "square": 2048,
    },
}


class MagikRandomLatent5(io.ComfyNode):
    @classmethod
    def define_schema(cls):
        return io.Schema(
            node_id="Magik.RandomLatent5",
            display_name="Magik Random Latent 5",
            category="Magik/Image/Latent",
            description=(
                "Randomly selects between 5 distinct resolution/orientation outcomes "
                "with equiprobability (1/5) and outputs the corresponding target dimensions."
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
                        "Quickly apply a target megapixel preset for all five dimension widgets below. "
                        "Select 'custom' to set them manually."
                    ),
                ),
                io.Int.Input(
                    "narrow_side_A",
                    default=512,
                    min=1,
                    max=0xffffffffffffffff,
                    tooltip="Short side of aspect-ratio target A.",
                ),
                io.Int.Input(
                    "wide_side_A",
                    default=768,
                    min=1,
                    max=0xffffffffffffffff,
                    tooltip="Long side of aspect-ratio target A.",
                ),
                io.Int.Input(
                    "narrow_side_B",
                    default=512,
                    min=1,
                    max=0xffffffffffffffff,
                    tooltip="Short side of aspect-ratio target B.",
                ),
                io.Int.Input(
                    "wide_side_B",
                    default=896,
                    min=1,
                    max=0xffffffffffffffff,
                    tooltip="Long side of aspect-ratio target B.",
                ),
                io.Int.Input(
                    "square",
                    default=512,
                    min=1,
                    max=0xffffffffffffffff,
                    tooltip="Side length used when the square target is chosen.",
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
                io.Int.Output("OUTPUT_W", display_name="Width"),
                io.Int.Output("OUTPUT_H", display_name="Height"),
                io.String.Output("ORIENTATION", display_name="Orientation"),
                io.Latent.Output("LATENT", display_name="Latent"),
            ],
        )

    @classmethod
    def execute(cls, seed, presets, narrow_side_A, wide_side_A, narrow_side_B, wide_side_B, square, batch_size):
        # A non-custom preset overrides the manual dimension widgets, so behavior
        # stays correct even if this is called directly (e.g. via the API) without
        # the frontend having synced/greyed-out the widget values.
        if presets != "custom":
            preset = PRESETS_5[presets]
            narrow_side_A = preset["narrow_side_A"]
            wide_side_A = preset["wide_side_A"]
            narrow_side_B = preset["narrow_side_B"]
            wide_side_B = preset["wide_side_B"]
            square = preset["square"]

        # Seed the random number generator to ensure the result is tied to the current seed
        random.seed(seed)
        outcome = random.randint(1, 5)

        if outcome == 1:
            output_w = square
            output_h = square
            orientation = "Square"
        elif outcome == 2:
            output_w = narrow_side_A
            output_h = wide_side_A
            orientation = "Portrait"
        elif outcome == 3:
            output_w = narrow_side_B
            output_h = wide_side_B
            orientation = "Portrait"
        elif outcome == 4:
            output_w = wide_side_A
            output_h = narrow_side_A
            orientation = "Landscape"
        else:
            output_w = wide_side_B
            output_h = narrow_side_B
            orientation = "Landscape"

        # Anima is a Cosmos-Predict2-2B derivative: 16-channel latent, 8x spatial downscale.
        latent = torch.zeros([batch_size, 16, output_h // 8, output_w // 8])

        return io.NodeOutput(output_w, output_h, orientation, {"samples": latent})