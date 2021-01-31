BASIC_PARAMETERS_WORKSHEET_NAME = 'basic_parameters'
MIDI_POS_NAME = 'midi_pos'
DG_PROBS_NAME = 'group_probs'
NUDGE_AMT_NAME = 'nudge_amt'

import ast
import copy
import json
import random
from time import gmtime, strftime

import numpy as np
import pandas as pd
from midiutil import MIDIFile


class ChanceEntry:
    attributes = ['prob_hit', 'min_vol', 'max_vol', 'duration']

    def __init__(self):
        self.prob_hit = 0
        self.min_vol = 0
        self.max_vol = 0
        self.duration = 1


class BasicParameters:

    def __init__(self):
        self.map_worksheet_name = None
        self.hits_worksheet_name = None
        self.measures = None
        self.beats = None
        self.pulses = None
        pass

    # Example of json_data:
    # '{"map_worksheet_name": "midi_map", "hits_worksheet_name": "hits", "measures": 1, "beats": 4, "pulses": 4}'
    def from_json(self, json_data):
        # This is, by far, the most Python magic thing I've ever done.  The dictionary merge isn't all that big of
        # a deal, but loading back into the __dict__ attribute is.  This monkey-patches the JSON elements in as class
        # attributes (properties).  It avoids a bunch of boilerplate logic at the risk of (dramatically) reducing
        # readability.  Not sure if this is Pythonic; might be better served using the *args, **kwargs style packing.
        # It sure feels super dangerous
        self.__dict__ = {**self.__dict__, **json.loads(json_data)}

    def from_worksheet(self, path, sheet_name='basic_parameters'):
        _ = pd.read_excel(path, sheet_name)
        self.from_json(list(_.to_dict().keys())[0])

    @property
    def pulse_length(self):
        return 1 / self.pulses

    @property
    def pulses_per_measure(self):
        return self.beats * self.pulses

    @property
    def pulse_keys(self):
        # Pulse markers in the measure
        return [i / self.pulses for i in range(self.pulses_per_measure)]


def default_midi_map():
    # Maps Rock 32 Pad DW Live drum kit
    _ = {
        'g1': {MIDI_POS_NAME: [36, 37], DG_PROBS_NAME: [0.5, 0.5], NUDGE_AMT_NAME: 1},
        'g2': {MIDI_POS_NAME: [40, 41, 42, 43], DG_PROBS_NAME: [0.55, 0.25, 0.1, 0.1], NUDGE_AMT_NAME: 3},
        'g3': {MIDI_POS_NAME: [44, 45, 46, 47], DG_PROBS_NAME: [0.6, 0.2, 0.1, 0.1], NUDGE_AMT_NAME: 1},
        'g4': {MIDI_POS_NAME: [48, 49], DG_PROBS_NAME: [0.5, 0.5], NUDGE_AMT_NAME: 2}
    }
    return pd.DataFrame.from_dict(_, orient='index')


class ConfigFileGenerator:

    def __init__(self, config):
        self.config = config

    def write_file(self, path):
        writer = pd.ExcelWriter(path, engine='xlsxwriter')

        # Add the high level parms to the first cell of a known worksheet
        pd.DataFrame().to_excel(writer, startrow=4, startcol=0, sheet_name=BASIC_PARAMETERS_WORKSHEET_NAME)
        worksheet = writer.sheets[BASIC_PARAMETERS_WORKSHEET_NAME]
        worksheet.write(0, 0, json.dumps(self.config.__dict__))

        # Add the drum group definitions
        default_midi_map().to_excel(writer, sheet_name=self.config.map_worksheet_name)

        # Add the empty hits
        self.default_drum_hits().to_excel(writer, sheet_name=self.config.hits_worksheet_name)

        writer.save()
        writer.close()
        print('Created ' + path)

    def default_drum_hits(self):
        # Create a set of drum group names
        drum_groups = ['g' + str(i) for i in range(1, 5)]

        # Expand for all groups for all attributes
        column_headers = [dg + '_' + a for dg in drum_groups for a in ChanceEntry.attributes]

        # Add the pulse keys for the first column
        hits = pd.DataFrame(index=self.config.pulse_keys)

        # Add all the attribute columns
        hits = pd.concat([hits, pd.DataFrame(columns=column_headers)])

        # Default empty values to 0 and return
        return hits.fillna(0)


class MIDINote:

    def __init__(self, pitch=0, start=0, duration=0, volume=0, track=0, channel=0):
        self.track = track
        self.channel = channel
        self.pitch = pitch
        self.start = start
        self.duration = duration
        self.volume = volume


class DrumGroup:

    def __init__(self):
        self.midi_pitches = []
        self.midi_probs = []
        self.nudge_amt = 0


class MIDIFileGenerator:

    def __init__(self):
        self.config = BasicParameters()
        self.drum_groups = {}
        self.drum_probs = None

    def do(self, path):
        self.config.from_worksheet(path)
        self.read_data(path)
        # _ = self.generate_midi_notes()
        _ = self.generate_midi_notes_2()
        self.write_midi_file(_)

    def read_data(self, path):
        # Read data from the midi map worksheet
        _ = pd.read_excel(path, sheet_name=self.config.map_worksheet_name, index_col=0)
        for drum_group_name in _.index:
            # Load the data into a DrumGroup dictionary
            dg = DrumGroup()
            dg.midi_pitches = ast.literal_eval(_[MIDI_POS_NAME][drum_group_name])
            dg.midi_probs = ast.literal_eval(_[DG_PROBS_NAME][drum_group_name])
            dg.nudge_amt = _[NUDGE_AMT_NAME][drum_group_name]
            self.drum_groups[drum_group_name] = dg

        # Read data from the probability matrix, as it were
        _ = pd.read_excel(path, sheet_name=self.config.hits_worksheet_name, index_col=0).fillna(0)
        # Load the data into a dictionary of ChanceEntries
        self.drum_probs = {drum_group_name + str(r): ChanceEntry()
                           for drum_group_name in self.drum_groups.keys() for r in list(_.index)}
        for index, row in _.iterrows():
            for drum_group_name in self.drum_groups.keys():

                # Reference to the specific chance entry object
                entry = self.drum_probs.get(drum_group_name + str(row.name))

                for a in ChanceEntry.attributes:
                    # Set the attribute value
                    setattr(entry, a, row[drum_group_name + '_' + a])

    def generate_midi_notes_2(self):
        _ = {}
        for i in range(0, 2):
            _ = {**_, **(self.generate_midi_notes_2a(i * 4))}
        return _

    def generate_midi_notes_2a(self, base_measure):
        first_measure = self.build_measure_precursor(base_measure)
        _ = copy.deepcopy(first_measure)

        for i in range(1, 4):
            _ = {**_, **(self.duplicate(first_measure, i))}

        last_measure = self.build_measure_precursor(base_measure)
        self._shift_timing(last_measure, 4)
        _ = {**_, **last_measure}

        return _

    def build_measure_precursor(self, measure_number):
        all_notes = {}

        for drum_group_name, drum_group in self.drum_groups.items():
            notes = self.build_measure_for_dg(measure_number, drum_group_name, drum_group)

            if len(notes) > 0:
                # Drum group, measure number, and pulse key
                group_key = drum_group_name + '_m' + str(1)
                all_notes[group_key] = notes

        return all_notes

    def duplicate(self, notes, shift_amount):
        new_notes = copy.deepcopy(notes)
        new_notes = {k + '_s' + str(shift_amount): v for k, v in new_notes.items()}
        self._shift_timing(new_notes, shift_amount)
        return new_notes

    def _shift_timing(self, notes, shift_amount):
        for nl in notes.values():
            for n in nl:
                n.start = n.start + ((shift_amount - 1) * self.config.beats)

    def generate_midi_notes(self):
        all_notes = {}

        # TODO Generate and hold a pattern?  Let other drums revolve around a fixed point
        for measure in range(self.config.measures):

            for drum_group_name, drum_group in self.drum_groups.items():
                notes = self.build_measure_for_dg(measure, drum_group_name, drum_group)

                if len(notes) > 0:
                    # Drum group, measure number, and pulse key
                    group_key = drum_group_name + '_m' + str(measure)
                    all_notes[group_key] = notes

        return all_notes

    def build_measure_for_dg(self, measure_number, drum_group_name, drum_group):
        notes = []

        for pulse in self.config.pulse_keys:
            chance_key = drum_group_name + str(pulse)
            drum_chance = self.drum_probs.get(chance_key)

            if random.random() <= drum_chance.prob_hit:
                notes.append(self.build_note(drum_group, drum_chance, measure_number, pulse))

        return notes

    def build_note(self, drum_group, drum_chance, measure_number, pulse):
        n = MIDINote()
        n.pitch = self.choose_pitch(drum_group)
        measure_adjusted_pulse = pulse + (measure_number * self.config.beats)
        n.start = self.generate_start_time(drum_group, measure_adjusted_pulse, laidback=False)
        n.duration = self.generate_duration(drum_chance, measure_adjusted_pulse, n.start)
        n.volume = self.choose_volume(drum_chance)
        return n

    def choose_pitch(self, drum_group):
        # Choose which drum from set of drum groups based on stated probabilities
        pitch_pos = np.random.choice(np.arange(0, len(drum_group.midi_probs)), p=drum_group.midi_probs)
        return drum_group.midi_pitches[pitch_pos]

    def generate_start_time(self, drum_group, measure_adjusted_pulse, laidback):
        # Nudge off the grid, but can't be negative after the nudge
        return max(measure_adjusted_pulse + self.nudge(drum_group.nudge_amt, laidback), 0)

    def generate_duration(self, drum_chance, measure_adjusted_pulse, start):
        # Cap the length so that it doesn't run into the next measure
        return min(drum_chance.duration * self.config.pulse_length,
                   (measure_adjusted_pulse + self.config.pulse_length) - start)

    def choose_volume(self, drum_chance):
        # Range bound random volume
        return random.randint(drum_chance.min_vol, drum_chance.max_vol)

    def write_midi_file(self, notes):
        now = gmtime()
        midi_content = MIDIFile(1)
        midi_content.addTrackName(0, 0, strftime("%#m/%d %H:%M:%S", now))

        # filtered_notes = {k: notes[k] for k in notes.keys() if any(xk in k for xk in ['g2', 'g3', 'g4'])}
        filtered_notes = notes
        [[midi_content.addNote(n.track, n.channel, n.pitch, n.start, n.duration, n.volume) for n in v]
         for v in filtered_notes.values()]

        with open('c:/temp/' + strftime("%Y%m%d %H%M%S", now) + '.mid', "wb+") as _:
            midi_content.writeFile(_)
            _.close()

    def nudge(self, time=0, laidback=False):
        return 0 if time == 0 else random.randrange((0 if laidback else -1 * time), time) * 0.01
