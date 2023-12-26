import numpy as np
from discord.ext import commands
from PIL import Image
import requests
from io import BytesIO
from config import MODEL_PATH
import torch
import torch.nn as nn
from ml_utils import get_default_device, predict_image, ImageClassificationBase, classes, preprocess, to_device
from torchvision import models

allowed_exts = ['jpg', 'jpeg', 'png', 'jfif']


class googlenet(ImageClassificationBase):
    def __init__(self):
        super().__init__()
        # Use a pretrained model
        self.network = models.googlenet(weights='IMAGENET1K_V1')
        # Replace last layer
        num_ftrs = self.network.fc.in_features
        self.network.fc = nn.Linear(num_ftrs, len(classes))

    def forward(self, xb):
        return torch.sigmoid(self.network(xb))


class GarbageBot(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.model = googlenet()
        state = torch.load(MODEL_PATH)
        self.model.load_state_dict(state['model_state_dict'])
        to_device(self.model, get_default_device())
        self.model.eval()

    @commands.command(
        name="test2"
    )
    async def test2(self, ctx):
        # Send image back
        await ctx.send("Testing Garbage Bot...")

    @commands.command(
        name="predict"
    )
    async def predict(self, ctx):
        # Check if a user has attached an image to the message
        if len(ctx.message.attachments) == 0:
            await ctx.send("No image attached.")
            return

        images = []

        for attachment in ctx.message.attachments:
            image_url = attachment.url
            ext = image_url.split(".")[-1]
            if ext.lower() in allowed_exts:
                images.append(Image.open(BytesIO(requests.get(image_url).content)))

        if not images:
            await ctx.send("Did not receive image input.")
            return

        images = [preprocess(image) for image in images]
        with torch.no_grad():
            preds = [predict_image(img=image, model=self.model, device=get_default_device()) for image in images]
            # prob = np.array(_prob.cpu())[0]

        for i, (_class, _prob) in enumerate(preds):
            prob = np.array(_prob.cpu())[0]
            await ctx.send(f"{i + 1}. Predicted Class: \"{_class}\" ({prob * 100:.2f} %)")
