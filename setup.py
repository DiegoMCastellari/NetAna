from setuptools import setup, find_packages
import codecs
import os

here = os.path.abspath(os.path.dirname(__file__))

# Setting up
setup(
    name="netana",
    version='0.0.1',
    author="Diego M Castellari",
    author_email="<diegomcastellari@gmail.com>",
    description='NetAna - Network Analysis Package',
    long_description_content_type="text/markdown",
    packages=find_packages(),
    install_requires=[
        'numpy==1.25.1',
        'pandas==2.0.3',
        'geopandas==0.13.2',
        'networkx==3.1',
        'momepy==0.6.0',
        'matplotlib==3.7.2'
        ],
    keywords=['python', 'geometric', 'network', 'analysis', 'service', 'networkx'],
    classifiers=[
        "Development Status :: 1 - Planning",
        "Intended Audience :: Developers",
        "Programming Language :: Python :: 3",
        "Operating System :: Microsoft :: Windows"
    ]
)