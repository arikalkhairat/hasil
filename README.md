# QR Code Watermarking Tool

## Overview
The QR Code Watermarking Tool is a powerful application that uses LSB (Least Significant Bit) steganography to embed QR code watermarks into DOCX documents. This tool provides a secure way to protect document authenticity through invisible watermarks that can be verified later.

![QR Code Watermarking Tool](static/img/screenshot.png)

## Features

- **QR Code Generation**: Create custom QR codes with your data
- **Watermark Embedding**: Invisibly embed QR codes into DOCX document images
- **Document Validation**: Extract and verify hidden QR code watermarks
- **Detailed Process Visualization**: See the entire steganography process in detail
- **Quality Analysis**: Calculate MSE and PSNR metrics to evaluate image quality
- **Modern Web Interface**: User-friendly interface with responsive design

## How It Works

The tool uses LSB (Least Significant Bit) steganography to hide QR code data within the blue channel of images in DOCX documents. This technique modifies only the least significant bit of each pixel, making the changes imperceptible to the human eye while preserving the ability to extract the data later.

### Process Steps:

1. **Image Analysis**: Assesses the carrier image to determine capacity
2. **QR Preparation**: Prepares and potentially resizes the QR code
3. **Header Creation**: Generates header information (dimensions)
4. **LSB Embedding**: Embeds data in the LSB of the blue channel
5. **Quality Analysis**: Calculates MSE and PSNR metrics

## Installation

### Prerequisites
- Python 3.8 or higher
- pip (Python package manager)

### Option 1: Using the Installer (Windows)

1. Download and run the `install.bat` file
2. The installer will:
   - Create a virtual environment
   - Install required dependencies
   - Set up the application

### Option 2: Manual Installation

```bash
# Clone the repository or download the source code
git clone https://github.com/yourusername/qr-watermarking-tool.git
cd qr-watermarking-tool

# Create a virtual environment
python -m venv venv

# Activate the virtual environment
# On Windows:
venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

## Usage

### Starting the Application

Run the application with:

```bash
# Activate the virtual environment (if not already activated)
# On Windows:
venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate

# Start the application
python app.py
```

The application will start and be accessible at [http://localhost:5000](http://localhost:5000) in your web browser.

### Using the Web Interface

The application has three main functions:

1. **Generate QR Code**:
   - Enter your data
   - Click "Generate QR Code"
   - Download the generated QR code

2. **Embed Watermark**:
   - Select a DOCX document
   - Select a QR code image
   - Click "Embed Watermark"
   - Download the watermarked document

3. **Validate Document**:
   - Select a DOCX document
   - Click "Validate Document"
   - View extracted QR codes (if any)

## Technical Details

### LSB Steganography

This tool implements LSB (Least Significant Bit) steganography, which works by replacing the least significant bit of each color channel with a bit of the data to be hidden. Since the least significant bit has the smallest impact on the color value, changes are virtually imperceptible to the human eye.

The implementation:
- Uses only the blue channel (less sensitive to the human eye)
- Includes dimension information in the header
- Automatically resizes QR codes if necessary to fit image capacity
- Calculates quality metrics (MSE, PSNR) to quantify the impact

### Image Quality Metrics

- **MSE (Mean Squared Error)**: Measures the average squared difference between the original and watermarked images.
- **PSNR (Peak Signal-to-Noise Ratio)**: Measures the ratio between the maximum possible power of a signal and the power of corrupting noise.
  - PSNR > 40 dB: Excellent quality
  - PSNR > 30 dB: Very good quality
  - PSNR > 20 dB: Good quality
  - PSNR < 20 dB: Poor quality

## Troubleshooting

### Common Issues

- **No images found**: Ensure your DOCX document contains images
- **Error during extraction**: The document may not contain watermarked images
- **Low PSNR values**: Image quality may be too low for effective watermarking

### Support

For issues or questions, please open an issue on the GitHub repository or contact the developer at your.email@example.com.

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgements

- Created by Arikal Sayangg
- Built with Python, Flask, and modern web technologies
- Uses LSB steganography techniques for secure watermarking 
