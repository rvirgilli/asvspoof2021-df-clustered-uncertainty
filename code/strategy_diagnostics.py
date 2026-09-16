"""Post-review fixed-score diagnostics; originals are read-only.

Run from workspace: UV_CACHE_DIR=/tmp/m1-strategy-uv uv run --no-project
  --with numpy==2.4.6 --with numba python exp/strategy_diagnostics.py
No inference, audio, training, or GPU work. All results are exploratory.
"""
import os
for name in ('OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS', 'MKL_NUM_THREADS'):
    os.environ[name] = '1'
import copy
import hashlib
import json
import multiprocessing as mp
from pathlib import Path
import time
import numpy as np
from numba import njit
import m1_campaign as campaign
import exp101_selection as selection
import exp101_matched_iid as matched

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / 'strategy-analysis'
OLD = json.loads((ROOT / 'ABLATION-RESULTS.json').read_text())
NAMES = OLD['inputs']['systems']
PAIRS = [(a, b) for a in range(8) for b in range(a+1, 8)]
KEYS = [f'{NAMES[a]} vs {NAMES[b]}' for a,b in PAIRS]
POINT = np.array([OLD['inputs']['point_eer_percent'][n] for n in NAMES])
HATS = np.array([POINT[a]-POINT[b] for a,b in PAIRS])
WORKERS = 20
ORDERS = SORTED_LABELS = ENDS = LABELS = SPEAKERS = ATTACKS = SPOOF = ATTS = BONA = None

def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

@njit(cache=False)
def both_eers(labels, weights, ends):
    # Same ordered accumulation and first-minimum rule as weighted_eer.
    # The second answer restricts candidate positions to distinct-score ends.
    nb = 0.0
    ns = 0.0
    for i in range(len(labels)):
        if labels[i] == 1:
            nb += weights[i]
        else:
            ns += weights[i]
    cb = 0.0
    cs = 0.0
    best = 2.0
    best_tie = 2.0
    value = 0.0
    value_tie = 0.0
    for i in range(len(labels)):
        if labels[i] == 1:
            cb += weights[i]
        else:
            cs += weights[i]
        frr = cb/nb
        far = 1.0-cs/ns
        distance = abs(frr-far)
        if distance < best:
            best = distance
            value = (frr+far)/2.0
        if ends[i] and distance < best_tie:
            best_tie = distance
            value_tie = (frr+far)/2.0
    return 100.0*value, 100.0*value_tie

def weights(rng, arm):
    if arm == 'trial':
        w = np.zeros(len(LABELS))
        np.add.at(w, rng.choice(BONA, size=len(BONA), replace=True), 1.0)
        np.add.at(w, rng.choice(SPOOF, size=len(SPOOF), replace=True), 1.0)
        return w
    nsp = 1 if arm == 'attack_only' else 93
    cs = np.bincount(rng.integers(0, nsp, nsp), minlength=nsp)
    w = np.ones(len(LABELS)) if nsp == 1 else cs[SPEAKERS].astype(float)
    if arm != 'speaker_only':
        ca = np.bincount(rng.choice(ATTS, size=len(ATTS), replace=True), minlength=ATTACKS.max()+1)
        w[SPOOF] *= ca[ATTACKS[SPOOF]]
    return w

def advance(rng, arm):
    if arm == 'trial':
        rng.choice(BONA, size=len(BONA), replace=True)
        rng.choice(SPOOF, size=len(SPOOF), replace=True)
    else:
        nsp = 1 if arm == 'attack_only' else 93
        rng.integers(0, nsp, nsp)
        if arm != 'speaker_only':
            rng.choice(ATTS, size=len(ATTS), replace=True)

def jobs(label, arm, seed, size=5000, block=100):
    rng = np.random.default_rng(seed)
    result = []
    for start in range(0, size, block):
        length = min(block, size-start)
        result.append((label, arm, start, length, copy.deepcopy(rng.bit_generator.state)))
        for _ in range(length):
            advance(rng, arm)
    return result

def compute(job):
    label, arm, start, length, state = job
    rng = np.random.default_rng()
    rng.bit_generator.state = state
    a = np.empty((length, 8))
    t = np.empty_like(a)
    cpu_start = time.process_time()
    for i in range(length):
        w = weights(rng, arm)
        for k in range(8):
            a[i,k],t[i,k] = both_eers(SORTED_LABELS[k], w[ORDERS[k]], ENDS[k])
    return label, start, a, t, time.process_time()-cpu_start

def summarize(a, point=POINT, family=None):
    ids = list(range(28)) if family is None else family
    d = np.column_stack([a[:,i]-a[:,j] for i,j in PAIRS])[:,ids]
    hats = np.array([point[i]-point[j] for i,j in PAIRS])[ids]
    sd = d.std(axis=0, ddof=1)
    q = float(np.percentile((np.abs(d-d.mean(axis=0))/sd).max(axis=1),95))
    pair_results = {}
    for col, idx in enumerate(ids):
        i,j = PAIRS[idx]
        lo,hi = hats[col]-q*sd[col], hats[col]+q*sd[col]
        reversal = float(np.mean(d[:,col]*np.sign(hats[col])<0))
        pair_results[KEYS[idx]] = {
            'hat': float(hats[col]), 'sd': float(sd[col]), 'lo': float(lo), 'hi': float(hi),
            'separated': bool(lo>0 or hi<0), 'mean': float(d[:,col].mean()),
            'mean_shift': float(d[:,col].mean()-hats[col]),
            'mean_shift_over_sd': float((d[:,col].mean()-hats[col])/sd[col]),
            'opposite_sign_frequency': reversal,
            'sign_frequency_mcse': float(np.sqrt(reversal*(1-reversal)/len(a))),
            'percentiles_2p5_97p5': np.percentile(d[:,col],[2.5,97.5]).tolist(),
            'critical_q_for_separation': float(abs(hats[col])/sd[col]),
            'correlation': float(np.corrcoef(a[:,i],a[:,j])[0,1]),
            'paired_over_unpaired_variance': float(sd[col]**2/(a[:,i].var(ddof=1)+a[:,j].var(ddof=1)))
        }
    return {'B':len(a), 'q':q, 'count':sum(p['separated'] for p in pair_results.values()),'pairs':pair_results}

def main():
    global ORDERS, SORTED_LABELS, ENDS, LABELS, SPEAKERS, ATTACKS, SPOOF, ATTS, BONA
    start = time.perf_counter()
    main_cpu = time.process_time()
    OUT.mkdir(exist_ok=True)
    assert not (OUT/'diagnostics.json').exists(), 'refuse overwrite completed run'
    protected = [ROOT/'main-BASE.tex', ROOT/'main-FORK.tex',ROOT/'SUPPLEMENT.md',ROOT/'ABLATION-RESULTS.json', *sorted((ROOT/'exp').glob('results*.json'))]
    seals = {str(p.relative_to(ROOT)):sha(p) for p in protected}
    paths = OLD['inputs']['paths']
    for name, path in paths.items():
        assert sha(path)==OLD['inputs']['sha256'][name], name
    campaign.KEY = selection.KEY = Path(paths['protocol_key'])
    campaign.DF_SCORES = selection.DF_SCORES = {n:Path(paths[n]) for n in NAMES}
    scores,LABELS,SPEAKERS,ATTACKS = selection.load_21df()
    assert len(LABELS)==533928 and int(LABELS.sum())==14869
    ORDERS = [np.argsort(scores[n]) for n in NAMES]
    SORTED_LABELS = [LABELS[o] for o in ORDERS]
    ENDS = [np.r_[scores[n][o][1:]!=scores[n][o][:-1],True] for n,o in zip(NAMES,ORDERS)]
    SPOOF = np.flatnonzero(LABELS==0)
    BONA = np.flatnonzero(LABELS==1)
    ATTS = np.unique(ATTACKS[SPOOF])
    point_tie = np.array([both_eers(l,np.ones(len(l)),e)[1] for l,e in zip(SORTED_LABELS,ENDS)])
    saved_path = Path('/tmp/m1-ablation-2122/ABLATION-REPLICATES.npz')
    assert sha(saved_path)==OLD['replicates']['sha256']
    saved = np.load(saved_path)
    arms = ['trial','speaker_attack','speaker_only','attack_only']
    seeds = np.random.SeedSequence(2026081604).spawn(4)
    validation_error = 0.0
    for arm,seed in zip(arms,seeds):
        rng = np.random.default_rng(seed)
        for r in range(10):
            w = weights(rng,arm)
            for k in range(8):
                v,t = both_eers(SORTED_LABELS[k],w[ORDERS[k]],ENDS[k])
                direct = 100*campaign.weighted_eer(ORDERS[k],LABELS,w)
                validation_error = max(validation_error,abs(v-direct))
                assert abs(v-direct)<1e-12
                if arm in saved.files:
                    assert abs(v-saved[arm][r,k])<1e-12
                # Independent numpy boundary implementation, same score order.
                wl = w[ORDERS[k]]
                cb = np.cumsum(wl*SORTED_LABELS[k]); cs = np.cumsum(wl*(1-SORTED_LABELS[k]))
                fr=(cb/cb[-1])[ENDS[k]]; fa=(1-cs/cs[-1])[ENDS[k]]
                z=np.argmin(np.abs(fr-fa))
                assert abs(t-100*((fr[z]+fa[z])/2))<1e-12
    print(json.dumps({'validation_max_error':validation_error,'setup_seconds':time.perf_counter()-start}),flush=True)
    specs = [(arm,arm,seed) for arm,seed in zip(arms,seeds)]
    specs += [(f'attack_repeat_{i}', 'attack_only', seed) for i,seed in enumerate(np.random.SeedSequence(2026091601).spawn(5))]
    # All five repeat seeds fixed before inspecting their endpoints.
    jobs_start=time.perf_counter()
    work = [job for label,arm,seed in specs for job in jobs(label,arm,seed)]
    print(json.dumps({'jobs':len(work),'stream_generation_seconds':time.perf_counter()-jobs_start}),flush=True)
    arrays={label:np.full((5000,8),np.nan) for label,_,_ in specs}
    ties={label:np.full((5000,8),np.nan) for label,_,_ in specs}
    cpu=0.0
    run_start=time.perf_counter()
    with mp.get_context('fork').Pool(WORKERS) as pool:
        for done,(label,offset,a,t,cost) in enumerate(pool.imap_unordered(compute,work,chunksize=1),1):
            arrays[label][offset:offset+len(a)]=a
            ties[label][offset:offset+len(t)]=t
            cpu+=cost
            if done%25==0:
                print(json.dumps({'blocks_done':done,'total_blocks':len(work),'run_seconds':time.perf_counter()-run_start}),flush=True)
    run_seconds=time.perf_counter()-run_start
    results={}
    ssl_ids=[p for p,(i,j) in enumerate(PAIRS) if i<4 and j<4]
    for label,a in arrays.items():
        assert np.isfinite(a).all() and np.isfinite(ties[label]).all()
        result = summarize(a)
        tie_result = summarize(ties[label],point_tie)
        result['tie_check'] = {
            'max_replicate_eer_difference':float(np.abs(a-ties[label]).max()),
            'max_pair_endpoint_difference':max(abs(result['pairs'][k][e]-tie_result['pairs'][k][e]) for k in KEYS for e in ['lo','hi']),
            'changed_indicators':[k for k in KEYS if result['pairs'][k]['separated']!=tie_result['pairs'][k]['separated']],
            'summary':tie_result}
        result['ssl_six_family']=summarize(a,family=ssl_ids)
        if label in arms:
            published=OLD['arms'][label]['summary']
            assert matched.summarize(a,POINT,NAMES)==published, label
            result['published_summary_exactly_reproduced']=True
        if label in saved.files:
            result['max_difference_from_saved_replicates']=float(np.abs(a-saved[label]).max())
            assert result['max_difference_from_saved_replicates']<1e-12
        results[label]=result
    pooled=np.concatenate([arrays[f'attack_repeat_{i}'] for i in range(5)])
    results['attack_repeats_pooled_25000']=summarize(pooled)
    # Paired row-resampling estimates Monte Carlo uncertainty, not data uncertainty.
    mc_start=time.perf_counter()
    rng=np.random.default_rng(2026091602)
    mc=[]
    idx=KEYS.index('LFCC-LCNN vs CQCC-GMM')
    base=saved['attack_only']
    for _ in range(1000):
        a=base[rng.integers(0,len(base),len(base))]
        d=np.column_stack([a[:,i]-a[:,j] for i,j in PAIRS])
        sd=d.std(axis=0,ddof=1)
        q=np.percentile((abs(d-d.mean(axis=0))/sd).max(axis=1),95)
        mc.append(float(HATS[idx]+q*sd[idx]))
    mc=np.array(mc)
    mc_seconds=time.perf_counter()-mc_start
    for p in protected:
        assert sha(p)==seals[str(p.relative_to(ROOT))]
    np.savez_compressed(OUT/'replicates.npz',**arrays,**{k+'_ties':v for k,v in ties.items()})
    payload={
        'status':'complete; exploratory diagnostics; fixed-score sensitivity only',
        'inputs_sha256':OLD['inputs']['sha256'], 'saved_ablation_sha256':sha(saved_path),
        'driver_sha256':sha(__file__), 'protected_files_before_and_after':seals,
        'seed_rule':{'primary_master':2026081604,'primary_arms_spawn_order':arms,'repeats_master':2026091601,'repeat_spawn_keys':list(range(5)),'mc_rows_seed':2026091602},
        'workers':WORKERS,'numpy':np.__version__,'primary_validation_max_error':validation_error,
        'point_tie_eers':dict(zip(NAMES,point_tie.tolist())),
        'results':results,
        'saved_attack_endpoint_mc':{'row_resamples':1000,'B_per_resample':5000,'upper_endpoint_quantiles_2p5_50_97p5':np.percentile(mc,[2.5,50,97.5]).tolist(),'fraction_upper_endpoint_below_zero':float(np.mean(mc<0)),'seconds':mc_seconds,'all_28_max_t_recomputed':True},
        'cost':{'raw_run_wall_seconds':run_seconds,'workers_cpu_seconds':cpu,'main_process_cpu_seconds':time.process_time()-main_cpu,'total_wall_seconds':time.perf_counter()-start},
        'replicates_sha256':sha(OUT/'replicates.npz')}
    (OUT/'diagnostics.json').write_text(json.dumps(payload,indent=2,allow_nan=False)+'\n')
    print(json.dumps({'cost':payload['cost'],'mc':payload['saved_attack_endpoint_mc'],'attack_repeats':[{k:results[k]['pairs']['LFCC-LCNN vs CQCC-GMM']['hi']} for k in results if k.startswith('attack')]}),flush=True)

if __name__=='__main__':
    main()
