"""Copyright (c) Microsoft Corporation. Licensed under the MIT license."""

import math

import torch
import torch.nn as nn
import torch.nn.functional as F
from timm.models.layers.helpers import to_2tuple


class LevelPatchEmbed(nn.Module):
    """At either the surface or at a single pressure level, maps all variables into a single
    embedding."""

    def __init__(
        self,
        max_vars: int,
        patch_size: int,
        embed_dim: int,
        history_size: int = 1,
        norm_layer=None,
        flatten=True,
    ):
        super().__init__()
        self.max_vars = max_vars
        self.kernel_size = (history_size,) + to_2tuple(patch_size)
        self.flatten = flatten
        self.embed_dim = embed_dim

        weight = torch.cat(
            # (C_out, C_in, kT, kH, kW)
            [torch.empty(embed_dim, 1, *self.kernel_size) for _ in range(max_vars)],
            dim=1,
        )
        self.weight = nn.Parameter(weight)
        self.bias = nn.Parameter(torch.empty(embed_dim))
        self.norm = norm_layer(embed_dim) if norm_layer else nn.Identity()
        self.reset_parameters()

    def reset_parameters(self):
        """The following initialisation is taken from

        https://pytorch.org/docs/stable/_modules/torch/nn/modules/conv.html#Conv3d
        """
        # Setting `a = sqrt(5)` in kaiming_uniform is the same as initialising with
        # `uniform(-1/sqrt(k), 1/sqrt(k))`, where `k = weight.size(1) * prod(*kernel_size)`.
        # For more details, see
        #
        #   https://github.com/pytorch/pytorch/issues/15314#issuecomment-477448573
        #
        nn.init.kaiming_uniform_(self.weight, a=math.sqrt(5))
        if self.bias is not None:
            fan_in, _ = nn.init._calculate_fan_in_and_fan_out(self.weight)
            if fan_in != 0:
                bound = 1 / math.sqrt(fan_in)
                nn.init.uniform_(self.bias, -bound, bound)

    def forward(self, x: torch.Tensor, vars: list[int]) -> torch.Tensor:
        """Run the embedding.

        Args:
            x (:class:`torch.Tensor`): Tensor to embed of a shape of `[B, V, T, H, W]`.
            vars (list[int]): A list of variable IDs. The length should be equal to `V`.

        Returns:
            :class:`torch.Tensor`: Embedded tensor a shape of `[B, L,  D]` if flattened,
                where `L = H * W / P**2`. Otherwise, the shape is `[B, D, H', W']`.

        """
        B, V, T, H, W = x.shape
        assert len(vars) == V, f"{V} != {len(vars)}"
        assert self.kernel_size[0] >= T, f"{T} > {self.kernel_size[0]}"
        assert H % self.kernel_size[1] == 0, f"{H} % {self.kernel_size[0]} != 0"
        assert W % self.kernel_size[2] == 0, f"{W} % {self.kernel_size[1]} != 0"
        assert max(vars) < self.max_vars, f"{max(vars)} >= {self.max_vars}"
        assert min(vars) >= 0, f"{min(vars)} < 0"
        assert len(set(vars)) == len(vars), f"{vars} contains duplicates"

        # Select the weights of the variables and history dimensions that are present in the batch.
        weight = self.weight[:, vars, :T, ...]  # [C_out, C_in, kT, kH, kW]
        # Adjust the stride if history is smaller than maximum.
        stride = (T,) + self.kernel_size[1:]

        # (B, V, T, H, W) -> (B, D, 1, H / P, W / P)
        proj = F.conv3d(x, weight, self.bias, stride=stride)
        if self.flatten:
            proj = proj.reshape(B, self.embed_dim, -1)  # (B, D, L)
            proj = proj.transpose(1, 2)  # (B, L, D)

        x = self.norm(proj)
        return x