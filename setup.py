from setuptools import setup, find_packages

with open("README.md", "r") as fh:
    long_description = fh.read()

install_requires = [
    'localcosmos-server',
    'localcosmos-cordova-builder',
    'localcosmos-app-kit-taxonomy',
    'django-tenants==3.4.7',
    'django-cleanup==6.0.0',
    'django-ipware==4.0.2',
    'django-filter==22.1',
    'lxml',
    'xlrd==2.0.1',
    'openpyxl==3.0.10',
    'deepl',
    'opencv-python',
    'opencv-python-headless',
    'unidecode',
]

setup(
    name='localcosmos_app_kit',
    version='0.3.3',
    description='LocalCosmos App Kit. Web Portal to build Android and iOS apps',
    long_description=long_description,
    long_description_content_type="text/markdown",
    license='The MIT License',
    platforms=['OS Independent'],
    keywords='django, localcosmos, localcosmos server, biodiversity',
    author='Thomas Uher',
    author_email='thomas.uher@sisol-systems.com',
    url='https://github.com/localcosmos/app-kit',
    packages=find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires='>=3.8',
    include_package_data=True,
    install_requires=install_requires,
)
