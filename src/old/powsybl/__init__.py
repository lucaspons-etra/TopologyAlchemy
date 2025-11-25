"""PowerSyBl converter package.

This package contains importers and exporters for PowerSyBl format power system data.
"""

# Conservative approach - only expose when dependencies are available
__all__ = []

def get_powsybl_converters():
    """Get PowerSyBl converters if dependencies are available."""
    try:
        from . import powsyblImporter, powSyBlExporter
        return {'powsyblImporter': powsyblImporter, 'powSyBlExporter': powSyBlExporter}
    except ImportError as e:
        print(f"Warning: PowerSyBl converters not available due to missing dependencies: {e}")
        return None