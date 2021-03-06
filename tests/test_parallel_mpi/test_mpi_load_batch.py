# example:
# mpirun -n 4 your_script.py

# always add those lines to your code
import pytraj as pt
import unittest
from pytraj.testing import aa_eq
from pytraj.utils.tools import concat_dict
from pytraj.parallel.base import _load_batch_pmap

from utils import fn
try:
    from mpi4py import MPI
    has_mpi4py = True
except ImportError:
    MPI = None
    has_mpi4py = False


@unittest.skipUnless(has_mpi4py, 'must have mpi4py')
def test_mpi_load_batch():
    # create ``comm`` so you can have the info about n_cpus, cpu id
    comm = MPI.COMM_WORLD

    # you are free to update anything below here
    # _load_batch_pmap is temp method name, will be changed in future

    traj_name = fn("tz2.nc")
    parm_name = fn("tz2.parm7")

    # load to TrajectoryIterator
    traj = pt.iterload(traj_name, parm_name, frame_slice=(0, 4000))

    # make a list of things you want to
    lines = ['autoimage', 'distance :3 :10', 'molsurf @CA']

    # gather the data to 1st core (rank=0)
    #
    n_cores = comm.size
    data = _load_batch_pmap(
        n_cores, lines=lines, traj=traj, mode='mpi', dtype='dict')

    if comm.rank != 0:
        assert data is None

    if comm.rank == 0:
        # each core return a tuple (core_id, dict)
        # so you need to concat the dict
        # use `from pytraj.tools import concat_dict
        data_0 = concat_dict(x[0] for x in data)

        # assert to serial version (do not need to copy below to your script)
        state = pt.load_batch(traj, lines)
        state.run()
        data = state.data[1:].to_dict()

        for key_0, key in zip(sorted(data_0.keys()), sorted(data.keys())):
            aa_eq(data_0[key_0], data[key])


if __name__ == '__main__':
    test_mpi_load_batch()
