from setuptools import setup, find_packages

setup(
    name='python-desktop-cbt-app',
    version='0.1',
    author='Your Name',
    author_email='your.email@example.com',
    description='A desktop application for computer-based testing with PDF scanning and uploading capabilities.',
    packages=find_packages(where='src'),
    package_dir={'': 'src'},
    install_requires=[
        'PyQt5',  # GUI framework
        'PyPDF2',  # PDF handling
        'opencv-python',  # For scanning functionality
        'Pillow',  # Image processing
        'pytest'  # Testing framework
    ],
    entry_points={
        'console_scripts': [
            'cbt-app=main:main',  # Adjust according to your main function
        ],
    },
)