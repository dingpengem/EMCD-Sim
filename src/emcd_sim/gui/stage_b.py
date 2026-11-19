"""Compatibility imports for the former Stage B control module.

New application code uses calculation_controls and calculation_worker. The
historical StageB class and EMCDWorker imports remain valid; this module owns
no widgets or numerical implementation.
"""
from .calculation_controls import CalculationControls
from .calculation_worker import EMCDWorker, calculate, calculate_multisite

StageB = CalculationControls
