import logging

from midiutil import MIDIFile

import countpoint_generator as cg


def simple_trace(scale, sps, starting_note='C3'):
    idx = scale[starting_note]
    cp_sps = [starting_note]
    for step in scale.sps_to_steps(sps):
        idx += step * -1
        cp_sps.append(scale[idx])
    return cp_sps


def interval_in_notes(scale, bottom_note, top_note):
    # Double the scale to handle the effective wraparound of intervals
    t_notes = scale.notes * 2

    # Calc the bottom index
    bottom_idx = t_notes.index(bottom_note)

    # Ensure the top index occurs after the bottom index
    # Calculate the interval; add one to bring it into music notation
    return (t_notes.index(top_note, bottom_idx) - bottom_idx) + 1


def real_cp1(scale, sps):
    # From the prior note
    # Determine direction to current note, up, down or stable
    # Take one step in the opposite direction
    # Determine what interval exists
    # Adjust...
    cf_notes = [cg.note_from_sp(sp) for sp in sps]
    cf_steps = scale.sps_to_steps(sps)
    result = [None] * len(sps)
    for i in range(len(cf_notes)):
        if i == 0 or i == len(cf_notes) - 1:
            result[i] = cf_notes[i]
        else:
            p = i - 1
            d = 1 if cf_steps[p] < 0 else -1 if cf_steps[p] > 0 else 0
            prior_note_index = scale.notes.index(result[p])
            current_note_index = (prior_note_index + d) % len(scale.notes)
            result[i] = scale.notes[current_note_index]
            scale.notes.index(result[p])
    return result


import random
import numpy as np


def real_cp2(scale, tune):
    logging.basicConfig(level=logging.DEBUG)

    cf_steps = scale.sps_to_steps(tune.sps)
    cf_directions = [np.sign(s) for s in cf_steps]
    starting_note = scale.sp_to_note(tune.starting_sp()) + '3'

    result = []
    prev_interval = 0

    for i in range(len(tune)):
        if i == 0 or i == len(tune) - 1:
            result.append(starting_note)
            logging.info('starting' if i == 0 else 'ending')
        else:
            step_size = direction = cf_directions[i - 1] * -1
            logging.debug(f'step_size: {step_size}')

            while True:

                prop_sp = scale.shift_note(result[i - 1], step_size)
                prop_interval = scale.interval(tune[i], prop_sp)
                override_draw = random.random()
                logging.debug(f'{prop_sp, prop_interval, override_draw}')

                # If the previous and proposed intervals are in the 4/5 range
                # with a chance of an override, go again
                # If the proposed interval is a 2 or 7, always go again
                # If the proposed note matches other notes, go again

                a = (prev_interval in [4, 5] and prop_interval in [4, 5])
                b = prop_interval in [2, 7]
                c = prop_sp in [result[i - k] for k in [1, 2]]
                logging.debug(f'decision: {a}, {b}, {c}')

                if a or b or c:
                    logging.info(f'go again')
                    step_size += direction
                    logging.debug(f'step_size: {step_size}')
                else:
                    logging.info('accepted proposal')
                    result.append(prop_sp)
                    prev_interval = prop_interval
                    break

    return result


sm = cg.ScaleManager()
cp_scale = sm.build_scale()

midi_content = MIDIFile(2)
midi_content.addTrackName(0, 0, 'cantus firmus')
midi_content.addTrackName(1, 0, 'counterpoint')

cf_tune = cg.Tune(cp_scale, ['C1', 'D1', 'F1', 'E1', 'F1', 'G1', 'A1', 'G1', 'E1', 'D1', 'C1'])
cp_tune = cg.Tune(cp_scale, real_cp2(cp_scale, cf_tune))

for i, v in enumerate(cf_tune.mps):
    midi_content.addNote(0, 0, v, i, 1, 100)

for i, v in enumerate(cp_tune.mps):
    midi_content.addNote(1, 0, v, i + 0.25, 1, 100)

with open('c:/temp/test.mid', "wb+") as f:
    midi_content.writeFile(f)
    midi_content.close()
