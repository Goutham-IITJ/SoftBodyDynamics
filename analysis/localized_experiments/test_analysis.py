"""CV failure-mode and artifact integrity tests; no constitutive fitting."""
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parent))
import unittest,json
import numpy as np
import pandas as pd
from analyze import foam_components,profile
from inspect_videos import ROOT,OUT,sha


class LocalizedTests(unittest.TestCase):
    def test_disconnected_visible_foam_lobes_are_retained(self):
        mask=np.zeros((150,200),bool);mask[20:120,10:70]=True;mask[20:120,130:190]=True;mask[140,100]=True
        result=foam_components(mask)
        self.assertTrue(result[50,40]);self.assertTrue(result[50,150]);self.assertFalse(result[140,100]);self.assertFalse(result[50,100])

    def test_bottom_observation_survives_hidden_yellow(self):
        yellow=np.zeros((100,100),bool);green=np.zeros_like(yellow);green[65:90,10:90]=True
        p=profile(yellow,green,[100])
        self.assertTrue(np.isnan(p[0,0]));self.assertTrue(np.isfinite(p[3,0]))

    def test_frame_timestamp_and_profile_integrity(self):
        for slug,count in [('half_area',452),('fingertip',441)]:
            p=OUT/slug;d=pd.read_csv(p/'measurements.csv');times=pd.read_csv(p/'timestamps.csv');q=pd.read_csv(p/'profiles.csv')
            np.testing.assert_array_equal(d.frame,np.arange(count));np.testing.assert_allclose(d.time_s,times.time_s,atol=1e-6)
            self.assertTrue(np.all(np.diff(d.time_s)>0));self.assertEqual(len(q),19*count)
            self.assertFalse(q.duplicated(['frame','u_reference']).any())
            np.testing.assert_allclose(q.time_s,d.time_s.to_numpy()[q.frame],atol=1e-6)
            for name in ['selected_manifest.csv']:
                selected=pd.read_csv(p/name)
                np.testing.assert_allclose(selected.time_s,d.time_s.to_numpy()[selected.frame],atol=1e-6)
            cal=json.loads((p/'calibration.json').read_text());poly=cal['y_to_relative_mm_polynomial']
            self.assertTrue(np.all(np.polyval(np.polyder(poly),np.arange(0,700))>0))
        event=pd.read_csv(OUT/'event_review_manifest.csv')
        for r in event.itertuples():
            d=pd.read_csv(OUT/r.experiment/'timestamps.csv');self.assertAlmostEqual(r.time_s,d.time_s.iloc[r.frame],places=6)

    def test_force_and_hidden_surface_are_not_claimed(self):
        peaks=pd.read_csv(OUT/'fingertip_peaks.csv')
        self.assertTrue(peaks.force_N.isna().all());self.assertFalse(peaks.depth_is_true_hidden_surface.any())
        loads=pd.read_csv(OUT/'load_assumptions.csv');self.assertFalse(loads.force_measured.any())
        finger=pd.read_csv(OUT/'fingertip/profiles.csv');self.assertGreater(finger.fingertip_occludes_true_top.sum(),0)

    def test_frozen_baseline_and_video_bytes_unchanged(self):
        hashes=json.loads((OUT/'baseline_provenance.json').read_text())['protected_sha256']
        self.assertEqual(len(hashes),461)
        for name,value in hashes.items():self.assertEqual(sha(ROOT/name),value,name)


if __name__=='__main__':unittest.main()
