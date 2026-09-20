"""Reconsideration Monte Carlo checks on fixed scores; CPU only, no inference.

Run with the release's locked uv environment. See evidence/REVISION-MC-PLAN.md.
The historical diagnostic driver and every historical result remain unchanged.
"""
import os
for name in ('OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS', 'MKL_NUM_THREADS'):
    os.environ[name] = '1'
import argparse
import hashlib
import json
import multiprocessing as mp
from pathlib import Path
import time
import numpy as np
from numba import njit
import strategy_diagnostics as old

ROOT = Path(__file__).resolve().parents[1]
ARMS = ['trial', 'speaker_attack', 'speaker_only']
PAIRS = np.array(old.PAIRS)
DIAG = json.loads((ROOT/'evidence/diagnostics.json').read_text())
HATS = np.array([DIAG['results']['trial']['pairs'][p]['hat'] for p in old.KEYS])
MASKS = {'all': np.ones(28, dtype=bool), 'ssl': PAIRS[:,1] < 4,
         'organizer': PAIRS[:,0] >= 4, 'cross': (PAIRS[:,0] < 4) & (PAIRS[:,1] >= 4)}

def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def summary(a):
    d = a[:, PAIRS[:,0]] - a[:, PAIRS[:,1]]
    sd = d.std(axis=0, ddof=1)
    q = float(np.quantile(np.max(abs(d-d.mean(axis=0))/sd, axis=1), .95))
    return sd, q, abs(HATS) > q*sd

def counts(flags):
    return {k: int(flags[v].sum()) for k,v in MASKS.items()}

def conditional(out):
    saved = np.load(ROOT/'evidence/replicates.npz')
    payload = {'scope': 'Monte Carlo noise conditional on saved rows; not fresh streams or population coverage',
               'master_seed': 2026092001, 'arm_order': ARMS, 'resamples': 1000, 'B': 5000,
               'numpy': np.__version__, 'driver_sha256': sha(__file__),
               'replicates_sha256': sha(ROOT/'evidence/replicates.npz'),
               'diagnostics_sha256': sha(ROOT/'evidence/diagnostics.json'), 'arms': {}}
    traces = {}
    for arm, seed in zip(ARMS, np.random.SeedSequence(2026092001).spawn(3)):
        a = saved[arm]
        sd0,q0,f0 = summary(a)
        assert abs(q0-DIAG['results'][arm]['q']) < 1e-12
        assert all(bool(f0[i]) == DIAG['results'][arm]['pairs'][p]['separated'] for i,p in enumerate(old.KEYS))
        rng = np.random.default_rng(seed)
        sds, qs, flags = [], [], []
        for _ in range(1000):
            sd,q,f = summary(a[rng.integers(0,5000,5000)])
            sds.append(sd); qs.append(q); flags.append(f)
        flags = np.array(flags)
        traces[arm+'_sd'] = np.array(sds); traces[arm+'_q'] = np.array(qs)
        traces[arm+'_indicators'] = flags
        payload['arms'][arm] = {'original_q': q0, 'original_counts': counts(f0),
            'changed_indicators': int(np.sum(flags != f0)),
            'count_ranges': {k: [int(flags[:,m].sum(1).min()), int(flags[:,m].sum(1).max())] for k,m in MASKS.items()}}
        print(arm, payload['arms'][arm], flush=True)
    np.savez_compressed(out/'revision-conditional-traces.npz', **traces)
    payload['traces_sha256'] = sha(out/'revision-conditional-traces.npz')
    (out/'revision-conditional.json').write_text(json.dumps(payload,indent=2)+'\n')

@njit
def fast_eers(orders, labels, w):
    # No fastmath: integer multiplicities, same first-minimum rule as NumPy.
    total_b = 0.; total_s = 0.
    for i in range(len(w)):
        if labels[i]: total_b += w[i]
        else: total_s += w[i]
    result = np.empty(8)
    for k in range(8):
        cb = 0.; cs = 0.; best = np.inf; eer = 0.
        for j in orders[k]:
            if labels[j]: cb += w[j]
            else: cs += w[j]
            fr = cb/total_b; fa = 1.-cs/total_s
            dist = abs(fr-fa)
            if dist < best:
                best = dist; eer = (fr+fa)/2.
        result[k] = 100.*eer
    return result

ORDERS = LABELS = None
SCRATCH = None

def compute(job):
    label,arm,start,length,state = job
    path = SCRATCH/f'{label}-{start:04d}.npy'
    if path.exists():
        return label,start,np.load(path)
    rng = np.random.default_rng(); rng.bit_generator.state = state
    a = np.empty((length,8))
    for r in range(length):
        if arm == 'trial':
            w = np.bincount(np.r_[rng.choice(old.BONA,len(old.BONA)),
                                   rng.choice(old.SPOOF,len(old.SPOOF))], minlength=len(LABELS)).astype(float)
        else:
            w = old.weights(rng,arm)
        a[r] = fast_eers(ORDERS,LABELS,w)
    temp = path.with_suffix('.tmp')
    with temp.open('wb') as f: np.save(f,a)
    temp.replace(path)
    return label,start,a

def fresh(out, scratch, workers):
    global ORDERS,LABELS,SCRATCH
    start = time.monotonic(); SCRATCH = scratch
    scratch.mkdir(parents=True,exist_ok=True)
    paths = old.input_paths()
    old.campaign.KEY = old.selection.KEY = paths['protocol_key']
    old.campaign.DF_SCORES = old.selection.DF_SCORES = {n:paths[n] for n in old.NAMES}
    scores,LABELS,old.SPEAKERS,old.ATTACKS = old.selection.load_21df()
    old.LABELS = LABELS
    old.BONA = np.flatnonzero(LABELS==1); old.SPOOF = np.flatnonzero(LABELS==0)
    old.ATTS = np.unique(old.ATTACKS[old.SPOOF])
    ORDERS = np.array([np.argsort(scores[n]) for n in old.NAMES])
    rows = [l.split() for l in paths['protocol_key'].read_text().splitlines()]
    group = [r for r in rows if r[0]=='VCC2SM3' and r[7]=='eval']
    composition = {'group':'VCC2SM3','n':len(group), 'bona_fide':sum(r[5]=='bonafide' for r in group),
                   'spoof':sum(r[5]=='spoof' for r in group),'sources':sorted({r[3] for r in group})}
    assert composition == {'group':'VCC2SM3','n':315,'bona_fide':315,'spoof':0,'sources':['vcc2018']}
    saved = np.load(ROOT/'evidence/replicates.npz')
    error = 0.
    for arm,seed in zip(ARMS,np.random.SeedSequence(2026081604).spawn(4)[:3]):
        rng = np.random.default_rng(seed)
        for r in range(10):
            w = old.weights(rng,arm)
            fast = fast_eers(ORDERS,LABELS,w)
            direct = np.array([100*old.campaign.weighted_eer(o,LABELS,w) for o in ORDERS])
            error = max(error,float(abs(fast-direct).max()),float(abs(fast-saved[arm][r]).max()))
            assert error < 1e-12, (arm,r,error)
    point = fast_eers(ORDERS,LABELS,np.ones(len(LABELS)))
    assert np.max(abs(point-old.POINT)) < 1e-12
    plan = {'master':2026092002, 'arms':ARMS, 'runs':5, 'B':5000,
            'driver_sha256':sha(__file__), 'inputs_sha256':old.OLD['inputs']['sha256']}
    contract = scratch/'contract.json'
    if contract.exists(): assert json.loads(contract.read_text()) == plan
    else: contract.write_text(json.dumps(plan,indent=2)+'\n')
    specs = [(f'{arm}_{r}',arm,seed) for arm,parent in zip(ARMS,np.random.SeedSequence(plan['master']).spawn(3))
             for r,seed in enumerate(parent.spawn(5))]
    work = [j for label,arm,seed in specs for j in old.jobs(label,arm,seed)]
    print(json.dumps({'validation_max_error':error,'composition':composition,'blocks':len(work)}),flush=True)
    arrays = {label:np.full((5000,8),np.nan) for label,_,_ in specs}
    with mp.get_context('fork').Pool(workers) as pool:
        for done,(label,offset,a) in enumerate(pool.imap_unordered(compute,work),1):
            arrays[label][offset:offset+len(a)] = a
            if done%25==0: print(json.dumps({'blocks_done':done,'blocks':len(work),'seconds':time.monotonic()-start}),flush=True)
    results = {}
    for label,a in arrays.items():
        assert np.isfinite(a).all()
        sd,q,f = summary(a)
        results[label] = {'q':q, 'counts':counts(f), 'pairs':{p:{'hat':float(HATS[i]),'sd':float(sd[i]),
            'lo':float(HATS[i]-q*sd[i]),'hi':float(HATS[i]+q*sd[i]),'separated':bool(f[i])} for i,p in enumerate(old.KEYS)}}
    np.savez_compressed(out/'revision-fresh-replicates.npz',**arrays)
    payload = {'scope':'Five predeclared fresh score-level streams per arm; fixed-score sensitivity only',
               'contract':plan,'numpy':np.__version__,'estimator_validation_max_error':error,'composition':composition,
               'results':results,'replicates_sha256':sha(out/'revision-fresh-replicates.npz'),
               'seconds':time.monotonic()-start}
    (out/'revision-fresh.json').write_text(json.dumps(payload,indent=2)+'\n')
    print(json.dumps({k:v['counts'] for k,v in results.items()}),flush=True)

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('mode',choices=['conditional','fresh'])
    parser.add_argument('--out',type=Path,required=True)
    parser.add_argument('--scratch',type=Path)
    parser.add_argument('--workers',type=int,default=16)
    args = parser.parse_args(); args.out.mkdir(parents=True,exist_ok=True)
    assert not (args.out/f'revision-{args.mode}.json').exists(), 'refuse overwrite completed result'
    if args.mode=='conditional': conditional(args.out)
    else:
        assert args.scratch is not None
        fresh(args.out,args.scratch,args.workers)
