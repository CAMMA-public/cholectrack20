### Groundtruth
- Keep the original format of the groundtruth as download

### Detections
**TEXT FILE FORMAT**:
- Produce and save detection output per video (e.g. VID01.txt). The filename should match the corresponding base file name of the groundtruth
- Each line in the text file is an object detection with 8 items formatted as:
  
  ```frameid,unused,x,y,w,h,s,c```
- keep the unused as -1 all through.
- There can be multiple objects in a frame, hence frameid can be repeated.
- It is best to keep the x,y,w,h coordinate values scaled by the height and width of the frame such that the values ranges between [0, 1]. This would still be scaled in the code.

