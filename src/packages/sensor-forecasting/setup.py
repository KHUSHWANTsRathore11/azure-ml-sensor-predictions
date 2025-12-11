from setuptools import setup, find_packages
import os

# Read version from version.py
version_file = os.path.join(os.path.dirname(__file__), 'version.py')
with open(version_file) as f:
    exec(f.read())

setup(
    name='sensor-forecasting',
    version=__version__,
    description='Custom TensorFlow models and utilities for sensor time series forecasting',
    author='Your Team',
    packages=find_packages(),
    install_requires=[
        'tensorflow==2.13.0',
        'numpy>=1.23.0',
        'pandas>=2.0.0',
        'scikit-learn>=1.3.0',
    ],
    python_requires='>=3.9',
    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'Programming Language :: Python :: 3.9',
    ],
)
