#!/bin/bash

# Script to set up the RAG service dependencies

echo "Setting up RAG service dependencies..."

# Install Python dependencies
pip install -r requirements.txt

# Install additional dependencies for docling
pip install docling==0.4.3 pytesseract pillow

# Check if tesseract is installed
if ! command -v tesseract &> /dev/null; then
    echo "Tesseract OCR is not installed. Installing..."
    
    # Check the operating system
    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        # Linux
        sudo apt-get update
        sudo apt-get install -y tesseract-ocr
    elif [[ "$OSTYPE" == "darwin"* ]]; then
        # macOS
        brew install tesseract
    else
        echo "Unsupported operating system. Please install Tesseract OCR manually."
        echo "Visit: https://github.com/tesseract-ocr/tesseract"
    fi
else
    echo "Tesseract OCR is already installed."
fi

# Create necessary directories
mkdir -p data/test_files

echo "Setup complete! You can now use the RAG service."
echo "Try running the example: python app/examples/docling_test.py" 