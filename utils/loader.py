"""
Created on Thu Aug 11 13:41:09 2022

@author: nwoye chinedu
"""


import os, sys
import json
import random
import torch
import numpy as np
from PIL import Image
import torchvision.transforms as transforms
from torch.utils.data import Dataset, ConcatDataset, DataLoader


class CholecTrack20():
    def __init__(self, 
                dataset_dir, 
                augmentation_list=['original', 'vflip', 'hflip', 'contrast', 'rot90'],
                normalize=True,
                target_transform  = None):
        self.normalize   = normalize
        self.dataset_dir = dataset_dir
    
    def __len__(self):
        
        return
    
    def __getitem__(self, index):       
        labels   = self.label_data[self.frames[index]]
        basename = "{}.png".format(str(self.frames[index]).zfill(6))
        img_path = os.path.join(self.img_dir, basename)
        image    = Image.open(img_path)
        if self.transform:
            image = self.transform(image)
        if self.target_transform:
            labels = self.target_transform(labels).reshape(-1)
        return image, labels

if __name__ == "__main__":
    print("Refers to https://github.com/CAMMA-public/cholect45 for the usage guide.")


