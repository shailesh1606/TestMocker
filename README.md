# Python Desktop CBT Application

This project is a Python desktop application designed for conducting computer-based tests (CBTs). It allows users to scan question papers and answer keys, take timed tests, and upload question papers and answer keys directly as PDFs.

## Features

- **Scan Question Papers**: Users can scan physical question papers and answer keys using a scanner device.
- **Timed Tests**: The application provides a timed interface for taking tests, ensuring that users can manage their time effectively.
- **PDF Uploads**: Users can upload question papers and answer keys in PDF format directly into the application.

## Project Structure

```
python-desktop-cbt-app
├── src
│   ├── main.py               # Entry point of the application
│   ├── ui
│   │   ├── main_window.py    # Main user interface management
│   │   └── test_window.py     # Test interface management
│   ├── scanner
│   │   └── pdf_scanner.py    # Scanning functionality
│   ├── tests
│   │   └── test_timer.py      # Unit tests for timer functionality
│   ├── utils
│   │   └── file_utils.py      # Utility functions for file operations
│   └── data
│       └── __init__.py        # Data package initializer
├── requirements.txt           # Project dependencies
├── README.md                  # Project documentation
└── setup.py                   # Packaging configuration
```

## Installation

1. Clone the repository:
   ```
   git clone <repository-url>
   cd python-desktop-cbt-app
   ```

2. Install the required dependencies:
   ```
   pip install -r requirements.txt
   ```

## Usage

1. Run the application:
   ```
   python src/main.py
   ```

2. Use the main interface to scan question papers or upload PDFs.

3. Navigate to the test interface to take a timed test.

## Contributing

Contributions are welcome! Please open an issue or submit a pull request for any enhancements or bug fixes.

## License

This project is licensed under the MIT License. See the LICENSE file for more details.