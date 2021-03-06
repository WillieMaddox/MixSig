import numbers
from collections import namedtuple
from functools import total_ordering
from math import isclose
import numpy as np
from .utils import name_generator
from .utils import color_generator
from .utils import normal_noise_generator
from .utils import uniform_noise_generator
from .utils import timesequence_generator
from .utils import create_one_hots_from_labels
from .utils import generate_labels

WaveProps = namedtuple('WaveProps', 'a w o p')


@total_ordering
class WaveProperty:

    def __init__(self, mean=None, delta=None):
        self.mean = 0.0 if mean is None else float(mean)
        self.delta = 0.0 if delta is None else float(delta)

        if isclose(self.delta, 0, abs_tol=1e-9):
            self.generate = lambda: self.mean
        else:
            self.generate = self._generator(self.mean, self.delta)

        self.value = self.generate()

    def __call__(self, **kwargs) -> float:
        self.value = self.generate()
        return self.value

    def _generator(self, mean, delta):
        """
        np.random.uniform(mean - delta, mean + delta) ==
        mean + (2 * np.random.random() - 1) * delta ==
        a x + b, where a = 2.0 * delta and b = mean - delta

        :param mean: midpoint of a uniform distribution
        :param delta: allowable distance from the mean from which to sample.
        :return: a closure
        """
        # a = 2.0 * delta
        # b = mean - delta
        lo, hi = mean - delta, mean + delta

        def inner():
            # return a * np.random.random() + b
            return np.random.uniform(lo, hi)
        return inner

    def __repr__(self):
        return f'{self.value}'

    def _get_value(self, other):
        if isinstance(other, self.__class__):
            return other.value
        if isinstance(other, numbers.Real):
            return other
        raise TypeError('Incompatible types.')

    def __add__(self, other):
        return self.value + self._get_value(other)

    def __radd__(self, other):
        return self._get_value(other) + self.value

    def __mul__(self, other):
        return self.value * self._get_value(other)

    def __rmul__(self, other):
        return self._get_value(other) * self.value

    def __eq__(self, other):
        return self.value == self._get_value(other)

    def __lt__(self, other):
        return self.value < self._get_value(other)


class Amplitude(WaveProperty):

    def __init__(self, mean=None, delta=None):
        mean = 1.0 if mean is None else float(mean)
        super().__init__(mean, delta)

    def __call__(self, amplitude=1, **kwargs) -> float:
        self.value = self.generate()
        return self.value * amplitude


class Frequency(WaveProperty):

    def __init__(self, mean=None, delta=None):
        mean = 1.0 if mean is None else float(mean)
        super().__init__(mean, delta)

    def __call__(self, frequency=1, **kwargs) -> float:
        self.value = self.generate()
        return self.value * frequency


class Offset(WaveProperty):

    def __call__(self, offset=0, **kwargs) -> float:
        self.value = self.generate()
        return self.value + offset


class Phase(WaveProperty):

    def _generator(self, mean, delta):
        def inner():
            return np.random.random()  # later on this will be scaled by 2*pi
        return inner

    def __call__(self, phase=0, **kwargs) -> float:
        self.value = self.generate()
        return self.value + phase


class Wave:
    def __init__(self,
                 *features,
                 time=None,
                 label=None,
                 amplitude=None,
                 frequency=None,
                 offset=None,
                 phase=None,
                 noise=None,
                 color=None,
                 name=None):

        # self.timestamps = None

        self._timestamp_generator = timesequence_generator(**time) if time is not None else lambda: None
        # self.is_independent = time is not None

        amplitude = amplitude or {}
        self.amplitude = Amplitude(**amplitude)

        frequency = frequency or {}
        self.frequency = Frequency(**frequency)

        offset = offset or {}
        self.offset = Offset(**offset)

        phase = phase or {}
        self.phase = Phase(**phase)

        self.noise = None
        noise = noise or {}
        if 'uniform' in noise:
            self._noise_generator = uniform_noise_generator(**noise['uniform'])
        elif 'normal' in noise:
            self._noise_generator = normal_noise_generator(**noise['normal'])
        else:
            self._noise_generator = lambda *args, **kwargs: 0

        self.color = color or color_generator()
        self.name = name or name_generator()

        self.features = features or ('x',)
        self._timestamps = None
        self._n_timestamps = None
        self._wp = None
        self.indices = None
        self._sample = None
        self._labels = None
        self._inputs = None
        self._label = label

    def generate(self, ts=None, indices=None, **kwargs):

        # self.timestamps = self._timestamp_generator() if self.is_independent else ts
        self._timestamps = self._timestamp_generator()
        if self._timestamps is None:
            self._timestamps = ts

        if self.n_timestamps != len(self.timestamps):
            self._n_timestamps = None
            self._labels = None

        self.indices = indices
        self.noise = self._noise_generator(self.n_timestamps)
        a = self.amplitude(**kwargs)
        w = self.frequency(**kwargs) * 2.0 * np.pi
        o = self.offset(**kwargs)
        p = self.phase(**kwargs) * 2.0 * np.pi
        self._wp = WaveProps(a, w, o, p)
        self._sample = None
        self._inputs = None

    @property
    def timestamps(self):
        if self.indices is None:
            return self.timestamps_full
        else:
            return self.timestamps_full[self.indices]

    @property
    def timestamps_full(self):
        if self._timestamps is None:
            self._timestamps = self._timestamp_generator()
        return self._timestamps

    @property
    def n_classes(self):
        return 1

    @property
    def n_timestamps(self):
        if self._n_timestamps is None:
            self._n_timestamps = len(self.timestamps_full)
        return self._n_timestamps

    def __len__(self):
        return len(self.timestamps)

    @property
    def sample(self):
        if self.indices is None:
            return self.sample_full
        else:
            return self.sample_full[self.indices]

    @property
    def sample_full(self):
        if self._sample is None:
            self._sample = self.d0xdt0()
        return self._sample

    @property
    def labels(self):
        if self.indices is None:
            return self.labels_full
        else:
            return self.labels_full[self.indices]

    @property
    def labels_full(self):
        if self._labels is None:
            self._labels = np.zeros((self.n_timestamps,), dtype=int) + self.label
        return self._labels

    @property
    def label(self):
        return self._label

    @label.setter
    def label(self, val):
        self._label = val

    @property
    def inputs(self):
        if self.indices is None:
            return self.inputs_full
        else:
            return self.inputs_full[self.indices]

    @property
    def inputs_full(self):
        if self._inputs is None:
            self._inputs = np.zeros((self.n_timestamps, len(self.features)))
            for i, feat in enumerate(self.features):
                if feat in ('x', 'd0xdt0'):
                    feature = self.d0xdt0()
                elif feat in ('dxdt', 'd1xdt1'):
                    feature = self.d1xdt1()
                elif feat == 'd2xdt2':
                    feature = self.d2xdt2()
                elif feat == 'd3xdt3':
                    feature = self.d3xdt3()
                elif feat == 'time':
                    feature = self.timestamps_full
                else:
                    raise ValueError(f'Unknown feature {feat}')
                self._inputs[:, i] = feature
        return self._inputs

    def d0xdt0(self):
        a, w, o, p = self._wp
        return a * np.sin(w * self.timestamps_full - p) + o + self.noise

    def d1xdt1(self):
        a, w, o, p = self._wp
        return a * w * np.cos(w * self.timestamps_full - p)

    def d2xdt2(self):
        a, w, o, p = self._wp
        return -1 * a * w ** 2 * np.sin(w * self.timestamps_full - p)

    def d3xdt3(self):
        a, w, o, p = self._wp
        return -1 * a * w ** 3 * np.cos(w * self.timestamps_full - p)

    def __repr__(self):
        return f'Wave(amplitude={self.amplitude}, frequency={self.frequency}, offset={self.offset}, phase={self.phase})'


class MixedWave:
    def __init__(self, classes=None, mwave_coeffs=None):

        self.name = 'Mixed'
        self.signals = None
        self.classes = np.array(classes)
        self.timestamps = None
        self.props = None
        self.labels = None
        self.one_hots = None
        self.samples = None
        self.mixed_signal = None
        self.wave_inputs = None
        self.inputs = None

        self._sample = None
        self._label = None

        if 'time' in mwave_coeffs:
            self.timestamp_generator = timesequence_generator(**mwave_coeffs['time'])

        mixed_wave_prop_defaults = {
            'amplitude': {'mean': 1, 'delta': 0},
            'frequency': {'mean': 1, 'delta': 0},
            'offset': {'mean': 0, 'delta': 0},
            'phase': {'mean': 0, 'delta': 0},
        }
        self.mixed_wave_props = {}
        for prop_name, default_coeffs in mixed_wave_prop_defaults.items():
            coeffs = mwave_coeffs[prop_name] if prop_name in mwave_coeffs else default_coeffs
            if prop_name == 'amplitude':
                self.mixed_wave_props[prop_name] = Amplitude(**coeffs)
            elif prop_name == 'frequency':
                self.mixed_wave_props[prop_name] = Frequency(**coeffs)
            elif prop_name == 'offset':
                self.mixed_wave_props[prop_name] = Offset(**coeffs)
            elif prop_name == 'phase':
                self.mixed_wave_props[prop_name] = Phase(**coeffs)

    def generate(self):
        """ Generate waves from property values."""
        # First process the timestamp dependent waves.  (i.e. make a mixed signal wave.)
        # generate new timestamps
        self.timestamps = self.timestamp_generator()

        # generate new mixed signal properties.
        self.props = {name: prop() for name, prop in self.mixed_wave_props.items()}

        # generate new individual waves.
        # for wave in self.waves:
        #     wave.generate(self.timestamps, **self.props)

        # create a uniform distribution of class labels -> np.array([2,1,3, ... ,1])
        # (500,), (t,), (n_timestamps,)
        self.labels = generate_labels(len(self.timestamps), self.n_classes, labels=self.classes)

        # create one-hots from labels -> np.array([[0,0,1,0], [0,1,0,0], [0,0,0,1], ... ,[0,1,0,0]])
        # (500, 4), (t, c), (n_timestamps, n_classes)
        # self.one_hots = create_one_hots_from_labels(self.labels, self.n_classes)

        # (4, 500), (c, t), (n_classes, n_timestamps)
        # self.samples = np.vstack([wave.sample for wave in self.waves if not wave.is_independent])

        # (500,), (t,), (n_timestamps,)
        # self.mixed_signal = np.sum(self.one_hots.T * self.samples, axis=0)

        # (4, 500, 2), (c, t, f), (n_classes, n_timestamps, n_features)
        # self.wave_inputs = np.stack([wave.inputs for wave in self.waves if not wave.is_independent])

        # (500, 2), (t, f), (n_timestamps, n_features)
        # self.inputs = np.sum(self.one_hots.T[..., None] * self.wave_inputs, axis=0)

    @property
    def sample(self):
        if self._sample is None:
            self._sample = self.mixed_signal
        return self._sample

    @property
    def n_classes(self):
        return len(self.classes)

    @property
    def n_timestamps(self):
        return len(self.timestamps)

    @property
    def label(self):
        return self._label

    @label.setter
    def label(self, val):
        self._label = val
