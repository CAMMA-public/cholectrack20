
""" run_cholectrack20.py

Run example:
run_cholectrack20.py --USE_PARALLEL False --METRICS Hota --TRACKERS_TO_EVAL Lif_T

Command Line Arguments: Defaults, # Comments
    Eval arguments:
        'USE_PARALLEL': False,
        'NUM_PARALLEL_CORES': 8,
        'BREAK_ON_ERROR': True,
        'PRINT_RESULTS': True,
        'PRINT_ONLY_COMBINED': False,
        'PRINT_CONFIG': True,
        'TIME_PROGRESS': True,
        'OUTPUT_SUMMARY': True,
        'OUTPUT_DETAILED': True,
        'PLOT_CURVES': True,
    Dataset arguments:        
         'GT_FOLDER': os.path.join(code_path, 'data/gt/mot_challenge/'),  # Location of GT data
         'GT_LOC_FORMAT': "{gt_folder}/labels/{seq}.json",  # '{gt_folder}/{seq}/gt/gt.txt'
         'TRACKERS_FOLDER': os.path.join(code_path, 'data/trackers/CKT20/'),  # Trackers location
         'TRACKER_SUB_FOLDER': 'labels',  # Tracker files are in TRACKER_FOLDER/tracker_name/TRACKER_SUB_FOLDER
         'TRACKERS_TO_EVAL': None,  # Filenames of trackers to eval (if None, all in folder)
         'TRACKER_DISPLAY_NAMES': None,  # Names of trackers to display, if None: TRACKERS_TO_EVAL
         'OUTPUT_FOLDER': None,  # Where to save eval results (if None, same as TRACKERS_FOLDER)
         'OUTPUT_SUB_FOLDER': '',  # Output files are saved in OUTPUT_FOLDER/tracker_name/OUTPUT_SUB_FOLDER
         'BENCHMARK': 'CTK20',  # Valid: 'MOT17', 'MOT16', 'MOT20', 'MOT15'
         'TRACK_TYPE': 'intraoperative_track',  # Valid: 'intraoperative_track', 'intracorporeal_track', 'visibility_track
         'CLASSES_TO_EVAL': ['grasper','bipolar','hook', 'scissors','clipper','irrigator','specimen-bag'],
         'SEQ_TO_EVAL': '1,6,7,12,25,39,92,111', # comma sep videos to eval
         'SPLIT_TO_EVAL': 'testing',  # Validation, 'training', 'testing', 'all'
         'INPUT_AS_ZIP': False,  # Whether tracker input files are zipped
         'PRINT_CONFIG': True,  # Whether to print current config
         'DO_PREPROC': True,  # Whether to perform preprocessing (never done for MOT15)               
    Metric arguments:
        'METRICS': ['HOTA', 'CLEAR', 'Identity', 'VACE']
"""
        
                           
                           

import sys
import os
import argparse
from multiprocessing import freeze_support

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import trackeval  # noqa: E402


# Variables
TRACK_TYPE = 'intraoperative' #@ Choices = ['intracorporeal', 'intraoperative','visibility']
CLASSES = ['combine'] #@ Choices = ['grasper', 'bipolar','hook', 'scissors', 'clipper', 'irrigator', 'specimen-bag', 'combine']
COMBINE_CLASSES = False
VISUAL_CHALLENGE = 'all' #@ Choices = ['blurred', 'bleeding', 'crowded', 'occluded', 'reflection', 'smoke', 'stainedlens', 'undercoverage', 'all', None]

GT_FOLDER = '/path/to/CholecTrack20/Dataset/'
GT_FOLDER = '/mnt/camma5_data2/nwoye/work/dataset/CholecTrack20/RELEASE/CholecTrack20/'

TRACKERS_FOLDER = '/mnt/camma5_data2/nwoye/work/dataset/CholecTrack20/exp/tools_bbox_tracking/pub/tracking/proposed/25fps/'+TRACK_TYPE
TRACKER_SUB_FOLDER = ''
TRACKERS = ['surgitrack_fsl_bmd_wav','surgitrack_ssl_bmd_wav']

OUTPUT_FOLDER = "/mnt/camma5_data2/nwoye/work/code/experiments/tools_bbox_tracking/analysisB/outputs/results/"
OUTPUT_SUB_FOLDER = TRACK_TYPE




if __name__ == '__main__':
    freeze_support()

    # Command line interface:
    default_eval_config = trackeval.Evaluator.get_default_eval_config()
    default_eval_config['DISPLAY_LESS_PROGRESS'] = False
    default_dataset_config = trackeval.datasets.CholecTrack2DBox.get_default_dataset_config()    
    default_dataset_config['TRACKERS_TO_EVAL'] = TRACKERS
    default_dataset_config['GT_FOLDER'] = GT_FOLDER
    default_dataset_config['TRACKERS_FOLDER'] = TRACKERS_FOLDER
    default_dataset_config['CLASSES_TO_EVAL'] = CLASSES
    default_dataset_config['TRACKER_SUB_FOLDER'] = TRACKER_SUB_FOLDER
    default_dataset_config['OUTPUT_SUB_FOLDER'] = OUTPUT_SUB_FOLDER
    default_dataset_config['TRACK_TYPE'] = TRACK_TYPE+"_track"
    default_dataset_config['COMBINE_CLASSES'] = COMBINE_CLASSES
    default_dataset_config['OUTPUT_FOLDER'] = OUTPUT_FOLDER
    default_dataset_config['VISUAL_CHALLENGE'] = VISUAL_CHALLENGE
    
    
    default_metrics_config = {'METRICS': ['HOTA', 'CLEAR', 'Identity'], 'THRESHOLD': 0.5}
    # default_metrics_config = {'METRICS': ['HOTA', ], 'THRESHOLD': 0.5}
    config = {**default_eval_config, **default_dataset_config, **default_metrics_config}  # Merge default configs
    parser = argparse.ArgumentParser()
    for setting in config.keys():
        if type(config[setting]) == list or type(config[setting]) == type(None):
            parser.add_argument("--" + setting, nargs='+')
        else:
            parser.add_argument("--" + setting)
    args = parser.parse_args().__dict__
    for setting in args.keys():
        if args[setting] is not None:
            if type(config[setting]) == type(True):
                if args[setting] == 'True':
                    x = True
                elif args[setting] == 'False':
                    x = False
                else:
                    raise Exception('Command line parameter ' + setting + 'must be True or False')
            elif type(config[setting]) == type(1):
                x = int(args[setting])
            elif type(args[setting]) == type(None):
                x = None
            elif setting == 'SEQ_INFO':
                x = dict(zip(args[setting], [None]*len(args[setting])))
            else:
                x = args[setting]
            config[setting] = x
    eval_config = {k: v for k, v in config.items() if k in default_eval_config.keys()}
    dataset_config = {k: v for k, v in config.items() if k in default_dataset_config.keys()}
    metrics_config = {k: v for k, v in config.items() if k in default_metrics_config.keys()}

    # Run code
    evaluator = trackeval.Evaluator(eval_config)
    dataset_list = [trackeval.datasets.CholecTrack2DBox(dataset_config)]
    metrics_list = []
    for metric in [trackeval.metrics.HOTA, trackeval.metrics.CLEAR, trackeval.metrics.Identity, trackeval.metrics.VACE]:
        if metric.get_name() in metrics_config['METRICS']:
            metrics_list.append(metric(metrics_config))
    if len(metrics_list) == 0:
        raise Exception('No metrics selected for evaluation')
    evaluator.evaluate(dataset_list, metrics_list)
