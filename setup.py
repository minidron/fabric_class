from setuptools import setup, find_packages


setup(
    name='fabric_class',
    version='0.0.0',
    author='Pavel Alekin',
    author_email='pavel.alekin@gmail.com',
    description='Fabric functions as class',
    long_description=open('README.md').read(),
    long_description_content_type='text/markdown',
    url='https://github.com/minidron/fabric_class',
    license='License :: OSI Approved :: MIT License',
    packages=find_packages(),
    include_package_data=True,
    keywords=['package', 'setup'],
    scripts=[],
    install_requires=[
        'Fabric3>=1.14.post1',
    ],
    zip_safe=False,
    python_requires=">=3.5",
    classifiers=[
        "Intended Audience :: Developers",
        "Operating System :: OS Independent",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3.5",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
    ],
)
