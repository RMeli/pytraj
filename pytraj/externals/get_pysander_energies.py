from pytraj._shared_methods import iterframe_master
from pytraj._get_common_objects import _get_topology, _get_data_from_dtype, _super_dispatch
from pytraj.compat import range
from pytraj.decorators import _register_pmap

__all__ = ['energy_decomposition']


def _default_func():
    from array import array
    return array('d', [])


@_register_pmap
@_super_dispatch()
def energy_decomposition(traj=None,
                          parm=None,
                          igb=8,
                          input_options=None,
                          qmmm_options=None,
                          mode=None,
                          dtype='dict',
                          frame_indices=None,
                          verbose=False,
                          top=None):
    """energy decomposition by calling `libsander`

    Parameters
    ----------
    traj : Trajectory-like or iterables that produce Frame
        if `traj` does not hold Topology information, `top` must be provided
    parm : str or Structure from ParmEd, default=None, optional
        To avoid any unexpected error, you should always provide original topology
        filename. If parm is None, pytraj will load Topology from traj.top.filename.

        - why do you need to load additional topology filename? Because cpptraj and sander
          use different Topology object, can not convert from one to another.
    igb : GB model, default=8 (GB-Neck2)
        If specify `input_options`, this `igb` input will be ignored
    input_options : InputOptions from `sander`, default=None, optional
        if `input_options` is None, use `gas_input` with given igb.
        If `input_options` is not None, use this
    qmmm_options : InputOptions from `sander` for QMMM, optional
    mode : str, default=None, optional
        if mode='minimal', get only 'bond', 'angle', 'dihedral' and 'total' energies
    top : pytraj.Topology or str, default=None, optional
        only need to specify this ``top`` if ``traj`` does not hold Topology
    dtype : str, {'dict', 'dataset', 'ndarray', 'dataframe'}, default='dict'
        return data type
    frame_indices : None or 1D array-like, default None
        if not None, only perform calculation for given frames
    verbose : bool, default False
        print warning message if True

    Returns
    -------
    Dict of energies (to be used with DataFrame) or DatasetList

    Examples
    --------
    >>> import pytraj as pt
    >>> # GB energy
    >>> traj = pt.datafiles.load_ala3()
    >>> traj.n_frames
    1
    >>> data = pt.energy_decomposition(traj, igb=8)
    >>> data['gb']
    array([-92.88577683])
    >>> data['bond']
    array([ 5.59350521])

    >>> # PME
    >>> import os
    >>> from pytraj.testing import amberhome
    >>> import sander
    >>> topfile = os.path.join(amberhome, "test/4096wat/prmtop")
    >>> rstfile = os.path.join(amberhome, "test/4096wat/eq1.x")
    >>> traj = pt.iterload(rstfile, topfile) 
    >>> options = sander.pme_input()
    >>> options.cut = 8.0
    >>> edict = pt.energy_decomposition(traj=traj, input_options=options)
    >>> edict['vdw'] 
    array([ 6028.95167558])
    """
    from collections import defaultdict, OrderedDict
    from pytraj.misc import get_atts
    import numpy as np

    try:
        import sander
    except ImportError:
        raise ImportError("need both `pysander` installed. Check Ambertools15")

    ddict = defaultdict(_default_func)

    if input_options is None:
        inp = sander.gas_input(igb)
    elif igb is not None:
        if verbose:
            print("inp is not None, ignore provided `igb` and use `inp`")
        inp = input_options

    if parm is None:
        try:
            # try to load from file by taking top.filename
            _parm = top.filename
        except AttributeError:
            raise ValueError("parm must be AmberParm object in ParmEd")
    else:
        # Structure, string
        _parm = parm

    if not hasattr(_parm, 'coordinates') or _parm.coordinates is None:
        try:
            # if `traj` is Trajectory-like (not frame_iter), try to take 1st
            # coords
            coords = traj[0].xyz
        except (TypeError, AttributeError):
            # create fake list
            coords = [0. for _ in range(top.n_atoms * 3)]
    else:
        # use default coords in `AmberParm`
        coords = _parm.coordinates

    if top.has_box():
        box = top.box.tolist()
        has_box = True
    else:
        box = None
        has_box = False

    with sander.setup(_parm, coords, box, inp, qmmm_options):
        for frame in iterframe_master(traj):
            if has_box:
                sander.set_box(*frame.box.tolist())
            sander.set_positions(frame.xyz)
            ene, frc = sander.energy_forces()

            # potentially slow
            ene_atts = get_atts(ene)
            for att in ene_atts:
                ddict[att].append(getattr(ene, att))

    new_dict = None
    if mode == 'minimal':
        new_dict = {}
        for key in ['bond', 'angle', 'dihedral', 'tot']:
            new_dict[key] = ddict[key]
    else:
        new_dict = ddict

    for key in new_dict.keys():
        new_dict[key] = np.asarray(new_dict[key])

    if dtype == 'dict':
        return OrderedDict(new_dict)
    else:
        from pytraj.datasets.DatasetList import DatasetList

        dslist = DatasetList()
        size = new_dict['tot'].__len__()
        for key in new_dict.keys():
            dslist.add_set('double')
            dslist[-1].key = key
            dslist[-1].resize(size)
            dslist[-1].data[:] = new_dict[key]
        return _get_data_from_dtype(dslist, dtype)
