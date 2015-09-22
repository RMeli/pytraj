from __future__ import print_function
import unittest
import pytraj as pt
from pytraj.utils import eq, aa_eq
import pytraj.common_actions as pyca


class Test(unittest.TestCase):
    def test_0(self):
        traj = pt.iterload("./data/md1_prod.Tc5b.x", "./data/Tc5b.top")
        #print(traj)

        for xyz0 in traj.xyz:
            frame = pt.Frame(traj.n_atoms, xyz0, _as_ptr=True)
            aa_eq(frame.xyz, xyz0)
            #print(frame.xyz[0, 0])

    def test_1(self):
        #print('api.Trajectory iterating')
        traj = pt.iterload("./data/md1_prod.Tc5b.x", "./data/Tc5b.top")
        api_t0 = pt.api.Trajectory(traj)
        #print(api_t0)

        # __iter__
        for f in api_t0:
            pass

        f.xyz[0, 0] = 10.
        assert f.xyz[0, 0] == 10.
        assert api_t0.xyz[-1, 0, 0] == 10.

        # __getitem__
        # make a new copy
        api_t0 = pt.api.Trajectory(traj)
        f0 = api_t0[0]
        f0.xyz[0, 0] = 200.
        assert api_t0.xyz[0, 0, 0] == 200.

        # translate
        # make a new copy
        api_t0 = pt.api.Trajectory(traj)
        t0 = traj[:]
        #print(api_t0.xyz[-1, 0])
        pt.translate(api_t0, 'x 1.2')
        #print(api_t0.xyz[-1, 0])
        pt.translate(t0, 'x 1.2')
        aa_eq(api_t0.xyz, t0.xyz)

        try:
            import mdtraj as md
            #print(md.rmsd(api_t0, api_t0, 0))
            #print(api_t0.xyz[-1, 0])
            #print(t0.xyz[-1, 0])
            pt.rmsd(t0, 0)
            pt.rmsd(api_t0, 0)
            #print(api_t0.xyz[-1, 0])
            #print(t0.xyz[-1, 0])
        except ImportError:
            pass

        # test rmsfit
        api_t0.rmsfit(0)


if __name__ == "__main__":
    unittest.main()
