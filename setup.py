import setuptools
import os


version = os.environ.get("PACKAGE_VERSION", "0.0.0")  # fallback if not set

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name = 'nsepython',
    packages=setuptools.find_packages(),
    version = version,
    license='GNU',
    include_package_data=True,
    description = 'Python library for NSE India APIs',
    long_description=long_description,
    long_description_content_type="text/markdown",  author = 'Aeron7',
    author_email = 'dexter@unofficed.com',
    url = 'https://github.com/aeron7/nsepython',
    install_requires=['requests', 'pandas','scipy'],
    keywords = ['nseindia', 'nse', 'python', 'sdk', 'trading', 'stock markets'],
    classifiers=[
      'Intended Audience :: Developers',
      'Natural Language :: English',
      'Operating System :: OS Independent',
      'Programming Language :: Python',
      'Programming Language :: Python :: 3',
      'Programming Language :: Python :: Implementation :: PyPy',
      'Topic :: Software Development :: Libraries :: Python Modules'
    ],
)
