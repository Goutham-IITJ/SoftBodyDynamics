"""Independent homogeneous block patch checks; no sponge/contact or fitting.
Run: python -B analysis/fem/patch_test.py
"""
from pathlib import Path
import sys
if __package__ in (None,''):sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
import itertools
import json
import hashlib
import csv
import numpy as np
from analysis.fem.tetra import Tet4,TetAssembly
from analysis.material.hyperfoam import Hyperfoam

SCENARIOS={'alpha10_beta0':Hyperfoam(2000.,10.,0.),'alpha20_beta0':Hyperfoam(2000.,20.,0.),'alpha10_beta0125':Hyperfoam(2000.,10.,.125)}
LENGTHS=np.array([.03,.02,.01])  # synthetic verification block, not specimen dimensions


def block_mesh(n=1,reflect=False):
    """Freudenthal six-tet cells; n=2 includes interior nodes for equilibrium check."""
    if not isinstance(n,int) or n<1:raise ValueError('n must be a positive integer')
    ids={p:i for i,p in enumerate(itertools.product(range(n+1),repeat=3))}
    X=np.array(list(ids),float)/n*LENGTHS
    cells=[]
    for base in itertools.product(range(n),repeat=3):
        for order in itertools.permutations(range(3)):
            p=np.array(base);corners=[ids[tuple(p)]]
            for axis in order:
                p=p.copy();p[axis]+=1;corners.append(ids[tuple(p)])
            cells.append(corners)
    if reflect:X[:,0]=LENGTHS[0]-X[:,0]
    return X,np.asarray(cells,dtype=int)


def boundary_faces(X,cells):
    """Identify boundary by topology; outward area vectors by geometric cross products."""
    faces={}
    for cell in cells:
        for omitted in range(4):
            face=tuple(int(cell[i]) for i in range(4) if i!=omitted)
            key=tuple(sorted(face));faces.setdefault(key,[]).append((face,int(cell[omitted])))
    boundary=[]
    for key,entries in faces.items():
        if len(entries)>2:raise ValueError('Nonmanifold mesh')
        if len(entries)!=1:continue
        face,opposite=entries[0];a,b,c=X[list(face)]
        area=.5*np.cross(b-a,c-a)
        if np.dot(area,X[opposite]-a)>0:area=-area
        boundary.append((np.array(face),area))
    return boundary


def surface_load(X,cells,P,current=None,sigma=None):
    """Independent consistent boundary load = integral N_a P N dA0.
    Optional current surface calculation uses sigma n da (Nanson cross-check).
    """
    loads=np.zeros_like(X);current_loads=np.zeros_like(X);face_totals={}
    for face,area in boundary_faces(X,cells):
        force=P@area
        np.add.at(loads,face,np.tile(force/3,(3,1)))
        axis=int(np.argmax(abs(area)));side=1 if area[axis]>0 else -1
        face_totals.setdefault((axis,side),np.zeros(3));face_totals[axis,side]+=force
        if current is not None:
            a,b,c=current[face];ac=.5*np.cross(b-a,c-a)
            # Face stored winding may not be outward; use reference winding to orient.
            aa,bb,cc=X[face]
            if np.dot(.5*np.cross(bb-aa,cc-aa),area)<0:ac=-ac
            np.add.at(current_loads,face,np.tile((sigma@ac)/3,(3,1)))
    return loads,face_totals,current_loads


def patch_cases(material):
    return {'compression':material.free_uniaxial(.6)[0],
            'expansion':np.eye(3)*1.12,
            'shear':np.array([[1,.3,0],[0,1,0],[0,0,1.]])}


def verify_patch(n,reflect,material,F):
    X,cells=block_mesh(n,reflect);mesh=TetAssembly(X,cells)
    current=X@F.T+np.array([.001,-.002,.003])
    response=mesh.evaluate(current,material);W,P,sigma=material.evaluate(F)
    volume=float(np.prod(LENGTHS));force_scale=max(np.linalg.norm(P)*volume**(2/3),1e-12)
    ext,face_forces,spatial=surface_load(X,cells,P,current,sigma)
    deformation_error=max(np.linalg.norm(s.F-F) for s in response.elements)
    energy_error=abs(response.energy-volume*W)/max(abs(volume*W),1e-15)
    traction_error=np.linalg.norm(response.energy_gradient-ext)/max(np.linalg.norm(ext),1e-12)
    surface_error=np.linalg.norm(ext-spatial)/max(np.linalg.norm(ext),1e-12)
    integrated_stress=sum(s.P*e.reference_volume for s,e in zip(response.elements,mesh._elements))
    stress_error=np.linalg.norm(integrated_stress-volume*P)/max(np.linalg.norm(volume*P),1e-15)
    # Independent identity sum_a grad_a outer X_a = integral P dV0.
    moment_tensor_error=np.linalg.norm(response.energy_gradient.T@X-volume*P)/max(np.linalg.norm(volume*P),1e-15)
    interior=np.all((X>1e-12)&(X<LENGTHS-1e-12),axis=1)
    interior_error=np.linalg.norm(response.internal_forces[interior])/force_scale
    net_error=np.linalg.norm(response.internal_forces.sum(axis=0))/force_scale
    torque=np.sum(np.cross(current-current.mean(axis=0),response.internal_forces),axis=0)
    torque_error=np.linalg.norm(torque)/(force_scale*np.linalg.norm(LENGTHS))
    faces=[]
    for (axis,side),actual in face_forces.items():
        normal=np.zeros(3);normal[axis]=side;area=volume/LENGTHS[axis];expected=P@normal*area
        err=np.linalg.norm(actual-expected)/max(np.linalg.norm(P)*area,1e-12)
        assert err<2e-10
        faces.append(dict(axis=axis,side=side,force_x_N=actual[0],force_y_N=actual[1],force_z_N=actual[2],analytical_x_N=expected[0],analytical_y_N=expected[1],analytical_z_N=expected[2],relative_error=err))
    assert abs(mesh.reference_volume-volume)/volume<1e-12
    assert deformation_error<1e-11
    assert max(energy_error,traction_error,surface_error,stress_error,moment_tensor_error,interior_error,net_error,torque_error)<2e-10
    return dict(nodes=len(X),elements=len(cells),volume_m3=mesh.reference_volume,energy_J=response.energy,min_J=min(s.J for s in response.elements),F_error=deformation_error,energy_relative_error=energy_error,traction_relative_error=traction_error,cauchy_surface_relative_error=surface_error,stress_relative_error=stress_error,stress_moment_relative_error=moment_tensor_error,interior_force_normalized=interior_error,net_force_normalized=net_error,torque_normalized=torque_error),faces


def write_csv(path,rows):
    with path.open('w',newline='') as stream:
        writer=csv.DictWriter(stream,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)


def run():
    here=Path(__file__).resolve().parent;out=here/'verification';out.mkdir(exist_ok=True)
    protected=list((here.parent/'material').rglob('*'))+list((here.parent/'outputs').rglob('*.csv'))
    hashes={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in protected if p.is_file()}
    patches=[];faces=[];gradients=[];balances=[]
    X=np.array([[.001,.002,-.001],[.023,.004,.001],[.005,.019,.002],[.003,.006,.016]])
    tet=Tet4(X)
    rng=np.random.default_rng(52)
    cases={'compression':np.diag([1.,1.,.6]),'expansion':np.eye(3)*1.12,'shear':np.array([[1,.25,0],[0,1,.1],[0,0,.9]])}
    for i in range(5):
        Q,_=np.linalg.qr(rng.normal(size=(3,3)));V,_=np.linalg.qr(rng.normal(size=(3,3)))
        cases['random_'+str(i)]=Q@np.diag(rng.uniform(.6,1.15,3))@V.T
    for label,material in SCENARIOS.items():
        for name,F in patch_cases(material).items():
            for n,reflect in [(1,False),(2,False),(2,True)]:
                row,ff=verify_patch(n,reflect,material,F)
                meta=dict(material=label,case=name,subdivisions=n,reflected=reflect)
                patches.append({**meta,**row});faces.extend({**meta,**f} for f in ff)
        for name,F in cases.items():
            x=X@F.T;state=tet.evaluate(x,material)
            force_scale=max(np.linalg.norm(state.internal_forces),1e-12)
            balances.append(dict(material=label,case=name,net_force_N=np.linalg.norm(state.internal_forces.sum(axis=0)),torque_Nm=np.linalg.norm(np.sum(np.cross(x-x.mean(axis=0),state.internal_forces),axis=0))))
            for ratio in [1e-3,1e-4,1e-5,1e-6,1e-7]:
                h=ratio*np.max(np.linalg.norm(X[1:]-X[0],axis=1));numeric=np.zeros((4,3))
                for a in range(4):
                    for j in range(3):
                        D=np.zeros_like(x);D[a,j]=h
                        numeric[a,j]=(tet.evaluate(x+D,material).energy-tet.evaluate(x-D,material).energy)/(2*h)
                error=np.linalg.norm(numeric-state.energy_gradient)/force_scale
                gradients.append(dict(material=label,case=name,step_relative=ratio,step_m=h,relative_error=error))
                if ratio==1e-5:assert error<3e-6
    write_csv(out/'patch_tests.csv',patches);write_csv(out/'boundary_reactions.csv',faces);write_csv(out/'nodal_gradients.csv',gradients);write_csv(out/'element_balance.csv',balances)
    assert all(hashlib.sha256(Path(p).read_bytes()).hexdigest()==h for p,h in hashes.items())
    summary=dict(patch_cases=len(patches),boundary_face_cases=len(faces),gradient_cases=len(gradients),max_gradient_error_at_step_1e5=max(r['relative_error'] for r in gradients if r['step_relative']==1e-5),max_patch_energy_error=max(r['energy_relative_error'] for r in patches),max_patch_traction_error=max(r['traction_relative_error'] for r in patches),max_cauchy_surface_error=max(r['cauchy_surface_relative_error'] for r in patches),max_interior_force_normalized=max(r['interior_force_normalized'] for r in patches),max_element_net_force_N=max(r['net_force_N'] for r in balances),max_element_torque_Nm=max(r['torque_Nm'] for r in balances),protected_inputs_unchanged=True,protected_sha256=hashes)
    (out/'summary.json').write_text(json.dumps(summary,indent=2))
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig,axes=plt.subplots(1,2,figsize=(12,4))
    for material in SCENARIOS:
        subset=[r for r in gradients if r['material']==material]
        steps=sorted({r['step_relative'] for r in subset})
        axes[0].loglog(steps,[max(r['relative_error'] for r in subset if r['step_relative']==s) for s in steps],'o-',label=material)
        vals=[r for r in patches if r['material']==material]
        axes[1].semilogy(range(len(vals)),[max(r['traction_relative_error'],1e-17) for r in vals],'o',label=material)
    axes[0].set(xlabel='Perturbation / longest reference edge',ylabel='Worst relative nodal gradient error');axes[1].set(xlabel='Patch/mesh case',ylabel='Relative boundary load error')
    for ax in axes:ax.grid(alpha=.2);ax.legend(fontsize=8)
    fig.tight_layout();fig.savefig(out/'verification.png',dpi=160);plt.close(fig)
    # Visualize the synthetic test block only, not a sponge model.
    fig=plt.figure(figsize=(9,4))
    for i,n in enumerate([1,2]):
        ax=fig.add_subplot(1,2,i+1,projection='3d');X,cells=block_mesh(n)
        edges={tuple(sorted(pair)) for c in cells for pair in itertools.combinations(c,2)}
        x=X@patch_cases(SCENARIOS['alpha10_beta0'])['shear'].T
        for a,b in edges:ax.plot(*((x[[a,b]]*1000).T),color='C0',lw=.6)
        ax.set(xlabel='x [mm]',ylabel='y [mm]',zlabel='z [mm]',title=f'{len(cells)} tetrahedra, affine shear')
    fig.tight_layout();fig.savefig(out/'synthetic_patch_meshes.png',dpi=150);plt.close(fig)
    print(json.dumps({k:v for k,v in summary.items() if k!='protected_sha256'},indent=2))


if __name__=='__main__':run()
