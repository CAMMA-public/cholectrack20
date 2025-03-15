#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Jul  6 15:05:28 2023
@author: Chinedu Nwoye
"""
import os
import sys
import json
from typing import Any
import numpy as np
import pandas as pd
from pathlib import Path


class Converter:  
    @property
    def scale(self):
        return [854,480,854,480]
    
    @staticmethod
    def json_to_array(json_data, keys) -> np.ndarray:
        """ Converts the given JSON data to a NumPy array based on the specified keys.
        Parameters:
            json_data (dict): The JSON data.
            keys (list): The keys to extract from the JSON data.
        Returns:
            np.ndarray: The converted NumPy array.
        """
        frames = sorted(list(map(int, json_data.keys())))
        output = []
        for fid in frames:
            data = json_data[str(fid)]
            for x in data:
                out = [fid]
                for key in keys:
                    value = x.pop(key, -1)
                    if isinstance(value, list):
                        out.extend(value)
                    else:
                        out.append(value)
                output.append(out)
        return np.array(output)  

    @property
    def report(self):
        print("Operation completed!")      


        
class MOTChallenge(Converter):    
    def convert(self, src, dst, ttype="intraoperative_track", store="seq") -> None:
        """  Converts the MOTChallenge annotation format to the desired format.
        Parameters:
            src (str): The path to the input file.
            dst (str): The path to the output folder.
            ttype (str, optional): The type of track. Defaults to "intraoperative_track".
                options -> ("intraoperative_track", "intracorporeal_track", "visibility_track", "det")
            store (str, optional): The save type. Defaults to "seq".
                options -> ("frames" for save per frame, "seq" for single file for a seq)
        Returns:
            None
        """
        assert ttype in ["intraoperative_track", "intracorporeal_track", "visibility_track", "det"], "Invalid ttype"
        assert store in ["frames", "seq"], "Invalid store type, options (frames, seq)"
        os.makedirs(dst, exist_ok=True)        
        
        keys    = [ttype, "tool_bbox", "score", "instrument", "visibility", "operator"]
        dataset = json.load(open(src, "rb"))
        anns    = dataset['annotations']
        output  = self.json_to_array(anns, keys)  
        
        if store == "seq":
            scaler = np.ones([1, output.shape[-1]])
            scaler[:,2:6] = self.scale
            output *= scaler
            fmt = ['%d','%d','%.1f','%.1f','%.1f','%.1f','%.2f','%d','%d','%d']
            dst = Path(os.path.join(dst, os.path.basename(src))).with_suffix(".txt")
            np.savetxt(dst, X=output, delimiter=",", fmt=fmt)
        else:
            if "det" in ttype:
                output = output[:, (0,7,2,3,4,5)]   
                fmt = ['%d','%.6f','%.6f','%.6f','%.6f']
            else:
                output = output[:, (0,7,1,2,3,4,5)]
                fmt = ['%d','%d','%.6f','%.6f','%.6f','%.6f']
            frames = sorted(np.unique(output[:,0]))
            for fid in frames:
                y = output[output[:,0]==fid][:,1:]                
                np.savetxt(os.path.join(dst, "{:0>6d}.txt".format(int(fid))), X=y, delimiter=" ", fmt=fmt)
        self.report
    
    
    
    
class COCO:
    def combine(self, seqpath_pattern:str, dst:str, seqs:list, split:str="training") -> None:
        """ Combines multiple COCO datasets into a single dataset.
        Parameters:
            seqpath_pattern (str): The file path pattern to locate the COCO datasets for combining.
            seqs (list): A list of sequences to combine.
            split (str, optional): The split type for the combined dataset. Defaults to "training".
        Returns:
            None.
        """
        anns_id = 0
        img_id  = 0
        images  = []
        videos  = []
        annotations = []
        for i, seq in enumerate(seqs):
            src     = seqpath_pattern.format(seq)
            dataset = json.load(open(src, "rb"))
            anns    = dataset['annotations']
            imgs    = dataset['images']
            videos.append({"id":i, "name":seq, "num_frames":len(imgs), "split":split})
            for ann in anns:
                ann['id'] += anns_id
                ann['image_id'] += img_id
                annotations.append(ann)
            anns_id += len(anns)
            for img in imgs:
                img['id'] += img_id
                img['prev_image_id'] += img_id if img['prev_image_id'] != -1 else 0
                img['next_image_id'] += img_id if img['next_image_id'] != -1 else 0
                images.append(img)
            img_id += len(imgs)      
        # save
        dataset['annotations'] = annotations
        dataset['images'] = images
        dataset['videos'] = videos  
        dst = Path(os.path.join(dst, split)).with_suffix(".json")
        with open(dst, "w") as f:
            json.dump(dataset, f)
        self.report


    def convert(self, src:str, dst:str, ttype:str="intraoperative_track") -> None:
        """ Converts to COCO dataset format.
        Parameters:
            src (str): The file path of the input COCO dataset.
            dst (str): The destination folder to save the converted dataset.
            ttype (str, optional): The target track type to convert to. Defaults to "intraoperative_track".
        Returns:
            None.
        """
        assert ttype in ["intraoperative_track", "intracorporeal_track", "visibility_track"], "Invalid ttype"
        os.makedirs(dst, exist_ok=True)
        dataset = json.load(open(src, "rb"))
        records = dataset['annotations']
        video   = dataset['video']['name']
        seqlen  = dataset['video']['num_frames']
        width   = dataset['video']['width']
        height  = dataset['video']['height']
        categories = dataset['categories']
        fids    = sorted(list(map(int, records.keys())))
        images  = []
        annotations = []
        ann_id = 0
        for img_id, fid in enumerate(fids):
            # get image details
            images.append( dict(
                    id=fid,
                    frame_id=fid,
                    seq=video,
                    height=height,
                    width=width,
                    prev_image_id=-1 if img_id==0 else (img_id-1),
                    next_image_id=-1 if (img_id+1)==len(fids) else (img_id+1),
                    file_name="VID{:0>2d}/images/{:0>6d}.png".format(video, int(fid)), 
                ) )
            # get annotations details
            anns = records[str(fid)]
            for ann in anns:
                ann_id += 1
                annotations.append( dict(
                    id=ann_id,
                    category_id=ann.pop("instrument"),
                    image_id=fid,
                    track_id=ann.pop(ttype),
                    bbox=ann.pop("tool_bbox"),
                    operator_id=ann.pop("operator"),
                    iscrowd=ann.pop("iscrowd"),
                    area=ann.pop("area"),
                    score=ann.pop("score"),
                    visibility=ann.pop("visibility"),
                ) )
                
        # save
        dataset['annotations'] = annotations
        dataset['images'] = images
        dataset['categories'] = categories
        dst = Path(os.path.join(dst, os.path.basename(src))).with_suffix(".json")
        with open(dst, "w") as f:
            json.dump(dataset, f)
        self.report
    
    
    

class TAO(Converter):
    def __init__(self):
        super(TAO, self)
        pass
    
    def convert(self) -> Any:
        raise NotImplementedError
    
    
    
    
class GenFilePaths:
    def generate(self, root:str, seq_paths:list, dst:str, split:str="training"):
        os.makedirs(dst, exist_ok=True)
        paths = []
        for seq_path in seq_paths:
            src = os.path.join(root, seq_path)
            dataset = json.load(open(src, "rb"))
            records = dataset['annotations']
            fids    = sorted(list(map(int, records.keys())))
            for fid in fids:
                paths.append( os.path.join(seq_paths, "{:0>6d}.png") )
        np.savetxt(os.path.join(dst,"data."+split), paths, fmt=str)
        self.__repr__


    
        
    
    
    
if __name__ == '__main__':
    
    obj = MOTChallenge() 
    
    videos = [1,2,4,6,7,11,12,13,17,23,25,30,31,37,39,92,96,103,110,111]
    ttypes = ["intraoperative_track", "intracorporeal_track", "visibility_track"]
    outdir = '/mnt/camma5_data2/nwoye/work/dataset/CholecTrack20/annotation/output/mot-challenge'
    indir = "/mnt/camma5_data2/nwoye/work/dataset/CholecTrack20/RELEASE/CholecTrack20/testing/VID{:02d}/"
    
    for ttype in ttypes:
        for video in videos:
            print("processing ...", ttype, video)
            file = os.path.join(indir.format(video), f"VID{video:0>2d}.json")
            out = os.path.join(outdir, f"{ttype}")
            obj . convert( src=file, dst=out, ttype=ttype, store="seq")
            
            