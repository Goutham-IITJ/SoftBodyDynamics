"""Focused spatial/support diagnosis from saved solves; no re-solving."""
import json
from pathlib import Path
import numpy as np
from analysis.localized_fem.solver import TractionSolver
from analysis.localized_fem.traction import Rectangle,integrate_rectangle
from analysis.localized_fem.simulate import write_json

HERE=Path(__file__).resolve().parent


def main():
    rows=[]
    for mesh,folder in [((2,2,1),'verification/coarse_0p3'),((4,4,2),'verification/medium_0p3'),((6,6,3),'verification/fine_0p3'),((8,8,4),'phase7c/refine_8')]:
        s=TractionSolver(mesh);p=HERE/folder;d=json.loads((p/'diagnostics.json').read_text())
        data=np.loadtxt(p/'nodes.csv',delimiter=',',skiprows=1);x=data[:,4:7]
        st=s.assembly.evaluate(x,s.material);down=s.X[:,2]-x[:,2];k=down.argmax()
        load=integrate_rectangle(s.X,s.top_faces,Rectangle(.0365,.025,.02,.03),.3)
        inside=np.all((s.X[s.top,:2]>=load.clipped_bounds_xy_m[0])&(s.X[s.top,:2]<=load.clipped_bounds_xy_m[1]),axis=1)
        row=dict(mesh=list(mesh),**d,cell_spacing_mm=(s.lengths/mesh*1000).tolist(),patch_cell_spans_xy=(np.array([.02,.03])/(s.lengths/mesh)[:2]).tolist(),top_vertices_inside_patch=int(inside.sum()),intersected_top_triangles=load.intersected_triangles,peak_reference_xyz_mm=(s.X[k]*1000).tolist(),peak_distance_to_patch_edge_mm=float(np.min(np.r_[s.X[k,:2]-load.clipped_bounds_xy_m[0],load.clipped_bounds_xy_m[1]-s.X[k,:2]])*1000),max_deformation_gradient_condition=float(max(np.linalg.cond(e.F) for e in st.elements)))
        if rows:
            for name in ['max_downward_mm','loaded_mean_downward_mm','unloaded_mean_downward_mm']:
                row[name+'_change_percent']=100*(row[name]/rows[-1][name]-1)
        rows.append(row)
    write_json(HERE/'phase7c/mesh_diagnosis.json',rows)
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig,axes=plt.subplots(1,3,figsize=(12,4))
    for ax,key in zip(axes,['max_downward_mm','loaded_mean_downward_mm','unloaded_mean_downward_mm']):
        ax.plot([r['tetrahedra'] for r in rows],[r[key] for r in rows],'o-');ax.set(xlabel='Tetrahedra',ylabel=key.replace('_',' '));ax.grid(alpha=.3)
    fig.suptitle('Fixed synthetic patch and force; bilateral support held fixed');fig.tight_layout();fig.savefig(HERE/'phase7c/refinement_diagnosis.png',dpi=150);plt.close(fig)
    checks=[]
    for name in ['support_pilot','support_4','support_6','cli_localized']:
        folder=HERE/'phase7c'/name
        data=np.loadtxt(folder/'nodes.csv',delimiter=',',skiprows=1);reaction=np.loadtxt(folder/'reactions.csv',delimiter=',',skiprows=1)
        bottom=np.flatnonzero(abs(data[:,3]-.007)<1e-12);gap=data[bottom,6]-.007
        d=json.loads((folder/'diagnostics.json').read_text())
        actual=reaction[bottom,2]
        assert gap.min()>=-1e-10 and actual.min()>=-5e-8
        assert np.max(abs(gap*actual))<1e-14
        assert d['free_residual_N']<=5e-8 and d['min_J']>0
        checks.append(dict(case=name,min_gap_m=float(gap.min()),max_gap_mm=float(gap.max()*1000),min_actual_contact_reaction_N=float(actual.min()),total_tensile_actual_reaction_N=float(-np.minimum(actual,0).sum()),complementarity_max_Nm=float(np.max(abs(gap*actual))),force_balance_N=float(np.max(abs((reaction+data[:,7:10]).sum(axis=0))))))
    write_json(HERE/'phase7c/support_audit.json',dict(status='PASS',cases=checks))


if __name__=='__main__':main()
