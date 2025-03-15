#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Aug 11 13:41:09 2022

@author: nwoye chinedu
"""

import os
import cv2
import json
import random
from matplotlib import pyplot as plt


class Visualize(object):
    def __init__(self, dataset_dir, split="Training", video="VID02"):
        self.video_dir = os.path.join(dataset_dir, split, video)
        
        
    def get_text_on_box_position(self, text, bbox, font_scale=0.6, thickness=1):
        x, y, w, h = bbox
        text_size = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, font_scale, thickness)[0]
        if y < text_size[1]-10:
            return (int(x+(w-text_size[0])//2), int(y+h+text_size[1]+5))
        else:
            return (int(x+(w-text_size[0])//2), int(y))
        
    def list_frames(self):
        return [int(x.split(".")[0]) for x in os.listdir(os.path.join(self.video_dir, "Frames/"))]
        
    def view(self, frame_id):
        label_file = os.path.join(self.video_dir, "{}.json".format(os.path.basename(self.video_dir)))
        labels = json.load(open(label_file, "rb"))['annotations'][str(frame_id)]
        image = cv2.imread(os.path.join(self.video_dir, "Frames/{:06d}.png".format(int(frame_id))))
        image = cv2.resize(image, [854, 480])
        thickness = 1
        font_scale = 0.6
        font = cv2.FONT_HERSHEY_SIMPLEX
        names = ["Grasper", "Bipolar", "Hook", "Scissors", "Clipper", "Irrigator", "Spec.bag",]
        for label in labels:
            color = random.choice([(50,200,20), (124,114,250), (250,250,30), (250,50,250), (200,220,230),(50,250,250), (250,20,30)])
            bbox = [x*s for x,s in zip([854,480,854,480], label["tool_bbox"])]
            clsid = label["instrument"]
            intraop_track_id = label["intraoperative_track"]
            intracp_track_id = label["intracorporeal_track"]
            visio_track_id = label["visibility_track"]
            
            x, y, w, h = bbox
            cv2.rectangle(image, (int(x), int(y)), (int(x+w), int(y+h)), color, 2)
            text = "{} [{}|{}|{}]".format(names[int(clsid)], intraop_track_id, intracp_track_id, visio_track_id)
            org = self.get_text_on_box_position(text, bbox, font_scale, thickness)
            org = [x+5 for x in org]
            cv2.putText(image, text, org, font, 1.0, (255,250,255), thickness, cv2.LINE_AA)
        image = cv2.cvtColor(image , cv2.COLOR_BGR2RGB)
        plt.imshow(image)
        plt.show()
        
       
    
if __name__ == '__main__': 

    obj = Visualize("/path/to/CholecTrack20/dataset", video="VID02")
    
    # To view the frame ids
    # print(obj.list_frames())
    
    obj.view(11851)