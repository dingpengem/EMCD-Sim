"""Independent FFT split-step double-channeling, projected Ni [001] IAM.

No elastic eigenmode decomposition. Coefficients use fft(wave)/N, where N is
number of spatial samples; q in cycles/angstrom, H in radians/nm. Complex
Cartesian responses retain the full dipole MDFF, on the BW relative scale.
"""
from dataclasses import dataclass
import numpy as np
from .cancellation import check_cancelled
from .geometry import electron_wavelength_angstrom, characteristic_qz_angstrom_inv
from .double_channeling import dipole_kernel,equivalent_site_phases
from .gui.memory_budget import reserve_memory


def transition_modes(tensor):
    """T=L L^dagger; columns are coherent complex dipole transition modes.

    Only eigenvalues within 64 eps of zero (relative to tensor norm) are
    rounded to zero. Substantial negatives raise; no physical mode is cut off.
    This is a 3x3 target tensor factorization, not an elastic eigenproblem.
    """
    t=np.asarray(tensor,complex)
    if t.shape!=(3,3) or not np.isfinite(t).all() or not np.allclose(t,t.conj().T,rtol=1e-12,atol=1e-14):
        raise ValueError('Finite Hermitian 3x3 transition tensor required')
    e,v=np.linalg.eigh(t)
    tolerance=64*np.finfo(float).eps*max(float(np.linalg.norm(t)),np.finfo(float).tiny)
    if e.min() < -tolerance:
        raise ValueError(f'Non-PSD MDFF: minimum eigenvalue {e.min():.6g}, roundoff tolerance {tolerance:.6g}')
    return v*np.sqrt(np.maximum(e,0))[None,:]


class FFTSplitStep:
    """Symmetric K/2 -> V -> K/2 on Fourier coefficients; batch-safe 1D/2D.

    Potential is real nm^-1, kinetic is real nm^-1 with optional batch axes.
    Negative dz is the exact adjoint of a positive step in this real potential.
    """
    def __init__(self,potential,kinetic):
        self.u=np.asarray(potential,float)
        self.d=np.asarray(kinetic,float)
        if (self.u.ndim not in (1,2) or self.d.shape[-self.u.ndim:]!=self.u.shape
                or not np.isfinite(self.u).all() or not np.isfinite(self.d).all()):
            raise ValueError('Finite real potential/kinetic arrays with matching spatial shape required')
        self.shape=self.u.shape
        self.size=self.u.size
        self._cached_dz=None

    def advance(self,coefficients,steps,dz,*,cancelled=None):
        check_cancelled(cancelled)
        if not isinstance(steps,int) or steps<0 or not np.isfinite(dz):
            raise ValueError('Nonnegative integer steps and finite dz required')
        c=np.asarray(coefficients,complex)
        if c.shape[-1]!=self.size or not np.isfinite(c).all():
            raise ValueError('Finite Fourier coefficients must match FFT grid')
        if self._cached_dz!=dz:
            self._kinetic=np.exp(.5j*dz*self.d)
            self._transmission=np.exp(1j*dz*self.u)
            self._cached_dz=dz
        axes=tuple(range(-self.u.ndim,0))
        c=c.reshape(c.shape[:-1]+self.shape).copy()
        for _ in range(steps):
            check_cancelled(cancelled)
            wave=np.fft.ifftn(c*self._kinetic,axes=axes)*self.size
            c=np.fft.fftn(wave*self._transmission,axes=axes)/self.size*self._kinetic
        check_cancelled(cancelled)
        return c.reshape(c.shape[:-self.u.ndim]+(self.size,))


def propagate_slices(coefficients,slices,*,adjoint=False):
    """Small direct reference, including reverse slice order for the adjoint."""
    c=np.asarray(coefficients,complex).copy()
    for plan,dz in (reversed(slices) if adjoint else slices):
        c=plan.advance(c,1,-dz if adjoint else dz)
    return c


def forward_event_amplitudes(incoming,kernel,tensor,outgoing_plan,slices,outgoing_indices):
    """Apply coherent transition modes, forward-propagate, select exit 000.

    kernel[g,h,a] includes Coulomb factor and a single site's phase. Return
    complex exit amplitudes per independent target mode (never summed coherently).
    """
    modes=transition_modes(tensor)
    scattered=np.einsum('g,gha,af->fh',incoming,kernel,modes,optimize=True)
    full=np.zeros((3,outgoing_plan.size),complex)
    full[:,outgoing_indices]=scattered
    return propagate_slices(full,slices)[:,0]


def depth_quadrature(thickness_nm,depth_steps):
    if not np.isfinite(thickness_nm) or thickness_nm<0 or not isinstance(depth_steps,int) or depth_steps<2:
        raise ValueError('Finite nonnegative thickness and integer depth_steps >=2 required')
    z=np.linspace(0,float(thickness_nm),depth_steps)
    w=np.full(depth_steps,float(thickness_nm)/(depth_steps-1))
    w[[0,-1]]*=.5
    return z,w


@dataclass
class ProjectedNiFFT:
    potential: np.ndarray
    hkl: np.ndarray
    g: np.ndarray
    acceleration_kv: float
    carrier: np.ndarray
    reduction: bool

    @classmethod
    def build(cls,elastic,*,grid_points=32,potential_cutoff=2.2,systematic_row=False,row_reduction=False,projected_geometry=None):
        if not isinstance(grid_points,int) or grid_points<12 or grid_points%2:
            raise ValueError('Even FFT grid >=12 required')
        if not np.isfinite(potential_cutoff) or potential_cutoff<=0:
            raise ValueError('Positive potential cutoff required')
        crystal=elastic.crystal
        a=crystal.lattice_angstrom[0,0]
        if projected_geometry is None and (not np.allclose(crystal.lattice_angstrom,np.eye(3)*a,atol=1e-12) or not all(s=='Ni' for s in crystal.species)):
            raise ValueError('Projected FFT currently requires cubic Ni [001] frame')
        if row_reduction and not systematic_row:
            raise ValueError('1D reduction requires explicit (200) systematic-row potential')
        if projected_geometry is not None:
            if systematic_row or row_reduction:raise ValueError('Oriented full-2D geometry cannot use [001] row reduction')
            if not np.allclose(crystal.lattice_angstrom,projected_geometry.crystal.lattice_angstrom,atol=1e-13):
                raise ValueError('FFT/BW oriented crystal frames differ')
        if projected_geometry is None and potential_cutoff >= (grid_points//2-1)*2/a:
            raise ValueError('Potential cutoff reaches unsafe FFT Nyquist boundary')
        n=np.rint(np.fft.fftfreq(grid_points)*grid_points).astype(int)
        mx,my=np.meshgrid(n,n,indexing='ij')
        hkl=np.stack((2*mx,2*my,np.zeros_like(mx)),axis=-1).reshape(-1,3)
        g=hkl[:,:2]/a
        if projected_geometry is not None:
            support=max(potential_cutoff,float(np.max(np.linalg.norm(elastic.reciprocal_vectors_xy,axis=1))))
            hkl,g=projected_geometry.harmonics(grid_points,support)
        fourier=np.zeros(len(g),complex)
        kv=elastic.microscope.acceleration_kv
        prefactor=10*(1+1000*kv/510998.95)*electron_wavelength_angstrom(kv)/elastic.potential.cell_volume_angstrom3
        for i,(h,gv) in enumerate(zip(hkl,g)):
            if (np.any(h) and np.linalg.norm(gv)<=potential_cutoff and crystal.is_allowed(tuple(h)) and (not systematic_row or h[1]==0)):
                fourier[i]=prefactor*elastic.potential.structure_factor(tuple(h))
        u=np.fft.ifft2(fourier.reshape(grid_points,grid_points))*grid_points**2
        if np.max(abs(u.imag))>1e-10:
            raise ValueError('Projected potential is not real/Hermitian')
        if row_reduction:
            if not np.allclose(u,u[:,:1],rtol=0,atol=1e-12):
                raise ValueError('Potential is not invariant in y')
            keep=hkl[:,1]==0
            return cls(u[:,0].real,hkl[keep],g[keep],kv,elastic.microscope.incident_k_xy,True)
        return cls(u.real,hkl,g,kv,elastic.microscope.incident_k_xy,False)

    def indices(self,hkl):
        lookup={tuple(h):i for i,h in enumerate(self.hkl)}
        try:indices=np.array([lookup[tuple(h)] for h in hkl])
        except KeyError as exc:raise ValueError(f'Beam outside FFT grid: {exc.args[0]}') from exc
        if len(set(indices))!=len(indices):raise ValueError('Beam basis must be unique')
        return indices

    def plan(self,energy_loss_ev=0.,q_xy=None,*,elastic_potential=True):
        loss=float(energy_loss_ev)
        kv=self.acceleration_kv-loss/1000
        if not np.isfinite(loss) or loss<0 or kv<=0:
            raise ValueError('Loss must be nonnegative and below incident energy')
        lam=electron_wavelength_angstrom(kv)
        ratio=((1+1000*kv/510998.95)*lam/((1+1000*self.acceleration_kv/510998.95)*
                    electron_wavelength_angstrom(self.acceleration_kv)))
        carrier=self.carrier if q_xy is None else self.carrier+np.asarray(q_xy,float)
        if carrier.shape[-1]!=2 or not np.isfinite(carrier).all():raise ValueError('Finite transverse carrier required')
        d=-10*np.pi*lam*(np.sum(self.g**2,axis=-1)+2*np.einsum('...a,ga->...g',carrier,self.g))
        d=d.reshape(d.shape[:-1]+self.potential.shape)
        return FFTSplitStep(self.potential*ratio if elastic_potential else np.zeros_like(self.potential),d)


def incident_fields(grid,thickness_nm,*,depth_steps=257,slice_step_nm=.04,cancelled=None):
    check_cancelled(cancelled)
    z,w=depth_quadrature(thickness_nm,depth_steps)
    if not np.isfinite(slice_step_nm) or slice_step_nm<=0:raise ValueError('Positive finite slice step required')
    interval=float(thickness_nm)/(depth_steps-1)
    n=int(np.ceil(interval/slice_step_nm)) if interval else 0
    dz=interval/n if n else 0.
    plan=grid.plan()
    c=np.zeros(grid.potential.size,complex);c[0]=1
    fields=np.empty((depth_steps,plan.size),complex);fields[0]=c
    for i in range(1,depth_steps):
        c=plan.advance(c,n,dz,cancelled=cancelled);fields[i]=c
    return fields,z,w,n,dz


def multislice_double_channeling_response(elastic,energy_ev,q_xy,thickness_nm,*,
        fft_grid=32,potential_cutoff=2.2,systematic_row=False,row_reduction=False,
        depth_steps=257,slice_step_nm=.04,outgoing_beams=None,outgoing_potential=True,
        batch_pixels=32,memory_budget_mib=2048,prepared_grid=None,prepared_incoming=None,projected_geometry=None,cancelled=None):
    """Adjoint FFT detector fields contracted coherently at independent depths.

    Retain all FFT harmonics during propagation; the explicit incoming/outgoing
    beam sets specify the MDFF paths, without projection or renormalization of
    propagated waves. Return response and norm/leakage/memory diagnostics.
    """
    check_cancelled(cancelled)
    q=np.asarray(q_xy,float)
    if q.ndim!=2 or q.shape[1]!=2 or not len(q) or not np.isfinite(q).all():raise ValueError('Finite nonempty (pixels,2) array required')
    if not isinstance(batch_pixels,int) or batch_pixels<1:raise ValueError('Positive integer batch required')
    depth_quadrature(thickness_nm,depth_steps)
    ni=len(elastic.beams.hkl);ob=elastic.beams if outgoing_beams is None else outgoing_beams
    no=len(ob.hkl);samples=fft_grid if row_reduction else fft_grid**2
    b=min(batch_pixels,len(q));sites=len(elastic.crystal.species)
    dense=96*b*ni*no/2**20
    working=(dense+(64*depth_steps*samples+192*b*samples+32*len(q)*9+64*sites*ni*no)/2**20+8)
    with reserve_memory(working,memory_budget_mib,dense_mib=dense) as admission:
        grid=prepared_grid if prepared_grid is not None else ProjectedNiFFT.build(elastic,grid_points=fft_grid,
            potential_cutoff=potential_cutoff,systematic_row=systematic_row,row_reduction=row_reduction,projected_geometry=projected_geometry)
        fields,z,w,n,dz=(prepared_incoming if prepared_incoming is not None else
            incident_fields(grid,thickness_nm,depth_steps=depth_steps,slice_step_nm=slice_step_nm,cancelled=cancelled))
        if fields.shape!=(depth_steps,grid.potential.size) or not np.allclose(z,np.linspace(0,thickness_nm,depth_steps)):
            raise ValueError('Prepared incoming fields do not match depth/grid settings')
        ii,oi=grid.indices(elastic.beams.hkl),grid.indices(ob.hkl)
        keep_i=np.zeros(grid.potential.size,bool);keep_i[ii]=True
        keep_o=np.zeros(grid.potential.size,bool);keep_o[oi]=True
        delta=np.asarray(ob.hkl)[None,:,:]-np.asarray(elastic.beams.hkl)[:,None,:]
        phases,site_weights=equivalent_site_phases(elastic.beams.hkl,ob.hkl,elastic.crystal.fractional_positions)
        if not len(phases):raise ValueError('At least one localized Ni site required')
        qz=-characteristic_qz_angstrom_inv(energy_ev,elastic.microscope.acceleration_kv)
        response=np.zeros((len(q),3,3),complex)
        norm_error=float(np.max(abs(np.sum(abs(fields)**2,axis=-1)-1)))
        incoming_leak=float(np.max(np.sum(abs(fields[:,~keep_i])**2,axis=-1)))
        outgoing_leak=0.;out_norm=0.
        for start in range(0,len(q),batch_pixels):
            check_cancelled(cancelled)
            sl=slice(start,start+batch_pixels);qb=q[sl];nb=len(qb)
            transfer=np.empty((nb,ni,no,3))
            transfer[...,:2]=qb[:,None,None,:]+grid.g[oi][None,None,:,:]-grid.g[ii][None,:,None,:]
            transfer[...,2]=qz
            kernel=dipole_kernel(transfer)
            check_cancelled(cancelled)
            plan=grid.plan(float(energy_ev),qb,elastic_potential=outgoing_potential)
            reciprocal=np.zeros((nb,plan.size),complex);reciprocal[:,0]=1
            for iz in range(depth_steps-1,-1,-1):
                check_cancelled(cancelled)
                for phase,site_weight in zip(phases,site_weights):
                    check_cancelled(cancelled)
                    v=np.einsum('g,bh,bgha,gh->ba',fields[iz,ii],reciprocal[:,oi].conj(),kernel,phase,optimize=True)
                    response[sl]+=w[iz]*site_weight*v[:,:,None]*v[:,None,:].conj()
                out_norm=max(out_norm,float(np.max(abs(np.sum(abs(reciprocal)**2,axis=-1)-1))))
                outgoing_leak=max(outgoing_leak,float(np.max(np.sum(abs(reciprocal[:,~keep_o])**2,axis=-1))))
                if iz:reciprocal=plan.advance(reciprocal,n,-dz,cancelled=cancelled)
        check_cancelled(cancelled)
        diagnostics=dict(incoming_norm_error=norm_error,outgoing_norm_error=out_norm,
            incoming_max_excluded_population=incoming_leak,outgoing_max_excluded_population=outgoing_leak,
            actual_slice_step_nm=dz,substeps_per_depth_interval=n,depth_steps=depth_steps,
            fft_samples=grid.potential.size,row_reduction=row_reduction,
            estimated_working_mib=working,dense_working_mib=dense,memory_admission=admission)
        return response,diagnostics


def run_tensor_multislice_double_channeling(model,tensor,*,thickness_nm=30.,grid_size=65,
        map_halfwidth_q=1.,reference_energy_ev=852.7,integration_mode='binary',
        aperture_subpixels=64,memory_budget_mib=2048,**propagation):
    """Explicit opt-in angular maps/EELS on the existing SimulationResult API."""
    from .simulation import SimulationResult
    from .double_channeling import intensities_from_response
    if not isinstance(grid_size,int) or grid_size<9 or not np.isfinite(map_halfwidth_q) or map_halfwidth_q<=0:
        raise ValueError('Integer map grid >=9 and positive finite halfwidth required')
    if not np.isfinite(reference_energy_ev) or reference_energy_ev<=0:raise ValueError('Positive reference energy required')
    working=((192+32*len(model.detectors))*grid_size**2+16*len(model.detectors)*len(tensor.energy_ev))/2**20
    with reserve_memory(working,memory_budget_mib):
        q=np.linspace(-map_halfwidth_q,map_halfwidth_q,grid_size)
        qx,qy=np.meshgrid(q,q,indexing='xy');pixels=np.column_stack((qx.ravel(),qy.ravel()))
        masks={k:d.mask(qx,qy) for k,d in model.detectors.items()}
        weights={k:d.integration_weights(qx,qy,mode=integration_mode,subpixels=aperture_subpixels)
            for k,d in model.detectors.items()}
        if not all(w.any() for w in weights.values()):raise ValueError('A detector is outside map')
        spectra={k:np.empty(len(tensor.energy_ev)) for k in weights}
        selected=int(np.argmin(abs(tensor.energy_ev-reference_energy_ev)))
        for i,e in enumerate(tensor.energy_ev):
            transition_modes(tensor.tensor_angstrom2_per_ev[i])
            response,_=multislice_double_channeling_response(model.elastic,float(e),pixels,thickness_nm,
                memory_budget_mib=memory_budget_mib,**propagation)
            t=tensor.tensor_angstrom2_per_ev[i]
            total=intensities_from_response(response,t).reshape(qx.shape)
            for k in spectra:
                spectra[k][i]=(total[masks[k]].sum() if integration_mode=='binary' else
                    (total*weights[k]).sum())*(q[1]-q[0])**2
            if i==selected:
                even=np.einsum('pab,ab->p',response,t.real).real.reshape(qx.shape)
                odd=np.einsum('pab,ab->p',response,1j*t.imag).real.reshape(qx.shape)
        return SimulationResult(tensor.energy_ev,qx,qy,even,odd,spectra,masks,None,thickness_nm,
            0.,model.chiral_groups,weights,integration_mode,aperture_subpixels)
