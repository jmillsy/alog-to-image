"""
ALOG to Image - Convert Artisan roaster .alog files to beautiful PNG visualizations.

This package provides tools to parse and visualize roast profiles from Artisan roaster software.
"""

__version__ = "1.0.0"

from .renderer import parse_alog, calculate_ror, render_alog

__all__ = ["parse_alog", "calculate_ror", "render_alog"]
