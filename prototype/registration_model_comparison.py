"""Development comparison of upstream camera transforms on shared SIFT matches.

References are explicit source-image landmark annotations, never fitted rink
coordinates. This command neither changes nor selects the production estimator.
"""
import argparse
import json
from pathlib import Path
import sys
import time

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from camera_geometry import features
from prototype.detection_cache import digest


def compare(reference_path, output):
    reference_path, output = Path(reference_path), Path(output)
    if output.exists():
        raise ValueError('Preserve existing comparison')
    spec = json.loads(reference_path.read_text())
    size = tuple(spec['normalization_size']); region = spec['region']
    def read(path):
        image = cv2.imread(path)
        if image is None:
            raise ValueError('Missing source image: '+path)
        return cv2.resize(image, size)
    cv2.setNumThreads(2); cv2.setRNGSeed(0)
    ka, da = features(read(spec['reference_image']), region)
    rows = []
    for target in spec['targets']:
        started = time.perf_counter()
        kb, db = features(read(target['image']), region)
        good = [] if da is None or db is None else [m for pair in cv2.BFMatcher().knnMatch(da, db, k=2)
                  if len(pair)==2 for m,n in [pair] if m.distance < .7*n.distance]
        a = np.array([ka[m.queryIdx].pt for m in good], np.float32)
        b = np.array([kb[m.trainIdx].pt for m in good], np.float32)
        row = {'source_frame': target['source_frame'], 'matches': len(good),
               'feature_and_matching_seconds': time.perf_counter()-started, 'models': {}}
        for name in ['projective', 'affine', 'similarity']:
            start = time.perf_counter()
            if len(good)<4:
                row['models'][name]={'status':'insufficient_shared_matches'}
                continue
            # Preserve the baseline's tolerance, iteration budget and confidence.
            # Affine estimators use their upstream default refinement (10 iterations).
            if name=='projective':
                matrix, mask = cv2.findHomography(a,b,cv2.RANSAC,1.5,maxIters=2000,confidence=.995)
            else:
                estimator = cv2.estimateAffine2D if name=='affine' else cv2.estimateAffinePartial2D
                matrix, mask = estimator(a,b,method=cv2.RANSAC,ransacReprojThreshold=1.5,
                                         maxIters=2000,confidence=.995)
                if matrix is not None:
                    matrix = np.vstack([matrix,[0,0,1]])
            result={'fit_seconds':time.perf_counter()-start,'status':'fit_failed'}
            if matrix is not None and np.isfinite(matrix).all():
                names=sorted(set(spec['landmarks']) & set(target['landmarks']))
                points=np.array([spec['landmarks'][k] for k in names],float)
                predicted=cv2.perspectiveTransform(points.reshape(-1,1,2),matrix).reshape(-1,2)
                expected=np.array([target['landmarks'][k] for k in names],float)
                errors=np.linalg.norm(predicted-expected,axis=1)
                result.update(status='fitted_not_validated',matrix=matrix.tolist(),
                              inliers=int(mask.sum()),
                              unique_inlier_reference_positions=len(np.unique(a[mask.ravel().astype(bool)],axis=0)),
                              landmarks=[{'name':k,'predicted_pixel':p.tolist(),'reference_pixel':e.tolist(),
                                          'error_px':float(error)} for k,p,e,error in zip(names,predicted,expected,errors)],
                              mean_landmark_error_px=float(np.mean(errors)),
                              max_landmark_error_px=float(np.max(errors)))
            row['models'][name]=result
        rows.append(row)
    paths=[reference_path,Path(__file__),Path(__file__).with_name('camera_geometry.py'),
           Path(spec['reference_image']),*[Path(t['image']) for t in spec['targets']]]
    result={'development':True,'production_changed':False,'metric_accuracy_verified':False,
            'annotation_provenance':spec.get('annotation_provenance'),
            'estimator_settings':'Shared baseline SIFT ratio .7; RANSAC 1.5 px, 2000 iterations, .995 confidence. Affine default refinement.',
            'input_sha256':{str(p.resolve()):digest(p) for p in paths},'frames':rows}
    output.write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
    return result


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--reference',required=True);parser.add_argument('--output',required=True)
    args=parser.parse_args();compare(args.reference,args.output)
