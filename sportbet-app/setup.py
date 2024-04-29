from setuptools import find_packages, setup

setup(
    name="sportbet",
    version="1.0.0",
    packages=find_packages(),
    include_package_data=True,
    zip_safe=False,
    install_requires=[
        "click",
        "requests",
        # "json",
        "jsonschema",
        "flask",
        "flask-caching",
        "flask-restful",
        "flask-sqlalchemy",
        "rfc3339-validator",
        "SQLAlchemy",
    ]
)