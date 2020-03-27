from setuptools import setup, find_packages


setup(
    name='oroi-scrape',
    version='0.1',
    author='Amy Guy',
    author_email='amy.guy@opendataservices.coop',
    url='https://github.com/opendataservices/oroi-scrape',
    license='MIT',
    classifiers=[],
    keywords='',
    packages=find_packages('src'),
    package_dir={'': 'src'},
    namespace_packages=[],
    include_package_data=True,
    zip_safe=False,
    install_requires=[
        'memorious >= 1.5.4',
        'datafreeze'
    ],
    entry_points={
        'memorious.plugins': [
            # 'example = example:init'
        ]
    }
)