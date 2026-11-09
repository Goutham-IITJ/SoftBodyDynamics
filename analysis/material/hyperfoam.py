"""One-term Abaqus-convention compressible hyperfoam, without thermal strain.

W = 2 mu / alpha**2 [sum(lambda_i**alpha)-3+(J**(-alpha*beta)-1)/beta].
mu: initial shear modulus in Pa; W: J/m^3; P, Cauchy stress: Pa.
F = dx/dX is dimensionless, shape (3,3), real, finite and det(F)>0.
The beta=0 limit is included; beta>=0 restricts this kernel to 0<=nu<0.5.
alpha is nonzero (either sign); mu>0. Parameters are NOT measured sponge data.
No Hessian, dynamics, mesh, contact, damping or thermal response is implemented.
"""
from dataclasses import dataclass
import numpy as np


def _remainder(t):
    """exp(t)-1-t without near-reference cancellation."""
    t=np.asarray(t,dtype=float)
    small=np.abs(t)<1e-3
    answer=np.empty_like(t)
    s=t[small]
    answer[small]=s*s*(.5+s*(1/6+s*(1/24+s*(1/120+s/720))))
    answer[~small]=np.expm1(t[~small])-t[~small]
    return answer


@dataclass(frozen=True)
class Hyperfoam:
    mu: float
    alpha: float
    beta: float = 0.0

    def __post_init__(self):
        values=np.asarray([self.mu,self.alpha,self.beta])
        if np.iscomplexobj(values) or not np.isfinite(values).all():
            raise ValueError('Parameters must be finite real scalars')
        if self.mu<=0 or self.alpha==0 or self.beta<0:
            raise ValueError('Require mu>0, alpha!=0, beta>=0')

    @property
    def nu(self):
        return self.beta/(1+2*self.beta)

    def evaluate(self, F):
        """Return (energy density, first Piola stress, Cauchy stress).

        SVD avoids eigenvector derivatives, including at repeated stretches.
        Floating-point overflow/underflow and nonfinite results raise ValueError;
        no determinant clamping or silent element repair is performed.
        """
        raw=np.asarray(F)
        if raw.shape!=(3,3) or np.iscomplexobj(raw):
            raise ValueError('F must be a real 3x3 matrix')
        F=np.asarray(raw,dtype=float)
        if not np.isfinite(F).all(): raise ValueError('F must be finite')
        sign,logj=np.linalg.slogdet(F)
        if sign<=0 or not np.isfinite(logj): raise ValueError('Require det(F)>0')
        try:
            with np.errstate(over='raise',invalid='raise',divide='raise'):
                U,stretch,Vt=np.linalg.svd(F)
                if np.any(stretch<=0): raise ValueError('Singular deformation')
                logs=np.log(stretch)
                # Consistent spectral logJ; slogdet above supplies orientation.
                L=logs.sum(); t=self.alpha*logs; v=-self.alpha*self.beta*L
                volumetric=0. if self.beta==0 else float(_remainder(v)/self.beta)
                W=float(2*self.mu/self.alpha**2*(np.sum(_remainder(t))+volumetric))
                # exp(t_i)-exp(v) via expm1, avoiding reference cancellation.
                principal=2*self.mu/self.alpha*np.exp(v)*np.expm1(t-v)/stretch
                P=(U*principal)@Vt
                J=float(np.exp(logj))
                if J<=0 or not np.isfinite(J): raise ValueError('Unrepresentable J')
                sigma=P@F.T/J
                if not np.isfinite(W) or not np.isfinite(P).all() or not np.isfinite(sigma).all():
                    raise ValueError('Nonfinite constitutive response')
        except (FloatingPointError,np.linalg.LinAlgError,OverflowError,ZeroDivisionError) as exc:
            raise ValueError('Numerically unrepresentable constitutive state') from exc
        return W,P,sigma

    def free_uniaxial(self, axial_stretch):
        """Analytic zero-lateral-traction branch; axial direction is z.

        Returns F, W, P, sigma, dPzz/dlambda (Pa). Positive tangent here
        is the derivative wrt tensile stretch; also positive compression stiffness.
        Lateral lambda_t=lambda_z**(-nu) follows from Pxx=Pyy=0.
        """
        lam=float(axial_stretch)
        if not np.isfinite(lam) or lam<=0: raise ValueError('Require lambda>0')
        with np.errstate(over='raise',invalid='raise'):
            lateral=np.exp(-self.nu*np.log(lam))
            F=np.diag([lateral,lateral,lam])
            W,P,sigma=self.evaluate(F)
            tangent=2*self.mu/self.alpha*((self.alpha-1)*lam**(self.alpha-2)+(1+self.alpha*self.nu)*lam**(-self.alpha*self.nu-2))
        if not np.isfinite(tangent): raise ValueError('Nonfinite tangent')
        return F,W,P,sigma,float(tangent)
