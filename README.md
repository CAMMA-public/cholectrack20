# CholecTrack20

**A Dataset for Multi-Class Multiple Tool Tracking in Laparoscopic Surgery**<br />
*Chinedu Innocent Nwoye,  Kareem Elgohary, Anvita Srinivas, Fauzan Zaid, Joël L. Lavanchy, and Nicolas Padoy* <br />

CVPR 2025  

[![CVPR Paper](https://img.shields.io/badge/Paper-CVPR%202025-blue)](https://doi.org/10.1016/j.media.2022.102433)
   [![Read on ArXiv](https://img.shields.io/badge/arxiv-2312.07352-red)](https://arxiv.org/abs/2312.07352) 
   [![Supplementary Material](https://img.shields.io/youtube/views/d_yHdJtCa98?label=supplementary%20video&style=social)](https://www.youtube.com/watch?v=d_yHdJtCa98&t=61s)

   
 <hr />

 ### Abstract  
<img src="images/ct20-img.png" alt="" width="330" align="right"/>
  <p align="justify">
CholecTrack20 is a surgical video dataset focusing on laparoscopic cholecystectomy and designed for surgical tool tracking, featuring 20 annotated videos. The dataset includes detailed labels for multi-class multi-tool tracking, offering trajectories for tool visibility within the camera scope, intracorporeal movement within the patient's body, and the life-long intraoperative trajectory of each tool. Annotations cover spatial coordinates, tool class, operator identity, phase, visual conditions (occlusion, bleeding, smoke), and more for tools like grasper, bipolar, hook, scissors, clipper, irrigator, and specimen bag, with annotations provided at 1 frame per second across 35K frames and 65K instance tool labels. The dataset uses official splits, allocating 10 videos for training, 2 for validation, and 8 for testing.
  </p> 


## Explore Samples


## Watch Videos


## Tools for Visualizing Annotations


## Evaluation Metrics and Libraries

>> **DetEval** - Custom code for tool detection built on COCO API for Average Precision (AP) meterics.
 [code](https://github.com/CAMMA-public/cholectrack20/tree/main/DetEval)

>> **TrackEval** - Adapted trackEval to include CholecTrack20 benchmark. The metric library is built on widely used CLEAR MOT, Identity, VACE, Track mAP, J & F, ID Euclidean, and HOTA metrics. Either you pull from original trackEval repo or you clone our adaptation 
[code](https://github.com/CAMMA-public/cholectrack20/tree/main/TrackEval)


## Detection Benchmark and Leaderboard


## Tracking Benchmark and Leaderboard


# Download

>> Read the [Data Use Agreement (DUA)]()

>> Read the [Dataset License]()

>> Complete the dataset request [Form]() to receive the download accesskey, keep it safe!

>> Visit the [download portal](Synapse.org) for download instructions and to download the data.



# Team

## Acknowledgement

This work was supported by French state funds managed within the Plan Investissements d’Avenir by the ANR under references: National AI Chair AI4ORSafety [ANR-20-CHIA-0029-01], DeepSurg [ANR-16-CE33-0009], IHU Strasbourg [ANR-10-IAHU-02] and by BPI France under references: project CONDOR, project 5G-OR. 
Joël L. Lavanchy received funding by the Swiss National Science Foundation (P500PM\_206724, P5R5PM\_217663). 
This work was granted access to the servers/HPC resources managed by CAMMA, IHU Strasbourg, Unistra Mesocentre, and GENCI-IDRIS [Grant 2021-AD011011638R3, 2021-AD011011638R4].




Metric evaluation part of the codes are borrowed from [TrackEval](https://github.com/JonathonLuiten/TrackEval) and [Cocoapi](https://github.com/cocodataset/cocoapi/blob/master/PythonAPI/pycocotools/cocoeval.py). Thanks for their excellent work!

## Publication & Citations

Conference
```
@InProceedings{nwoye2023cholectrack20,
  author    = {Nwoye, Chinedu Innocent and Elgohary , Kareem  and Srinivas, Anvita and Zaid, Fauzan and Lavanchy, Joël L.  and Padoy, Nicolas},
  title     = {CholecTrack20: A Dataset for Multi-Class Multiple Tool Tracking in Laparoscopic Surgery},
  booktitle = {Proceedings of the IEEE/CVF Conference on Computer Vision and Pattern Recognition (CVPR)},
  year      = {2025},
  month     = {June}
}
```

arXiv
```

@misc{nwoye2023cholectrack20,
    title={CholecTrack20: A Dataset for Multi-Class Multiple Tool Tracking in Laparoscopic Surgery},
    author={Chinedu Innocent Nwoye and Kareem Elgohary and Anvita Srinivas and Fauzan Zaid and Joël L. Lavanchy and Nicolas Padoy},
    year={2023},
    eprint={2312.07352},
    archivePrefix={arXiv},
    primaryClass={cs.CV}
}
```

---

<!--A endoscopic video dataset for multi-class multi-tool tracking defined across 3 different perspectives of considering the temporal duration of a tool trajectory: (a) intraoperative, (b) intracorporeal, and (c) visibility.
-->


## Contributing
We welcome contributions of new metrics and new supported benchmarks. Also any other new features or code improvements. Send a PR, an email, or open an issue detailing what you'd like to add/change to begin a conversation.
