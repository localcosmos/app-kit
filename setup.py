from setuptools import setup, find_packages

with open("README.md", "r") as fh:
    long_description = fh.read()

install_requires = [
    'localcosmos-server==0.24.8',
    'localcosmos-cordova-builder==0.9.6',
    'django-tenants==3.7.0',
    'django-cleanup==9.0.0',
    'django-ipware==7.0.1',
    'django-filter==24.3',
    'lxml',
    'openpyxl==3.1.5',
    'deepl',
    'opencv-python',
    'opencv-python-headless',
    'unidecode',
]

setup(
    name='localcosmos_app_kit',
    version='0.9.10',
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
