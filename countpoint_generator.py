from collections import namedtuple

from numpy import cumsum


# sps - Scientific PitcheS
# mps - MIDI PitcheS
# notes - Only the letters
# idxs - indexes related to an expanded list of sps or mps
# scale - sps (as fields) and MIDI pitches as values


def note_from_sp(sp):
    return sp[:len(sp) - 1]


class Scale:

    def __init__(self, scale_type, notes, sps, mps, root_note=None):
        self.root_note = root_note
        self.scale_type = scale_type
        self.name = ('' if self.root_note is None else f'{self.root_note}_') + self.scale_type
        self.notes = notes
        ScaleDetails = namedtuple(self.name, sps)
        self._pitches = ScaleDetails(*mps)

    def __str__(self):
        return self.name + ': ' + str(self.notes)

    def __getitem__(self, item):
        """Returns the SPN note for a positional index and vice versa"""
        sps_idxs = self._pitches._fields

        # Item is an SPN if a string, otherwise we expect an in positional index
        return sps_idxs.index(item) if isinstance(item, str) else sps_idxs.__getitem__(item)

    def sp_to_mp(self, sp):
        """Scientific pitch to MIDI pitch"""
        return self._pitches[self.__getitem__(sp)]

    def mp_to_sp(self, mp):
        """MIDI pitch to scientific pitch"""
        return self[self._pitches.index(mp)]

    def sp_to_note(self, sp):
        """Scientific pitch to note.  C4 -> C"""
        return sp[:len(sp) - 1]

    def note_idx(self, note):
        """Note index in the set of notes that comprises the scale.  D -> 2"""
        return self.notes.index(note)

    def sps_to_steps(self, sps):
        """
        Translate a series of sps to the number of positions b/w the notes
        ['A1', 'B1', 'D2'] -> [1. 2]
        """
        return [self.steps(sps[i], sps[j]) for i, j in enumerate(range(1, len(sps)))]

    def steps(self, sp1, sp2):
        """Steps between two notes.  ('B1', 'D2') -> 2"""
        return self.__getitem__(sp2) - self.__getitem__(sp1)

    def shift_note(self, sp, amount=0):
        """Returns the note 'amount' positions away from the sp as dictated by the scale"""
        return self[self[sp] + amount]

    def interval(self, sp1, sp2):
        """Flattened down to len of the notes in the scale; rotating interval"""
        return self.steps(sp1, sp2) % len(self.notes) + 1


class ScaleManager:
    _OCTAVE_RANGE = range(0, 8)

    _ALL_NOTES = ('C', 'Cs', 'D', 'Ds', 'E', 'F', 'Fs', 'G', 'Gs', 'A', 'As', 'B')

    _SCALES = {'Chromatic': tuple([0] + [1] * (len(_ALL_NOTES) - 2)),
               'Major': (0, 2, 2, 1, 2, 2, 2),
               'Minor': (0, 2, 1, 2, 2, 1, 2)}

    def __init__(self):
        sps = self._notes_to_sps(self._ALL_NOTES)
        midi_offset = 24
        mps = list(range(midi_offset, len(sps) + midi_offset))
        self._chromatic_scale = Scale('Chromatic', self._ALL_NOTES, sps, mps)

    def _idxs_to_notes(self, positions, root):
        notes = self._chromatic_scale.notes
        root_idx = notes.index(root)
        return [notes[(root_idx + np) % len(notes)] for np in positions]

    def _notes_to_sps(self, notes):
        """
        Expands the set of notes over the full set of supported octaves.
        :param notes: List of the notes in one octave
        :return: List of Scientific Pitches across all supported octaves
        """
        return [f'{n}{o}' for o in self._OCTAVE_RANGE for n in notes]

    def build_scale(self, root='C', scale_type='Major'):
        steps = self._SCALES[scale_type]
        idxs = list(cumsum(steps))
        notes = self._idxs_to_notes(idxs, root)

        sps = self._notes_to_sps(notes)
        mps = [self._chromatic_scale.sp_to_mp(sp) for sp in sps]
        return Scale(scale_type, notes, sps, mps, root)


class Tune:

    def __init__(self, scale, tune_sps):
        self.scale = scale
        self.sps = tune_sps
        self.mps = [self.scale.sp_to_mp(sp) for sp in self.sps]

    def __len__(self):
        return len(self.sps)

    def __getitem__(self, item):
        return self.sps[item]

    def __str__(self):
        return str(self.sps)

    def peak_sp(self):
        return self.scale[min(self.mps)]

    def trough_sp(self):
        return self.scale[max(self.mps)]

    def starting_sp(self):
        return self.sps[0]

    def ending_sp(self):
        return self.sps[-1]


# determine direction of second to last step
# setup contrary motion on second to last step
# see if stepwise contrary motion results in consonant interval
# see if skipwise contrary motion results in consonant interval
# what is the closest consonant interval?
