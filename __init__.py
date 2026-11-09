from typing_extensions import override
from comfy_api.latest import ComfyExtension, io

from .magik_latent_3 import MagikRandomLatent3
from .magik_latent_5 import MagikRandomLatent5

WEB_DIRECTORY = "./js"


class MagikEmptyLatentExtension(ComfyExtension):
    @override
    async def get_node_list(self) -> list[type[io.ComfyNode]]:
        return [
            MagikRandomLatent3, 
            MagikRandomLatent5
        ]


async def comfy_entrypoint() -> MagikEmptyLatentExtension:
    return MagikEmptyLatentExtension()
