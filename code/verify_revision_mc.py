"""Independent arithmetic check: weighted moments for conditional row resamples.

Does not import revision_mc or its summary implementation. Fresh streams are
independently summarized from the archived eight-system output rows.
"""
import os
for name in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS'):
    os.environ[name]='1'
from pathlib import Path
import hashlib
import itertools
import json
import numpy as np

ROOT=Path(__file__).resolve().parents[1]
E=ROOT/'evidence'
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def read(n): return json.loads((E/n).read_text())

def main():
    conditional=read('revision-conditional.json')
    fresh=read('revision-fresh.json')
    diag=read('diagnostics.json')
    names=read('ABLATION-RESULTS.json')['inputs']['systems']
    pairs=list(itertools.combinations(range(8),2))
    keys=[f'{names[i]} vs {names[j]}' for i,j in pairs]
    hats=np.array([diag['results']['trial']['pairs'][k]['hat'] for k in keys])
    masks={'all':np.ones(28,dtype=bool),'ssl':np.array([j<4 for i,j in pairs]),
           'organizer':np.array([i>=4 for i,j in pairs]),'cross':np.array([i<4<=j for i,j in pairs])}
    archive=np.load(E/'replicates.npz'); traces=np.load(E/'revision-conditional-traces.npz')
    assert conditional['replicates_sha256']==sha(E/'replicates.npz')
    assert conditional['traces_sha256']==sha(E/'revision-conditional-traces.npz')
    errors=[]
    for arm,seed in zip(['trial','speaker_attack','speaker_only'],np.random.SeedSequence(2026092001).spawn(3)):
        rng=np.random.default_rng(seed)
        a=archive[arm]; d=np.array([a[:,i]-a[:,j] for i,j in pairs]).T
        base=np.array([diag['results'][arm]['pairs'][k]['separated'] for k in keys])
        counts={k:[] for k in masks}; changes=0
        for r in range(1000):
            indices=rng.integers(0,5000,5000)
            weights=np.bincount(indices,minlength=5000)
            mean=np.average(d,axis=0,weights=weights)
            sd=np.sqrt(np.sum(weights[:,None]*(d-mean)**2,axis=0)/4999)
            maxima=np.max(np.abs(d-mean)/sd,axis=1)
            # Explicit linear percentile of the 5,000 maxima with multiplicity.
            order=np.sort(maxima[indices]); x=.95*4999; lo=int(x)
            q=order[lo]+(x-lo)*(order[lo+1]-order[lo])
            flags=(hats-q*sd>0)|(hats+q*sd<0)
            errors.extend([float(np.max(abs(sd-traces[arm+'_sd'][r]))),float(abs(q-traces[arm+'_q'][r]))])
            assert errors[-2]<2e-12 and errors[-1]<2e-12
            assert np.array_equal(flags,traces[arm+'_indicators'][r])
            changes+=int(np.sum(flags!=base))
            for k,m in masks.items(): counts[k].append(int(flags[m].sum()))
        assert changes==conditional['arms'][arm]['changed_indicators']==0
        assert {k:[min(v),max(v)] for k,v in counts.items()}==conditional['arms'][arm]['count_ranges']
    reps=np.load(E/'revision-fresh-replicates.npz')
    assert fresh['replicates_sha256']==sha(E/'revision-fresh-replicates.npz')
    fresh_changes={}
    for arm in ['trial','speaker_attack','speaker_only']:
        changes=[]
        for r in range(5):
            key=f'{arm}_{r}'; a=reps[key]
            d=np.array([a[:,i]-a[:,j] for i,j in pairs]).T
            sd=np.array([np.std(d[:,i],ddof=1) for i in range(28)])
            mean=np.array([np.mean(d[:,i]) for i in range(28)])
            maxima=np.sort(np.max(np.abs(d-mean)/sd,axis=1))
            x=.95*4999; lo=int(x); q=float(maxima[lo]+(x-lo)*(maxima[lo+1]-maxima[lo]))
            flags=(hats-q*sd>0)|(hats+q*sd<0)
            saved=fresh['results'][key]
            assert abs(q-saved['q'])<2e-12
            assert {k:int(flags[m].sum()) for k,m in masks.items()}==saved['counts']
            for i,p in enumerate(keys):
                rec=saved['pairs'][p]
                assert abs(sd[i]-rec['sd'])<2e-12
                assert abs(hats[i]-q*sd[i]-rec['lo'])<2e-12
                assert abs(hats[i]+q*sd[i]-rec['hi'])<2e-12
                assert bool(flags[i])==rec['separated']
            changes.append([p for i,p in enumerate(keys) if bool(flags[i])!=diag['results'][arm]['pairs'][p]['separated']])
        fresh_changes[arm]=changes
    files=['revision-conditional.json','revision-conditional-traces.npz','revision-fresh.json',
           'revision-fresh-replicates.npz','replicates.npz','diagnostics.json','REVISION-MC-PLAN.md']
    # Independently parse the hash-checked protocol; never infer composition from influence.
    input_root=Path(os.environ['M1_INPUT_ROOT'])
    input_doc=json.loads((ROOT/'ABLATION-RESULTS.json').read_text())['inputs']
    protocol=input_root/input_doc['paths']['protocol_key']
    assert sha(protocol)==input_doc['sha256']['protocol_key']
    group=[row.split() for row in protocol.read_text().splitlines()
           if row.split()[0]=='VCC2SM3' and row.split()[7]=='eval']
    composition={'group':'VCC2SM3','n':len(group),
                 'bona_fide':sum(r[5]=='bonafide' for r in group),
                 'spoof':sum(r[5]=='spoof' for r in group),'sources':sorted({r[3] for r in group})}
    assert composition==fresh['composition']
    payload={'status':'PASS','conditional_resamples_checked':3000,'fresh_streams_checked':15,
             'composition':composition,'protocol_sha256':sha(protocol),
             'conditional_max_arithmetic_difference':max(errors),'fresh_changed_pairs_by_stream':fresh_changes,
             'bindings':{n:sha(E/n) for n in files},'verifier_sha256':sha(Path(__file__))}
    (E/'revision-mc-verification.json').write_text(json.dumps(payload,indent=2)+'\n')
    print(json.dumps(payload,indent=2))

if __name__=='__main__': main()
