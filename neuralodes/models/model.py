import torch
from torch import nn
from ..utils import get_activation
from . import (
    ConvolutionalResidualBlock,
    ConvolutionalClassificationHead,
    ConvolutionalDownSampler,
    ConvolutionalODELayer,
    LinearResidualBlock,
)
from ..ode_solver import ExplicitEuler

class ResNetLinear(torch.nn.Module):
    def __init__(
            self,
            num_blocks=6,
            input_size=28*28,
            output_size=10,
            activation="relu",
            with_norm=False,
        ):
        super().__init__()

        self.activation = get_activation(activation)()
        self.residual_blocks = nn.Sequential(
            *[
                LinearResidualBlock(
                    size=input_size,
                    activation=self.activation,
                    with_norm=with_norm,
                )
                for i in range(num_blocks)        
            ]
        )
        self.norm = None
        if with_norm:
            self.norm = nn.BatchNorm1d(input_size)

        self.classification_head = nn.Sequential(
            self.activation,
            nn.Linear(input_size, output_size),
        )

    def forward(self, x):
        b = x.shape[0]
        x.reshape(b, -1)
        x = self.residual_blocks(x)
        if self.norm is not None:
            x = self.norm(x)
        x = self.classification_head(x)
        return x


class ResNetConv(torch.nn.Module):
    def __init__(
            self,
            num_blocks=6,
            in_channels=1,
            n_channels=64,
            output_size=10,
            activation="relu",
            with_norm=False,
            kernel_size=3,
            n_downsampling_blocks=2,
            ):
        super().__init__()

        self.activation = get_activation(activation)()
        self.downsampler = ConvolutionalDownSampler(
            in_channels=in_channels,
            out_channels=n_channels,
            activation=activation,
            with_norm=with_norm,
            kernel_size=kernel_size,
            n_downsampling_blocks=n_downsampling_blocks,
        )
        self.residual_blocks = torch.nn.Sequential(
            *[
                ConvolutionalResidualBlock(
                    n_channels=n_channels,
                    activation=self.activation,
                    with_norm=with_norm,
                )
                for i in range(num_blocks)        
            ]
        )
        self.classification_head = ConvolutionalClassificationHead(
            in_channels=n_channels,
            output_size=output_size,
            activation=activation,
            with_norm=with_norm,
        )

    def forward(self, x):
        x = self.downsampler(x)
        x = self.residual_blocks(x)
        x = self.classification_head(x)
        return x


class ConvolutionalODEClassifier(torch.nn.Module):
    def __init__(
            self,
            in_channels=1,
            n_channels=64,
            output_size=10,
            kernel_size=3,
            n_downsampling_blocks=2,
            activation="relu",
            with_norm="False",
            tableau_low=ExplicitEuler(),
            tableau_high=None,
            t0=0.0,
            t1=1.0,
            dt=0.1,
            atol=1e-6,
            rtol=1e-6,
        ):
        super().__init__()
        self.ode_layer = ConvolutionalODELayer(
            in_channels=n_channels,
            out_channels=n_channels,
            activation=activation,
            with_norm=with_norm,
            tableau_low=tableau_low,
            tableau_high=tableau_high,
            t0=t0,
            t1=t1,
            dt=dt,
            atol=atol,
            rtol=rtol,
        )
        self.downsampler = ConvolutionalDownSampler(
            in_channels=in_channels,
            out_channels=n_channels,
            activation=activation,
            with_norm=with_norm,
            kernel_size=kernel_size,
            n_downsampling_blocks=n_downsampling_blocks,
        )
        self.classification_head = ConvolutionalClassificationHead(
            in_channels=n_channels,
            output_size=output_size,
            activation=activation,
            with_norm=with_norm,
        )

    def forward(self, x):
        x = self.downsampler(x)
        x = self.ode_layer(x)
        x = self.classification_head(x)
        return x
