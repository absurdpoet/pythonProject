import logging
from collections import namedtuple

import numpy as np
import pandas as pd

logging.basicConfig(level=logging.INFO)

DrumGroup = namedtuple('DrumGroup',
                       ['name', 'track', 'midi_pitch_set', 'prob_pitch', 'nudge'],
                       defaults=(0,))
# DrumGroup.__new__.__defaults__ = (0,)

DrumChance = namedtuple('DrumChance',
                        ['prob_hit', 'min_vol', 'max_vol', 'duration'],
                        defaults=(0, 25, 100, 1))
# DrumChance.__new__.__defaults__ = (0, 25, 100, 1)

MIDI_MAP_SHEET = 'midi_map'
HITS_SHEET = 'prob_hits'

# TODO Parameterize
WRITE_PATH = r'c:\temp\sample.xlsx'

# TODO Externalize
pulses_beat = 4
beats_measure = 4
measures_sim = 1


def build_default_workbook(path=WRITE_PATH):
    """Builds a default workbook containing empty but representative settings"""
    writer = pd.ExcelWriter(path, engine='xlsxwriter')

    num_drum_groups = 4

    # Sample configuration; something to get started with
    dgs = [DrumGroup('kick', 1, (36, 52), (0.5, 0.5), 1),
           DrumGroup('snare', 1, (40,), (1.0,), 3),
           DrumGroup('hat', 2, (44,), (1.0,), 1),
           DrumGroup('ride', 2, (49, 51), (0.5, 0.5), 2)]

    pd.DataFrame(dgs[:num_drum_groups]).to_excel(writer, sheet_name=MIDI_MAP_SHEET)

    # Determine index markers for the measure(s)
    total_beats = pulses_beat * beats_measure * measures_sim
    pbx = [idx / pulses_beat for idx in range(total_beats)]

    # Build the default matrix by:
    # 1. establishing the column headers for each drum group
    col_headers = DrumChance._fields * num_drum_groups
    # 2. building a sample row using default values
    row = DrumChance.__new__.__defaults__ * num_drum_groups
    # 3. expanding that into an appropriately sized DataFrame (for serialization through pandas)
    default_matrix = pd.DataFrame([row] * len(pbx), index=pbx, columns=col_headers)

    default_matrix.to_excel(writer, sheet_name=HITS_SHEET + '_0')
    writer.save()


build_default_workbook()

#######################################################################################################################

from midiutil import MIDIFile
from time import gmtime, strftime
from typing import List, Tuple
import random
import ast

# TODO Parameterize
READ_PATH = r'c:\temp\sample6.xlsx'

now = gmtime()


def read_drum_groups(path: str, sheet_name: str = MIDI_MAP_SHEET):
    # Drum groups carry the drum group config information
    drum_groups = list()

    # Set of track IDs
    drum_tracks = set()

    for row in pd.read_excel(path, sheet_name=sheet_name, index_col=0).itertuples():
        # Capture the drum group in actionable form
        drum_groups.append(DrumGroup(row.name,
                                     row.track,
                                     ast.literal_eval(row.midi_pitch_set),
                                     ast.literal_eval(row.prob_pitch),
                                     row.nudge))
        # Take note of the track ID
        drum_tracks.add(row.track)

    return drum_tracks, drum_groups


def read_drum_hits(path: str, sheet_name: str):
    """Reads drum hit probabilities from workbook"""
    drum_hits = pd.read_excel(path, sheet_name=sheet_name, index_col=0)
    logging.info("Drum hits shape: " + str(drum_hits.shape))
    return drum_hits


def log_midi_evts(midi_container: MIDIFile, tracks: Tuple[int] = (1,), evtname: str = 'NoteOn'):
    """Logs out MIDI NoteOn information"""
    for t in tracks:
        note_on_evts = [evt for evt in midi_container.tracks[t].eventList if evt.evtname == evtname]
        if not note_on_evts:
            logging.warning(f"No {evtname} events for track {t}")
            break

        if logging.getLogger().isEnabledFor(logging.INFO):
            [logging.info(evt.__dict__) for evt in note_on_evts]


def generate_measure(num_tracks: int, drum_groups: List[DrumGroup], drum_hits: pd.DataFrame) -> MIDIFile:
    """
    Core function that generates a measure of drum hits.  Places contents in what is effectively a
    temporary container
    """
    midi_measure = MIDIFile(numTracks=num_tracks)

    for row in drum_hits.itertuples():
        time = row.Index

        for i, drum_group in enumerate(drum_groups):
            # Slice the drum group out of the set of groups
            # Offset of 1 to adjust for presence of pandas Index column
            l_bound = i * len(DrumChance._fields) + 1
            drum_chance = DrumChance(*row[l_bound:l_bound + len(DrumChance._fields)])

            # Core random check which drives the drum hit
            if random.random() <= drum_chance.prob_hit:
                nudge = random.randrange(-1 * drum_group.nudge, drum_group.nudge) * 0.01

                # Choose which drum from set of drum groups based on stated probabilities
                pitch_pos = np.random.choice(np.arange(0, len(drum_group.prob_pitch)), p=drum_group.prob_pitch)

                midi_measure.addNote(track=drum_group.track - 1,
                                     channel=0,
                                     pitch=drum_group.midi_pitch_set[pitch_pos],
                                     time=max(0, time + nudge),
                                     duration=(drum_chance.duration / pulses_beat) - nudge,
                                     volume=random.randint(drum_chance.min_vol, drum_chance.max_vol))
    return midi_measure


def simulate_drum_track(pattern: List[int]):
    """Stitches together a series of drum patterns into a MIDI file for use elsewhere."""
    drum_track_idxs, drum_groups = read_drum_groups(READ_PATH)
    num_tracks = max(drum_track_idxs) + 1

    # Generate the core measures to work with
    measures = list()
    # Note, there must be a worksheet defined for each unique measure generated.  The suffix of the worksheet name
    # must match the identifier in the pattern list.
    num_unique_measures = max(pattern) + 1
    for i in range(num_unique_measures):
        worksheet_name = HITS_SHEET + '_' + str(i)
        drum_hits = read_drum_hits(READ_PATH, worksheet_name)
        measure = generate_measure(num_tracks, drum_groups, drum_hits)
        measures.append(measure)

    # Setup final MIDI container for the file that will be written to disk
    midi_file = MIDIFile(num_tracks)
    for idx in drum_track_idxs:
        # Pull the details of the track name from the name of the drum group and augment with date time info
        track_name = ', '.join([dg.name for dg in drum_groups if dg.track == idx] + [strftime("%m%d %H%M", now)])
        midi_file.addTrackName(idx, 0, track_name)

    # Assemble the final set from the individual patterns
    # Each 'p' in the pattern reflects the measure identifier to use in the pattern
    for i, p in enumerate(pattern):
        mx = measures[p]
        measure_tick = mx.ticks_per_quarternote * beats_measure * i
        # Transfer the NoteOn events from measure container to the final container as defined by the measure pattern.
        # Adjust the timing to account for the measure.  Effectively an in place operation.
        # for idx in range(1, len(mx.tracks)):
        for idx, track in enumerate(mx.tracks):
            for evt in filter(lambda e: e.evtname == 'NoteOn', track.eventList):
                midi_file.addNote(track=idx,
                                  channel=0,
                                  pitch=evt.pitch,
                                  time=mx.tick_to_quarter(measure_tick + evt.tick),
                                  duration=mx.tick_to_quarter(evt.duration),
                                  volume=evt.volume)

    with open('c:/temp/' + strftime("%Y%m%d %H%M%S", now) + '.mid', "wb+") as f:
        midi_file.writeFile(f)
        f.close()


starting_pattern = [0]
simulate_drum_track(starting_pattern)
