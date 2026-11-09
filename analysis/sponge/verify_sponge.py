"""Stage 4 integration verification; synthetic parameters, no experimental input.

Run from the repository root: python -B analysis/sponge/verify_sponge.py
Writes only its own verification directory. Existing stages are hashed read-only.
"""
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
import csv
import hashlib
import itertools
import json
from dataclasses import asdict
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d.art3d import Poly3DCollection,Line3DCollection
from analysis.sponge.geometry import Sponge,SpongeConfig
from analysis.fem_solver.solver import BlockSolver
from analysis.material.hyperfoam import Hyperfoam

HERE=Path(__file__).resolve().parent
OUT=HERE/'verification'


def protected_hashes():
    root=HERE.parent
    return {p.relative_to(root).as_posix():hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(root.rglob('*')) if p.is_file() and HERE not in p.parents
            and '__pycache__' not in p.parts}


def write_csv(name,rows):
    rows=list(rows)
    if not rows:return
    with (OUT/name).open('w',newline='',encoding='utf-8') as f:
        writer=csv.DictWriter(f,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)


def save_nodes(name,reference,current):
    write_csv(name,({'node':i,'X_m':X[0],'Y_m':X[1],'Z_m':X[2],
                     'x_m':x[0],'y_m':x[1],'z_m':x[2]} for i,(X,x) in enumerate(zip(reference,current))))


def plot_states(sponge,states,path):
    """All yellow vertices come directly from equilibrium.positions."""
    fig=plt.figure(figsize=(13,5.8))
    edges=sorted({tuple(sorted(e)) for c in sponge.solver.cells for e in itertools.combinations(c,2)})
    for index,(title,r) in enumerate(states):
        ax=fig.add_subplot(1,2,index+1,projection='3d')
        table=np.array([[-.01,-.01,0],[.083,-.01,0],[.083,.06,0],[-.01,.06,0]])*1000
        ax.add_collection3d(Poly3DCollection([table],facecolors='#dddddd',alpha=.25))
        back=sponge.backing_vertices*1000
        ax.add_collection3d(Poly3DCollection(back[sponge.backing_faces],facecolors='#238443',edgecolors='#125428',linewidths=.45))
        nodes=r.positions*1000
        ax.add_collection3d(Poly3DCollection(nodes[sponge.boundary],facecolors='#ffd84c',edgecolors='#8c740e',linewidths=.45,alpha=.65))
        ax.add_collection3d(Line3DCollection(nodes[np.asarray(edges)],colors='#947914',linewidths=.35,alpha=.45))
        card=sponge.platen_vertices(r.displacement)*1000
        ax.add_collection3d(Poly3DCollection([card],facecolors='#a6bddb',edgecolors='#355477',linewidths=1,alpha=.65))
        ax.set(xlim=(-8,81),ylim=(-3,56),zlim=(0,31),xlabel='x (mm)',ylabel='y (mm)',zlabel='z (mm)')
        ax.set_box_aspect((89,59,31));ax.view_init(elev=23,azim=-60)
        ax.set_title(f'{title}\nd = {1000*r.displacement:.3f} mm; reaction = {r.top_reaction:.3f} N',fontsize=10)
    fig.suptitle('Stage 4: solved yellow FEM nodes; rigid green backing and massless card\nSynthetic material only: mu = 2000 Pa, alpha = 10, beta = 0',fontsize=12)
    fig.subplots_adjust(left=.01,right=.98,bottom=.08,top=.80,wspace=.04)
    fig.savefig(path,dpi=170);plt.close(fig)


def run():
    before=protected_hashes();OUT.mkdir(exist_ok=True)
    config=SpongeConfig();rows=[];histories=[];translation=[];meshes=[];by_case={}
    max_position_error=0.
    for subdivisions in [(1,1,1),(2,2,2)]:
        mesh='x'.join(map(str,subdivisions))
        for beta in [0.,.125]:
            label=f'{mesh}_beta{beta:g}';s=Sponge(config,subdivisions,Hyperfoam(2000,10,beta));solver=s.solver
            X=solver.X;back=s.backing_vertices.copy()
            volumes=np.array([np.linalg.det((X[c[1:]]-X[c[0]]).T)/6 for c in solver.cells])
            assert np.all(volumes>0) and len(np.unique(X,axis=0))==len(X)
            np.testing.assert_allclose(X.min(axis=0),[0,0,.007],atol=1e-16)
            np.testing.assert_allclose(X.max(axis=0),[.073,.05,.027],atol=1e-16)
            np.testing.assert_allclose(volumes.sum(),config.yellow_volume,rtol=1e-12)
            meshes.append(dict(mesh=mesh,beta=beta,nodes=len(X),tetrahedra=len(solver.cells),free_dofs=len(solver.free),reference_volume_m3=volumes.sum(),min_tet_volume_m3=volumes.min(),boundary_triangles=len(s.boundary)))
            write_csv(f'{label}_tetrahedra.csv',(dict(element=i,n0=c[0],n1=c[1],n2=c[2],n3=c[3]) for i,c in enumerate(solver.cells)))
            write_csv(f'{label}_boundary.csv',(dict(face=i,n0=f[0],n1=f[1],n2=f[2]) for i,f in enumerate(s.boundary)))
            reference=s.solve_force(0)
            sequence=[('reference',reference,0.)]
            start=reference
            for d in [.004,.008]:
                start=s.solve_displacement(d,start=start);sequence.append((f'd{d*1000:g}mm',start,None))
            compressed=start
            for force in [1.,2.,1.,0.]:
                r=s.solve_force(force);name=('force' if force==2 or len(sequence)<5 else 'unload')+f'{force:g}N'
                sequence.append((name,r,force))
            np.testing.assert_allclose(sequence[-1][1].positions,X,atol=3e-8)
            assert abs(sequence[-1][1].energy)<1e-10
            if beta:assert sequence[-1][1].iterations>0
            for name,r,target in sequence:
                np.testing.assert_array_equal(back,s.backing_vertices)
                np.testing.assert_allclose(r.positions[solver.top,2],config.top_z-r.displacement,atol=1e-15)
                np.testing.assert_allclose(r.positions[solver.bottom,2],.007,atol=1e-15)
                assert r.min_J>0 and r.free_residual<=1.01e-8
                assert abs(r.top_reaction-r.bottom_reaction)<5e-7
                assert np.max(abs(r.gradient.sum(axis=0)))<5e-7
                if target is not None:assert abs(r.top_reaction-target)<2e-7
                F,W,P,*_=solver.material.free_uniaxial(1-r.displacement/config.yellow_height)
                analytic=(X-[0,0,.007])@F.T+[0,0,.007]
                error=float(np.max(abs(r.positions-analytic)));max_position_error=max(max_position_error,error)
                assert error<3e-8 and abs(r.energy-W*config.yellow_volume)<1e-10
                assert abs(r.top_reaction+config.contact_area*P[2,2])<2e-7
                allJ=min(h['min_J'] for h in r.history);assert allJ>0
                # Finite card/backing are visuals; constraints are full-face planes.
                top=r.positions[solver.top,:2];bottom=r.positions[solver.bottom,:2];card=s.platen_vertices(r.displacement)
                def outside(points,low,high):return int(np.count_nonzero(np.any((points<np.asarray(low)-1e-8)|(points>np.asarray(high)+1e-8),axis=1)))
                rows.append(dict(mesh=mesh,beta=beta,case=name,target_force_N='' if target is None else target,compression_m=r.displacement,yellow_strain=r.displacement/config.yellow_height,top_z_m=config.top_z-r.displacement,energy_J=r.energy,top_reaction_N=r.top_reaction,bottom_reaction_N=r.bottom_reaction,free_residual_N=r.free_residual,force_balance_N=abs(r.top_reaction-r.bottom_reaction),min_J=r.min_J,max_J=r.max_J,history_min_J=allJ,iterations=r.iterations,analytic_position_error_m=error,top_nodes_outside_card=outside(top,card[:,:2].min(axis=0),card[:,:2].max(axis=0)),bottom_nodes_outside_backing=outside(bottom,[0,0],[.073,.05]),termination=r.termination))
                save_nodes(f'{label}_{name}_nodes.csv',X,r.positions)
                for i,h in enumerate(r.history):histories.append(dict(mesh=mesh,beta=beta,case=name,history_index=i,platen_displacement_m=h.get('platen_displacement_m',r.displacement),iteration=h['iteration'],energy_J=h['energy_J'],free_residual_N=h['free_residual_N'],min_J=h['min_J'],step_length=h['step_length']))
                by_case[(mesh,beta,name)]=r
            write_csv(f'{label}_outer_root_history.csv',solver.force_history)
            write_csv(f'{label}_continuation.csv',solver.continuation_attempts)
            if subdivisions==(2,2,2):
                flat=BlockSolver(solver.material,dimensions=(.073,.05,.02),subdivisions=subdivisions)
                # Match the same operations, with only the reference z coordinate changed.
                for name,high in [('d8mm',compressed),('force2N',by_case[(mesh,beta,'force2N')]),('unload0N',sequence[-1][1])]:
                    low=flat.solve_displacement(.008) if name=='d8mm' else flat.solve_force(2. if name=='force2N' else 0.)
                    de=abs(high.energy-low.energy);df=abs(high.top_reaction-low.top_reaction);dd=abs(high.displacement-low.displacement)
                    dx=float(np.max(abs(high.positions-[0,0,.007]-low.positions)))
                    assert de<1e-10 and df<2e-7 and dd<1e-8 and dx<3e-8
                    translation.append(dict(beta=beta,case=name,energy_difference_J=de,reaction_difference_N=df,compression_difference_m=dd,translated_node_difference_m=dx))
                if beta==0:
                    plot_states(s,[('Undeformed equilibrium',reference),('Compressed equilibrium (40% yellow strain)',compressed)],OUT/'sponge_equilibria.png')
                    write_csv('rigid_backing_vertices.csv',(dict(node=i,x_m=p[0],y_m=p[1],z_m=p[2]) for i,p in enumerate(back)))
                    write_csv('compressed_platen_vertices.csv',(dict(node=i,x_m=p[0],y_m=p[1],z_m=p[2]) for i,p in enumerate(s.platen_vertices(compressed.displacement))))
            print(f'PASS {label}: {len(sequence)} equilibria',flush=True)
    comparisons=[]
    for beta in [0.,.125]:
        for case in ['reference','d4mm','d8mm','force1N','force2N','unload1N','unload0N']:
            a=by_case[('1x1x1',beta,case)];b=by_case[('2x2x2',beta,case)]
            de=abs(a.energy-b.energy);df=abs(a.top_reaction-b.top_reaction);dd=abs(a.displacement-b.displacement)
            assert de<1e-10 and df<2e-7 and dd<1e-8
            comparisons.append(dict(beta=beta,case=case,energy_difference_J=de,reaction_difference_N=df,compression_difference_m=dd))
    write_csv('equilibria.csv',rows);write_csv('mesh_checks.csv',meshes);write_csv('iteration_history.csv',histories)
    write_csv('translation_checks.csv',translation);write_csv('mesh_comparisons.csv',comparisons)
    after=protected_hashes();assert before==after,'A protected prior-stage file changed'
    summary=dict(status='PASS',geometry_SI=asdict(config),nominal_contact_area_m2=config.contact_area,yellow_volume_m3=config.yellow_volume,synthetic_materials=[dict(mu_Pa=2000,alpha=10,beta=b) for b in [0,.125]],mesh_resolutions=[[1,1,1],[2,2,2]],equilibria=len(rows),translation_checks=len(translation),max_free_residual_N=max(r['free_residual_N'] for r in rows),max_force_balance_N=max(r['force_balance_N'] for r in rows),min_J=min(r['min_J'] for r in rows),min_history_J=min(r['history_min_J'] for r in rows),max_analytic_position_error_m=max_position_error,max_unload_position_error_m=max(float(np.max(abs(by_case[(m,b,'unload0N')].positions-Sponge(subdivisions=n).solver.X))) for m,n in [('1x1x1',(1,1,1)),('2x2x2',(2,2,2))] for b in [0.,.125]),max_translation_energy_difference_J=max(r['energy_difference_J'] for r in translation),max_translation_reaction_difference_N=max(r['reaction_difference_N'] for r in translation),max_translation_node_difference_m=max(r['translated_node_difference_m'] for r in translation),max_mesh_reaction_difference_N=max(r['reaction_difference_N'] for r in comparisons),max_mesh_compression_difference_m=max(r['compression_difference_m'] for r in comparisons),protected_files_unchanged=len(before),assumptions=['rigid backing; no interlayer shear','massless rigid platen; full-face frictionless bilateral planes','no finite-footprint collision','synthetic parameters; no calibration','quasi-static unloading; no recovery timescale'])
    (OUT/'summary.json').write_text(json.dumps(summary,indent=2)+'\n',encoding='utf-8')
    (OUT/'preserved_analysis_sha256.json').write_text(json.dumps(before,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(summary,indent=2))


if __name__=='__main__':run()
