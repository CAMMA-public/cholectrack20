import os
import csv
import sys
import json
import traceback
import configparser
import numpy as np
from scipy.optimize import linear_sum_assignment
from ._base_dataset import _BaseDataset
from .. import utils
from .. import _timing
from ..utils import TrackEvalException


class CholecTrack2DBox(_BaseDataset):
    """Dataset class for CholecTrack20 2D bounding box tracking"""

    @staticmethod
    def get_default_dataset_config():
        """Default class config values"""
        code_path = utils.get_code_path()
        default_config = {
            'GT_FOLDER': os.path.join(code_path, 'data/CholecTrack20/'),  # Location of GT data
            'GT_LOC_FORMAT': "{gt_folder}/{split}/{seq}/{seq}.json",  # gt label identifier per video            
            'TRACKERS_FOLDER': os.path.join(code_path, 'data/trackers/CTK20/'),  # Trackers location
            'TRACKER_SUB_FOLDER': 'labels',  # Tracker files are in TRACKER_FOLDER/tracker_name/TRACKER_SUB_FOLDER
            'TRACKERS_TO_EVAL': None,  # Filenames of trackers to eval (if None, all in folder)
            'TRACKER_DISPLAY_NAMES': None,  # Names of trackers to display, if None: TRACKERS_TO_EVAL                        
            'OUTPUT_FOLDER': None,  # Where to save eval results (if None, same as TRACKERS_FOLDER)
            'OUTPUT_SUB_FOLDER': '',  # Output files are saved in OUTPUT_FOLDER/tracker_name/OUTPUT_SUB_FOLDER            
            'BENCHMARK': 'CTK20',  # Valid: 'CTK20'
            'TRACK_TYPE': 'intraoperative_track',  # Valid: 'intraoperative_track', 'intracorporeal_track', 'visibility_track'
            'IMAGE_HEIGHT': 480,
            'IMAGE_WIDTH': 854,
            'VISUAL_CHALLENGE': '',
            'VALID_VISUAL_CHALLENGES': ['blurred', 'bleeding', 'crowded', 'occluded', 'reflection', 'smoke', 'stainedlens', 'undercoverage', 'none', "all"],
            'CLASSES_TO_EVAL': ['grasper','bipolar','hook', 'scissors','clipper','irrigator','specimen-bag'],
            'VALID_CLASSES': {0:'grasper', 1:'bipolar', 2:'hook', 3:'scissors', 4:'clipper', 5:'irrigator', 6:'specimen-bag', -1:'combine'},
            'COMBINE_CLASSES': False,
            'SEQ_TO_EVAL': '1,6,7,12,25,39,92,111', # comma sep videos to eval
            'VALID_SEQS': '1,2,4,6,7,11,12,13,17,23,25,30,31,37,39,92,96,103,110,111', # all videos            
            'SPLIT_TO_EVAL': 'testing',  # validation: 'training', 'testing', 'all'
            'INPUT_AS_ZIP': False,  # Whether tracker input files are zipped
            'PRINT_CONFIG': True,  # Whether to print current config
            'DO_PREPROC': True,  # Whether to perform preprocessing        
            'SEQMAP_FOLDER': None,  # Where seqmaps are found (if None, GT_FOLDER/seqmaps)
            'SEQMAP_FILE': None,  # Directly specify seqmap file (if none use seqmap_folder/benchmark-split_to_eval)
            'SEQ_INFO': None,  # If not None, directly specify sequences to eval and their number of timesteps            
            'SKIP_SPLIT_FOL': False,  # If False, data is in GT_FOLDER/BENCHMARK-SPLIT_TO_EVAL/ and in
                                      # TRACKERS_FOLDER/BENCHMARK-SPLIT_TO_EVAL/tracker/
                                      # If True, then the middle 'benchmark-split' folder is skipped for both.
        }
        return default_config

    def __init__(self, config=None):
        """Initialise dataset, checking that all required files are present"""
        super().__init__()
        # Fill non-given config values with defaults
        self.config = utils.init_config(config, self.get_default_dataset_config(), self.get_name())

        # Dataset: get classes to eval
        self.benchmark   = self.config['BENCHMARK']
        self.subset      = self.config['SPLIT_TO_EVAL']
        self.trackidtype = self.config['TRACK_TYPE']        
        self.img_scaler  = [self.config['IMAGE_WIDTH'], self.config['IMAGE_HEIGHT'], self.config['IMAGE_WIDTH'], self.config['IMAGE_HEIGHT']]            
        self.valid_class_numbers = list(self.config['VALID_CLASSES'].keys())
        self.valid_class_names   = list(self.config['VALID_CLASSES'].values())
        self.class_name_to_class_id = {v:k for k,v in self.config['VALID_CLASSES'].items()}
        self.should_classes_combine = self.config['COMBINE_CLASSES']
        self.class_list  = [cls.lower() if cls.lower() in self.config['VALID_CLASSES'].values() else None for cls in self.config['CLASSES_TO_EVAL']]
        if not all(self.class_list):
            raise TrackEvalException('Attempted to evaluate an invalid class..')
        print("Eval Through Visual Challenge:", self.config['VISUAL_CHALLENGE'])
         
        if not isinstance(self.config['VISUAL_CHALLENGE'], list): 
            self.config['VISUAL_CHALLENGE'] = str(self.config['VISUAL_CHALLENGE']).split(",")
        self.config['VISUAL_CHALLENGE'] = ["all" if not len(i) else str(i).lower() for i in self.config['VISUAL_CHALLENGE']]
        self.valid_visual_challenges = [x for x in self.config['VALID_VISUAL_CHALLENGES'] if x not in ("all", "none")]  
        self.visual_challenge = [vc if vc in self.config['VALID_VISUAL_CHALLENGES'] else None for vc in self.config['VISUAL_CHALLENGE']]
        if not all(self.visual_challenge):
            raise TrackEvalException("Incorrect Visual challenge. Valid options : "+", ".join(self.config['VALID_VISUAL_CHALLENGES']))
        
        # Groundtruth: get sequences to eval and check gt files exist and get sequence info
        self.seq_lengths  = {}
        self.seq_timesteps= {}
        self.gt_fol       = self.config['GT_FOLDER']
        self.valid_seqs   = self.config['VALID_SEQS'] # valid video ids
        self.seqs_to_eval = self.valid_seqs if self.config['SEQ_TO_EVAL'] == 'all' else str(self.config['SEQ_TO_EVAL'])
        self.seq_list     = ["VID{:0>2d}".format(int(x)) if x in self.valid_seqs.split(",") else None for x in self.seqs_to_eval.split(",")]
        if len(self.seq_list) < 1:
            raise TrackEvalException('No sequences are selected to be evaluated.')
        if not all(self.seq_list):
            raise TrackEvalException('Attempted to evaluate an invalid video id..')
        for seq in self.seq_list:
            curr_file = self.config["GT_LOC_FORMAT"].format(gt_folder=self.gt_fol, split=self.subset, seq=seq)
            if not os.path.isfile(curr_file):
                print('GT file not found ' + curr_file)
                raise TrackEvalException('GT file not found for sequence: ' + seq)
            else:
                seq_frames = self.filter_frames(curr_file, self.visual_challenge)
                ordered_seq_frames      = sorted(list(map(int, seq_frames)))
                self.seq_timesteps[seq] = {t:str(int(float(osf))) for t, osf in enumerate(ordered_seq_frames)}
                self.seq_lengths[seq]   = len(seq_frames)
        
        # Prediction: get tracker folders and trackers to eval and check the track output files exist
        self.tracker_fol     = self.config['TRACKERS_FOLDER']
        self.tracker_sub_fol = self.config['TRACKER_SUB_FOLDER']
        self.tracker_list    = os.listdir(self.tracker_fol) if self.config['TRACKERS_TO_EVAL'] is None else self.config['TRACKERS_TO_EVAL']
        if self.config['TRACKER_DISPLAY_NAMES'] is None:
            self.tracker_to_disp = dict(zip(self.tracker_list, self.tracker_list))
        elif (self.config['TRACKERS_TO_EVAL'] is not None) and (len(self.config['TRACKER_DISPLAY_NAMES']) == len(self.tracker_list)):
            self.tracker_to_disp = dict(zip(self.tracker_list, self.config['TRACKER_DISPLAY_NAMES']))
        else:
            raise TrackEvalException('List of tracker files and tracker display names do not match.')
        for tracker in self.tracker_list:
            for seq in self.seq_list:
                curr_file = os.path.join(self.tracker_fol, tracker, self.tracker_sub_fol, seq + '.txt')
                if not os.path.isfile(curr_file):
                    print('Tracker file not found: ' + curr_file)
                    raise TrackEvalException('Tracker file not found: ' + os.path.join(tracker, self.tracker_sub_fol, os.path.basename(curr_file)))

        # Results: get output folders
        self.output_fol     = self.config['OUTPUT_FOLDER']
        self.output_sub_fol = self.config['OUTPUT_SUB_FOLDER']
        if self.output_fol is None:
            self.output_fol = os.path.join(self.tracker_fol, "track_results")
            os.makedirs(self.output_fol, exist_ok=True)

        # Others
        self.use_super_categories = False
        self.data_is_zipped = self.config['INPUT_AS_ZIP']
        self.do_preproc = self.config['DO_PREPROC']


    def filter_frames(self, curr_file, cond=['all']):
        anns = json.load(open(curr_file, "rb"))['annotations']
        # seq_frames = [k for k, value in anns.items() if np.any([v.get(cond, 0) for v in value])] if cond else anns.keys()
        if cond == ['all']:
            seq_frames = anns.keys()
        elif cond == ['none']:
            seq_frames = [k for k, value in anns.items() if not np.any([np.sum([v.get(c, 0) for c in self.valid_visual_challenges]) for v in value])] 
        else:
            seq_frames = [k for k, value in anns.items() if np.any([np.sum([v.get(c, 0) for c in cond]) for v in value])]       
        return seq_frames
    


    def get_display_name(self, tracker):
        return self.tracker_to_disp[tracker]


    def _load_ctk20_json_file(self, file):
        """ Function that loads data which is in a commonly used text file format.
        Assumes each det is given by one row of a text file.
        There is no limit to the number or meaning of each column,
        however one column needs to give the timestep of each det (time_col) which is default col 0.
        
        Returns read_data and ignore_data.
        Each is a dict (with keys as timesteps as strings) of lists (over dets) of lists (over column values).
        Note that all data is returned as strings, and must be converted to float/int later if needed.
        Note that timesteps will not be present in the returned dict keys if there are no dets for them
        """
        read_data = {}
        crowd_ignore_data = {}
        try:
            fp = open(file, "rb")
            fp.seek(0, os.SEEK_END)            
            if fp.tell(): # check if file is empty
                fp.seek(0)                
                reader = json.load(fp)['annotations']      
                print("[INFO] GT has {} frames".format(len(reader)))
                for timestep, records in reader.items():
                    try:
                        rows = [ [
                                    int(timestep),
                                    record.pop(self.trackidtype),
                                    *[j*k for j,k in zip(record.pop('tool_bbox'), self.img_scaler)],
                                    record.pop("score"),
                                    record.pop("instrument"),
                                 ] for record in records]
                        timestep = str(int(float(timestep)))
                        read_data[timestep] = rows
                    except Exception:
                        exc_str_init = 'In file %s the following line cannot be read correctly: \n' % os.path.basename(
                            file)
                        exc_str = ' '.join([exc_str_init, timestep])
                        raise TrackEvalException(exc_str)
            fp.close()
        except Exception:
            print('Error loading file: %s, printing traceback.' % file)
            traceback.print_exc()
            raise TrackEvalException('File %s cannot be read because it is either not present or invalidly formatted' % os.path.basename(file))
        return read_data, crowd_ignore_data
    
    
    def _load_raw_file(self, tracker, seq, is_gt):
        """Load a file (gt or tracker) in the CTK20 2D box format

        If is_gt, this returns a dict which contains the fields:
        [gt_ids, gt_classes] : list (for each timestep) of 1D NDArrays (for each det).
        [gt_dets, gt_crowd_ignore_regions]: list (for each timestep) of lists of detections.
        [gt_extras] : list (for each timestep) of dicts (for each extra) of 1D NDArrays (for each det).

        if not is_gt, this returns a dict which contains the fields:
        [tracker_ids, tracker_classes, tracker_confidences] : list (for each timestep) of 1D NDArrays (for each det).
        [tracker_dets]: list (for each timestep) of lists of detections.
        """
        # File location
        if is_gt:
            file = self.config["GT_LOC_FORMAT"].format(gt_folder=self.gt_fol, seq=seq, split=self.subset,)
            read_data, ignore_data = self._load_ctk20_json_file(file)
        else:
            file = os.path.join(self.tracker_fol, tracker, self.tracker_sub_fol, seq + '.txt')
            read_data, ignore_data = self._load_simple_text_file(file, is_zipped=self.data_is_zipped, zip_file=None)
                        
            read_copy = dict()
            for k, v in read_data.items():
                read_copy[str(int(k))] = v
            read_data = read_copy
            
        # Convert data to required format
        num_timesteps = self.seq_lengths[seq]
        data_keys     = ['ids', 'classes', 'dets']
        if is_gt:
            data_keys += ['gt_crowd_ignore_regions', 'gt_extras']
        else:
            data_keys += ['tracker_confidences']
        raw_data = {key: [None] * num_timesteps for key in data_keys}

        # Evaluate only annotated 25 fps frames      
        annotated_time_keys_dict = self.seq_timesteps[seq]
                
        for t in range(num_timesteps):
            time_key = annotated_time_keys_dict[t]
            if time_key in read_data.keys():
                try:
                    time_data = np.asarray(read_data[time_key], dtype=np.float)
                except ValueError:
                    if is_gt:
                        raise TrackEvalException('Cannot convert gt data for sequence %s to float. Is data corrupted?' % seq)
                    else:
                        raise TrackEvalException('Cannot convert tracking data from tracker %s, sequence %s to float. Is data corrupted?' % (tracker, seq))
                try:
                    raw_data['dets'][t] = np.atleast_2d(time_data[:, 2:6])
                    raw_data['ids'][t] = np.atleast_1d(time_data[:, 1]).astype(int)
                except IndexError:
                    if is_gt:
                        err = 'Cannot load gt data from sequence %s, because there is not enough columns in the data.' % seq
                        raise TrackEvalException(err)
                    else:
                        err = 'Cannot load tracker data from tracker %s, sequence %s, because there is not enough columns in the data.' % (tracker, seq)
                        raise TrackEvalException(err)
                if time_data.shape[1] >= 8:
                    raw_data['classes'][t] = np.atleast_1d(time_data[:, 7]).astype(int)
                else:
                    if not is_gt:
                        raw_data['classes'][t] = np.ones_like(raw_data['ids'][t])
                    else:
                        raise TrackEvalException('GT data is not in a valid format, there is not enough rows in seq %s, timestep %i.' % (seq, t))
                if is_gt:
                    gt_extras_dict = {'zero_marked': np.atleast_1d(time_data[:, 6].astype(int))}
                    raw_data['gt_extras'][t] = gt_extras_dict
                else:
                    raw_data['tracker_confidences'][t] = np.atleast_1d(time_data[:, 6])
            else:
                pass
                raw_data['dets'][t] = np.empty((0, 4))
                raw_data['ids'][t] = np.empty(0).astype(int)
                raw_data['classes'][t] = np.empty(0).astype(int)
                if is_gt:
                    gt_extras_dict = {'zero_marked': np.empty(0)}
                    raw_data['gt_extras'][t] = gt_extras_dict
                else:
                    raw_data['tracker_confidences'][t] = np.empty(0)
            if is_gt:
                raw_data['gt_crowd_ignore_regions'][t] = np.empty((0, 4))

        if is_gt:
            key_map = {'ids': 'gt_ids', 'classes': 'gt_classes', 'dets': 'gt_dets'}
        else:
            key_map = {'ids': 'tracker_ids', 'classes': 'tracker_classes', 'dets': 'tracker_dets'}
        for k, v in key_map.items():
            raw_data[v] = raw_data.pop(k)
        raw_data['num_timesteps'] = num_timesteps
        raw_data['seq'] = seq
        return raw_data
    
    
    
    @_timing.time
    def get_preprocessed_seq_data(self, raw_data, cls):
        """ Preprocess data for a single sequence for a single class ready for evaluation.
        Inputs:
             - raw_data is a dict containing the data for the sequence already read in by get_raw_seq_data().
             - cls is the class to be evaluated.
        Outputs:
             - data is a dict containing all of the information that metrics need to perform evaluation.
                It contains the following fields:
                    [num_timesteps, num_gt_ids, num_tracker_ids, num_gt_dets, num_tracker_dets] : integers.
                    [gt_ids, tracker_ids, tracker_confidences]: list (for each timestep) of 1D NDArrays (for each det).
                    [gt_dets, tracker_dets]: list (for each timestep) of lists of detections.
                    [similarity_scores]: list (for each timestep) of 2D NDArrays.
        Notes:
            General preprocessing (preproc) occurs in 4 steps. Some datasets may not use all of these steps.
                1) Extract only detections relevant for the class to be evaluated (including distractor detections).
                2) Match gt dets and tracker dets. Remove tracker dets that are matched to a gt det that is of a
                    distractor class, or otherwise marked as to be removed.
                3) Remove unmatched tracker dets if they fall within a crowd ignore region or don't meet a certain
                    other criteria (e.g. are too small).
                4) Remove gt dets that were only useful for preprocessing and not for actual evaluation.
            After the above preprocessing steps, this function also calculates the number of gt and tracker detections
                and unique track ids. It also relabels gt and tracker ids to be contiguous and checks that ids are
                unique within each timestep.

        MCholecTrack20:
                1) There is six class to be evaluated, and all the classes are used for preproc.
                2) Any class marked as distractor is removed.
                3) There is no crowd ignore regions.
        """
        # Check that input data has unique ids
        self._check_unique_ids(raw_data)
        
        distractor_class_names = ['trocar', 'stapler', 'probe', 'needle', 'clip']
        distractor_class_names = [] if cls.lower()=='combine' else [k for k in self.valid_class_names if k.lower() != cls.lower()] 
        distractor_classes = [self.class_name_to_class_id[x] for x in distractor_class_names]
        cls_id = self.class_name_to_class_id[cls]
        

        data_keys = ['gt_ids', 'tracker_ids', 'gt_dets', 'tracker_dets', 'tracker_confidences', 'similarity_scores']
        data = {key: [None] * raw_data['num_timesteps'] for key in data_keys}
        unique_gt_ids = []
        unique_tracker_ids = []
        num_gt_dets = 0
        num_tracker_dets = 0
        for t in range(raw_data['num_timesteps']):

            # Get all data
            gt_ids = raw_data['gt_ids'][t]
            gt_dets = raw_data['gt_dets'][t]
            gt_classes = raw_data['gt_classes'][t]
            gt_zero_marked = raw_data['gt_extras'][t]['zero_marked']

            tracker_ids = raw_data['tracker_ids'][t]
            tracker_dets = raw_data['tracker_dets'][t]
            tracker_classes = raw_data['tracker_classes'][t]
            tracker_confidences = raw_data['tracker_confidences'][t]
            similarity_scores = raw_data['similarity_scores'][t]

            # Evaluation for valid classes
            if len(tracker_classes) > 0 and np.max(tracker_classes) > 7:
                raise TrackEvalException(
                    'Evaluation is only valid for cholecysectomy tool class. Non cholec tool class (%i) found in sequence %s at '
                    'timestep %i.' % (np.max(tracker_classes), raw_data['seq'], t))

            # Match tracker and gt dets (with hungarian algorithm) and remove tracker dets which match with gt dets
            # which are labeled as belonging to a distractor class.
            to_remove_tracker = np.array([], np.int)
            if self.do_preproc and self.benchmark != 'ROUGH' and gt_ids.shape[0] > 0 and tracker_ids.shape[0] > 0:

                # Check all classes are valid:
                invalid_classes = np.setdiff1d(np.unique(gt_classes), self.valid_class_numbers)
                if len(invalid_classes) > 0:
                    print(' '.join([str(x) for x in invalid_classes]))
                    raise(TrackEvalException('Attempting to evaluate using invalid gt classes. '
                                             'This warning only triggers if preprocessing is performed, '
                                             'Please either check your gt data, or disable preprocessing. '
                                             'The following invalid classes were found in timestep ' + str(t) + ': ' +
                                             ' '.join([str(x) for x in invalid_classes])))

                matching_scores = similarity_scores.copy()
                matching_scores[matching_scores < 0.5 - np.finfo('float').eps] = 0
                match_rows, match_cols = linear_sum_assignment(-matching_scores)
                actually_matched_mask = matching_scores[match_rows, match_cols] > 0 + np.finfo('float').eps
                match_rows = match_rows[actually_matched_mask]
                match_cols = match_cols[actually_matched_mask]

                is_distractor_class = np.isin(gt_classes[match_rows], distractor_classes)
                to_remove_tracker = match_cols[is_distractor_class]

            # Apply preprocessing to remove all unwanted tracker dets.
            data['tracker_ids'][t] = np.delete(tracker_ids, to_remove_tracker, axis=0)
            data['tracker_dets'][t] = np.delete(tracker_dets, to_remove_tracker, axis=0)
            data['tracker_confidences'][t] = np.delete(tracker_confidences, to_remove_tracker, axis=0)
            similarity_scores = np.delete(similarity_scores, to_remove_tracker, axis=1)
            
            
            # Remove gt detections not in the considered classes
            if cls_id == -1:
                gt_to_keep_mask = np.ones_like(gt_classes, dtype=bool) # keep all and eval as a single class
            else:
                gt_to_keep_mask = (np.not_equal(gt_zero_marked, 0)) & (np.equal(gt_classes, cls_id)) # keep specific class
            data['gt_ids'][t] = gt_ids[gt_to_keep_mask]
            data['gt_dets'][t] = gt_dets[gt_to_keep_mask, :]
            data['similarity_scores'][t] = similarity_scores[gt_to_keep_mask]

            unique_gt_ids += list(np.unique(data['gt_ids'][t]))
            unique_tracker_ids += list(np.unique(data['tracker_ids'][t]))
            num_tracker_dets += len(data['tracker_ids'][t])
            num_gt_dets += len(data['gt_ids'][t])

        # Re-label IDs such that there are no empty IDs
        if len(unique_gt_ids) > 0:
            unique_gt_ids = np.unique(unique_gt_ids)
            gt_id_map = np.nan * np.ones((np.max(unique_gt_ids) + 1))
            gt_id_map[unique_gt_ids] = np.arange(len(unique_gt_ids))
            for t in range(raw_data['num_timesteps']):
                if len(data['gt_ids'][t]) > 0:
                    data['gt_ids'][t] = gt_id_map[data['gt_ids'][t]].astype(np.int)
        if len(unique_tracker_ids) > 0:
            unique_tracker_ids = np.unique(unique_tracker_ids)
            tracker_id_map = np.nan * np.ones((np.max(unique_tracker_ids) + 1))
            tracker_id_map[unique_tracker_ids] = np.arange(len(unique_tracker_ids))
            for t in range(raw_data['num_timesteps']):
                if len(data['tracker_ids'][t]) > 0:
                    data['tracker_ids'][t] = tracker_id_map[data['tracker_ids'][t]].astype(np.int)

        # Record overview statistics.
        data['num_tracker_dets'] = num_tracker_dets
        data['num_gt_dets'] = num_gt_dets
        data['num_tracker_ids'] = len(unique_tracker_ids)
        data['num_gt_ids'] = len(unique_gt_ids)
        data['num_timesteps'] = raw_data['num_timesteps']
        data['seq'] = raw_data['seq']

        # Ensure again that ids are unique per timestep after preproc.
        self._check_unique_ids(data, after_preproc=True)

        return data

    def _calculate_similarities(self, gt_dets_t, tracker_dets_t):
        similarity_scores = self._calculate_box_ious(gt_dets_t, tracker_dets_t, box_format='xywh')
        return similarity_scores
