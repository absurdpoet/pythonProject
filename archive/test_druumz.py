import pytest

from archive import druumz


@pytest.fixture
def config():
    _ = druumz.BasicParameters()
    _.from_json(
        '{"map_worksheet_name": "midi_map", "hits_worksheet_name": "hits", "measures": 1, "beats": 4, "pulses": 4}')
    return _


def test_chance_entry():
    x = druumz.ChanceEntry()
    assert x.prob_hit == 0


def test_basic_parameters(config):
    assert config.beats == 4
    assert config.total_pulses == 16


def test_config_file_generator(config):
    x = druumz.ConfigFileGenerator(config)
    d = x.default_drum_hits()
    assert d.iloc[0]['g1_min_vol'] == 0
    assert d.iloc[1]['g2_min_vol'] == 0


def test_midi_file_generator():
    x = druumz.MIDIFileGenerator()
    x.read_file(r'c:\temp\unit_tester.xlsx')
    assert x.midi_map.index[3] == 'g4'

    d = x.drum_probs
    assert d.iloc[0]['g1_min_vol'] == 50.0
    assert d.iloc[1]['g2_min_vol'] == 1.0

