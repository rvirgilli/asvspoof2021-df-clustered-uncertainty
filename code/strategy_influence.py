"""Descriptive concentration of paired delete-one-group refits, without CIs."""
from pathlib import Path
import json
import time
import numpy as np
import strategy_diagnostics as diag

def main():
    start=time.perf_counter(); cpu=time.process_time()
    source=json.loads((diag.ROOT/'ABLATION-RESULTS.json').read_text())
    paths=source['inputs']['paths']
    for key,path in paths.items():
        assert diag.sha(path)==source['inputs']['sha256'][key]
    diag.selection.KEY=Path(paths['protocol_key'])
    diag.selection.DF_SCORES={n:Path(paths[n]) for n in diag.NAMES}
    scores,lab,sp,at=diag.selection.load_21df()
    orders=[np.argsort(scores[n]) for n in diag.NAMES]
    labs=[lab[o] for o in orders]
    ends=[np.r_[scores[n][o][1:]!=scores[n][o][:-1],True] for n,o in zip(diag.NAMES,orders)]
    def refit(w):
        return np.array([diag.both_eers(l,w[o],e)[0] for l,o,e in zip(labs,orders,ends)])
    speaker_names=sorted({p[0] for line in Path(paths['protocol_key']).read_text().splitlines() if (p:=line.split())[7]=='eval'})
    meta={p[0]:p[3] for line in Path(paths['protocol_key']).read_text().splitlines() if (p:=line.split())[7]=='eval' and p[5]=='bonafide'}
    output={}
    for factor,groups in [('speaker',np.unique(sp)),('attack',np.unique(at[lab==0]))]:
        refits=[]
        for group in groups:
            w=np.ones(len(lab))
            w[sp==group if factor=='speaker' else ((at==group)&(lab==0))]=0
            refits.append(refit(w))
        refits=np.array(refits)
        pairs={}
        for idx,(i,j) in enumerate(diag.PAIRS):
            d=refits[:,i]-refits[:,j]
            square=(d-d.mean())**2
            share=square/square.sum()
            order=np.argsort(-share)
            record={'jackknife_variance':float((len(groups)-1)/len(groups)*square.sum()),
                'top_one_ss_share':float(share[order[0]]),'top_five_ss_share':float(share[order[:5]].sum()),
                'effective_number_by_ss_concentration':float(1/np.sum(share**2)),
                'max_abs_gap_displacement':float(np.abs(d-diag.HATS[idx]).max()),
                'top_groups':[{'index':int(groups[k]),'ss_share':float(share[k]),'deletion_gap':float(d[k])} for k in order[:5]]}
            if factor=='speaker':
                for item in record['top_groups']:
                    name=speaker_names[item['index']]
                    item['speaker_label']=name;item['bona_fide_source']=meta[name]
            pairs[diag.KEYS[idx]]=record
        output[factor]={'group_count':len(groups),'pairs':pairs}
    floor=json.loads((diag.ROOT/'exp/results_floor.json').read_text())['pairs']
    max_error=max(abs(output[fac]['pairs'][key]['jackknife_variance']-val['V_spk' if fac=='speaker' else 'V_att']) for key,val in floor.items() for fac in ['speaker','attack'])
    assert max_error<0.000051
    payload={'status':'exploratory descriptive paired influence concentration, no population effective sample size or causal decomposition',
        'results':output,'existing_rounded_component_max_error':max_error,
        'driver_sha256':diag.sha(__file__),'inputs_sha256':source['inputs']['sha256'],
        'wall_seconds':time.perf_counter()-start,'cpu_seconds':time.process_time()-cpu}
    (diag.OUT/'influence.json').write_text(json.dumps(payload,indent=2)+'\n')
    print(json.dumps({key:output['speaker']['pairs'][key] for key in ['XLSR-Mamba vs XLSR-Conformer','XLS-R+SLS vs XLSR-Conformer','XLSR-Conformer vs SSL-AASIST']},indent=2))
    print('wall_seconds',payload['wall_seconds'],'cpu_seconds',payload['cpu_seconds'])

if __name__=='__main__':
    main()
