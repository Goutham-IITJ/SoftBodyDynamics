"""Run: python -B -m unittest discover -s analysis/material -p test_hyperfoam.py -v"""
import unittest
import numpy as np
from scipy.optimize import root_scalar
from hyperfoam import Hyperfoam


class ConstitutiveTests(unittest.TestCase):
    def test_reference(self):
        for alpha in [-2.,.001,2.,15.]:
            for beta in [0.,1e-10,.125,.5]:
                W,P,s=Hyperfoam(2000,alpha,beta).evaluate(np.eye(3))
                self.assertEqual(W,0.); np.testing.assert_array_equal(P,np.zeros((3,3)))

    def test_objectivity_and_isotropy(self):
        rng=np.random.default_rng(31)
        for _ in range(12):
            R,_=np.linalg.qr(rng.normal(size=(3,3)))
            if np.linalg.det(R)<0: R[:,0]*=-1
            F=np.array([[.83,.18,0],[.02,1.04,.11],[0,0,.65]])
            m=Hyperfoam(1800,13,.125); W,P,s=m.evaluate(F)
            Wr,Pr,sr=m.evaluate(R@F)
            self.assertAlmostEqual(Wr/W,1,places=11)
            np.testing.assert_allclose(Pr,R@P,rtol=1e-11,atol=1e-8)
            np.testing.assert_allclose(sr,R@s@R.T,rtol=1e-11,atol=1e-8)
            Wi,Pi,_=m.evaluate(F@R)
            self.assertAlmostEqual(Wi/W,1,places=11)
            np.testing.assert_allclose(Pi,P@R,rtol=1e-11,atol=1e-8)
            w,p,_=m.evaluate(R); self.assertLess(abs(w),1e-20); self.assertLess(np.linalg.norm(p),1e-9)

    def test_invalid(self):
        bad=[np.diag([1,1,-1]),np.diag([1,1,0]),np.ones((2,2)),np.full((3,3),np.nan),np.full((3,3),np.inf),np.eye(3).astype(complex)]
        for F in bad:
            with self.assertRaises(ValueError):Hyperfoam(1000,2).evaluate(F)
        for args in [(0,2,0),(1,0,0),(1,2,-.1),(np.nan,2,0)]:
            with self.assertRaises(ValueError):Hyperfoam(*args)
        with self.assertRaises(ValueError):Hyperfoam(1,1e200).evaluate(np.eye(3)*2)
        with self.assertRaises(ValueError):Hyperfoam(1,1e-200).evaluate(np.eye(3)*2)

    def test_stress_gradient(self):
        rng=np.random.default_rng(7)
        matrices=[np.diag([1,1,.6]),np.eye(3)*.8,np.eye(3)*1.2,np.eye(3)+np.array([[0,.3,0],[0,0,0],[0,0,0]])]
        for _ in range(16):
            U,_=np.linalg.qr(rng.normal(size=(3,3))); V,_=np.linalg.qr(rng.normal(size=(3,3)))
            matrices.append(U@np.diag(rng.uniform(.55,1.2,3))@V.T)
        for alpha,beta in [(2,0),(13,0),(13,.125),(-2,.5),(.01,1e-8)]:
            m=Hyperfoam(2100,alpha,beta)
            for F in matrices:
                P=m.evaluate(F)[1]; numeric=np.empty((3,3)); h=1e-6
                for i in range(3):
                    for j in range(3):
                        D=np.zeros((3,3));D[i,j]=h
                        numeric[i,j]=(m.evaluate(F+D)[0]-m.evaluate(F-D)[0])/(2*h)
                error=np.linalg.norm(P-numeric)/max(np.linalg.norm(P),1.)
                self.assertLess(error,3e-6)

    def test_lateral_traction_and_tangent(self):
        for beta in [0,1e-8,.125,.5]:
            for lam in np.linspace(.45,1.1,25):
                m=Hyperfoam(2000,13,beta);F,W,P,s,t=m.free_uniaxial(lam)
                self.assertGreater(np.linalg.det(F),0); self.assertGreater(t,0)
                self.assertLess(abs(P[0,0]),1e-8)
                def traction(loglat):return m.evaluate(np.diag([np.exp(loglat),np.exp(loglat),lam]))[1][0,0]
                solved=root_scalar(traction,bracket=[-1,1],xtol=1e-13).root
                self.assertAlmostEqual(np.exp(solved),F[0,0],places=10)
                h=1e-6
                numeric=(m.free_uniaxial(lam+h)[2][2,2]-m.free_uniaxial(lam-h)[2][2,2])/(2*h)
                self.assertLess(abs(numeric-t)/t,1e-7)

    def test_limits_and_small_strain(self):
        F=np.array([[.8,.1,0],[0,1.05,0],[0,0,.7]])
        base=Hyperfoam(1200,10,0).evaluate(F)
        near=Hyperfoam(1200,10,1e-10).evaluate(F)
        np.testing.assert_allclose(near[1],base[1],rtol=1e-8,atol=1e-5)
        self.assertAlmostEqual(near[0]/base[0],1,places=8)
        for beta in [0,.125,.5]:
            m=Hyperfoam(1200,10,beta); h=1e-6
            shear=np.eye(3);shear[0,1]=h
            self.assertAlmostEqual(m.evaluate(shear)[1][0,1]/h/1200,1,places=5)
            pressure=np.trace(m.evaluate(np.eye(3)*(1+h))[2])/3
            K=2*1200*(1/3+beta)
            self.assertAlmostEqual(pressure/(3*h*K),1,places=4)
        # Finite rotation has exactly no imposed strain in theory.
        for l in [.2,.5,1,1.5]:
            self.assertTrue(np.isfinite(Hyperfoam(1200,10).evaluate(np.eye(3)*l)[0]))

    def test_scale_energy_and_stress_symmetry(self):
        F=np.array([[.7,.2,.1],[0,1.1,.1],[0,0,.9]])
        for beta in [0,.125,.5]:
            w,p,s=Hyperfoam(1000,13,beta).evaluate(F)
            w2,p2,s2=Hyperfoam(2000,13,beta).evaluate(F)
            self.assertGreater(w,0);self.assertAlmostEqual(w2,2*w)
            np.testing.assert_allclose(p2,2*p);np.testing.assert_allclose(s,s.T,atol=1e-10)
        # Near-reference energy remains positive and quadratic, not cancellation noise.
        w=Hyperfoam(1000,13,.125).evaluate(np.eye(3)* (1+1e-8))[0]
        self.assertGreater(w,0)

def generate_verification():
    """Material-point diagnostics only; never constructs a mesh/contact problem."""
    import hashlib,json,platform
    from pathlib import Path
    import pandas as pd
    from scipy.optimize import minimize_scalar,brentq
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    here=Path(__file__).resolve().parent; out=here/'verification';out.mkdir(exist_ok=True)
    source=here.parent/'outputs'; config=here.parent/'config.json'
    inputs=[config]+list(source.glob('*/measurements.csv'))
    sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
    before={str(p):sha(p) for p in inputs}
    cfg=json.loads(config.read_text()); obs=[]
    for name,c in cfg['videos'].items():
        frame=pd.read_csv(source/name/'measurements.csv')
        for cycle in c['cycles']:
            hold=frame[frame.time_s.between(*cycle['hold'])]
            obs.append(dict(video=name,cycle=cycle['id'],split=cycle['split'],x_mm=hold.compression_mm.median(),water_g=c['water_g'],force_N=(c['water_g']+75)*.00981,first_frame=int(hold.frame.iloc[0]),last_frame=int(hold.frame.iloc[-1])))
    obs=pd.DataFrame(obs);obs.to_csv(out/'observations.csv',index=False)
    train=obs[obs.split=='initial_fit'].sort_values('force_N'); assert set(train.video)=={'500ml','1000ml'}
    A=.00365; H=.027
    # Exact traction-free branch, compression nominal stress per unit mu.
    def unit_force(lam,alpha,beta):
        nu=beta/(1+2*beta)
        return -A*2/alpha*np.exp(-alpha*nu*np.log(lam))*np.expm1(alpha*(1+nu)*np.log(lam))/lam
    def predict(force,mu,alpha,beta):
        return 1000*H*(1-brentq(lambda l:mu*unit_force(l,alpha,beta)-force,.2,1,xtol=1e-13))
    def fit_scale(x,force,alpha,beta):
        g=unit_force(1-x/(1000*H),alpha,beta)
        mu=float(np.sum(g/force)/np.sum((g/force)**2))
        return mu,float(np.sum(((mu*g-force)/force)**2))
    def fit_two(x,force,beta):
        grid=np.geomspace(.2,60,180)
        values=[fit_scale(x,force,a,beta)[1] for a in grid]; k=int(np.argmin(values))
        sol=minimize_scalar(lambda a:fit_scale(x,force,a,beta)[1],bounds=(grid[max(0,k-1)],grid[min(len(grid)-1,k+1)]),method='bounded',options={'xatol':1e-10})
        alpha=float(sol.x);mu,loss=fit_scale(x,force,alpha,beta)
        return mu,alpha,loss,alpha<.201 or alpha>59.99
    fits=[];pred=[];profiles=[];curves=[];sensitivity=[]
    x=train.x_mm.to_numpy(); force=train.force_N.to_numpy()
    for beta in [0.,.125,.5]:
        for shape in ['free','fixed_2','fixed_10','fixed_20']:
            if shape=='free':mu,alpha,loss,bound=fit_two(x,force,beta)
            else:alpha=float(shape.split('_')[1]);mu,loss=fit_scale(x,force,alpha,beta);bound=False
            fits.append(dict(beta=beta,nu_assumed=beta/(1+2*beta),shape_strategy=shape,mu_effective_Pa=mu,alpha=alpha,relative_force_loss=loss,shape_at_search_boundary=bound))
            for r in obs.itertuples():
                xp=predict(r.force_N,mu,alpha,beta);fp=mu*unit_force(1-r.x_mm/(1000*H),alpha,beta)
                pred.append(dict(beta=beta,shape_strategy=shape,video=r.video,cycle=r.cycle,split=r.split,predicted_x_mm=xp,measured_x_mm=r.x_mm,x_error_mm=xp-r.x_mm,predicted_force_N=fp,assumed_force_N=r.force_N,force_error_N=fp-r.force_N))
            if shape=='free':
                model=Hyperfoam(mu,alpha,beta)
                for lam in np.linspace(.45,1,112):
                    F,W,P,sigma,tangent=model.free_uniaxial(lam)
                    assert tangent>0 and abs(P[0,0])<1e-7
                    assert np.isclose(-A*P[2,2],mu*unit_force(lam,alpha,beta),rtol=1e-11,atol=1e-10)
                    curves.append(dict(beta=beta,alpha=alpha,mu_Pa=mu,axial_stretch=lam,compression_mm=H*(1-lam)*1000,lateral_stretch=F[0,0],J=np.linalg.det(F),W_J_m3=W,nominal_axial_Pa=P[2,2],cauchy_axial_Pa=sigma[2,2],compression_force_N=-A*P[2,2],tangent_N_mm=A*tangent/H/1000,lateral_traction_Pa=P[0,0]))
        for alpha in np.geomspace(.2,60,160):
            mu,loss=fit_scale(x,force,alpha,beta);xp=np.array([predict(f,mu,alpha,beta) for f in force]);u=.3+.1*x
            profiles.append(dict(beta=beta,alpha=alpha,mu_Pa=mu,relative_force_loss=loss,max_normalized_x_error=np.max(abs(xp-x)/u),within_engineering_allowances=bool(np.all(abs(xp-x)<=u))))
        for tare in [50,75,100]:
            for scales in [(1,1),(.9,.9),(1.1,1.1),(.9,1.1),(1.1,.9)]:
                for shifts in [(-.3,-.3),(0,0),(.3,.3),(-.3,.3),(.3,-.3)]:
                    xx=x*np.array(scales)+shifts;ff=(train.water_g.to_numpy()+tare)*.00981
                    mu,alpha,loss,bound=fit_two(xx,ff,beta)
                    sensitivity.append(dict(beta=beta,tare_g=tare,scale_low=scales[0],scale_high=scales[1],shift_low_mm=shifts[0],shift_high_mm=shifts[1],mu_Pa=mu,alpha=alpha,loss=loss,boundary=bound,prediction_750_mm=predict((750+tare)*.00981,mu,alpha,beta)))
    for name,rows in [('fits',fits),('predictions',pred),('shape_profile',profiles),('compression_response',curves),('parameter_sensitivity',sensitivity)]:pd.DataFrame(rows).to_csv(out/(name+'.csv'),index=False)
    # Numerical gradient step sweep; random orientations include repeated stretches.
    rng=np.random.default_rng(44);grad=[];obj=[]
    for alpha,beta in [(2.,0.),(13.,0.),(13.,.125),(-2.,.5)]:
        m=Hyperfoam(2100,alpha,beta)
        for case in range(15):
            R,_=np.linalg.qr(rng.normal(size=(3,3)))
            S,_=np.linalg.qr(rng.normal(size=(3,3)))
            stretches=np.array([.75,.75,.75]) if case==0 else rng.uniform(.5,1.2,3)
            F=R@np.diag(stretches)@S.T;W,P,sigma=m.evaluate(F)
            wr,pr,sr=m.evaluate(R@F)
            obj.append(dict(alpha=alpha,beta=beta,case=case,energy_relative_error=abs(wr-W)/max(abs(W),1),stress_relative_error=np.linalg.norm(pr-R@P)/max(np.linalg.norm(P),1)))
            for h in [1e-4,1e-5,1e-6,1e-7]:
                numeric=np.empty((3,3))
                for i in range(3):
                    for j in range(3):
                        delta=np.zeros((3,3));delta[i,j]=h
                        numeric[i,j]=(m.evaluate(F+delta)[0]-m.evaluate(F-delta)[0])/(2*h)
                grad.append(dict(alpha=alpha,beta=beta,case=case,step=h,relative_gradient_error=np.linalg.norm(numeric-P)/max(np.linalg.norm(P),1)))
    pd.DataFrame(grad).to_csv(out/'gradient_checks.csv',index=False);pd.DataFrame(obj).to_csv(out/'objectivity_checks.csv',index=False)
    assert max(g['relative_gradient_error'] for g in grad if g['step']==1e-6)<3e-6
    df=pd.DataFrame(curves);fig,axs=plt.subplots(2,3,figsize=(13,7))
    for beta,g in df.groupby('beta'):
        label=f'assumed nu={beta/(1+2*beta):.2f}'
        for ax,col,title in zip(axs.flat,['compression_force_N','lateral_stretch','J','W_J_m3','nominal_axial_Pa','tangent_N_mm'],['Force [N]','Lateral stretch','Volume ratio J','Energy [J/m³]','Nominal axial stress [Pa]','Axial tangent [N/mm]']):
            ax.plot(g.compression_mm,g[col],label=label);ax.set(xlabel='Compression [mm]',ylabel=title);ax.grid(alpha=.2)
    for r in obs.itertuples():axs[0,0].plot(r.x_mm,r.force_N,'ko' if r.split=='initial_fit' else 'kx')
    axs[0,0].legend();fig.suptitle('Ideal homogeneous traction-free material test; each compressibility scenario refitted using two training points only')
    fig.tight_layout();fig.savefig(out/'compression_response.png',dpi=150);plt.close(fig)
    prof=pd.DataFrame(profiles);fig,ax=plt.subplots(figsize=(8,4))
    for beta,g in prof.groupby('beta'):ax.semilogx(g.alpha,g.max_normalized_x_error,label=f'beta={beta}')
    ax.axhline(1,color='k',ls='--');ax.set(xlabel='Shape alpha (scale refitted)',ylabel='Maximum training displacement error / allowance',ylim=(0,5));ax.legend();ax.grid(alpha=.2);fig.tight_layout();fig.savefig(out/'identifiability.png',dpi=150);plt.close(fig)
    assert before=={str(p):sha(p) for p in inputs}
    report=dict(input_sha256=before,inputs_unchanged=True,python=platform.python_version(),numpy=np.__version__,unit_test_methods=7,gradient_states=60,gradient_step_sweep_evaluations=240,max_gradient_relative_error_h1e6=max(g['relative_gradient_error'] for g in grad if g['step']==1e-6),max_objectivity_energy_relative_error=max(g['energy_relative_error'] for g in obj),max_objectivity_stress_relative_error=max(g['stress_relative_error'] for g in obj),minimum_uniaxial_tangent_N_mm=min(g['tangent_N_mm'] for g in curves),reference='https://docs.software.vt.edu/abaqusv2026/English/SIMACAEMATRefMap/simamat-c-hyperfoam.htm',height_assumed_m=H,area_assumed_m2=A,fit_loss='sum(((mu*unit_force(lambda)-F)/F)**2); lambda=1-x/H; fitting cycles only')
    (out/'summary.json').write_text(json.dumps(report,indent=2))
    print(pd.DataFrame(fits).to_string(index=False));print(report)
    print('profile accepted alpha',prof[prof.within_engineering_allowances].groupby('beta').alpha.agg(['min','max']).to_string())
    print('parameter sensitivity',pd.DataFrame(sensitivity).groupby('beta')[['mu_Pa','alpha','prediction_750_mm']].agg(['min','max']).to_string())

if __name__=='__main__':
    import sys
    if '--report' in sys.argv:
        result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(ConstitutiveTests))
        if not result.wasSuccessful():sys.exit(1)
        generate_verification()
    else: unittest.main()
