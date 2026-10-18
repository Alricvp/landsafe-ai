"""
sim_localize.py - prove the leak-localisation maths BEFORE buying hardware.

The idea: two sensors clamped on a pipe hear the same leak at slightly
different times. That time gap (in seconds) times the speed of sound in
the pipe (in m/s) gives a distance.

    sensor A at xA, sensor B at xB, leak somewhere between them at x
    time for A to hear it : (x  - xA) / a
    time for B to hear it : (xB - x ) / a
    time gap (B minus A)  : (xA + xB - 2x) / a
    => x = (xA + xB - a * gap) / 2

This script simulates what the two microphones would hear, finds the gap
by cross-correlation, and prints the true position next to the estimate.

If the leak sits OUTSIDE the two sensors, the gap stops carrying position
information - that is exactly why real systems need several nodes.

No external libraries - plain Python.

Usage:
    python sim_localize.py
    python sim_localize.py --snr 2
    python sim_localize.py --trials 10 --seed 3
"""

import argparse
import math
import random

WAVE_SPEED = 1050.0   # m/s, structure-borne sound in a water-filled pipe
FS = 2000             # samples per second (1 sample = 0.5 ms = ~0.5 m)


# ----------------------------------------------------------------- signals

def lowpass(xs, alpha):
    out, prev = [], 0.0
    for x in xs:
        prev += alpha * (x - prev)
        out.append(prev)
    return out


def highpass(xs, alpha):
    lp = lowpass(xs, alpha)
    return [x - y for x, y in zip(xs, lp)]


def band_noise(n, rng):
    """Band-limited hiss (~200 Hz - 8 kHz) - what a leak sounds like."""
    raw = [rng.gauss(0.0, 1.0) for _ in range(n)]
    return highpass(lowpass(raw, 0.35), 0.02)


def delay(xs, k):
    """Shift a recording later by k samples."""
    k = int(round(k))
    if k <= 0:
        return list(xs)
    return [0.0] * k + list(xs[:len(xs) - k])


def reject_transients(xs, k=5.0):
    """
    Impulsive noise (valve clicks, hammer taps) is heard by BOTH sensors at
    the same instant, which creates a fake zero-lag correlation peak.
    Standard practice is to clip those samples out before correlating.
    """
    n = len(xs)
    mean = sum(xs) / n
    sd = math.sqrt(sum((v - mean) ** 2 for v in xs) / n) or 1.0
    thr = k * sd
    return [mean if abs(v - mean) > thr else v for v in xs]


def simulate(x_a, x_b, x_leak, snr, n, rng, with_leak=True, with_click=True):
    """Returns (rec_a, rec_b): what the two sensors would record."""
    source = band_noise(2 * n, rng)

    def record(x_sensor):
        if with_leak:
            dist = abs(x_leak - x_sensor)
            lag = dist / WAVE_SPEED * FS            # travel time
            gain = snr / (1.0 + 0.015 * dist)       # 1/r spreading
            comp = [v * gain for v in delay(source, lag)][:n]
        else:
            comp = [0.0] * n

        bg = [rng.gauss(0.0, 1.0) for _ in range(n)]                 # local noise
        hum = [0.3 * math.sin(2 * math.pi * 50 * i / FS) for i in range(n)]  # pump
        rec = [c + b + h for c, b, h in zip(comp, bg, hum)]

        if with_click:                                # valve slam, both hear it
            at = int(n * 0.72)
            rec[at] += 12.0
            rec[at + 1] += 7.0

        return reject_transients(rec)

    return record(x_a), record(x_b)


# ----------------------------------------------------------------- physics

def expected_gap(x_a, x_b, x_leak):
    """Time gap in samples between the two sensors hearing the leak."""
    return (x_a + x_b - 2.0 * x_leak) / WAVE_SPEED * FS


def estimate(x_a, x_b, lag_samples):
    """Turn the measured gap into a position along the pipe."""
    return 0.5 * (x_a + x_b - WAVE_SPEED * lag_samples / FS)


# ------------------------------------------------------------- correlation

def cross_correlate(a, b, max_lag):
    """
    Slide b over a and find the offset with the strongest match.
    Returns (lag_samples, confidence 0-1) where confidence is the
    normalised correlation coefficient at that offset.
    """
    n = min(len(a), len(b))
    best_lag, best = 0, -1.0
    for lag in range(-max_lag, max_lag + 1):
        i0, i1 = max(0, -lag), min(n, n - lag)
        if i1 - i0 < 40:
            continue
        num = 0.0
        ea = eb = 0.0
        for i in range(i0, i1):
            av, bv = a[i], b[i + lag]
            num += av * bv
            ea += av * av
            eb += bv * bv
        denom = math.sqrt(ea * eb)
        if denom <= 0:
            continue
        r = num / denom
        if r > best:
            best_lag, best = lag, r
    return best_lag, best


# ----------------------------------------------------------------- trials

def trial(rng, snr, n, x_a, x_b, x_leak, with_leak=True):
    rec_a, rec_b = simulate(x_a, x_b, x_leak, snr, n, rng, with_leak)
    max_lag = int((x_b - x_a) / WAVE_SPEED * FS) + 5   # physics gate
    lag, conf = cross_correlate(rec_a, rec_b, max_lag)
    return lag, conf, estimate(x_a, x_b, lag)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--trials", type=int, default=8)
    ap.add_argument("--snr", type=float, default=6.0,
                    help="leak strength relative to background noise")
    ap.add_argument("--spacing", type=float, default=100.0)
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--seconds", type=float, default=0.5)
    args = ap.parse_args()

    x_a = 100.0
    x_b = x_a + args.spacing
    n = int(FS * args.seconds)
    rng = random.Random(args.seed)

    print("=" * 72)
    print("LEAK LOCALISATION SIMULATION - sensors at "
          f"{x_a:.0f} m and {x_b:.0f} m, spacing {args.spacing:.0f} m")
    print(f"sound speed {WAVE_SPEED:.0f} m/s | sampling {FS} Hz "
          f"({FS / WAVE_SPEED * 100:.1f} cm per sample)")
    print(f"leak-to-background ratio {args.snr} | "
          f"{args.trials} trials, different leak position each time")
    print("=" * 72)
    print(f"{'true (m)':>9} {'gap expect':>11} {'gap found':>10} "
          f"{'estimate':>10} {'error':>8} {'conf':>7}")
    print("-" * 72)

    errs = []
    for i in range(args.trials):
        x_leak = x_a + args.spacing * (i + 1) / (args.trials + 1)
        lag, conf, est = trial(rng, args.snr, n, x_a, x_b, x_leak)
        err = est - x_leak
        errs.append(abs(err))
        print(f"{x_leak:9.1f} {expected_gap(x_a, x_b, x_leak):11.0f} "
              f"{lag:10d} {est:10.1f} {err:+8.1f} {conf:7.3f}")

    avg, worst = sum(errs) / len(errs), max(errs)
    print("-" * 72)
    print(f"AVERAGE ERROR {avg:.1f} m | WORST {worst:.1f} m "
          f"| limit = noise floor: {1 / FS * WAVE_SPEED:.1f} m per sample")
    print(f"VERDICT: {'PASS' if avg < args.spacing * 0.1 else 'FAIL'} "
          f"(target: under {args.spacing * 0.1:.0f} m average error)")
    print()

    # Control: no leak at all must NOT produce a confident match.
    _, conf_empty, _ = trial(rng, args.snr, n, x_a, x_b, x_a + 30, with_leak=False)
    print(f"CONTROL (no leak): confidence {conf_empty:.3f} -> "
          f"{'PASS - stays quiet' if conf_empty < 0.30 else 'FAIL - would false-alarm'}")

    # Leak outside the two sensors: position cannot be recovered.
    lag_out, conf_out, est_out = trial(rng, args.snr, n, x_a, x_b, x_b + 60)
    print(f"OUTSIDE CASE (leak at {x_b + 60:.0f} m, beyond sensor B): "
          f"confidence {conf_out:.3f}, estimate {est_out:.0f} m")
    print("  -> expected: low confidence, estimate pinned near the middle; "
          "this is why a real deployment uses three or more nodes.")


if __name__ == "__main__":
    main()