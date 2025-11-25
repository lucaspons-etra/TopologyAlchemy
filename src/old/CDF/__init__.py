"""CDF (Common Data Format) converter package.

This package contains importers and exporters for CDF format power system data.
Requires netCDF4 dependency.
"""

# Conservative approach - only expose when dependencies are available
__all__ = []

def get_cdf_converters():
    """Get CDF converters if dependencies are available."""
    try:
        from . import cdfImporter, cdfExporter
        return {'cdfImporter': cdfImporter, 'cdfExporter': cdfExporter}
    except ImportError as e:
        print(f"Warning: CDF converters not available due to missing dependencies: {e}")
        return None