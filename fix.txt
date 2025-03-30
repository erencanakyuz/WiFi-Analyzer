import os
import re

def check_pyqt_imports():
    pyqt5_files = []
    pyqt6_files = []
    
    for root, dirs, files in os.walk("."):
        for file in files:
            if file.endswith(".py"):
                file_path = os.path.join(root, file)
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    try:
                        content = f.read()
                        if re.search(r'from PyQt5\.', content) or re.search(r'import PyQt5', content):
                            pyqt5_files.append(file_path)
                        if re.search(r'from PyQt6\.', content) or re.search(r'import PyQt6', content):
                            pyqt6_files.append(file_path)
                    except Exception as e:
                        print(f"Error reading {file_path}: {e}")
    
    return pyqt5_files, pyqt6_files

pyqt5_files, pyqt6_files = check_pyqt_imports()

print("Files with PyQt5 imports:")
for file in pyqt5_files:
    print(f"- {file}")

print("\nFiles with PyQt6 imports:")
for file in pyqt6_files:
    print(f"- {file}")

if pyqt5_files and pyqt6_files:
    print("\n⚠️ WARNING: Your project has mixed PyQt5 and PyQt6 imports, which could cause compatibility issues.")
elif pyqt5_files:
    print("\nYour project appears to be using PyQt5.")
elif pyqt6_files:
    print("\nYour project appears to be using PyQt6.")
else:
    print("\nNo PyQt imports found.")