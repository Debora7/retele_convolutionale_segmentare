import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import pathlib as pt
import random
import tensorflow as tf
import yaml

from tensorflow import keras
from tensorflow.keras.preprocessing.image import load_img
from UNetModel import UNetModel
from PIL import Image, ImageEnhance

config = None
with open('config.yaml') as f:  # reads .yml/.yaml files
    config = yaml.safe_load(f)


class LungSegDataGenerator(keras.utils.Sequence):
    """Un DataGenerator custom pentru setul de date pentru segmentare plamanilor"""

    def __init__(self,
                 dataset_df,
                 img_size,
                 batch_size,
                 shuffle=True,
                 rotation=0,
                 factor=1,
                 probability=config['augmentare']['probabilitate']):
        self.dataset_df = dataset_df.reset_index(drop=True)
        self.img_size = tuple(img_size)
        self.batch_size = batch_size
        self.shuffle = shuffle
        self.indexes = np.arange(len(self.dataset_df))
        self.rotation = rotation
        self.factor = factor
        self.probability = probability

    def __len__(self):
        """
        Returns:
            int: Returneaza numarul de batches per epoca
        """
        batch_per_epoch = len(self.dataset_df)//self.batch_size
        return batch_per_epoch  # de completat

    def __combine_masks(self, img_right, img_left):
        """Combina mastile pentru cei doi plamani intr-o singura masca

        Args:
            img_right (pillow.Image): masca pentru plamanul drept
            img_left (pillow.Image): masca pentru plamanul stang

        Returns:
            numpy.array: masca cu cei doi plamani
        """

        img_right = np.array(img_right, dtype="uint8") * 1 / 255
        img_left = np.array(img_left, dtype="uint8") * 1 / 255

        img = (img_right + img_left).astype("uint8")

        return img

    def __apply_data_aug(self, img, mask):
        # rotatie with self.rotation
        self.rotation = random.randint(0, config['augmentare']['rotatie'])
        rotated = img.rotate(self.rotation)
        mask = Image.fromarray(np.uint8(mask))
        rotated_2 = mask.rotate(self.rotation)

        # flip
        if (random.randint(1, 100) < self.probability):
            fliped = rotated.transpose(Image.FLIP_LEFT_RIGHT)
            fliped2 = rotated_2.transpose(Image.FLIP_LEFT_RIGHT)
            output_1 = fliped
            output_2 = fliped2
        else:
            output_1 = rotated
            output_2 = rotated_2

        # brightnness
        self.factor = random.uniform(0, config['augmentare']['factor'])
        enhancer = ImageEnhance.Brightness(output_1)

        img_output = enhancer.enhance(self.factor)
        mask_output = output_2

        return img_output, mask_output

    def __getitem__(self, idx):
        """Returneaza un tuple (input, target) care corespunde cu batch #idx.

        Args:
            idx (int): indexul batch-ului curent

        Returns:
           tuple:  (input, target) care corespunde cu batch #idx
        """

        i = idx * self.batch_size
        batch_indexes = self.indexes[i:i + self.batch_size]
        batch_df = self.dataset_df.loc[batch_indexes, :].reset_index(drop=True)

        # x, y trebuie sa aiba dimensiunea [batch size, height, width, nr de canale]
        x = np.zeros((self.batch_size,) + self.img_size + (3,), dtype="float32")
        y = np.zeros((self.batch_size,) + self.img_size + (3,), dtype="float32")

        for i, row in batch_df.iterrows():
            # citeste imaginea de input de la calea row['image_path]
            # hint: functia load_img
            img = load_img(row['image_path'], target_size=self.img_size)  # de completat

            # citeste mastile de segmentare pentru cei doi plamani
            img_right = load_img(row['right_lung_mask_path'], target_size=self.img_size)  # de completat
            img_left = load_img(row['left_lung_mask_path'], target_size=self.img_size)  # de completat

            mask = self.__combine_masks(img_right, img_left)

            img, mask = self.__apply_data_aug(img, mask)

            # flip
            x[i] = np.array(img) * 1/255
            y[i] = mask

        return x, y

    def on_epoch_end(self):
        """
        Actualizeaza indecsii dupa fiecare epoca si ii amesteca daca parametrul shuffle este True
        """
        self.indexes = np.arange(len(self.dataset_df))
        if self.shuffle == True:
            np.random.shuffle(self.indexes)
