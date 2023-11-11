import os
import cv2
import tempfile
from shutil import copy

#import logging
#logging.basicConfig(level=logging.DEBUG)

class Detector:
    def __init__(self, weightsPath, fps=1):
        self.weightsPath = weightsPath
        self.fps = fps
    
    def detect(self, vidpath):
        id = os.path.splitext(os.path.basename(vidpath))[0]

        results_dir = "mydata/results/" + id + "/"
        if os.path.exists(results_dir):
            results = []
            for f in sorted(os.listdir(results_dir)):
                if f.endswith(".jpg"):
                    results.append(id + "/" + f)
            return results

        cap = cv2.VideoCapture(vidpath)
        fps = cap.get(cv2.CAP_PROP_FPS)+0.5
        
        i = 0

        with tempfile.TemporaryDirectory() as tmpdir:
            i_frame = 0
            while True:
                i_frame += 1
                # read one frame (and "return" status)
                ret, frame = cap.read()
                
                # exit if error (check it because it doesn't rise error when it has problem to read)
                if not ret:
                    break
                
                if i_frame % int(fps / self.fps + 0.5) != 0:   # take fps frames per second
                    continue

                cv2.imwrite(tmpdir + f"/{id}_{i:06d}.jpg", frame)
                i += 1

            tmpfile = tmpdir + '/results.txt'
            
            ret = os.system(f"python detect.py --source {tmpdir} --weights {self.weightsPath} --img 640 --project mydata/results --name {id} > {tmpfile} 2>&1 ")

            if ret != 0:
                raise Exception("Внутренняя ошибка")

            copy(tmpfile, results_dir + "/result.txt")

            results = []
            frames = []
            with open(tmpfile, encoding='utf-8') as f:
                i_frame = 0
                for line in f:
                    if line.startswith("image "):
                        i_frame += 1
                        path = line.split()[2][:-1]
                        if "(no detections)" in line:
                            os.remove(results_dir + os.path.basename(path))
                        else:
                            path = line.split()[2][:-1]
                            results.append(id + "/" + os.path.basename(path))
                            frames.append(i_frame)
            
            # filter out single detections
            best_results = []
            for i in range(len(frames)-1):
                if frames[i+1] == frames[i]+1:
                    best_results.append(results[i])
                elif i > 0 and frames[i] == frames[i-1]+1:
                    best_results.append(results[i])
            if len(frames) >= 2 and frames[-1] == frames[-2] + 1:
                best_results.append(results[-1])
        
        # close input stream
        cap.release()

        return best_results