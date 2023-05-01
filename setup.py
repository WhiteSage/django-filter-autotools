import setuptools

with open("README.md", "r") as fh:
    readme = fh.read()

setuptools.setup(
    name="django-filter-autotools", 
    version="0.0.3", 
    description=(
        "Provides some mixins which allow automatic generation of filtersets with"
        "a list of lookups, including new lookups not registered into Django."
    ),
    author="Carlos Pastor",
    long_description=readme,
    long_description_content_type="text/markdown",
    packages=setuptools.find_packages(), 
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],  
    python_requires='>=3.6', 
    license="MIT",
    install_requires=[
        "django-filter>=21.1",
    ],
)