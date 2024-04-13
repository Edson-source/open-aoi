from setuptools import setup

package_name = "open_aoi_ros_services"
setup(
    name=package_name,
    version="0.0.1",
    license="MIT License",
    packages=[package_name],
    data_files=[
        ("share/" + package_name, ["package.xml"]),
        ("share/ament_index/resource_index/packages", ["resource/" + package_name]),
    ],
    install_requires=["setuptools"],
    zip_safe=True,
    maintainer="Cherniaev Egor",
    maintainer_email="chrnyaevek@gmail.com",
    entry_points={
        "console_scripts": [
            f"aoi_image_acquisition = {package_name}.service_image_acquisition:main",
            f"aoi_identification = {package_name}.service_identification:main"
        ],
    },
)
