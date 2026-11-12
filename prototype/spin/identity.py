"""Identity continuity annotations, without changing upstream predictions.

A visibility recovery is a point prediction, not verified physical re-identification.
Every native model-hidden interval breaks the claimed continuity; no fitted gap
length or video-specific threshold is used. Raw visible predictions remain available.
"""


def continuity_annotations(times, visible, names):
    if len(times)!=len(visible) or any(len(row)!=len(names) for row in visible):
        raise ValueError('Visibility dimensions do not match timestamps and names')
    queries=[]
    for j,name in enumerate(names):
        first_hidden=next((i for i,row in enumerate(visible) if not row[j]),None)
        fragments=[]
        for i,(t,row) in enumerate(zip(times,visible)):
            if not row[j]:continue
            status='identity_unverified_after_visibility_loss' if first_hidden is not None and i>first_hidden else 'continuous_model_observations_from_seed'
            if not fragments or fragments[-1]['end_index']!=i-1:
                fragments.append({'start_index':i,'end_index':i,'start_s':t,'end_s':t,'status':status})
            else:fragments[-1].update(end_index=i,end_s=t)
        queries.append({'point_name':name,'first_hidden_index':first_hidden,'fragments':fragments,
                        'physical_identity_verified':False})
    return {'policy':'Native model visibility loss breaks identity continuity. Reappearances remain unverified; raw predictions are neither discarded nor reassigned.',
            'queries':queries,'predictions_modified':False}
