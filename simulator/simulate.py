#!/usr/bin/env python3
"""Simulate a magnetic capsule moving over an array of 3-axis magnetometers.

Prints one JSON object per line (JSON Lines), so it can be piped to a file,
to another program, or (later) to AWS Kinesis.
"""
import argparse
import json
import math
import random
import time

MU0_OVER_4PI = 1e-7  # T*m/A


def dipole_field(m, r):
    """Magnetic field (tesla) of a point dipole.

    m: dipole moment vector (A*m^2); r: vector from dipole to sensor (m).
    """
    d = math.sqrt(sum(c * c for c in r))
    rhat = [c / d for c in r]
    m_dot_r = sum(mi * ri for mi, ri in zip(m, rhat))
    return [MU0_OVER_4PI * (3 * m_dot_r * rh - mi) / d ** 3 for rh, mi in zip(rhat, m)]


def sensor_grid(n=3, spacing=0.10):
    """n x n grid of sensors in the z=0 plane, centred on the origin."""
    offset = (n - 1) * spacing / 2
    return [(i * spacing - offset, j * spacing - offset, 0.0)
            for i in range(n) for j in range(n)]


def capsule_state(t):
    """Position (m) and dipole moment (A*m^2) of the capsule at time t (s)."""
    w = 2 * math.pi / 20.0  # one loop every 20 s
    pos = (0.06 * math.cos(w * t), 0.06 * math.sin(w * t), 0.12 + 0.02 * math.sin(0.5 * w * t))
    strength = 0.1
    moment = (strength * math.cos(3 * w * t), strength * math.sin(3 * w * t), 0.0)
    return pos, moment


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--rate", type=float, default=10.0, help="samples per second")
    p.add_argument("--duration", type=float, default=20.0, help="seconds of data")
    p.add_argument("--noise-ut", type=float, default=0.1, help="sensor noise std-dev, microtesla")
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--realtime", action="store_true", help="pace output at the sample rate")
    args = p.parse_args()

    random.seed(args.seed)
    sensors = sensor_grid()
    for k in range(int(args.duration * args.rate)):
        t = k / args.rate
        pos, moment = capsule_state(t)
        readings = []
        for s in sensors:
            r = [s[0] - pos[0], s[1] - pos[1], s[2] - pos[2]]
            b = dipole_field(moment, r)
            readings.append([round(c * 1e6 + random.gauss(0, args.noise_ut), 4) for c in b])
        print(json.dumps({
            "t": round(t, 3),
            "true_position_m": [round(c, 5) for c in pos],
            "readings_ut": readings,
        }))
        if args.realtime:
            time.sleep(1.0 / args.rate)


if __name__ == "__main__":
    try:
        main()
    except BrokenPipeError:
        pass  # e.g. output piped into `head`
