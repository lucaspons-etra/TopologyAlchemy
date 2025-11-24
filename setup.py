"""
Topology Alchemy - Electrical Grid Topology Conversion Toolkit

A flexible and powerful toolkit for converting, manipulating, and exchanging
electrical grid topology data between multiple formats. Developed as part of
the EU Horizon 2020 OPENTUNITY research project.
"""

from setuptools import setup, find_packages
from pathlib import Path

# Read the README file
this_directory = Path(__file__).parent
long_description = (this_directory / "README.md").read_text(encoding='utf-8')

# Read requirements
requirements = []
with open('requirements.txt', 'r', encoding='utf-8') as f:
    for line in f:
        line = line.strip()
        # Skip empty lines, comments, and private repository dependencies
        if line and not line.startswith('#') and not line.startswith('git+ssh://'):
            requirements.append(line)

setup(
    name='topology-alchemy',
    version='1.0.0',
    author='OPENTUNITY Consortium',
    author_email='info@opentunity.eu',
    description='Electrical grid topology data conversion toolkit',
    long_description=long_description,
    long_description_content_type='text/markdown',
    url='https://github.com/lucaspons-etra/TopologyAlchemy',
    project_urls={
        'Bug Tracker': 'https://github.com/lucaspons-etra/TopologyAlchemy/issues',
        'Documentation': 'https://github.com/lucaspons-etra/TopologyAlchemy/wiki',
        'Source Code': 'https://github.com/lucaspons-etra/TopologyAlchemy',
        'OPENTUNITY Project': 'https://opentunity.eu',
    },
    packages=find_packages(where='src'),
    package_dir={'': 'src'},
    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: Science/Research',
        'Intended Audience :: Developers',
        'Topic :: Scientific/Engineering',
        'Topic :: Software Development :: Libraries :: Python Modules',
        'License :: OSI Approved :: Apache Software License',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
        'Programming Language :: Python :: 3.11',
        'Operating System :: OS Independent',
    ],
    python_requires='>=3.8',
    install_requires=requirements,
    extras_require={
        'dev': [
            'pytest>=7.0.0',
            'pytest-cov>=3.0.0',
            'pytest-asyncio>=0.18.0',
            'black>=22.0.0',
            'flake8>=4.0.0',
            'mypy>=0.950',
        ],
    },
    entry_points={
        'console_scripts': [
            'topology-alchemy=main:main',
        ],
    },
    include_package_data=True,
    package_data={
        '': ['*.js', '*.json', '*.xml'],
    },
    keywords=[
        'power-systems',
        'grid-topology',
        'electrical-engineering',
        'data-conversion',
        'interoperability',
        'pandapower',
        'powsybl',
        'cgmes',
        'cim',
    ],
    zip_safe=False,
)
