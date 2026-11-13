"""Compare predicted image axes with explicitly supplied source annotations.

Pixel annotations are not independent physical rotation ground truth. Missing
predictions count against coverage and never disappear from the report.
"""
import argparse
import json
import math
from pathlib import Path
import numpy as np
import cv2


def axis_angle(points):
    a,b = np.array(points,float)
    d = b-a
    return math.atan2(d[1],d[0])


def evaluate(result_directory, reference_path, output):
    if Path(output).exists():
        raise ValueError('Output exists; preserve previous comparison')
    directory = Path(result_directory)
    result = json.loads((directory/'result.json').read_text())
    rows = json.loads((directory/'observations.json').read_text())
    reference = json.loads(Path(reference_path).read_text())
    if reference['source_sha256'] != result['source_sha256']:
        raise ValueError('Reference and predictions use different sources')
    comparisons, errors = [], []
    labeled = missing = 0
    for ref in reference['samples']:
        t = ref['time_s']
        row = {'time_s':t,'source_reference':ref,'prediction':None,'absolute_axial_error_deg':None}
        if ref.get('axis_endpoints_source_px') is None:
            row['status'] = 'source_reference_ambiguous'
        else:
            labeled += 1
            matches = [r for r in rows if abs(r['time_s']-t) < 1e-7]
            pair = matches[0].get('axis_endpoints_source_px') if len(matches)==1 else None
            if pair is None:
                row['status'] = 'missing_prediction'
                missing += 1
            else:
                delta = (axis_angle(pair)-axis_angle(ref['axis_endpoints_source_px'])+math.pi/2)%math.pi-math.pi/2
                error = math.degrees(abs(delta))
                row.update(status='unverified_prediction_compared',prediction=pair,absolute_axial_error_deg=error)
                row['axis_midpoint_distance_px'] = float(np.linalg.norm(
                    np.mean(pair,axis=0)-np.mean(ref['axis_endpoints_source_px'],axis=0)))
                detection = matches[0].get('chosen_handle')
                if detection is not None:
                    bounds = matches[0]['crop_source_bounds']
                    corners = np.array(detection['corners_crop_px'])+bounds[:2]
                    midpoint = tuple(np.mean(ref['axis_endpoints_source_px'],axis=0))
                    row['reference_midpoint_signed_distance_to_predicted_box_px'] = float(
                        cv2.pointPolygonTest(corners.astype(np.float32),midpoint,True))
                errors.append(error)
        comparisons.append(row)
    report = {'development':True,'reference_provenance':reference,'comparisons':comparisons,
              'reference_frames':len(comparisons),'reference_axes_available':labeled,
              'missing_predictions_on_labeled_frames':missing,
              'answer_coverage':len(errors)/labeled if labeled else None,
              'image_axis_mae_deg_among_answered':float(np.mean(errors)) if errors else None,
              'physical_revolution_accuracy':None,
              'scope':'Agent-labelled source-image comparison. An angle-only match can select the wrong object; also inspect localization. Coverage includes missing predictions. No independent physical angle/count ground truth.'}
    Path(output).write_text(json.dumps(report,indent=2,allow_nan=False)+'\n')
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--result-directory',required=True)
    parser.add_argument('--reference',required=True)
    parser.add_argument('--output',required=True)
    args = parser.parse_args()
    evaluate(args.result_directory,args.reference,args.output)
