import pytest


def test_scale_manager__init__():
    import countpoint_generator as cg
    sm = cg.ScaleManager()
    assert sm._chromatic_scale.name == 'Chromatic'


def test_scale__getitem__():
    import countpoint_generator as cg
    s = cg.ScaleManager().build_scale()
    assert s['C1'] == 7
    assert s['C2'] == 14
    assert s['C7'] == 49
    assert s[0] == 'C0'
    assert s[-1] == 'B7'


def test_build_scale():
    import countpoint_generator as cg
    s = cg.ScaleManager().build_scale()
    assert s.name == 'C_Major'
    assert s.sp_to_mp('C2') == 48
    assert s['C2'] == 14
    with pytest.raises(ValueError):
        _ = s['Cs2']


def test_intervals():
    import countpoint_generator as cg
    s = cg.ScaleManager()
    sc = s.build_scale()
    assert sc.steps('C2', 'D2') == 1
    assert sc.steps('C2', 'D3') == 8
    assert sc.steps('C2', 'D4') == 15
    assert sc.interval('C2', 'D3') == 2
    assert sc.interval('C2', 'D4') == 2


def test_tune():
    import countpoint_generator as cg
    s = cg.ScaleManager().build_scale()
    sps = ['C1', 'D1', 'F1', 'E1', 'F1', 'G1', 'A1', 'G1', 'E1', 'D1', 'C1']
    t = cg.Tune(s, sps)
    assert t.peak_sp() == 'C1'
    assert t.trough_sp() == 'A1'
