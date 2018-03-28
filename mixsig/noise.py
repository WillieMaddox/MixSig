import numpy as np
from .utils import name_generator
from .utils import color_generator


class UniformNoise:
    def __init__(self, n_timestamps=None, mu=0.0, delta=0.5):

        self.n_timestamps = n_timestamps
        self.mu = mu
        self.delta = delta
        self.low = self.mu - self.delta
        self.hi = self.mu + self.delta
        self._value = None

    def __len__(self):
        return len(self.value)

    def __call__(self):
        return self.value

    @property
    def value(self):
        if self._value is None:
            self._generate()
        return self._value

    def generate(self, n_timestamps=None):
        if n_timestamps is not None:
            self.n_timestamps = n_timestamps
        self._generate()
        return self._value

    def _generate(self):
        if self.n_timestamps is None:
            raise AttributeError('n_timesteps: Not Found')
        self._value = np.random.uniform(self.low, self.hi, (self.n_timestamps,))

    def __repr__(self):
        return 'UniformNoise(low={}, hi={})'.format(self.low, self.hi)


class NormalNoise:

    def __init__(self, n_timestamps=None, mu=0.0, sigma=0.01):

        self.n_timestamps = n_timestamps
        self.mu = mu
        self.sigma = sigma
        self._value = None

    def __len__(self):
        return len(self.value)

    def __call__(self):
        return self.value

    @property
    def value(self):
        if self._value is None:
            self._generate()
        return self._value

    def generate(self, n_timestamps=None):
        if n_timestamps is not None:
            self.n_timestamps = n_timestamps
        self._generate()
        return self._value

    def _generate(self):
        if self.n_timestamps is None:
            raise AttributeError('n_timesteps: Not Found')
        self._value = np.random.normal(self.mu, self.sigma, (self.n_timestamps,))

    def __repr__(self):
        return 'NormalNoise(mu={}, sigma={})'.format(self.mu, self.sigma)


class NoNoise:
    def __init__(self):
        self._value = None

    def __call__(self):
        return self.value

    @property
    def value(self):
        if self._value is None:
            self._generate()
        return self._value

    def generate(self, n_timestamps=None):
        self._generate()
        return self._value

    def _generate(self):
        self._value = 0

    def __repr__(self):
        return 'NoNoise()'


class OUNoise:
    """Ornstein-Uhlenbeck process."""

    def __init__(self, n_signals=1, n_timestamps=None, mu=None, theta=0.15, sigma=0.2):
        """Initialize parameters and noise process."""
        self.n_signals = n_signals
        self.n_timestamps = n_timestamps

        if isinstance(mu, np.ndarray):
            assert len(mu) == n_signals
            self.mu = mu
        elif isinstance(mu, int):
            self.mu = np.ones(self.n_signals) * float(mu)
        elif isinstance(mu, float):
            self.mu = np.ones(self.n_signals) * mu
        elif mu is None:
            self.mu = np.zeros(self.n_signals)
        else:
            raise ValueError('What is mu???')

        # self.mu = mu if mu is not None else np.zeros(self.n_signals)

        self.theta = theta
        self.sigma = sigma

        self.state = np.ones(self.n_signals) * self.mu

        self._signals = None

    def __call__(self):
        return self.signals

    @property
    def signals(self):
        if self._signals is None:
            self._signals = self.generate()
        return self._signals

    def generate(self, n_timestamps=None, reset=False):
        if n_timestamps is not None:
            self.n_timestamps = n_timestamps
        if self.n_timestamps is None:
            raise ValueError('Timestamps are None')
        if reset:
            self.reset()

        self._signals = np.empty((self.n_signals, self.n_timestamps))
        for i in range(self.n_timestamps):
            self._signals[:, i] = self.sample()
        return self._signals

    def sample(self):
        """Update internal state and return it as a noise sample."""
        x = self.state
        dx = self.theta * (self.mu - x) + self.sigma * np.random.randn(len(x))
        self.state = x + dx
        return self.state

    def reset(self):
        """Reset the internal state (= noise) to mean (mu)."""
        self.state = np.ones(self.n_signals) * self.mu

