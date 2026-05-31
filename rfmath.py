#!/usr/bin/env python3
import argparse
import math
import re
import sys
from dataclasses import dataclass

ABS_PATTERN = re.compile(r'^\s*([+-]?(?:\d+(?:\.\d*)?|\.\d+))\s*([A-Za-zµ]+)\s*$')
REL_PATTERN = re.compile(r'^\s*([+-]?(?:\d+(?:\.\d*)?|\.\d+))\s*(db)\s*$', re.IGNORECASE)
GAIN_PATTERN = re.compile(r'^\s*([+-]?(?:\d+(?:\.\d*)?|\.\d+))\s*(dbi)\s*$', re.IGNORECASE)
FREQ_PATTERN = re.compile(r'^\s*([+-]?(?:\d+(?:\.\d*)?|\.\d+))\s*(mhz|ghz)\s*$', re.IGNORECASE)
DIST_PATTERN = re.compile(r'^\s*([+-]?(?:\d+(?:\.\d*)?|\.\d+))\s*(m|km)\s*$', re.IGNORECASE)

LINEAR_UNITS_TO_WATTS = {
    "uw": 1e-6,
    "µw": 1e-6,
    "mw": 1e-3,
    "w": 1.0,
    "kw": 1e3,
    "MW": 1e6,
    "GW": 1e9,
}


@dataclass
class AbsolutePower:
    value: float
    unit: str

    def to_watts(self) -> float:
        ul = self.unit.lower()
        if ul == "dbm":
            return 10.0 ** ((self.value - 30.0) / 10.0)
        if ul == "dbw":
            return 10.0 ** (self.value / 10.0)
        if self.unit in LINEAR_UNITS_TO_WATTS:
            watts = self.value * LINEAR_UNITS_TO_WATTS[self.unit]
        elif ul in LINEAR_UNITS_TO_WATTS:
            watts = self.value * LINEAR_UNITS_TO_WATTS[ul]
        else:
            raise ValueError(f"Unsupported absolute unit: {self.unit}")
        if watts <= 0:
            raise ValueError(f"{self.unit} value must be greater than 0.")
        return watts

    def to_dbm(self) -> float:
        watts = self.to_watts()
        return 10.0 * math.log10(watts * 1000.0)


@dataclass
class RelativeValue:
    value: float
    unit: str


@dataclass
class AntennaGain:
    value: float
    unit: str


@dataclass
class Frequency:
    value: float
    unit: str

    def to_mhz(self) -> float:
        u = self.unit.lower()
        if self.value <= 0:
            raise ValueError("Frequency must be greater than 0.")
        if u == "mhz":
            return self.value
        if u == "ghz":
            return self.value * 1000.0
        raise ValueError(f"Unsupported frequency unit: {self.unit}")


@dataclass
class Distance:
    value: float
    unit: str

    def to_km(self) -> float:
        u = self.unit.lower()
        if self.value <= 0:
            raise ValueError("Distance must be greater than 0.")
        if u == "km":
            return self.value
        if u == "m":
            return self.value / 1000.0
        raise ValueError(f"Unsupported distance unit: {self.unit}")


def parse_absolute(token: str) -> AbsolutePower:
    m = ABS_PATTERN.match(token)
    if not m:
        raise argparse.ArgumentTypeError(
            f"Invalid absolute power value '{token}'. Supported units: uW, µW, mW, W, kW, MW, GW, dBm, dBW."
        )
    value = float(m.group(1))
    unit = m.group(2)
    ul = unit.lower()

    if ul in {"dbm", "dbw"}:
        canonical_unit = ul
    elif unit in LINEAR_UNITS_TO_WATTS:
        canonical_unit = unit
    elif ul in {"uw", "µw", "mw", "w", "kw"}:
        canonical_unit = ul
    else:
        raise argparse.ArgumentTypeError(
            f"Unsupported unit in '{token}'. Supported absolute units: uW, µW, mW, W, kW, MW, GW, dBm, dBW."
        )
    return AbsolutePower(value=value, unit=canonical_unit)


def parse_relative(token: str) -> RelativeValue:
    m = REL_PATTERN.match(token)
    if not m:
        raise argparse.ArgumentTypeError(
            f"Invalid relative value '{token}'. Use dB, e.g. +3dB or -1.5dB."
        )
    return RelativeValue(value=float(m.group(1)), unit=m.group(2))


def parse_gain(token: str) -> AntennaGain:
    m = GAIN_PATTERN.match(token)
    if not m:
        raise argparse.ArgumentTypeError(
            f"Invalid antenna gain '{token}'. Use dBi, e.g. 6dBi."
        )
    return AntennaGain(value=float(m.group(1)), unit=m.group(2))


def parse_frequency(token: str) -> Frequency:
    m = FREQ_PATTERN.match(token)
    if not m:
        raise argparse.ArgumentTypeError(
            f"Invalid frequency '{token}'. Use MHz or GHz, e.g. 2400MHz or 5.8GHz."
        )
    return Frequency(value=float(m.group(1)), unit=m.group(2))


def parse_distance(token: str) -> Distance:
    m = DIST_PATTERN.match(token)
    if not m:
        raise argparse.ArgumentTypeError(
            f"Invalid distance '{token}'. Use m or km, e.g. 500m or 5km."
        )
    return Distance(value=float(m.group(1)), unit=m.group(2))


def dbm_to_w(dbm: float) -> float:
    return 10.0 ** ((dbm - 30.0) / 10.0)


def dbm_to_mw(dbm: float) -> float:
    return 10.0 ** (dbm / 10.0)


def dbm_to_dbw(dbm: float) -> float:
    return dbm - 30.0


def fspl_db(freq_mhz: float, distance_km: float) -> float:
    if freq_mhz <= 0:
        raise ValueError("Frequency must be greater than 0.")
    if distance_km <= 0:
        raise ValueError("Distance must be greater than 0.")
    return 32.44 + 20.0 * math.log10(freq_mhz) + 20.0 * math.log10(distance_km)


def format_number(value: float) -> str:
    if value == 0:
        return "0"
    return f"{value:.15f}".rstrip("0").rstrip(".")


def print_power_block(dbm: float, title: str | None = None) -> None:
    if title:
        print(title)
    print(f"dBm: {format_number(dbm)}")
    print(f"dBW: {format_number(dbm_to_dbw(dbm))}")
    print(f"W:   {format_number(dbm_to_w(dbm))}")
    print(f"mW:  {format_number(dbm_to_mw(dbm))}")


def cmd_power(args: argparse.Namespace) -> int:
    dbm = args.input_value.to_dbm()
    print_power_block(dbm, title="Power conversion")
    return 0


def cmd_gain(args: argparse.Namespace) -> int:
    if not args.adjustments:
        raise ValueError("Provide at least one dB adjustment.")
    start_dbm = args.input_value.to_dbm()
    total_db = sum(adj.value for adj in args.adjustments)
    result_dbm = start_dbm + total_db

    print("Gain/loss calculation")
    print(f"Input:       {format_number(start_dbm)} dBm")
    print(f"Adjustment:  {format_number(total_db)} dB")
    print(f"Output:      {format_number(result_dbm)} dBm")
    print()
    print_power_block(result_dbm)
    return 0


def cmd_eirp(args: argparse.Namespace) -> int:
    tx_dbm = args.tx.to_dbm()
    gain_dbi = args.gain.value
    loss_db = args.loss.value if args.loss else 0.0
    eirp_dbm = tx_dbm + gain_dbi - loss_db

    print("EIRP calculation")
    print(f"Tx power:      {format_number(tx_dbm)} dBm")
    print(f"Antenna gain:  {format_number(gain_dbi)} dBi")
    print(f"Cable loss:    {format_number(loss_db)} dB")
    print(f"EIRP:          {format_number(eirp_dbm)} dBm")
    print()
    print_power_block(eirp_dbm)
    return 0


def cmd_link_budget(args: argparse.Namespace) -> int:
    tx_dbm = args.tx.to_dbm()
    tx_gain_dbi = args.tx_gain.value
    tx_loss_db = args.tx_loss.value if args.tx_loss else 0.0
    rx_gain_dbi = args.rx_gain.value
    rx_loss_db = args.rx_loss.value if args.rx_loss else 0.0
    misc_loss_db = args.misc_loss.value if args.misc_loss else 0.0
    freq_mhz = args.freq.to_mhz()
    distance_km = args.distance.to_km()

    eirp_dbm = tx_dbm + tx_gain_dbi - tx_loss_db
    path_loss_db = fspl_db(freq_mhz, distance_km)
    rx_dbm = eirp_dbm - path_loss_db + rx_gain_dbi - rx_loss_db - misc_loss_db

    print("Link budget calculation")
    print(f"Tx power:        {format_number(tx_dbm)} dBm")
    print(f"Tx antenna gain: {format_number(tx_gain_dbi)} dBi")
    print(f"Tx loss:         {format_number(tx_loss_db)} dB")
    print(f"EIRP:            {format_number(eirp_dbm)} dBm")
    print(f"Frequency:       {format_number(freq_mhz)} MHz")
    print(f"Distance:        {format_number(distance_km)} km")
    print(f"FSPL:            {format_number(path_loss_db)} dB")
    print(f"Rx antenna gain: {format_number(rx_gain_dbi)} dBi")
    print(f"Rx loss:         {format_number(rx_loss_db)} dB")
    print(f"Misc loss:       {format_number(misc_loss_db)} dB")
    print(f"Received power:  {format_number(rx_dbm)} dBm")

    if args.rx_sensitivity is not None:
        sensitivity_dbm = args.rx_sensitivity.to_dbm()
        margin_db = rx_dbm - sensitivity_dbm
        print(f"Rx sensitivity:  {format_number(sensitivity_dbm)} dBm")
        print(f"Link margin:     {format_number(margin_db)} dB")

    print()
    print("Received power summary")
    print(f"dBm: {format_number(rx_dbm)}")
    print(f"dBW: {format_number(dbm_to_dbw(rx_dbm))}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="rfmath",
        description="RF Math CLI: power conversions, gain/loss math, EIRP, and link budget calculations."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    power_parser = subparsers.add_parser("power", help="Convert between linear power units and dBW/dBm.")
    power_parser.add_argument("input_value", type=parse_absolute, help="Absolute power, e.g. 10W, 100mW, 500uW, 2kW, 30dBm, 0dBW")
    power_parser.set_defaults(func=cmd_power)

    gain_parser = subparsers.add_parser("gain", help="Apply one or more dB gain/loss adjustments to an absolute power value.")
    gain_parser.add_argument("input_value", type=parse_absolute, help="Absolute power, e.g. 20dBm, 0.1W, 500uW, 2kW")
    gain_parser.add_argument("adjustments", type=parse_relative, nargs=argparse.REMAINDER, help="Relative dB adjustments, e.g. +3dB -1.5dB")
    gain_parser.set_defaults(func=cmd_gain)

    eirp_parser = subparsers.add_parser("eirp", help="Calculate EIRP from transmitter power, antenna gain, and cable loss.")
    eirp_parser.add_argument("--tx", required=True, type=parse_absolute, help="Transmit power, e.g. 20dBm, 100mW, 1W, 500uW, 2kW")
    eirp_parser.add_argument("--gain", required=True, type=parse_gain, help="Antenna gain, e.g. 6dBi")
    eirp_parser.add_argument("--loss", required=False, type=parse_relative, default=RelativeValue(0.0, "dB"), help="Cable/system loss, e.g. 2dB (default: 0dB)")
    eirp_parser.set_defaults(func=cmd_eirp)

    link_parser = subparsers.add_parser("link-budget", help="Calculate EIRP, FSPL, received power, and optional link margin.")
    link_parser.add_argument("--tx", required=True, type=parse_absolute, help="Transmit power, e.g. 20dBm, 100mW, 1W")
    link_parser.add_argument("--tx-gain", required=True, type=parse_gain, help="Tx antenna gain, e.g. 6dBi")
    link_parser.add_argument("--tx-loss", required=False, type=parse_relative, default=RelativeValue(0.0, "dB"), help="Tx-side loss, e.g. 2dB (default: 0dB)")
    link_parser.add_argument("--freq", required=True, type=parse_frequency, help="Frequency, e.g. 2400MHz or 5.8GHz")
    link_parser.add_argument("--distance", required=True, type=parse_distance, help="Distance, e.g. 500m or 5km")
    link_parser.add_argument("--rx-gain", required=True, type=parse_gain, help="Rx antenna gain, e.g. 6dBi")
    link_parser.add_argument("--rx-loss", required=False, type=parse_relative, default=RelativeValue(0.0, "dB"), help="Rx-side loss, e.g. 2dB (default: 0dB)")
    link_parser.add_argument("--misc-loss", required=False, type=parse_relative, default=RelativeValue(0.0, "dB"), help="Additional propagation/system loss, e.g. 1dB (default: 0dB)")
    link_parser.add_argument("--rx-sensitivity", required=False, type=parse_absolute, help="Receiver sensitivity, typically in dBm, e.g. -75dBm")
    link_parser.set_defaults(func=cmd_link_budget)

    return parser


def main(argv=None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except ValueError as exc:
        parser.error(str(exc))
        return 2


if __name__ == "__main__":
    sys.exit(main())
