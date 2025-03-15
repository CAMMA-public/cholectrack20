VIDEO_TO_EVAL=[1,6,7,12,23,25,39,92,111]
GT_FOLDER='/path/to/CholecTrack20/dataset/'
GT_LOC_FORMAT='{gt_folder}/{split}/{seq}/{seq}.json'
SPLIT='testing'
DET_PATH='/path/to/detection/files'

MODEL='yolov7'
python eval.py \
    --GT_ROOT $GT_FOLDER \
    --GT_LOC_FORMAT $GT_LOC_FORMAT \
    --SPLIT $SPLIT \
    --MODEL_NAME $MODEL \
    --DET_ROOT ${DET_PATH}/${MODEL} \
    --OUTPUT_FILE "/path/to/write/output/result.txt" \
    --CONDITIONS "each" \ # valid : bleeding, blurred', smoke, crowded, occluded, reflection, stainedlens, undercoverage, clear, None
    --VIDEO_TO_EVAL 1,6,7,12,25,39,92,111 \
    --FPS 25