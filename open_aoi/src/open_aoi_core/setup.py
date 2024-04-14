from setuptools import setup

package_name = "open_aoi_core"
setup(
    name=package_name,
    version="0.0.1",
    license="MIT License",
    packages=[
        package_name,
        f"{package_name}/controllers",
        f"{package_name}/mixins",
        f"{package_name}/defaults",
        f"{package_name}/tests",
    ],
    data_files=[
        ("share/" + package_name, ["package.xml"]),
        ("share/ament_index/resource_index/packages", ["resource/" + package_name]),
    ],
    install_requires=["setuptools"],
    zip_safe=True,
    maintainer="Cherniaev Egor",
    maintainer_email="chrnyaevek@gmail.com",
)
