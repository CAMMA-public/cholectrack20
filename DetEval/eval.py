#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Oct 27 14:29:32 2022

@author: nwoye chinedu
"""

import os
import json
import sys
import argparse
import numpy as np
from collections import OrderedDict, defaultdict
from pycocotools.coco import COCO
from pycocotools.cocoeval import COCOeval



class CholecTrack20():    
    @staticmethod
    def default_argparse():
        parser = argparse.ArgumentParser()
        parser.add_argument('--BENCHMARK', type=str, default='MCMIT', help='?')
        parser.add_argument('--GT_FORMAT', type=str, default="{gt_root}/{split}/{seq}/{seq}.json", help='pattern') 
        parser.add_argument('--DET_FORMAT', type=str, default="{pd_root}/{seq}.{ext}", help='pattern') 
        parser.add_argument('--GT_ROOT', type=str, default='data/gt/mcmit/', help='path to groundtruth?')
        parser.add_argument('--DET_ROOT', type=str, default='data/detectors/mcmit/', help='path to predictors?')
        parser.add_argument('--DET_FILE_TYPE', type=str, default='TXT', choices=['JSON','TXT'], help='file_type') 
        parser.add_argument('--THRESHOLDS', type=str, nargs='*', default=[0.5,0.55,0.6,0.65,0.7,0.75,0.8,0.85,0.9,0.95], help='detection IoU threshold')
        parser.add_argument('--VIDEO_TO_EVAL', type=str, default='all', help='e.g.: 1, 2,.., all')
        parser.add_argument('--OUTPUT_FILE', type=str, default=None, help='path to write feedback') 
        parser.add_argument('--FPS', type=str, default=1, help='framerate ') 
        parser.add_argument('--SPLIT', type=str, default='testing', help='data split') 
        parser.add_argument('--MODEL_NAME', type=str, default=None, help='file to write feedback ')
        parser.add_argument('--CLASSES_TO_EVAL', type=str, default=None, help='e.g.: grasper, hook, each, all, etc. default=all')  
        parser.add_argument('--PHASES', type=str, default=None, help='frames belonging to phase id') 
        parser.add_argument('--CONDITIONS', type=str, default=None, help='Frames with surgical visual challenges')        
        FLAGS, unparsed = parser.parse_known_args()
        return FLAGS
    
    def __init__(self):
        self.result_buffer  = defaultdict(list)
        self.offset         = 1e7
        self.valid_classes  = {'grasper': 0, 'bipolar': 1, 'hook': 2, 'scissors': 3, 'clipper': 4, 'irrigator': 5, 'specimenbag': 6}
        self.valid_conditions = {'bleeding': 0, 'blurred': 0, 'smoke': 0, 'crowded': 0, 'occluded': 0, 'reflection': 0, 'stainedlens': 0, 'undercoverage': 0, 'clear':0}
        self.valid_videos   = [1,2,4,6,7,11,12,13,17,23,25,30,31,37,39,92,96,103,110,111]
        self.valid_phases = {'preparation' : 0, 'calotTriangleDissection' : 1, 'clippingAndCutting' : 2, 'gallbladderDissection' : 3, 'gallbladderPackaging' : 4, 'cleaningAndCoagulation' : 5, 'gallbladderRetraction' : 6}
        self.config         = self.default_argparse()
        
        # videos
        eval_seqs    = self.valid_videos if self.config.VIDEO_TO_EVAL == "all" else str(self.config.VIDEO_TO_EVAL).split(",")
        eval_seqs    = ["VID{:0>2d}".format(int(x)) for x in eval_seqs]
        
        # phases        
        if self.config.PHASES == "each":
            self.config.PHASES = ",".join([v for v in self.valid_phases.keys()])
        eval_phases = str(self.config.PHASES).lower().split(",")
        
        # classes
        if self.config.CLASSES_TO_EVAL == "each":
            self.config.CLASSES_TO_EVAL = ",".join([v for v in self.valid_classes.keys()])
        eval_classes = str(self.config.CLASSES_TO_EVAL).lower().split(",")
            
        # visual challenge
        if self.config.CONDITIONS == "each":
            self.config.CONDITIONS = ",".join([v for v in self.valid_conditions.keys()])
        eval_conditions = str(self.config.CONDITIONS).lower().split(",")
            
        
        print(self.config.MODEL_NAME, "RECEIVED", self.config.GT_ROOT)
        # Evaluate
        for seq in eval_seqs:
            gt_file = self.config.GT_FORMAT.format(gt_root=self.config.GT_ROOT, seq=seq, split=self.config.SPLIT)    
            if not os.path.isfile(gt_file): raise Exception('GT file not found for sequence: ' + gt_file)        
            gt_data = self.load_gt_json(gt_file) 
                        
            pd_file = self.config.DET_FORMAT.format(pd_root=self.config.DET_ROOT, seq=seq, ext=self.config.DET_FILE_TYPE.lower())   
            if not os.path.isfile(pd_file): raise Exception('PD file not found for sequence: ' + pd_file)        
            pd_data = self.load_pd_txt(pd_file)
            
            
            if self.config.PHASES:
                for eval_phase in eval_phases:
                    if eval_phase.lower().strip() in self.valid_phases.keys() or eval_phase.lower().strip()=='all':
                        print("{}\n>> {}-test | Phase: {}\n{}".format("*"*50, seq, eval_phase.lower(), "-"*50))      
                        _gt_data_, _pd_data_ = self.get_data_by_phase(eval_phase=eval_phase, gt_data=gt_data.copy(), pd_data=pd_data.copy())
                        if len(_gt_data_['annotations']) > 0:
                            results = self.eval_json(_gt_data_, _pd_data_, thresholds=self.config.THRESHOLDS)                    
                            self.log_result(results, item=eval_phase, seq=seq)    
                    else:
                        raise Exception('Attempted to evaluate an invalid phase: '+eval_phase.lower())
            
            
            if self.config.CLASSES_TO_EVAL:
                for eval_class in eval_classes:
                    if eval_class.lower().strip() in self.valid_classes.keys() or eval_class.lower().strip()=='all':
                        print("{}\n>> {}-test | class: {}\n{}".format("*"*50, seq, eval_class.lower(), "-"*50))
                        # self.eval_json(seq, gt_data=gt_data.copy(), pd_data=pd_data.copy(), eval_class=eval_class, thresholds=self.config.THRESHOLDS)        
                        _gt_data_, _pd_data_ = self.get_data_by_category(eval_class=eval_class, gt_data=gt_data.copy(), pd_data=pd_data.copy())
                        if len(_gt_data_['annotations']) > 0:
                            results = self.eval_json(_gt_data_, _pd_data_, thresholds=self.config.THRESHOLDS)                    
                            self.log_result(results, item=eval_class, seq=seq)    
                    else:
                        raise Exception('Attempted to evaluate an invalid class: '+eval_class.lower())
                        
            if self.config.CONDITIONS:
                 for eval_cond in eval_conditions:
                     if eval_cond.lower().strip() in self.valid_conditions.keys() or eval_cond.lower().strip()=='all':
                         print("{}\n>> {}-test | Condition: {}\n{}".format("*"*50, seq, eval_cond.lower(), "-"*50))      
                         _gt_data_, _pd_data_ = self.get_data_by_condition(eval_condition=eval_cond, gt_data=gt_data.copy(), pd_data=pd_data.copy())
                         if len(_gt_data_['annotations']) > 0:
                             results = self.eval_json(_gt_data_, _pd_data_, thresholds=self.config.THRESHOLDS)                    
                             self.log_result(results, item=eval_cond, seq=seq)    
                     else:
                         raise Exception('Attempted to evaluate an invalid conditon: '+eval_cond.lower())
             
        
        # Reporting
        OVERALL = []
        for eval_cat, result_buffer in self.result_buffer.items():
            AP = np.array(result_buffer, dtype=object)
            mAP = [["AVG"] + np.nanmean(AP[:,1:5].astype(np.float32), axis=0).tolist()]
            header = [["Model", self.config.MODEL_NAME, "Detection ", str(self.config.FPS)+" FPS" ]]
            subhead = [["SEQ", "AP@.5:.95", "AP@.5 ", "AP@.75"]]
            classinfo = [["CATEGORY:", eval_cat.upper(), "Tool(s)", "--------"]]
            summary = np.concatenate([classinfo, header, subhead, AP, mAP], axis=0)    
            summary[3:,1:] = np.round(summary[3:,1:].astype(float)*100.0, decimals=1)
            fmt ="%-12s"*summary.shape[1]        
            os.makedirs(os.path.dirname(self.config.OUTPUT_FILE), exist_ok=True)
            with open(self.config.OUTPUT_FILE, "a+") as file:
                np.savetxt(file, summary, delimiter="&", fmt=fmt)
                print("-"*50, "\n", file=file)
            OVERALL.append(mAP[0][1:])
        OVERALL = np.array(OVERALL)
        overall = np.array([['mAP(%)', *np.round(np.nanmean(OVERALL, axis=0).astype(float)*100.0, decimals=1)]])
        with open(self.config.OUTPUT_FILE, "a+") as file:
            np.savetxt(file, overall, delimiter="&", fmt=fmt)

    
                
    
    def load_pd_txt(self, file_path, imDim=[854, 480, 854, 480]):
        records = np.genfromtxt(file_path, dtype=float, delimiter=",")
        print("Num. of labels in PD:", len(records))
        labels  = []
        ofs     = 0 #if int(self.config.FPS)==1 else 1
        for k, data in enumerate(records):
                bbox = list(map(float, data[2:6]))
                if max(bbox) < 0.99999999999999999:
                    bbox = [b*x for b,x in zip(bbox, imDim)]
                labels.append({
                    "id":k+1,
                    "image_id": int(data[0]+ofs), 
                    "category_id": int(data[7]), 
                    "bbox": bbox, 
                    "score": data[6] if len(data)>6 else 1.0,
                    "area": float(bbox[-1] * bbox[-2]),
                }) 
        output = {"annotations": labels}
        return output
    

    def load_gt_json(self, src:str):
        """ Converts to COCO dataset format.
        Parameters:
            src (str): The file path of the input json dataset video label.
        Returns:
            Dataset.
        """
        ann_id  = 0
        dataset = json.load(open(src, "rb"))
        records = dataset['annotations']
        categories = dataset['categories']['tools']
        video   = dataset['video']['name']
        width   = dataset['video']['width']
        height  = dataset['video']['height']
        scaler  = np.array([width, height, width, height])
        fids    = sorted(list(map(int, records.keys())))
        images  = []
        labels  = []
        for fid in fids:
            # get image details
            images.append( dict(
                    id=fid,
                    frame_id=fid,
                    seq=video,
                    height=height,
                    width=width,
                    file_name="{}/images/{:0>6d}.png".format(video, int(fid)), 
                ) )            
            # get annotations details
            anns = records[str(fid)]
            for ann in anns:
                ann_id += 1
                bbox = [np.round(x,1) for x in ann.get("tool_bbox") * scaler]
                labels.append( dict(
                    id=ann_id,
                    image_id=fid,
                    category_id=ann.get("instrument"),
                    bbox=bbox,
                    iscrowd=0, 
                    score=float(ann.get("score")),
                    area=float(ann.get("area")),
                    crowded=int(ann.get("crowded")),                  
                    phase=int(ann.get("phase")),
                    triplet=int(ann.get("triplet")),
                    reflection=int(ann.get("reflection")),
                    occluded=int(ann.get("occluded")),
                    bleeding=int(ann.get("bleeding")),
                    smoke=int(ann.get("smoke")),
                    blurred=int(ann.get("blurred")),
                    undercoverage=int(ann.get("undercoverage")),
                    stainedlens=int(ann.get("stainedlens")),
                    clear=int((int(ann.get("stainedlens"))+int(ann.get("undercoverage"))+int(ann.get("blurred"))+int(ann.get("smoke"))+int(ann.get("bleeding"))+\
                        int(ann.get("occluded"))+int(ann.get("reflection"))+int(ann.get("crowded")))==0)
                ) )    
                    
        output = {"annotations": labels, "images": images, "categories": categories}
        print("Num. of labels in GT:", len(labels))  
        return output
        
        
    def get_data_by_condition(self, eval_condition, gt_data, pd_data):  
        frames = []
        category = eval_condition.lower().strip()
        if category in self.valid_conditions.keys():
            gt_annotations = []
            for data in gt_data['annotations']:
                if data[category] == 1:
                    gt_annotations.append(data)
                    frames.append(data["image_id"])                    
            gt_data['annotations'] = gt_annotations
            frames = np.unique(frames)
            pd_annotations = []
            for data in pd_data['annotations']:
                if data["image_id"] in frames:
                    pd_annotations.append(data)
            pd_data['annotations'] = pd_annotations 
        return gt_data, pd_data
        
    
    def get_data_by_phase(self, eval_phase, gt_data, pd_data, ):  
        frames = []
        category = self.valid_phases.get(eval_phase.lower().strip(), -1)
        if category >= 0:
            gt_annotations = []
            pd_annotations = []
            for data in gt_data['annotations']:
                if data["phase"] == category:
                    gt_annotations.append(data)
                    frames.append(data["image_id"])                    
            gt_data['annotations'] = gt_annotations
            frames = np.unique(frames)
            for data in pd_data['annotations']:
                if data["image_id"] in frames:
                    pd_annotations.append(data)
            pd_data['annotations'] = pd_annotations 
        return gt_data, pd_data
    
        
    def get_data_by_category(self, eval_class, gt_data, pd_data, ):  
        category = self.valid_classes.get(eval_class.lower().strip(), -1)
        if category >= 0:
            gt_annotations = []
            pd_annotations = []
            for data in gt_data['annotations']:
                if data["category_id"] == category:
                    gt_annotations.append(data)
            gt_data['annotations'] = gt_annotations
            for data in pd_data['annotations']:
                if data["category_id"] == category:
                    pd_annotations.append(data)
            pd_data['annotations'] = pd_annotations 
        return gt_data, pd_data
    
    
    def eval_json(self, gt_data, pd_data, thresholds=np.array([0.5,0.55,0.6,0.65,0.7,0.75,0.8,0.85,0.9,0.95])):  
        # Eval
        coco_gt = COCO()
        coco_pd = COCO()
        coco_gt.dataset = gt_data
        coco_pd.dataset = pd_data  
        coco_gt.createIndex()
        coco_pd.createIndex()   
        cocoEval = COCOeval(coco_gt, coco_pd, 'bbox')
        cocoEval.params.iouType = "bbox"
        cocoEval.evaluate()
        cocoEval.accumulate()
        cocoEval.summarize()
        # Reporting
        results = cocoEval.stats[:3] 
        return results
        
    
    def log_result(self, results, seq=None, item=None):
        self.result_buffer[str(item).lower().strip()].append([seq, results[0], results[1], results[2]])
        
        
        
        
        
if __name__ == "__main__":  
    mcmit_coco = CholecTrack20()