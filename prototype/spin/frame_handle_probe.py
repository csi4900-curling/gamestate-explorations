"""Reusable development probe: independent-frame handle masks, never CoTracker.

The colour baseline segments the coloured cap too; it is intentionally a
baseline, not a trained grip detector. Florence supplies unverified referring
segmentation. Neither backend certifies physical handle orientation.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
import resource
import time

import cv2
import numpy as np

from prototype.spin.signed_rotation import summarize


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def mask_axis(mask):
    y, x = np.nonzero(mask)
    if len(x) < 3:
        return None
    corners = cv2.boxPoints(cv2.minAreaRect(np.column_stack([x, y]).astype(np.float32)))
    edges = np.roll(corners, -1, axis=0)-corners
    i = int(np.argmax(np.linalg.norm(edges, axis=1)))
    if np.linalg.norm(edges[i]) < 2:
        return None
    return np.array([corners[i], corners[(i+1) % 4]])


def obb_axis(corners):
    """Select the lower of the opposite long box edges, as the paper does."""
    corners = np.asarray(corners,float)
    if corners.shape != (4,2) or not np.isfinite(corners).all():
        raise ValueError('Four finite OBB corners required')
    lengths = np.linalg.norm(np.roll(corners,-1,axis=0)-corners,axis=1)
    i = int(np.argmax(lengths))
    opposite = (i+2)%4
    if np.mean(corners[[opposite,(opposite+1)%4],1]) > np.mean(corners[[i,(i+1)%4],1]):
        i = opposite
    return corners[[i,(i+1)%4]]


def run(config_path, output):
    cfg = json.loads(Path(config_path).read_text())
    output = Path(output)
    output.mkdir(exist_ok=False)
    started = time.perf_counter()
    job = Path(cfg['observation_job'])
    bundle = json.loads((job/'camera-calibration.json').read_text())
    if sha(cfg['video']) != bundle['source_sha256']:
        raise ValueError('Source/calibration mismatch')
    records = []
    for line in (job/'observations/match-observations.jsonl').open():
        row = json.loads(line)
        if cfg['interval_s'][0]-.2 <= row['time_s'] <= cfg['interval_s'][1]+.2:
            board = row['boards'][cfg['panel']]
            stones = [s for s in board['stones'] if s.get('tracker_id') == cfg['tracker_id']]
            if len(stones) == 1:
                records.append((row['time_s'], stones[0]['bbox_xyxy'], board['registration']))
    if not records:
        raise ValueError('No saved candidate observations')
    record = bundle['calibrations'][0]['panels'][cfg['panel']]
    P = np.array(record['camera_model']['projection_xyz_up_to_normalized_source'])
    S = np.diag([1/3., 1/3., 1.])
    model = processor = torch = obb_model = None
    load_s = 0.
    if cfg['backend'] == 'florence':
        import torch
        from transformers import AutoProcessor, Florence2ForConditionalGeneration
        torch.set_num_threads(cfg['threads'])
        load_start = time.perf_counter()
        model = Florence2ForConditionalGeneration.from_pretrained(
            cfg['model_path'], torch_dtype=torch.float32, attn_implementation='eager',
            local_files_only=True).eval()
        processor = AutoProcessor.from_pretrained(cfg['model_path'], local_files_only=True)
        load_s = time.perf_counter()-load_start
    elif cfg['backend'] == 'yolo_obb':
        import torch
        from ultralytics import YOLO
        torch.set_num_threads(cfg['threads'])
        if not Path(cfg['model_path']).is_file():
            raise ValueError('Explicit trained handle checkpoint required')
        load_start = time.perf_counter()
        obb_model = YOLO(cfg['model_path'])
        if obb_model.task != 'obb' or set(obb_model.names.values()) != {'red_handle','yellow_handle'}:
            raise ValueError('Expected specialized red/yellow handle OBB checkpoint')
        load_s = time.perf_counter()-load_start
    elif cfg['backend'] != 'colour_minrect':
        raise ValueError('Unsupported backend')
    cv2.setNumThreads(cfg['threads'])
    cap = cv2.VideoCapture(cfg['video'])
    if not cap.isOpened():
        raise ValueError('Cannot open source')
    fps = cap.get(cv2.CAP_PROP_FPS)
    first, last = [round(x*fps) for x in cfg['interval_s']]
    selected = set(round(x*fps) for x in cfg.get('sample_times_s', []))
    cap.set(cv2.CAP_PROP_POS_FRAMES, first)
    rows, tiles = [], []
    writer = cv2.VideoWriter(str(output/'mask-review.mp4'), cv2.VideoWriter_fourcc(*'mp4v'),
                             fps if not selected else 2., (320, 350))
    if not writer.isOpened():
        raise ValueError('Cannot create review video')
    try:
        for frame_id in range(first, last):
            ok, frame = cap.read()
            if not ok or round(cap.get(cv2.CAP_PROP_POS_FRAMES))-1 != frame_id:
                raise ValueError(f'Source decode mismatch at {frame_id}')
            if selected and frame_id not in selected:
                continue
            t = frame_id/fps
            nearest = min(records, key=lambda x: abs(x[0]-t))
            row = {'time_s': t, 'frame_index': frame_id, 'angle_rad': None,
                   'status': 'source_candidate_gap', 'geometry_sample_time_s': nearest[0]}
            # Saved 10Hz box interpolation locates a crop only, never supplies angles.
            before = [r for r in records if r[0] <= t+1e-8]
            after = [r for r in records if r[0] >= t-1e-8]
            if not before or not after or after[0][0]-before[-1][0] > .15:
                rows.append(row)
                continue
            left, right = before[-1], after[0]
            f = (t-left[0])/(right[0]-left[0]) if right[0] > left[0] else 0.
            box = np.array(left[1])*(1-f)+np.array(right[1])*f
            cx, cy = (box[:2]+box[2:])/2
            side = int(math.ceil(max(box[2:]-box[:2])*cfg['crop_scale']))
            x0, y0 = int(round(cx-side/2)), int(round(cy-side/2))
            x1, y1 = x0+side, y0+side
            if x0 < 0 or y0 < 0 or x1 > frame.shape[1] or y1 > frame.shape[0]:
                row['status'] = 'crop_out_of_frame'
                rows.append(row)
                continue
            crop = frame[y0:y1, x0:x1]
            mask = np.zeros(crop.shape[:2], np.uint8)
            inference_start = time.perf_counter()
            predicted_pair = None
            if model is not None:
                from PIL import Image
                image = Image.fromarray(cv2.cvtColor(crop, cv2.COLOR_BGR2RGB))
                task = '<REFERRING_EXPRESSION_SEGMENTATION>'
                inputs = processor(text=task+cfg['prompt'], images=image, return_tensors='pt')
                with torch.inference_mode():
                    ids = model.generate(**inputs, max_new_tokens=cfg['max_new_tokens'],
                                         num_beams=cfg['num_beams'], do_sample=False)
                raw = processor.batch_decode(ids, skip_special_tokens=False)[0]
                parsed = processor.post_process_generation(raw, task=task, image_size=image.size)
                row.update(raw_generation=raw, parsed=parsed,
                           generation_budget_reached=int(ids.shape[-1]) >= cfg['max_new_tokens'])
                groups = parsed.get(task, {}).get('polygons', [])
                if len(groups) == 1 and not row['generation_budget_reached']:
                    for polygon in groups[0]:
                        pts = np.array(polygon).reshape(-1, 2).round().astype(np.int32)
                        if len(pts) >= 3:
                            cv2.fillPoly(mask, [pts], 255)
            elif obb_model is not None:
                result = obb_model.predict(crop,imgsz=cfg['imgsz'],conf=cfg['confidence'],
                                           iou=cfg['iou'],device='cpu',verbose=False)[0]
                boxes = result.obb
                row['handle_candidates'] = []
                if boxes is not None:
                    for corners,score,cls in zip(boxes.xyxyxyxy.cpu().numpy(),boxes.conf.cpu().numpy(),boxes.cls.cpu().numpy()):
                        row['handle_candidates'].append({'corners_crop_px':corners.tolist(),
                            'confidence':float(score),'class':obb_model.names[int(cls)]})
                if row['handle_candidates']:
                    chosen = max(row['handle_candidates'],key=lambda x:x['confidence'])
                    row['chosen_handle'] = chosen
                    corners = np.array(chosen['corners_crop_px'])
                    cv2.fillPoly(mask,[np.round(corners).astype(np.int32)],255)
                    predicted_pair = obb_axis(corners)
            else:
                hsv = cv2.cvtColor(crop, cv2.COLOR_BGR2HSV)
                for lower, upper in cfg['hsv_ranges']:
                    mask |= cv2.inRange(hsv, np.array(lower, np.uint8), np.array(upper, np.uint8))
            row['inference_wall_s'] = time.perf_counter()-inference_start
            pair = predicted_pair if obb_model is not None else mask_axis(mask)
            row.update(crop_source_bounds=[x0,y0,x1,y1], mask_pixels=int(np.count_nonzero(mask)),
                       status='no_mask_axis', bbox_localization='Interpolated saved ByteTrack candidate boxes; physical identity unverified')
            if pair is not None:
                pair += [x0,y0]
                row['axis_endpoints_source_px'] = pair.tolist()
                A = nearest[2].get('reference_to_current')
                if A is not None and nearest[2].get('status') == 'source_calibration_registered':
                    current = S@np.array(A)@np.linalg.inv(S)@P
                    plane = current[:,[0,1,3]].copy()
                    plane[:,2] += current[:,2]*cfg['assumed_handle_height_m']
                    H = np.linalg.inv(plane)@S
                    q = cv2.perspectiveTransform(pair[None].astype(np.float64), H)[0]
                    delta = q[1]-q[0]
                    row.update(status='unverified_mask_axis', angle_rad=float(np.arctan2(delta[1],delta[0]) % math.pi))
            tile = crop.copy()
            tile[mask > 0] = (tile[mask > 0]*.5+np.array([0,255,0])*.5).astype(np.uint8)
            if pair is not None:
                local = np.round(pair-[x0,y0]).astype(int)
                cv2.line(tile,tuple(local[0]),tuple(local[1]),(255,0,255),1)
            tile = cv2.resize(tile, (320,320), interpolation=cv2.INTER_NEAREST)
            tile = cv2.copyMakeBorder(tile,30,0,0,0,cv2.BORDER_CONSTANT,value=(255,255,255))
            label = f'{t:.3f}s | '+(f'{math.degrees(row["angle_rad"]):.1f} deg' if row['angle_rad'] is not None else row['status'])
            cv2.putText(tile,label,(5,20),cv2.FONT_HERSHEY_SIMPLEX,.48,(0,0,0),1)
            writer.write(tile)
            if selected or (frame_id-first) % 24 == 0:
                tiles.append(tile)
            rows.append(row)
            (output/'observations.json').write_text(json.dumps(rows,indent=2)+'\n')
            if selected or len(rows) % 30 == 0:
                print(f'{len(rows)} samples; last={t:.3f}; inference={row["inference_wall_s"]:.2f}s',flush=True)
    finally:
        cap.release()
        writer.release()
    (output/'observations.json').write_text(json.dumps(rows,indent=2)+'\n')
    if tiles:
        sheet = np.full((math.ceil(len(tiles)/3)*350,960,3),255,np.uint8)
        for i,tile in enumerate(tiles):
            sheet[i//3*350:(i//3+1)*350,i%3*320:(i%3+1)*320] = tile
        cv2.imwrite(str(output/'mask-review.png'),sheet)
    result = {'development':True, 'config':cfg, 'source_sha256':bundle['source_sha256'],
              'samples':len(rows), 'angles_available':sum(r['angle_rad'] is not None for r in rows),
              'wall_s':time.perf_counter()-started,'model_load_wall_s':load_s,
              'inference_wall_s':sum(r.get('inference_wall_s',0) for r in rows),
              'peak_rss_mib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/1024,
              'code_sha256':{str(p):sha(p) for p in [Path(__file__),Path(__file__).with_name('signed_rotation.py')]},
              'config_sha256':sha(config_path),'calibration_sha256':sha(job/'camera-calibration.json'),
              'model_sha256':sha(cfg['model_path']) if obb_model is not None else None,
              'observations_sha256':sha(job/'observations/match-observations.jsonl'),
              'orientation':summarize([r['time_s'] for r in rows],[r['angle_rad'] for r in rows]),
              'scope':'Independent-frame mask-axis probe, not validated grip orientation. No CoTracker, manual angle seeds, calibration refit, monotonic direction prior, or gap filling. Sparse samples cannot establish dense count.'}
    (output/'result.json').write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
    print(json.dumps({k:result[k] for k in ['samples','angles_available','wall_s','inference_wall_s','peak_rss_mib']}),flush=True)
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config',required=True)
    parser.add_argument('--output',required=True)
    args = parser.parse_args()
    run(args.config,args.output)
